// Emit physical births, deaths and checkpoint digests for a frozen fetch field.
#include "assay.hpp"

#include <charconv>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string_view>

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: field SEED");
        const std::string_view arg = argv[1];
        tide::Config cfg;
        auto parsed = std::from_chars(arg.data(), arg.data() + arg.size(), cfg.seed);
        if (parsed.ec != std::errc{} || parsed.ptr != arg.data() + arg.size() || cfg.seed == 0)
            throw std::invalid_argument("invalid seed");
        cfg.access.fetch = true;
        cfg.width = cfg.height = 8;
        cfg.boundary = tide::Boundary::torus;
        cfg.placement = tide::Placement::first_free;
        cfg.max_age = 80;
        cfg.mutation_ppm = 20000;
        tide::World field(cfg);
        field.seed_site(field.index(4,4), tide::ancestor);
        std::vector<tide::Event> events;
        for (int tick = 1; tick <= 4096; ++tick) {
            field.step(&events);
            field.check();
            for (const auto& e : events) {
                if (e.effect == tide::Effect::birth) {
                    std::ostringstream hex;
                    for (unsigned char byte : e.product)
                        hex << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(byte);
                    std::cout << "birth\t" << tick << '\t' << e.actor << '\t' << e.actor_born
                              << '\t' << e.target << '\t' << hex.str() << '\n';
                } else if (e.effect == tide::Effect::death) {
                    std::cout << "death\t" << tick << '\t' << e.actor << '\t' << e.actor_born << '\n';
                }
            }
            if (tick == 512 || tick == 1024 || tick == 2048 || tick == 4096)
                std::cout << "checkpoint\t" << tick << '\t' << field.hash() << '\n';
        }
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n';
        return 1;
    }
}
