// Check: a polite writer W whose do counter starts at V instead
// of K = 192 (as after a copy error in MOV 3 do = K) probes target[V mod 64]. Next to a live
// polite B, does it copy into B's INERT offsets? W's MOV 3 is replaced by MOV 34 34 (a no-op
// write of K onto itself) so do keeps its seeded value V for the first cycle.
#include "ps_core.hpp"
#include <cstdio>
#include <vector>
using namespace ps;
int main() {
  const std::vector<int> ext = {30, 34, 36, 38, 40, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56,
                                57, 58, 59, 60, 61, 62, 63};
  for (int V : {192, 222, 196, 236, 250, 210}) {
    int trials = 0, hit = 0, killed30 = 0, bytes = 0, b_alive = 0;
    for (uint64_t seed = 1; seed <= 200; ++seed) {
      Config c;
      c.mass0 = 48; c.width = 9; c.height = 9; c.p_mut = 0; c.p_hydro = 0; c.seed = seed;
      c.ext_write = ExtWrite::FillOnly;
      World w(c);
      std::vector<uint8_t> pb = polite(), pw = polite();
      pb.resize(64, INERT); pw.resize(64, INERT);
      pw[3] = pw[0]; pw[4] = 34; pw[5] = 34;
      pw[33] = static_cast<uint8_t>(V);
      // B at (4,4), W at (5,4); walls are off, so W's RND picks among four neighbors.
      w.set_free_mass(w.site_index(4, 4), 64);
      w.set_free_mass(w.site_index(5, 4), 64);
      if (!w.seed_program(4, 4, pb) || !w.seed_program(5, 4, pw)) { printf("seed fail\n"); return 1; }
      const int32_t b = w.site_index(4, 4);
      w.set_free_mass(b, 64);
      // Run until W finishes its first copy cycle (about 64 iterations x 5 instructions).
      w.run(600);
      trials += 1;
      const uint8_t* bb = w.bytes_at(b);
      int n = 0;
      for (int k : ext) n += bb[k] != INERT;
      hit += n > 0;
      bytes += n;
      killed30 += bb[30] != INERT;
      b_alive += w.site_active(b);
    }
    printf("V=%3d (offset %2d) trials=%d B_filled=%d mean_bytes=%.2f B_30_filled=%d B_active=%d\n",
           V, V % 64, trials, hit, static_cast<double>(bytes) / trials, killed30, b_alive);
  }
}
