// Observe one generation of the frozen mutation-free assay.
#include "vm.hpp"

#include <charconv>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace {
std::string decode(std::string_view hex) {
    if (hex.empty() || hex.size() > 2 * tide::capacity || hex.size() % 2)
        throw std::invalid_argument("expected a hexadecimal genome");
    std::string bytes;
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned byte;
        auto end = hex.data() + i + 2;
        auto parsed = std::from_chars(hex.data() + i, end, byte, 16);
        if (parsed.ec != std::errc{} || parsed.ptr != end)
            throw std::invalid_argument("invalid genome byte");
        bytes.push_back(static_cast<char>(byte));
    }
    return bytes;
}

std::string encode(const std::string& bytes) {
    std::ostringstream out;
    for (unsigned char byte : bytes)
        out << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(byte);
    return out.str();
}

void observe(tide::World& arena, int focal, int horizon) {
    std::map<std::string, int> seen;
    seen.emplace(arena.dynamics(), 0);
    std::vector<tide::Event> events;
    int reads = 0, fetches = 0;
    for (int t = 1; t <= horizon; ++t) {
        arena.step(&events);
        arena.check();
        for (const auto& event : events) {
            if (event.actor != focal) continue;
            reads += event.read_contact.site >= 0;
            fetches += event.fetch_contact.site >= 0;
            if (event.effect == tide::Effect::birth) {
                std::cout << "birth\t" << t << "\t-\t" << reads << '\t' << fetches
                          << '\t' << encode(event.product) << '\n';
                return;
            }
        }
        auto [it, inserted] = seen.emplace(arena.dynamics(), t);
        if (!inserted) {
            std::cout << "cycle\t" << t << '\t' << it->second << '\t' << reads << '\t'
                      << fetches << "\t-\n";
            return;
        }
    }
    std::cout << "timeout\t" << horizon << "\t-\t" << reads << '\t' << fetches << "\t-\n";
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 7)
            throw std::invalid_argument("usage: observe ARM on|off FOCAL_HEX DONOR_HEX NESW 64|4096");
        std::string_view arm = argv[1], allow = argv[2], dir = argv[5], limit = argv[6];
        const std::string_view compass = "NESW";
        if ((arm != "read" && arm != "fetch") || (allow != "on" && allow != "off") ||
            dir.size() != 1 || compass.find(dir) == compass.npos || (limit != "64" && limit != "4096"))
            throw std::invalid_argument("invalid assay configuration");
        tide::Config cfg;
        cfg.access = {arm == "read", arm == "fetch"};
        cfg.placement = tide::Placement::first_free;
        tide::World arena(cfg);
        const int focal = arena.index(2, 2);
        arena.seed_site(focal, decode(argv[3]));
        arena.set_access(focal, allow == "on" ? cfg.access : tide::Access{});
        arena.seed_site(arena.neighbor(focal, static_cast<int>(compass.find(dir))), decode(argv[4]));
        observe(arena, focal, limit == "64" ? 64 : 4096);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
