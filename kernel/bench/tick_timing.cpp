// Wall-clock cost of VM v1 field ticks under three access arms. A timing benchmark only: it
// prints elapsed time, each world's final state hash and its occupied-site count at the last
// tick (a workload check, since step cost grows with occupied sites). It reports no lineage
// or population outcome.
// Usage: tick_timing WIDTH HEIGHT FIRST_SEED WORLDS TICKS [events]
//   events: also collect the per-tick Event vector that study observers use.
// World: WIDTH x HEIGHT torus, first-free placement, age limit 80, 20,000 ppm copy
// substitution, retained bytes, one R..CLD at x = WIDTH / 4, y = HEIGHT / 2. At 16 x 4 this is
// site 36, the setting of trait-lineage-01 and natural-renewal-01. Arms: self (no external
// access), read (neighbor reads), read_fetch (neighbor reads and neighbor instruction fetch).
#include "vm.hpp"

#include <chrono>
#include <cstdio>
#include <string>
#include <string_view>
#include <vector>

namespace {
using namespace tide;
World initial(int width, int height, int seed, Access access) {
    Config c;
    c.width = width; c.height = height; c.boundary = Boundary::torus; c.placement = Placement::first_free;
    c.max_age = 80; c.mutation_ppm = 20000; c.access = access; c.seed = seed;
    World w(c);
    w.seed_site(w.index(width / 4, height / 2), "R..CLD");
    return w;
}
}

int main(int argc, char** argv) {
    if (argc < 6) {
        std::fprintf(stderr, "usage: tick_timing WIDTH HEIGHT FIRST_SEED WORLDS TICKS [events]\n");
        return 2;
    }
    const int width = std::stoi(argv[1]), height = std::stoi(argv[2]);
    const int first = std::stoi(argv[3]), worlds = std::stoi(argv[4]), ticks = std::stoi(argv[5]);
    const bool with_events = argc > 6 && std::string_view(argv[6]) == "events";
    const struct { const char* name; Access access; } arms[] = {
        {"self", {false, false}}, {"read", {true, false}}, {"read_fetch", {true, true}}};
    std::printf("width\theight\tarm\tseed\tticks\tevents\tseconds_first_half\tseconds_second_half\toccupied_at_end\tfinal_hash\n");
    for (const auto& arm : arms) {
        for (int seed = first; seed < first + worlds; ++seed) {
            World w = initial(width, height, seed, arm.access);
            std::vector<Event> events;
            double half[2] = {0, 0};
            for (int h = 0; h < 2; ++h) {
                const auto start = std::chrono::steady_clock::now();
                for (int t = 0; t < ticks / 2; ++t) w.step(with_events ? &events : nullptr);
                half[h] = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            }
            int occupied = 0;
            for (int i = 0; i < w.size(); ++i) occupied += w.at(i).kind == Bank::occupied;
            std::printf("%d\t%d\t%s\t%d\t%d\t%d\t%.6f\t%.6f\t%d\t%s\n", width, height, arm.name, seed, ticks, with_events ? 1 : 0,
                        half[0], half[1], occupied, w.hash().c_str());
        }
    }
}
