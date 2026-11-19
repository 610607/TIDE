// Copy durations and cut share in a populated run, tracked by content identity.
// Usage: chk_cut_pop P_ROT SEED
#include "ps_core.hpp"
#include <cstdio>
#include <cstdlib>
#include <map>
using namespace ps;
int main(int /*argc*/, char** argv) {
  Config c; c.width = 48; c.height = 48; c.p_rot = std::atof(argv[1]); c.p_hydro = 3e-6;
  c.mass0 = 48; c.seed = std::atoi(argv[2]); c.ext_write = ExtWrite::FillOnly; c.p_mut = 0;
  World w(c);
  w.seed_program(24, 24, polite());
  const int n = c.width * c.height;
  std::map<int32_t, uint64_t> start;  // body -> tick of copy start
  std::map<int, int> hist[2];         // duration bucket (50 ticks) -> count, by cut
  uint64_t ended[2] = {}, sumdur[2] = {};
  std::map<int32_t, bool> cutnow;
  while (w.tick() < 20000) {
    w.run(1);
    std::map<int32_t, bool> active_copy;
    for (int32_t s = 0; s < n; ++s) if (w.copy_target(s) >= 0) active_copy[w.body(s)] = w.copy_was_cut(s);
    for (auto& [b, cut] : active_copy) if (!start.count(b)) start[b] = w.tick();
    for (auto it = start.begin(); it != start.end();) {
      if (!active_copy.count(it->first)) {
        const bool cut = cutnow[it->first];
        const uint64_t d = w.tick() - it->second;
        ended[cut] += 1; sumdur[cut] += d; hist[cut][std::min<int>(d / 50, 10)] += 1;
        it = start.erase(it);
      } else ++it;
    }
    cutnow = active_copy;
  }
  for (int k = 0; k < 2; ++k) {
    std::printf("%s ended=%llu mean_dur=%.1f hist(50-tick bins, last=500+):", k ? "cut  " : "uncut",
                (unsigned long long)ended[k], ended[k] ? double(sumdur[k]) / ended[k] : 0.0);
    for (int b = 0; b <= 10; ++b) std::printf(" %d", hist[k][b]);
    std::printf("\n");
  }
  std::printf("started=%llu cut=%llu born=%llu born_cut=%llu\n", (unsigned long long)w.stats().copies_started,
              (unsigned long long)w.stats().copies_cut, (unsigned long long)w.stats().copies_born,
              (unsigned long long)w.stats().copies_born_cut);
}
