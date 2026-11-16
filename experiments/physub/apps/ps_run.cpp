// Runner: seeds one ancestor at the center and prints interval statistics as TSV.
// Usage: ps_run [key=value ...]  (keys: see apply())

#include "ps_core.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <map>
#include <memory>
#include <string>

using namespace ps;

namespace {

struct RunOpts {
  uint64_t ticks = 20000;
  uint64_t interval = 2000;
  std::string anc = "copier";
  std::string rival = "none";
  std::string frames;          // binary replay for viewer/index.html; empty = off
  uint64_t every = 50;         // ticks between frames
};

// Replay format (little-endian), read by viewer/index.html:
//   header: "PSV1", u16 width, u16 height, u16 site_len, u16 act_cap
//   frame:  u64 tick, u32 active, u32 births(total), u32 free, u32 code, u32 wall, u32 energy,
//           then per site arrays: code[n*len] u8, act[n] u8, ip[n] u8 (255 = none),
//           free[n] u16, energy[n] u16, wall[n*4] u8, lineage[n] u16
class FrameWriter {
public:
  explicit FrameWriter(const std::string& path, const Config& c) : out_(path, std::ios::binary) {
    out_.write("PSV1", 4);
    for (int v : {c.width, c.height, c.site_len, c.act_cap}) put<uint16_t>(v);
  }
  bool ok() const { return static_cast<bool>(out_); }
  void write(const World& w) {
    const Config& c = w.config();
    const int32_t n = c.width * c.height;
    const Ledger l = w.ledger();
    put<uint64_t>(w.tick());
    put<uint32_t>(w.active_count());
    put<uint32_t>(w.stats().births);
    for (int64_t v : {l.free_mass, l.code_mass, l.wall_mass, l.energy}) put<uint32_t>(v);
    for (int32_t s = 0; s < n; ++s) out_.write(reinterpret_cast<const char*>(w.bytes_at(s)), c.site_len);
    for (int32_t s = 0; s < n; ++s) put<uint8_t>(w.site_active(s) ? 1 : 0);
    for (int32_t s = 0; s < n; ++s) put<uint8_t>(w.first_ip(s) < 0 ? kNoIp : w.first_ip(s));
    for (int32_t s = 0; s < n; ++s) put<uint16_t>(std::min<int32_t>(w.free_mass(s), kU16Max));
    for (int32_t s = 0; s < n; ++s) put<uint16_t>(std::min<int32_t>(w.energy_at(s), kU16Max));
    for (int32_t s = 0; s < n; ++s) {
      for (uint8_t d = 0; d < kDirs; ++d) put<uint8_t>(w.wall_units(s, d));
    }
    for (int32_t s = 0; s < n; ++s) put<uint16_t>(w.lineage(s));
  }

private:
  static constexpr int kNoIp = 255;
  static constexpr int32_t kU16Max = 65535;
  std::ofstream out_;
  template <typename T> void put(int64_t v) {
    const T x = static_cast<T>(v);
    out_.write(reinterpret_cast<const char*>(&x), sizeof(T));
  }
};

const std::vector<uint8_t>* program_named(const std::string& name) {
  if (name == "copier") return &ancestor();
  if (name == "polite") return &polite();
  return nullptr;
}

bool apply(Config& c, RunOpts& r, const std::string& k, const std::string& v) {
  const long long n = std::atoll(v.c_str());
  const double x = std::atof(v.c_str());
  if (k == "ticks") r.ticks = n;
  else if (k == "interval") r.interval = n;
  else if (k == "width") c.width = static_cast<int>(n);
  else if (k == "height") c.height = static_cast<int>(n);
  else if (k == "site_len") c.site_len = static_cast<int>(n);
  else if (k == "mass0") c.mass0 = static_cast<int32_t>(n);
  else if (k == "d_div") c.d_div = static_cast<int32_t>(n);
  else if (k == "e0") c.e0 = static_cast<int32_t>(n);
  else if (k == "e_in") c.e_in = static_cast<int32_t>(n);
  else if (k == "e_max") c.e_max = static_cast<int32_t>(n);
  else if (k == "e_basal") c.e_basal = static_cast<int32_t>(n);
  else if (k == "e_op") c.e_op = static_cast<int32_t>(n);
  else if (k == "e_bond") c.e_bond = static_cast<int32_t>(n);
  else if (k == "e_ignite") c.e_ignite = static_cast<int32_t>(n);
  else if (k == "e_div") c.e_div = static_cast<int32_t>(n);
  else if (k == "e_act") c.e_act = static_cast<int32_t>(n);
  else if (k == "e_diffuse") c.e_diffuse = n != 0;
  else if (k == "bond_store") c.bond_store = n != 0;
  else if (k == "e_wall") c.e_wall = static_cast<int32_t>(n);
  else if (k == "p_mut") c.p_mut = x;
  else if (k == "p_hydro") c.p_hydro = x;
  else if (k == "p_dead") c.p_dead = x;
  else if (k == "p_erode") c.p_erode = x;
  else if (k == "seed") c.seed = static_cast<uint64_t>(n);
  else if (k == "act_cap") c.act_cap = static_cast<int>(n);
  else if (k == "stall_fail") c.stall_fail = n != 0;
  else if (k == "w_max") c.w_max = static_cast<uint8_t>(n);
  else if (k == "e_erase") c.e_erase = static_cast<int32_t>(n);
  else if (k == "ext_write") return parse_ext_write(v, c.ext_write);
  else if (k == "anc") r.anc = v;
  else if (k == "frames") r.frames = v;
  else if (k == "every") r.every = std::max<long long>(n, 1);
  else if (k == "rival") r.rival = v;
  else return false;
  return true;
}

void print_header() {
  std::cout << "tick\tactive\tbirths\tmean_ham\tstarved\twick\tstalls\toverwrites\terasures"
               "\tconflicts\tno_mass\tfree\tcode\twall\tenergy\tledger\tL1\tL2\text_blocked\text_erased\n";
}

// Active sites founded by lineage id (1 = anc, 2 = rival). Observation only.
int active_in(const World& w, uint16_t id) {
  int n = 0;
  const int32_t sites = w.config().width * w.config().height;
  for (int32_t s = 0; s < sites; ++s) n += w.site_active(s) && w.lineage(s) == id;
  return n;
}

void print_row(const World& w, const Stats& prev) {
  const Stats& s = w.stats();
  const Ledger l = w.ledger();
  std::cout << w.tick() << '\t' << w.active_count() << '\t' << s.births - prev.births << '\t'
            << (s.births > prev.births ? static_cast<double>(s.birth_hamming - prev.birth_hamming) / (s.births - prev.births) : 0.0) << '\t'
            << s.deaths_starve - prev.deaths_starve << '\t' << s.deaths_wick - prev.deaths_wick
            << '\t' << s.stalls - prev.stalls << '\t' << s.overwrites - prev.overwrites << '\t'
            << s.erasures - prev.erasures << '\t' << s.write_conflict - prev.write_conflict
            << '\t' << s.write_no_mass - prev.write_no_mass << '\t' << l.free_mass << '\t'
            << l.code_mass << '\t' << l.wall_mass << '\t' << l.energy << '\t'
            << (w.ledger_ok() ? "ok" : "FAIL") << '\t' << active_in(w, 1) << '\t'
            << active_in(w, 2) << '\t' << s.ext_blocked - prev.ext_blocked << '\t'
            << s.ext_erasures - prev.ext_erasures << '\n';
}

void print_genotypes(const World& w) {
  std::map<std::vector<uint8_t>, int> counts;
  const Config& c = w.config();
  for (int32_t s = 0; s < c.width * c.height; ++s) {
    auto bytes = w.site_bytes(s);
    if (std::all_of(bytes.begin(), bytes.end(), [](uint8_t b) { return b == INERT; })) continue;
    counts[bytes] += 1;
  }
  std::vector<std::pair<int, std::vector<uint8_t>>> top;
  for (auto& [bytes, n] : counts) top.push_back({n, bytes});
  std::sort(top.begin(), top.end(), [](auto& a, auto& b) { return a.first > b.first; });
  std::cout << "# genotypes=" << counts.size() << '\n';
  const size_t kTop = 3;
  for (size_t i = 0; i < std::min(kTop, top.size()); ++i) {
    std::cout << "# " << top[i].first << " sites: " << disassemble(top[i].second) << '\n';
  }
}

} // namespace

int main(int argc, char** argv) {
  Config cfg;
  RunOpts run;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    const auto eq = arg.find('=');
    if (eq == std::string::npos || !apply(cfg, run, arg.substr(0, eq), arg.substr(eq + 1))) {
      std::cerr << "unknown argument: " << arg << '\n';
      return 2;
    }
  }
  World w(cfg);
  const auto* anc = program_named(run.anc);
  const auto* rival = run.rival == "none" ? nullptr : program_named(run.rival);
  if (!anc || (run.rival != "none" && !rival)) {
    std::cerr << "unknown program name\n";
    return 2;
  }
  const int ax = rival ? cfg.width / 4 : cfg.width / 2;
  bool ok = w.seed_program(ax, cfg.height / 2, *anc);
  if (rival) ok = ok && w.seed_program(3 * cfg.width / 4, cfg.height / 2, *rival);
  if (!ok) {
    std::cerr << "cannot seed programs\n";
    return 1;
  }
  std::unique_ptr<FrameWriter> frames;
  if (!run.frames.empty()) {
    frames = std::make_unique<FrameWriter>(run.frames, cfg);
    if (!frames->ok()) {
      std::cerr << "cannot open " << run.frames << '\n';
      return 1;
    }
    frames->write(w);
  }
  print_header();
  Stats prev = w.stats();
  while (w.tick() < run.ticks) {
    w.run(1);
    if (frames && (w.tick() % run.every == 0 || w.active_count() == 0)) frames->write(w);
    if (w.tick() % run.interval == 0 || w.tick() == run.ticks || w.active_count() == 0) {
      print_row(w, prev);
      prev = w.stats();
    }
    if (w.active_count() == 0) break;
  }
  print_genotypes(w);
  std::cout << "# walls_built=" << w.stats().walls_built << " ignite_fail=" << w.stats().ignite_fail
            << '\n';
  std::cout << "# instructions=" << w.stats().instructions << " births=" << w.stats().births
            << " mean_ham=" << (w.stats().births ? static_cast<double>(w.stats().birth_hamming) / w.stats().births : 0.0) << " digest=" << std::hex << w.digest()
            << std::dec << '\n';
  return 0;
}
