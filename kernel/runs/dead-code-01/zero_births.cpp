// Post hoc check for dead-code-01, written after the frozen analysis had run; not part of the frozen study.
// Replays one world of the study without the observer and counts births whose product holds a zero byte.
// Usage: zero_births ARM retain|empty SEED TICKS; prints one TSV row. Build from the repository root with
//   g++ -O2 -std=c++20 -Ikernel/src -o kernel/build/dead-code/zero_births kernel/runs/dead-code-01/zero_births.cpp kernel/src/vm.cpp
// The founder, lattice and rules are those of study.cpp's initial(); the birth total must equal world.tsv.
#include "vm.hpp"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
using namespace tide;
int main(int argc, char** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: zero_births ARM retain|empty SEED TICKS\n");
        return 2;
    }
    std::string arm = argv[1], rec = argv[2];
    Config c;
    c.width = 32; c.height = 32; c.boundary = Boundary::torus; c.placement = Placement::first_free;
    c.max_age = 80; c.mutation_ppm = 20000;
    c.access = {arm != "self", arm == "read_fetch"};
    c.reclamation = rec == "retain" ? Reclamation::retain : Reclamation::empty;
    c.seed = std::strtoull(argv[3], nullptr, 10);
    Tick horizon = std::strtoull(argv[4], nullptr, 10);
    World w(c);
    w.seed_site(w.index(8, 16), "R..CLD");
    std::vector<Event> ev;
    unsigned long long births = 0, with_zero = 0, all_zero = 0;
    std::map<std::string, unsigned long long> zero_genotypes;
    while (w.tick() < horizon) {
        ev.clear();
        w.step(&ev);
        for (const auto& e : ev) {
            if (e.effect != Effect::birth) continue;
            ++births;
            if (e.product.find('\0') != std::string::npos) {
                ++with_zero;
                if (e.product.find_first_not_of('\0') == std::string::npos) ++all_zero;
                std::string hex;
                for (unsigned char b : e.product) { char buf[3]; std::snprintf(buf, 3, "%02x", b); hex += buf; }
                ++zero_genotypes[hex];
            }
        }
    }
    std::vector<std::pair<unsigned long long, std::string>> top;
    for (auto& [g, n] : zero_genotypes) top.push_back({n, g});
    std::sort(top.rbegin(), top.rend());
    std::string listed;
    for (size_t i = 0; i < top.size() && i < 5; ++i)
        listed += (i ? ";" : "") + top[i].second + ":" + std::to_string(top[i].first);
    // arm, reclamation, seed, ticks, births, births with a zero byte, all-zero births,
    // and the five commonest products holding a zero byte.
    std::printf("%s\t%s\t%llu\t%llu\t%llu\t%llu\t%llu\t%s\n", arm.c_str(), rec.c_str(),
                (unsigned long long)c.seed, (unsigned long long)horizon, births, with_zero, all_zero,
                listed.empty() ? "-" : listed.c_str());
}
