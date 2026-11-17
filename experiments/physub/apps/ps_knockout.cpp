// Single-byte knockout of a seeded program: set one non-inert byte to INERT (as hydrolysis
// would), seed it alone at the center of a small world with no mutation, hydrolysis or
// erosion, and count active sites that still carry the knocked-out program. A byte is
// lethal when no copy besides at most one site remains; impaired when copies fall below
// half the intact baseline. Usage: ps_knockout [anc=polite|ancestor] [size=9]
// [ticks=4000] [seed=1]

#include "ps_core.hpp"

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <set>
#include <string>
#include <vector>

using namespace ps;

namespace {

struct Trial {
  int children = 0;    // births by the founder into other sites
  int first = -1;      // tick of the founder's first and second such birth
  int second = -1;
  int functional = 0;  // active sites matching the seeded program outside volatile bytes
  bool founder_active = false;
};

bool same_static(const std::vector<uint8_t>& a, const std::vector<uint8_t>& b,
                 const std::set<int>& volatile_bytes) {
  for (size_t k = 0; k < a.size(); ++k) {
    if (!volatile_bytes.count(static_cast<int>(k)) && a[k] != b[k]) return false;
  }
  return true;
}

Trial run_trial(const std::vector<uint8_t>& program, const std::set<int>& volatile_bytes,
                int size, int ticks, uint64_t seed) {
  Config cfg;
  cfg.width = size;
  cfg.height = size;
  cfg.site_len = 64;
  cfg.mass0 = 48;
  cfg.p_hydro = 0.0;
  cfg.p_mut = 0.0;
  cfg.p_erode = 0.0;
  cfg.seed = seed;
  World w(cfg);
  Trial r;
  if (!w.seed_program(size / 2, size / 2, program)) return r;
  const int32_t center = w.site_index(size / 2, size / 2);
  const std::vector<uint8_t> ref = w.site_bytes(center);
  for (int t = 0; t < ticks; ++t) {
    w.run(1);
    for (const auto& b : w.births_this_tick()) {
      if (b.parent != center || b.child == center) continue;
      if (r.first < 0) r.first = t;
      else if (r.second < 0) r.second = t;
      r.children += 1;
    }
  }
  for (int32_t s = 0; s < size * size; ++s) {
    r.functional += w.site_active(s) && same_static(w.site_bytes(s), ref, volatile_bytes);
  }
  r.founder_active = w.site_active(center);
  return r;
}

} // namespace

int main(int argc, char** argv) {
  std::string anc = "polite";
  int size = 9;
  int ticks = 4000;
  uint64_t seed = 1;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    const auto eq = a.find('=');
    const std::string k = a.substr(0, eq);
    const std::string v = eq == std::string::npos ? "" : a.substr(eq + 1);
    if (k == "anc" && (v == "polite" || v == "ancestor")) anc = v;
    else if (k == "size") size = std::atoi(v.c_str());
    else if (k == "ticks") ticks = std::atoi(v.c_str());
    else if (k == "seed") seed = std::strtoull(v.c_str(), nullptr, 10);
    else {
      std::cerr << "bad argument: " << a << '\n';
      return 1;
    }
  }
  // Bytes the program rewrites while running: source and destination counters, direction,
  // and polite's probe cell.
  const std::vector<uint8_t>& base = anc == "polite" ? polite() : ancestor();
  const std::set<int> volatile_bytes =
      anc == "polite" ? std::set<int>{31, 32, 33, 44} : std::set<int>{24, 25, 26};

  const Trial b = run_trial(base, volatile_bytes, size, ticks, seed);
  std::printf("# anc=%s size=%d ticks=%d seed=%llu\n", anc.c_str(), size, ticks,
              static_cast<unsigned long long>(seed));
  std::printf("# baseline children=%d first_birth=%d second_birth=%d functional=%d\n",
              b.children, b.first, b.second, b.functional);
  std::printf("offset\tbyte\top\tchildren\tfunctional\tfounder_active\tclass\n");
  int non_inert = 0, lethal = 0, impaired = 0, zombies = 0;
  for (size_t i = 0; i < base.size(); ++i) {
    if (base[i] == INERT) continue;
    non_inert += 1;
    std::vector<uint8_t> program = base;
    program[i] = INERT;
    const Trial r = run_trial(program, volatile_bytes, size, ticks, seed);
    const char* cls = "neutral";
    if (r.functional <= 1) {
      cls = "lethal";
      lethal += 1;
      zombies += r.founder_active;
    } else if (2 * r.functional < b.functional) {
      cls = "impaired";
      impaired += 1;
    }
    const std::string op = disassemble({base[i]});
    std::printf("%zu\t%d\t%s\t%d\t%d\t%s\t%s\n", i, base[i], op.c_str(), r.children,
                r.functional, r.founder_active ? "yes" : "no", cls);
  }
  std::printf("# non_inert=%d lethal=%d impaired=%d lethal_founder_active=%d\n", non_inert,
              lethal, impaired, zombies);
  if (lethal > 0) {
    std::printf("# saturated offspring per lifetime ~ %d neighbors / %d lethal bytes = %.3f\n",
                kDirs, lethal, static_cast<double>(kDirs) / lethal);
  }
  return 0;
}
