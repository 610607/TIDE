// Print the first short copies (< 50 ticks) in a populated run.
// Usage: chk_cut_short P_ROT SEED
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
  std::map<int32_t, std::pair<uint64_t, int32_t>> start;  // body -> (tick, site at start)
  int shown = 0;
  std::map<int, int> by_offset;
  while (w.tick() < 20000) {
    w.run(1);
    std::map<int32_t, int32_t> now;  // body -> site
    for (int32_t s = 0; s < n; ++s) if (w.copy_target(s) >= 0) now[w.body(s)] = s;
    for (auto& [b, s] : now) if (!start.count(b)) start[b] = {w.tick(), s};
    for (auto it = start.begin(); it != start.end();) {
      if (!now.count(it->first)) {
        const uint64_t d = w.tick() - it->second.first;
        int32_t site = -1;
        for (int32_t s = 0; s < n; ++s) if (w.body(s) == it->first) site = s;
        if (d < 50) {
          by_offset[w.first_ip(site)] += 1;
          if (shown < 4) {
            ++shown;
            std::printf("tick=%llu dur=%llu active=%d ip=%d\n  %s\n", (unsigned long long)w.tick(),
                        (unsigned long long)d, w.site_active(site), w.first_ip(site),
                        disassemble(w.site_bytes(site)).c_str());
          }
        }
        it = start.erase(it);
      } else ++it;
    }
  }
  std::printf("short copies by ip at end:");
  for (auto [k, v] : by_offset) std::printf(" %d:%d", k, v);
  std::printf("\n");
}
