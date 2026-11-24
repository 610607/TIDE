// Follow seeded families in the ordinary field without transferring daughters.
#include "assay.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
constexpr char reader[] = "RSCLD";

struct Lineage {
    bool focal_family = false;
    bool transmitted = false;
    int reader_depth = -1;
    int external = 0, from_live = 0, from_free = 0, from_own_reserve = 0, from_other_reserve = 0;
    std::string sources, copied;
};

void run(int patch, bool reader_focal, bool grant, bool empty, bool reverse, std::ostream& births, std::ostream& totals) {
    tide::Config cfg;
    cfg.width = cfg.height = 8;
    cfg.access.read = true;
    cfg.placement = tide::Placement::first_free;
    cfg.boundary = tide::Boundary::torus;
    cfg.max_age = 80;
    cfg.reclamation = empty ? tide::Reclamation::empty : tide::Reclamation::retain;
    tide::World world(cfg);
    const int focal = world.index(4,4);
    world.seed_site(focal, reader_focal ? reader : tide::ancestor);
    world.set_access(focal, {grant, false});
    world.seed_site(world.index(2,2), tide::ancestor);
    for (int i = 0; i < 3; ++i)
        world.seed_site(world.index(5,4+i), i < patch ? reader : tide::ancestor);
    std::vector<Lineage> lineage(world.size());
    lineage[focal].focal_family = true;
    lineage[focal].reader_depth = reader_focal ? 0 : -1;
    std::vector<tide::Event> events;
    const auto group = std::string(empty ? "empty\t" : "retain\t") + std::to_string(patch) + "\t" + (reader_focal ? reader : tide::ancestor) +
                       "\t" + (grant ? "on" : "off");
    int all_births = 0, deaths = 0, recent = 0, founder_births = 0, family_births = 0;
    int reader_births = 0, max_depth = 0, transmitting_daughters = 0, last_reader_birth = 0;
    for (int t = 1; t <= 512; ++t) {
        world.step(&events, reverse);
        world.check();
        for (const auto& e : events) {
            auto& p = lineage[e.actor];
            if (e.effect == tide::Effect::death) {
                ++deaths;
                p = {};
                if (e.actor == focal && e.actor_born == 0 && !grant) world.set_access(focal, cfg.access);
            } else if (e.effect == tide::Effect::reserve && p.focal_family) {
                p.external = p.from_live = p.from_free = p.from_own_reserve = p.from_other_reserve = 0;
                p.copied.clear();
                p.sources.clear();
            } else if (e.effect == tide::Effect::copy && p.focal_family) {
                if (e.read_site != e.actor) {
                    ++p.external;
                    const auto& bank = e.read_contact;
                    if (bank.kind == tide::Bank::occupied) ++p.from_live;
                    else if (bank.kind == tide::Bank::free) ++p.from_free;
                    else if (bank.reservation_owner == e.actor) ++p.from_own_reserve;
                    else ++p.from_other_reserve;
                }
                if (!p.sources.empty()) p.sources += ',';
                p.sources += std::to_string(e.read_site) + "." + std::to_string(e.read_offset);
                if (e.input != e.output) throw std::logic_error("unexpected substitution");
                p.copied.push_back(static_cast<char>(e.input));
            } else if (e.effect == tide::Effect::birth) {
                ++all_births;
                recent += t > 512 - 80;
                auto& child = lineage[e.target];
                child = {};
                if (!p.focal_family) continue;
                if (p.copied != e.product) throw std::logic_error("copy history mismatch");
                child.focal_family = true;
                ++family_births;
                founder_births += e.actor == focal && e.actor_born == 0;
                if (p.reader_depth >= 0 && e.product == reader && p.external > 0) {
                    child.reader_depth = p.reader_depth + 1;
                    ++reader_births;
                    last_reader_birth = t;
                    max_depth = std::max(max_depth, child.reader_depth);
                    if (p.reader_depth > 0 && !p.transmitted) ++transmitting_daughters;
                    p.transmitted = true;
                }
                births << group << '\t' << t << '\t' << e.actor << '\t' << e.actor_born << '\t'
                       << e.target << '\t';
                constexpr char digits[] = "0123456789abcdef";
                for (unsigned char c : e.product) births << digits[c >> 4] << digits[c & 15];
                births << '\t' << p.external << '\t' << p.from_live << '\t' << p.from_free << '\t'
                       << p.from_own_reserve << '\t' << p.from_other_reserve << '\t' << p.sources << '\t' << child.reader_depth << '\n';
            }
        }
    }
    int living = 0, family_living = 0, readers_living = 0;
    for (int i = 0; i < world.size(); ++i) {
        if (world.at(i).kind == tide::Bank::occupied) {
            ++living;
            family_living += lineage[i].focal_family;
            readers_living += lineage[i].reader_depth >= 0;
        }
    }
    if (5 + all_births - deaths != living) throw std::logic_error("population ledger mismatch");
    totals << group << '\t' << founder_births << '\t' << family_births << '\t' << reader_births
           << '\t' << max_depth << '\t' << transmitting_daughters << '\t' << last_reader_birth << '\t'
           << readers_living << '\t' << family_living
           << '\t' << all_births << '\t' << deaths << '\t' << living << '\t' << recent << '\t'
           << (!living ? "extinct" : recent ? "reproducing" : "stagnant") << '\t' << world.hash() << '\n';
}
}

int main(int argc, char** argv) {
    try {
        if ((argc != 4 && argc != 5) || (argc == 5 && std::string_view(argv[4]) != "--reverse") ||
            (std::string_view(argv[3]) != "empty" && std::string_view(argv[3]) != "retain"))
            throw std::invalid_argument("usage: donor_patch TOTALS.tsv BIRTHS.tsv retain|empty [--reverse]");
        std::ofstream totals(argv[1]), births(argv[2]);
        totals.exceptions(std::ios::badbit | std::ios::failbit);
        births.exceptions(std::ios::badbit | std::ios::failbit);
        totals << "reclamation\tpatch_depth\tfocal\tpermission\tfounder_births\tfamily_births\treader_births\tmax_reader_depth"
                  "\ttransmitting_daughters\tlast_reader_birth\treader_living\tfamily_living\tall_births\tdeaths\tliving\tfinal80_births"
                  "\tstatus\tstate_fnv64\n";
        births << "reclamation\tpatch_depth\tfocal\tpermission\ttick\tparent_site\tparent_born\tchild_site\tproduct_hex"
                  "\texternal_bytes\tlive_bytes\tfree_bytes\town_reserved_bytes\tother_reserved_bytes\tread_addresses\treader_depth\n";
        for (int k = 0; k <= 3; ++k)
            for (bool reader_focal : {true, false})
                for (bool grant : {true,false})
                    run(k,reader_focal,grant,std::string_view(argv[3]) == "empty",argc == 5,births,totals);
        totals.close();
        births.close();
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n';
        return 1;
    }
}
