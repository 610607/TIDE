// First-copy probe for block rotation: seeds polite alone in a 16x16 world without
// mutation, decay or erosion, and follows its first copy (first write into a neighbor to the
// first paid ignition into a neighbor) over many seeds. Reports how often a rotation cut the
// copy, how often the copy ended in a birth, and the copy's mean duration. Observation only.
// Usage: ps_copycut p_rot=P [seeds=N] [ext_write=fill]

#include "ps_core.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

using namespace ps;

int main(int argc, char** argv) {
  Config cfg;
  cfg.width = 16;
  cfg.height = 16;
  cfg.mass0 = 48;
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  cfg.ext_write = ExtWrite::FillOnly;
  int seeds = 400;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    const auto eq = a.find('=');
    const std::string k = a.substr(0, eq), v = eq == std::string::npos ? "" : a.substr(eq + 1);
    if (k == "p_rot") cfg.p_rot = std::atof(v.c_str());
    else if (k == "seeds") seeds = std::atoi(v.c_str());
    else if (k == "ext_write" && parse_ext_write(v, cfg.ext_write)) {}
    else {
      std::cerr << "unknown argument: " << a << '\n';
      return 1;
    }
  }
  constexpr uint64_t kLimit = 5000;
  int ended = 0, cut = 0, born = 0, born_cut = 0;
  uint64_t duration = 0;
  for (int s = 1; s <= seeds; ++s) {
    Config c = cfg;
    c.seed = static_cast<uint64_t>(s);
    World w(c);
    if (!w.seed_program(c.width / 2, c.height / 2, polite())) return 1;
    uint64_t start = 0;
    while (w.tick() < kLimit && w.active_count() > 0) {
      w.run(1);
      const Stats& st = w.stats();
      if (start == 0 && st.copies_started >= 1) start = w.tick();
      if (st.copies_born >= 1 || st.copies_started >= 2) {
        ended += 1;
        cut += st.copies_cut >= 1;
        born += st.copies_born >= 1;
        born_cut += st.copies_born_cut >= 1;
        duration += w.tick() - start;
        break;
      }
    }
  }
  const double e = ended ? static_cast<double>(ended) : 1.0;
  std::cout << "p_rot=" << cfg.p_rot << " seeds=" << seeds << " ended=" << ended
            << " cut=" << cut / e << " born=" << born / e << " born_if_cut="
            << (cut ? static_cast<double>(born_cut) / cut : 0.0) << " born_if_uncut="
            << (ended > cut ? static_cast<double>(born - born_cut) / (ended - cut) : 0.0)
            << " mean_duration=" << duration / e << '\n';
  return 0;
}
