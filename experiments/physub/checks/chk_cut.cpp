// First-copy cut probability and duration for polite alone at a given p_rot.
// Usage: chk_cut P_ROT SEEDS
#include "ps_core.hpp"
#include <cstdio>
#include <cstdlib>
using namespace ps;
int main(int /*argc*/, char** argv) {
  const double p = std::atof(argv[1]);
  const int n = std::atoi(argv[2]);
  int cut = 0, ended = 0, born = 0; double dur = 0;
  for (int seed = 1; seed <= n; ++seed) {
    Config c; c.width = 16; c.height = 16; c.p_rot = p; c.p_hydro = 0; c.p_erode = 0;
    c.mass0 = 48; c.seed = seed; c.ext_write = ExtWrite::FillOnly;
    World w(c);
    w.seed_program(8, 8, polite());
    uint64_t start = 0;
    while (w.tick() < 5000) {
      w.run(1);
      const Stats& s = w.stats();
      if (start == 0 && s.copies_started >= 1) start = w.tick();
      if (s.copies_born >= 1 || s.copies_started >= 2 || w.active_count() == 0) {
        ended += 1; born += s.copies_born >= 1; cut += s.copies_cut >= 1;
        dur += w.tick() - start; break;
      }
    }
  }
  std::printf("p_rot=%g seeds=%d ended=%d born=%d cut=%.3f mean_duration=%.1f\n", p, n, ended, born,
              double(cut) / ended, dur / ended);
}
