// Check: polite with [34] filled reads K from a neighbor. With
// wall units on that edge, each read crosses with probability 1/(W+1), independently for
// MOV 0 (so = K) and MOV 3 (do = K). Started from copy-born counters (31 = 223, 33 = 225),
// does the founder copy off register? Neighbor in direction [34] holds polite (K = 192).
#include "ps_census.hpp"
#include <cstdio>
#include <vector>
using namespace ps;
int main() {
  const census::Reference& ref = *census::reference_named("polite");
  for (int W : {0, 1, 2, 4, 8}) {
    int copies = 0, exact = 0, multi = 0, trials = 0;
    for (uint64_t seed = 1; seed <= 100; ++seed) {
      Config c;
      c.mass0 = 48; c.width = 9; c.height = 9; c.p_mut = 0; c.p_hydro = 0; c.seed = seed;
      c.ext_write = ExtWrite::FillOnly; c.p_erode = 0;
      World w(c);
      std::vector<uint8_t> p = polite();
      p.resize(64, INERT);
      p[34] = 2;  // direction (2 - 1) % 4 = 1: +x
      std::string key(p.begin(), p.end());
      for (int x : ref.volatile_offsets) key[x] = 0;
      std::vector<uint8_t> born = census::trial_program(key, ref);
      born[31] = 223; born[32] = 1; born[33] = 225; born[44] = INERT;
      const int32_t ctr = w.site_index(4, 4);
      w.set_free_mass(ctr, 64);
      w.seed_program(4, 4, born);
      w.set_wall(ctr, 1, static_cast<uint8_t>(W));
      trials += 1;
      bool first = true;
      for (int k = 0; k < 3000 && first; ++k) {
        w.run(1);
        for (const auto& b : w.births_this_tick()) {
          if (b.parent != ctr || census::classify(b) != census::kCopy) continue;
          copies += 1;
          const bool ex = census::masked(w, b.child, ref) == key;
          exact += ex;
          multi += census::diff_sources(w, b, ref).cls == census::kClsMulti;
          first = false;
        }
      }
    }
    printf("W=%d trials=%d first founder copy found=%d exact=%d multi=%d\n", W, trials, copies, exact, multi);
  }
}
