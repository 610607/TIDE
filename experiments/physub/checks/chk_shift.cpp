// Check: does a polite key with a filled so/do pointer
// direction (36 or 38) copy in register when it starts from the counters a copy-born child
// carries (31 = 223, 33 = 225) rather than the census's volatile reset (192, 192)?
#include "ps_core.hpp"

#include <cstdio>
#include <vector>
using namespace ps;
static bool same_key(const uint8_t* a, const std::vector<uint8_t>& k) {
  for (int i = 0; i < 64; ++i) {
    if (i == 31 || i == 32 || i == 33 || i == 44) continue;
    const uint8_t kb = i < (int)k.size() ? k[i] : INERT;
    if (a[i] != kb) return false;
  }
  return true;
}
int main() {
  struct V { const char* name; std::vector<int> fill; bool born; };
  std::vector<V> vs = {
    {"base reset", {}, false}, {"base born", {}, true},
    {"36 reset", {36}, false}, {"36 born", {36}, true},
    {"38 reset", {38}, false}, {"38 born", {38}, true},
    {"36+38 reset", {36, 38}, false}, {"36+38 born", {36, 38}, true},
    {"34 born", {34}, true}, {"40 born", {40}, true}};
  for (int io = 0; io < 2; ++io) {
    for (const auto& v : vs) {
      Config c;
      c.mass0 = 48; c.width = 9; c.height = 9; c.p_mut = 0; c.p_hydro = 0; c.seed = 1;
      c.ext_write = ExtWrite::FillOnly;
      c.inert_operand = io ? InertOperand::Fail : InertOperand::Zero;
      std::vector<uint8_t> p = polite();
      p.resize(64, INERT);
      for (int k : v.fill) p[k] = 1;
      if (v.born) { p[31] = 223; p[33] = 225; }
      World w(c);
      const int32_t ctr = w.site_index(4, 4);
      w.set_free_mass(ctr, 64);
      if (!w.seed_program(4, 4, p)) { printf("seed failed %s\n", v.name); continue; }
      int copies = 0, exact = 0, first_exact = -1;
      for (int t = 0; t < 2000; ++t) {
        w.run(1);
        for (const auto& b : w.births_this_tick()) {
          if (b.parent != ctr) continue;
          copies += 1;
          const bool ex = same_key(w.bytes_at(b.child), p);
          exact += ex;
          if (first_exact < 0) first_exact = ex;
        }
      }
      int carriers = 0, active = 0;
      for (int32_t s = 0; s < 81; ++s) {
        if (!w.site_active(s)) continue;
        active += 1;
        carriers += same_key(w.bytes_at(s), p);
      }
      printf("%-5s %-12s founder_births=%d exact=%d first_exact=%d active=%d carriers=%d\n",
             io ? "fail" : "zero", v.name, copies, exact, first_exact, active, carriers);
    }
  }
}
