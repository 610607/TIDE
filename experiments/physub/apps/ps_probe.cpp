// Birth probe: classifies every birth of a polite-seeded run by parent integrity, copy
// differences, child lifespan and child fertility. Observation only.
// Usage: ps_probe ticks=N seed=S p_mut=X p_hydro=Y rival=0|1 [mass0=M]

#include "ps_core.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>

using namespace ps;

namespace {

// Offsets of the polite ancestor whose value changes while it runs (counters, direction,
// probe). Everything else is program text or constants.
constexpr std::array<int, 4> kVolatile = {31, 32, 33, 44};

bool is_volatile(int k) {
  for (int v : kVolatile) if (v == k) return true;
  return false;
}

int text_distance(const uint8_t* bytes, const std::vector<uint8_t>& ref, int len) {
  int d = 0;
  for (int k = 0; k < len; ++k) {
    const uint8_t r = k < static_cast<int>(ref.size()) ? ref[k] : INERT;
    d += !is_volatile(k) && bytes[k] != r;
  }
  return d;
}

// Program-region match: the ancestor's own length only, so leftover bytes in the tail of a
// recycled site do not count as alterations.
bool prefix_intact(const uint8_t* bytes) {
  const auto& ref = polite();
  for (int k = 0; k < static_cast<int>(ref.size()); ++k) {
    if (!is_volatile(k) && bytes[k] != ref[k]) return false;
  }
  return true;
}

// Sources of child-parent differences in copies made by prefix-intact parents.
// F: last written by another site; D: written by the parent, now inert (decayed);
// M: written by the parent with another value (mutation, or the parent changed since);
// R: not written since the child's previous ignition (residue or failed write).
enum Src { kF = 0, kD = 1, kM = 2, kR = 3, kSrcs = 4 };
constexpr const char* kSrcName[kSrcs] = {"foreign", "decay", "mut", "residue"};

struct ErrTally {
  uint64_t births = 0;
  uint64_t n[kSrcs] = {};
  uint64_t residue_parent_inert = 0;  // residue where the parent byte is inert
  std::map<int, uint64_t> at[kSrcs];
};

void tally_errors(const World& w, const World::Birth& b, int len, ErrTally& t) {
  t.births += 1;
  const uint8_t* c = w.bytes_at(b.child);
  const uint8_t* p = w.bytes_at(b.parent);
  for (int k = 0; k < len; ++k) {
    if (is_volatile(k) || c[k] == p[k]) continue;
    const uint64_t bit = uint64_t{1} << k;
    Src s = kR;
    if (b.by_other & bit) s = kF;
    else if (b.by_parent & bit) s = (c[k] == INERT && p[k] != INERT) ? kD : kM;
    t.n[s] += 1;
    t.at[s][k] += 1;
    if (s == kR && p[k] == INERT) t.residue_parent_inert += 1;
  }
}

void print_errors(const ErrTally& t) {
  const double b = t.births ? static_cast<double>(t.births) : 1.0;
  std::cout << "intact-parent copy diffs per birth (n=" << t.births << "):";
  for (int s = 0; s < kSrcs; ++s) std::cout << ' ' << kSrcName[s] << '=' << t.n[s] / b;
  std::cout << " (residue where parent inert: " << t.residue_parent_inert / b << ")\n";
  for (int s = 0; s < kSrcs; ++s) {
    std::multimap<uint64_t, int, std::greater<>> top;
    for (auto [k, n] : t.at[s]) top.insert({n, k});
    std::cout << "  " << kSrcName[s] << " top offsets:";
    int shown = 0;
    for (auto [n, k] : top) {
      if (shown++ == 10) break;
      std::cout << ' ' << k << ':' << n;
    }
    std::cout << '\n';
  }
}

struct Record {
  uint64_t born = 0;
  uint64_t died = 0;
  int offspring = 0;
  bool parent_intact = false;
  int child_text = 0;  // child text distance to the ancestor at birth
  int copy_diff = 0;   // child vs parent, volatile offsets excluded
  int kind = 0;        // see Kind
};

// Self: the parent re-ignites its own site. Copy: most of the child's code was written by
// the parent since the child's last ignition. Reignite: the child's code was already there.
enum Kind { kSelfIgnite = 0, kCopy = 1, kReignite = 2, kKinds = 3 };
constexpr const char* kKindName[kKinds] = {"self", "copy", "reignite"};

int classify(const World::Birth& b) {
  if (b.parent == b.child) return kSelfIgnite;
  return b.code > 0 && 2 * b.written >= b.code ? kCopy : kReignite;
}

struct Window {
  uint64_t births = 0, exact = 0, intact = 0, copies = 0, reignites = 0, intact_copies = 0;
  uint64_t pfx_copies = 0;
};

struct Group {
  uint64_t n = 0, lifespan = 0, fertile = 0, offspring = 0, intact_child = 0, copy_diff = 0;
};

// Program text of a site with the ancestor's volatile offsets masked.
std::string masked(const World& w, int32_t s) {
  std::string t(reinterpret_cast<const char*>(w.bytes_at(s)), w.config().site_len);
  for (int v : kVolatile) t[v] = 0;
  return t;
}

void print_window(const World& w, const Window& win, const Stats& prev) {
  std::map<std::string, int> counts;
  const int32_t n = w.config().width * w.config().height;
  for (int32_t s = 0; s < n; ++s) if (w.site_active(s)) counts[masked(w, s)] += 1;
  std::string top;
  int best = 0;
  for (auto& [t, c] : counts) if (c > best) { best = c; top = t; }
  const int dist = best ? text_distance(reinterpret_cast<const uint8_t*>(top.data()), polite(),
                                        w.config().site_len) : -1;
  // Space census: blank = inactive and all bytes inert; open0 = byte 0 inert (a polite
  // copy target); dead = inactive with any non-inert byte.
  int blank = 0, open0 = 0, dead = 0, pfx_active = 0;
  for (int32_t s = 0; s < n; ++s) {
    const uint8_t* bs = w.bytes_at(s);
    bool any = false;
    for (int k = 0; k < w.config().site_len && !any; ++k) any = bs[k] != INERT;
    open0 += bs[0] == INERT;
    if (!w.site_active(s)) { blank += !any; dead += any; }
    else pfx_active += prefix_intact(bs);
  }
  const double b = win.births ? static_cast<double>(win.births) : 1.0;
  std::cout << w.tick() << '\t' << w.active_count() << '\t' << win.births << '\t'
            << 100.0 * win.exact / b << '\t' << 100.0 * win.intact / b << '\t' << best << '\t'
            << dist << '\t' << counts.size() << '\t' << win.copies << '\t' << win.reignites
            << '\t' << win.intact_copies << '\t' << blank << '\t' << open0 << '\t' << dead
            << '\t' << pfx_active << '\t' << win.pfx_copies << '\t'
            << w.stats().ext_erasures - prev.ext_erasures << '\t'
            << w.stats().stalls - prev.stalls << '\t'
            << w.stats().deaths_starve - prev.deaths_starve << '\t' << w.ledger().energy
            << std::endl;
}

void print_top_programs(const World& w) {
  std::map<std::string, int> counts;
  const int32_t n = w.config().width * w.config().height;
  for (int32_t s = 0; s < n; ++s) if (w.site_active(s)) counts[masked(w, s)] += 1;
  std::multimap<int, std::string, std::greater<>> top;
  for (auto& [t, c] : counts) top.insert({c, t});
  int shown = 0;
  for (auto& [c, t] : top) {
    if (shown++ == 3) break;
    std::vector<uint8_t> bytes(t.begin(), t.end());
    std::cout << "# " << c << " active, dist " << text_distance(bytes.data(), polite(), w.config().site_len)
              << ": " << disassemble(bytes) << '\n';
  }
}

} // namespace

int main(int argc, char** argv) {
  Config cfg;
  cfg.mass0 = 48;
  uint64_t ticks = 20000;
  bool rival = false;
  uint64_t interval = 10000;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    const auto eq = a.find('=');
    if (eq == std::string::npos || a.find(' ') != std::string::npos) {
      std::cerr << "bad argument (zsh needs ${=args}): " << a << '\n';
      return 1;
    }
    const std::string k = a.substr(0, eq), v = a.substr(eq + 1);
    if (k == "ticks") ticks = std::atoll(v.c_str());
    else if (k == "seed") cfg.seed = std::atoll(v.c_str());
    else if (k == "p_mut") cfg.p_mut = std::atof(v.c_str());
    else if (k == "p_hydro") cfg.p_hydro = std::atof(v.c_str());
    else if (k == "p_dead") cfg.p_dead = std::atof(v.c_str());
    else if (k == "mass0") cfg.mass0 = std::atoi(v.c_str());
    else if (k == "rival") rival = v == "1";
    else if (k == "e_erase") cfg.e_erase = std::atoi(v.c_str());
    else if (k == "e_ignite") cfg.e_ignite = std::atoi(v.c_str());
    else if (k == "e_max") cfg.e_max = std::atoi(v.c_str());
    else if (k == "e_in") cfg.e_in = std::atoi(v.c_str());
    else if (k == "e_basal") cfg.e_basal = std::atoi(v.c_str());
    else if (k == "e_bond") cfg.e_bond = std::atoi(v.c_str());
    else if (k == "e_div") cfg.e_div = std::atoi(v.c_str());
    else if (k == "e_act") cfg.e_act = std::atoi(v.c_str());
    else if (k == "e_diffuse") cfg.e_diffuse = std::atoi(v.c_str()) != 0;
    else if (k == "bond_store") cfg.bond_store = std::atoi(v.c_str()) != 0;
    else if (k == "ext_write") {
      if (!parse_ext_write(v, cfg.ext_write)) {
        std::cerr << "bad ext_write: " << v << '\n';
        return 1;
      }
    }
    else if (k == "width") cfg.width = std::atoi(v.c_str());
    else if (k == "height") cfg.height = std::atoi(v.c_str());
    else if (k == "interval") interval = std::max<long long>(1, std::atoll(v.c_str()));
    else {
      std::cerr << "unknown key: " << k << '\n';
      return 1;
    }
  }
  World w(cfg);
  const int ax = rival ? cfg.width / 4 : cfg.width / 2;
  w.seed_program(ax, cfg.height / 2, polite());
  if (rival) w.seed_program(3 * cfg.width / 4, cfg.height / 2, ancestor());
  const int L = cfg.site_len;
  std::vector<Record> recs;
  std::vector<int> current(cfg.width * cfg.height, -1); // record of the site's activation
  std::map<int, uint64_t> diff_at;                       // offset -> count of copy differences
  std::map<std::string, uint64_t> altered_kinds;         // parent text change -> births
  Window win;
  Stats prev_stats;
  ErrTally errs;
  std::cout << "tick\tactive\tbirths\texact%\tintact_parent%\ttop_count\ttop_dist\tdistinct"
               "\tcopies\treignites\tintact_copies\tblank\topen0\tdead\tpfx_active\tpfx_copies\text_erased\tstalls\tstarved\tenergy\n";
  while (w.tick() < ticks && w.active_count() > 0) {
    w.run(1);
    if (w.tick() % interval == 0) {
      print_window(w, win, prev_stats);
      win = Window{};
      prev_stats = w.stats();
    }
    for (const auto& b : w.births_this_tick()) {
      Record r;
      r.born = w.tick();
      r.parent_intact = text_distance(w.bytes_at(b.parent), polite(), L) == 0;
      if (!r.parent_intact) {
        std::string sig;
        const uint8_t* pb = w.bytes_at(b.parent);
        for (int k = 0; k < L && sig.size() < 60; ++k) {
          const uint8_t ref = k < static_cast<int>(polite().size()) ? polite()[k] : INERT;
          if (!is_volatile(k) && pb[k] != ref) {
            sig += std::to_string(k) + ":" + std::to_string(ref) + ">" + std::to_string(pb[k]) + " ";
          }
        }
        altered_kinds[sig] += 1;
      }
      r.child_text = text_distance(w.bytes_at(b.child), polite(), L);
      for (int k = 0; k < L; ++k) {
        if (!is_volatile(k) && w.bytes_at(b.child)[k] != w.bytes_at(b.parent)[k]) {
          r.copy_diff += 1;
          diff_at[k] += 1;
        }
      }
      r.kind = classify(b);
      win.births += 1;
      win.exact += r.copy_diff == 0;
      win.intact += r.parent_intact;
      win.copies += r.kind == kCopy;
      win.reignites += r.kind == kReignite;
      win.intact_copies += r.kind == kCopy && r.parent_intact;
      win.pfx_copies += r.kind == kCopy && prefix_intact(w.bytes_at(b.parent));
      if (r.kind == kCopy && prefix_intact(w.bytes_at(b.parent))) tally_errors(w, b, L, errs);
      if (current[b.parent] >= 0) recs[current[b.parent]].offspring += 1;
      if (current[b.child] >= 0 && recs[current[b.child]].died == 0) recs[current[b.child]].died = w.tick();
      current[b.child] = static_cast<int>(recs.size());
      recs.push_back(r);
    }
    for (size_t s = 0; s < current.size(); ++s) {
      const int c = current[s];
      if (c >= 0 && recs[c].died == 0 && !w.site_active(static_cast<int32_t>(s))) recs[c].died = w.tick();
    }
  }
  Group g[2][kKinds];
  for (const Record& r : recs) {
    Group& x = g[r.parent_intact][r.kind];
    x.n += 1;
    x.lifespan += (r.died ? r.died : w.tick()) - r.born;
    x.fertile += r.offspring > 0;
    x.offspring += r.offspring;
    x.intact_child += r.child_text == 0;
    x.copy_diff += r.copy_diff;
  }
  for (int i = 1; i >= 0; --i) for (int k = 0; k < kKinds; ++k) {
    const Group& x = g[i][k];
    if (!x.n) continue;
    std::cout << (i ? "parent intact " : "parent altered") << ' ' << kKindName[k] << " births=" << x.n
              << " intact_child=" << 100.0 * x.intact_child / x.n << "%"
              << " mean_copy_diff=" << static_cast<double>(x.copy_diff) / x.n
              << " mean_life=" << x.lifespan / x.n
              << " fertile=" << 100.0 * x.fertile / x.n << "%\n";
  }
  std::cout << "copy differences by offset (top):";
  std::multimap<uint64_t, int, std::greater<>> top;
  for (auto [k, n] : diff_at) top.insert({n, k});
  int shown = 0;
  for (auto [n, k] : top) {
    if (shown++ == 12) break;
    std::cout << ' ' << k << ':' << n;
  }
  std::multimap<uint64_t, std::string, std::greater<>> kinds;
  for (auto& [sig, n] : altered_kinds) kinds.insert({n, sig});
  std::cout << "\naltered parents with most births (offset:ancestor>now):\n";
  shown = 0;
  for (auto& [n, sig] : kinds) {
    if (shown++ == 6) break;
    std::cout << "  " << n << "  " << sig << '\n';
  }
  print_errors(errs);
  print_top_programs(w);
  const Ledger l = w.ledger();
  std::cout << "final tick=" << w.tick() << " active=" << w.active_count()
            << " free=" << l.free_mass << " code=" << l.code_mass
            << " ext_blocked=" << w.stats().ext_blocked
            << " ext_erased=" << w.stats().ext_erasures << '\n';
  return 0;
}
