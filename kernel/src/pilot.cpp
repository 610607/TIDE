#include "assay.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <tuple>

using namespace tide;

namespace {
int parse_seed(std::string_view text) {
    int value = 0;
    auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size() || value < 1)
        throw std::invalid_argument("seed must be a positive integer");
    return value;
}
std::string hex(const std::string& bytes) {
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (unsigned char byte : bytes) out << std::setw(2) << static_cast<int>(byte);
    return out.str();
}
const char* bank_name(Bank kind) {
    constexpr std::array names{"free", "reserved", "occupied"};
    return names.at(static_cast<unsigned>(kind));
}
struct Exposure {
    Tick tick = 0;
    int direction = -1;
    Contact bank;
};
struct Subject {
    int site = -1;
    Tick born = 0;
    std::string genome;
    Exposure first;
};
struct Individual {
    Subject self;
    std::optional<Subject> qualifying_parent;
};
Config pilot_config(std::string_view arm, int seed) {
    Config cfg;
    if (arm == "read") cfg.access.read = true;
    else if (arm == "fetch") cfg.access.fetch = true;
    else if (arm != "self") throw std::invalid_argument("unknown arm");
    cfg.width = cfg.height = 8;
    cfg.boundary = Boundary::torus;
    cfg.placement = Placement::first_free;
    cfg.max_age = 80;
    cfg.mutation_ppm = 20000;
    cfg.seed = seed;
    return cfg;
}

std::string scores(const Assay& result) {
    return std::to_string(result.generations) + "/" + std::to_string(result.generations_using_channel) +
           "/" + std::to_string(result.elapsed) + "/" + (result.cycle ? "1" : "0");
}
struct Paired {
    Assay on, off, ancestor_on, ancestor_off;
    std::string outcome;
};
class Assays {
    using Key = std::tuple<std::string, std::string, int, bool, bool>;
    std::map<Key, Assay> cache;
    Assay run(const std::string& focal, const Exposure& first, Access arm, bool allow) {
        Key key{focal, first.bank.bytes, first.direction, arm.read, allow};
        auto [it, inserted] = cache.try_emplace(key);
        if (inserted)
            it->second = assay(focal, first.bank.bytes, first.direction, arm, allow ? arm : Access{});
        return it->second;
    }
public:
    Paired test(const Subject& subject, Access arm) {
        Paired p{};
        auto& first = subject.first;
        if (first.bank.kind != Bank::occupied) {
            p.outcome = "nonlive_contact";
            return p;
        }
        p.on = run(subject.genome, first, arm, true);
        p.off = run(subject.genome, first, arm, false);
        p.ancestor_on = run(ancestor, first, arm, true);
        p.ancestor_off = run(ancestor, first, arm, false);
        if (p.ancestor_on.generations != 3 || p.ancestor_off.generations != 3)
            p.outcome = "control_failed";
        else if (p.on.generations == 3 && p.off.generations == 3)
            p.outcome = "both_reproduce";
        else if (p.on.generations_using_channel == 3 && p.off.cycle)
            p.outcome = "dependent";
        else p.outcome = "inconclusive";
        return p;
    }
};
void subject_row(std::ostream& out, const Subject& sub, const Paired& p) {
    const auto& f = sub.first;
    out << '\t' << sub.site << '\t' << sub.born << '\t' << hex(sub.genome)
        << '\t' << f.tick << '\t' << f.direction << '\t' << f.bank.site
        << '\t' << bank_name(f.bank.kind) << '\t' << f.bank.born << '\t' << f.bank.reservation_owner
        << '\t' << hex(f.bank.bytes) << '\t' << p.outcome;
    if (p.outcome == "nonlive_contact") out << "\t-\t-\t-\t-";
    else out << '\t' << scores(p.on) << '\t' << scores(p.off)
             << '\t' << scores(p.ancestor_on) << '\t' << scores(p.ancestor_off);
}
void link_header(std::ostream& out) {
    out << "arm\tseed\ttick\tdaughter_site\tdaughter_hex\tconfirmed";
    for (auto role : {"mother", "child"})
        for (auto field : {"site","born","genome","contact_tick","direction","donor_site","bank",
                           "donor_born","reservation_owner","donor_hex","result","on","off",
                           "ancestor_on","ancestor_off"})
            out << '\t' << role << '_' << field;
    out << '\n';
}
void trace_header(std::ostream& out) {
    out << "tick\tactor\tborn\tfetch_site\tpc\top\teffect\tread_site\tread_offset\ttarget"
           "\twrite_offset\tinput\toutput\tproduct_hex\tfetch_kind\tfetch_born\tfetch_owner"
           "\tfetch_hex\tread_kind\tread_born\tread_owner\tread_hex\n";
}
void trace_row(std::ostream& out, const Event& e) {
    out << e.tick << '\t' << e.actor << '\t' << e.actor_born << '\t' << e.fetch_site << '\t' << e.pc
        << '\t' << e.op << '\t' << name(e.effect) << '\t' << e.read_site << '\t' << e.read_offset
        << '\t' << e.target << '\t' << e.write_offset << '\t' << e.input << '\t' << e.output
        << '\t' << hex(e.product);
    for (auto bank : {&e.fetch_contact, &e.read_contact}) {
        if (bank->site == -1) out << "\t-\t-\t-\t-";
        else out << '\t' << bank_name(bank->kind) << '\t' << bank->born << '\t'
                 << bank->reservation_owner << '\t' << hex(bank->bytes);
    }
    out << '\n';
}

void run(const std::string& arm, int seed, Assays& assays, std::ostream* summary,
         std::ostream* links, std::ostream* trace) {
    const auto cfg = pilot_config(arm, seed);
    World world(cfg);
    const int root = world.index(4,4);
    world.seed_site(root, ancestor);
    std::vector<Individual> population(world.size());
    population[root].self = {root, 0, ancestor, {}};
    std::vector<Event> events;
    int births = 0, deaths = 0, qualifying = 0, pairs = 0, confirmed = 0, recent = 0;
    Tick first_pair = 0;
    std::array<int, 3> contacts{};
    for (int t = 1; t <= 512; ++t) {
        world.step(&events);
        world.check();
        for (auto& e : events) {
            auto& actor = population[e.actor];
            if (trace) trace_row(*trace, e);
            if (e.effect == Effect::death) { ++deaths; continue; }
            const Contact& hit = cfg.access.read ? e.read_contact : e.fetch_contact;
            if (hit.site >= 0) {
                ++contacts.at(static_cast<unsigned>(hit.kind));
                if (actor.self.first.tick == 0) {
                    int dir = 0;
                    while (dir < 4 && world.neighbor(e.actor, dir) != hit.site) ++dir;
                    if (dir == 4) throw std::logic_error("nonlocal contact");
                    actor.self.first = {e.tick, dir, hit};
                }
            }
            if (e.effect != Effect::birth) continue;
            ++births;
            recent += t > 512 - 80;
            Individual newborn{{e.target, e.tick, e.product, {}}, {}};
            if (actor.self.first.tick) {
                ++qualifying;
                newborn.qualifying_parent = actor.self;
                if (actor.qualifying_parent) {
                    ++pairs;
                    if (!first_pair) first_pair = e.tick;
                    if (links) {
                        const auto& mother = *actor.qualifying_parent;
                        const auto ma = assays.test(mother, cfg.access);
                        const auto ca = assays.test(actor.self, cfg.access);
                        const bool positive = ma.outcome == "dependent" && ca.outcome == "dependent";
                        confirmed += positive;
                        *links << arm << '\t' << seed << '\t' << e.tick << '\t' << e.target << '\t'
                               << hex(e.product) << '\t' << positive;
                        subject_row(*links, mother, ma);
                        subject_row(*links, actor.self, ca);
                        *links << '\n';
                    }
                }
            }
            population[e.target] = std::move(newborn);
        }
    }
    int living = 0;
    for (int i = 0; i < world.size(); ++i) living += world.at(i).kind == Bank::occupied;
    if (living != 1 + births - deaths) throw std::logic_error("population ledger mismatch");
    if (summary)
        *summary << arm << '\t' << seed << '\t' << (living == 0 ? "extinct" : recent ? "reproducing" : "stagnant")
                 << '\t' << births << '\t' << deaths << '\t' << living << '\t' << recent
                 << '\t' << contacts[0] << '\t' << contacts[1] << '\t' << contacts[2]
                 << '\t' << qualifying << '\t' << pairs << '\t' << first_pair << '\t' << confirmed
                 << '\t' << world.hash() << '\n';
}
}
int main(int argc, char** argv) {
    try {
        Assays assays;
        const bool pilot = argc == 3 && std::string_view(argv[1]) == "pilot";
        if (pilot || (argc == 5 && std::string_view(argv[1]) == "batch")) {
            const int first = pilot ? 1 : parse_seed(argv[2]);
            const int last = pilot ? 8 : parse_seed(argv[3]);
            if (first > last) throw std::invalid_argument("reversed seed range");
            std::ofstream links(argv[pilot ? 2 : 4]);
            links.exceptions(std::ios::badbit | std::ios::failbit);
            link_header(links);
            std::cout << "arm\tseed\tstatus\tbirths\tdeaths\tliving\tfinal80_births\tfree_contacts"
                         "\treserved_contacts\tlive_contacts\texposed_births\tcandidate_births\tfirst_candidate_tick"
                         "\tconfirmed_births\tstate_fnv64\n";
            for (auto arm : {"self", "read", "fetch"})
                for (int seed = first; ; ++seed) {
                    run(arm, seed, assays, &std::cout, &links, nullptr);
                    if (seed == last) break;
                }
            links.close();
        } else if (argc == 4 && std::string_view(argv[1]) == "trace") {
            trace_header(std::cout);
            run(argv[2], parse_seed(argv[3]), assays, nullptr, nullptr, &std::cout);
        } else if (argc == 6 && std::string_view(argv[1]) == "assay") {
            const auto arm = pilot_config(argv[2], 1).access;
            const std::string_view directions = "NESW", arg = argv[5];
            const auto dir = directions.find(arg);
            if (arg.size() != 1 || dir == directions.npos)
                throw std::invalid_argument("direction must be N, E, S or W");
            std::cout << "branch\tgeneration\t";
            trace_header(std::cout);
            for (bool control : {false, true}) for (bool allow : {true, false}) {
                const std::string branch = std::string(control ? "ancestor_" : "focal_") + (allow ? "on" : "off");
                auto witness = [&](int generation, const Event& e) {
                    std::cout << branch << '\t' << generation << '\t';
                    trace_row(std::cout, e);
                };
                auto result = assay(control ? ancestor : argv[3], argv[4], static_cast<int>(dir),
                                    arm, allow ? arm : Access{}, 0, witness);
                std::cerr << branch << '\t' << scores(result) << '\n';
            }
        } else throw std::invalid_argument("usage: tide pilot LINKS.tsv | tide batch FIRST LAST LINKS.tsv | tide trace ARM SEED | "
                                           "tide assay ARM GENOME DONOR DIRECTION");
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n';
        return 1;
    }
}
