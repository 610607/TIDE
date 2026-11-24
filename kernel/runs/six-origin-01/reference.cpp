#include "../vacancy-01/common.hpp"

#include <iostream>
#include <optional>

namespace {
constexpr char ancestor[] = "R..CLD";

tide::World field(int seed, int ppm) {
    tide::Config c;
    c.width = 16; c.height = 4; c.boundary = tide::Boundary::torus;
    c.placement = tide::Placement::first_free; c.max_age = 80;
    c.access.read = true; c.mutation_ppm = ppm; c.seed = seed;
    tide::World w(c);
    w.seed_site(36, ancestor);
    return w;
}

void controls(std::ostream& out, bool reverse) {
    out << "seed\tpermission\tfounder_births\texternal_reads\tchild_tick_site\tend_hash\n";
    std::vector<std::string> histories;
    for (bool allow : {true, false}) {
        auto w = field(1, 0);
        w.set_access(36, {allow, false});
        int births = 0, reads = 0;
        std::string children;
        std::vector<tide::Event> events;
        for (int tick = 1; tick <= 81; ++tick) {
            w.step(&events, reverse);
            for (const auto& e : events) {
                if (e.actor != 36 || e.actor_born != 0) continue;
                reads += e.read_contact.site >= 0;
                if (e.effect == tide::Effect::birth) {
                    vacancy::require(e.product == ancestor, "ancestor offspring differs");
                    ++births;
                    if (!children.empty()) children += ',';
                    children += std::to_string(tick) + "/" + std::to_string(e.target);
                }
            }
        }
        w.set_access(36, w.config().access);
        w.check();
        vacancy::require(births > 0 && !reads, "ancestor control failed");
        out << "1\t" << (allow ? "on" : "off") << '\t' << births << '\t' << reads
            << '\t' << children << '\t' << w.hash() << '\n';
        histories.push_back(children + " " + w.hash());
    }
    vacancy::require(histories[0] == histories[1], "ancestor denial changed history");
}

void neighborhoods(bool reverse) {
    std::optional<tide::World> world;
    int previous = -1, seed, tick, site, born, source, offset;
    std::cout << "seed\ttick\tsite\tborn\tsource\toffset\tN\tE\tS\tW\n";
    while (std::cin >> seed >> tick >> site >> born >> source >> offset) {
        if (seed != previous) {
            vacancy::require(seed > previous && seed >= 19521 && seed <= 21568, "unordered template seeds");
            world = field(seed, 20000);
            previous = seed;
        }
        vacancy::require(tick > 0 && tick <= 2048, "invalid template tick");
        while (world->tick()+1 < static_cast<tide::Tick>(tick)) world->step(nullptr, reverse);
        const auto& focal = world->at(site);
        const auto& cpu = focal.cpu;
        vacancy::require(world->tick()+1 == static_cast<tide::Tick>(tick) &&
                         focal.kind == tide::Bank::occupied && focal.born == static_cast<tide::Tick>(born) &&
                         world->at(cpu.bank).bytes.at(cpu.pc) == 'C' && cpu.source == source && cpu.read == offset,
                         "copy opening differs");
        std::cout << seed << '\t' << tick << '\t' << site << '\t' << born << '\t' << source << '\t' << offset;
        for (int d = 0; d < 4; ++d) {
            const int n = world->neighbor(site,d);
            const auto& bank = world->at(n);
            std::cout << '\t' << n << '/' << vacancy::kind(bank.kind) << '/' << bank.born << '/'
                      << bank.owner << '/' << vacancy::hex(bank.bytes);
        }
        std::cout << '\n';
    }
    vacancy::require(std::cin.eof(), "malformed neighborhood request");
}
}

int main(int argc, char** argv) {
    try {
        if (argc >= 2 && std::string_view(argv[1]) == "--neighbors") {
            if (argc > 3 || (argc == 3 && std::string_view(argv[2]) != "--reverse"))
                throw std::invalid_argument("usage: reference --neighbors [--reverse]");
            neighborhoods(argc == 3);
            return 0;
        }
        if (argc < 2) throw std::invalid_argument("usage: reference CONTROL.tsv [--replication] [--reverse]");
        bool reverse = false, replication = false;
        for (int i = 2; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (arg == "--reverse" && !reverse) reverse = true;
            else if (arg == "--replication" && !replication) replication = true;
            else throw std::invalid_argument("unknown or duplicate option");
        }
        std::ofstream out(argv[1]);
        out.exceptions(std::ios::badbit | std::ios::failbit);
        controls(out, reverse);
        out.close();
        std::cout << "seed\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tstate_fnv64\n";
        const int first = replication ? 20545 : 19521;
        for (int seed = first; seed < first+1024; ++seed) {
            auto w = field(seed, 20000);
            int births = 0, deaths = 0, recent = 0;
            std::vector<tide::Event> events;
            for (int t = 1; t <= vacancy::field_end; ++t) {
                w.step(&events, reverse);
                for (const auto& e : events) {
                    deaths += e.effect == tide::Effect::death;
                    births += e.effect == tide::Effect::birth;
                    recent += e.effect == tide::Effect::birth && t > vacancy::field_end - 80;
                }
            }
            w.check();
            int living = 0;
            for (int i = 0; i < w.size(); ++i) living += w.at(i).kind == tide::Bank::occupied;
            vacancy::require(1 + births - deaths == living, "unbalanced field");
            std::cout << seed << '\t' << births << '\t' << deaths << '\t' << living << '\t' << recent << '\t'
                      << (!living ? "extinct" : recent ? "reproducing" : "stagnant") << '\t' << w.hash() << '\n';
        }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
