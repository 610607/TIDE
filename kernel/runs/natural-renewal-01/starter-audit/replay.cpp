// Observe post-death pairs at the opening of each tick in the archived field.
#include "../../vacancy-01/common.hpp"
#include <iostream>

using namespace tide;
using vacancy::require;

struct Watch {
    int actor, site, born, peer, peer_site, peer_born, first, last;
};

int main(int argc, char** argv) {
    try {
        require(argc == 6 || (argc == 7 && std::string_view(argv[6]) == "--reverse"),
                "usage: replay SEED HORIZON HASH2048 HASHEND HASHTAIL [--reverse]");
        const int seed = std::stoi(argv[1]), horizon = std::stoi(argv[2]);
        Config cfg;
        cfg.seed = seed; cfg.width = 16; cfg.height = 4; cfg.max_age = 80;
        cfg.mutation_ppm = 20000; cfg.access.read = true;
        cfg.boundary = Boundary::torus; cfg.placement = Placement::first_free;
        World world(cfg);
        world.seed_site(36, "R..CLD");
        std::vector<Watch> watches;
        Watch watch{};
        while (std::cin >> watch.actor >> watch.site >> watch.born >> watch.peer >> watch.peer_site
                        >> watch.peer_born >> watch.first >> watch.last) watches.push_back(watch);
        require(std::cin.eof(), "invalid pair input");
        std::cout << "seed\tactor\tpeer\ttick\tbearing_site\tsource\ttarget\tfree_neighbors"
                     "\tpending_op\twritten\tpc\top\teffect\tread_site\tread_offset\twrite_offset"
                     "\tinput\toutput\tallocation_after\tallocation_bytes_after\n";
        std::vector<Event> events;
        for (int tick = 1; tick <= horizon + 81; ++tick) {
            std::vector<const Watch*> active;
            for (const auto& w : watches) {
                bool death_boundary = tick == w.last + 1 && tick == w.born + 81 && tick <= w.peer_born + 81;
                if ((w.first <= tick && tick <= w.last) || death_boundary) active.push_back(&w);
            }
            // Save the opening registers before executing the synchronous step.
            struct Opening { int facing, source, target, free, written; char pending; };
            std::vector<Opening> openings;
            for (const Watch* w : active) {
                const auto& actor = world.at(w->site);
                const auto& peer = world.at(w->peer_site);
                require(actor.kind == Bank::occupied && actor.born == Tick(w->born) &&
                        peer.kind == Bank::occupied && peer.born == Tick(w->peer_born) &&
                        actor.bytes == peer.bytes && w->site != w->peer_site, "pair identity mismatch");
                const auto& bank = world.at(actor.cpu.bank).bytes;
                char pending = actor.cpu.pc < int(bank.size()) ? bank.at(actor.cpu.pc) : '-';
                openings.push_back({world.neighbor(w->site, actor.cpu.bearing), actor.cpu.source,
                                    actor.cpu.target, vacancy::free_neighbors(world, w->site),
                                    actor.cpu.written, pending});
            }
            world.step(active.empty() ? nullptr : &events, argc == 7);
            for (size_t i = 0; i < active.size(); ++i) {
                const auto& w = *active[i];
                const auto& o = openings[i];
                auto e = std::find_if(events.begin(), events.end(), [&](const Event& v){ return v.actor == w.site; });
                require(e != events.end() && e->actor_born == Tick(w.born) &&
                        (e->effect == Effect::death) == (tick == w.born + 81),
                        "actor unavailable");
                if (e->effect == Effect::copy && e->read_site == w.peer_site)
                    require(e->read_contact.kind == Bank::occupied && e->read_contact.born == Tick(w.peer_born),
                            "wrong live supplier");
                std::cout << seed << '\t' << w.actor << '\t' << w.peer << '\t' << tick
                          << '\t' << o.facing << '\t' << o.source << '\t' << o.target << '\t' << o.free
                          << '\t' << o.pending << '\t' << o.written << '\t' << e->pc
                          << '\t' << (e->op < 0 ? '-' : char(e->op)) << '\t' << name(e->effect)
                          << '\t' << e->read_site << '\t' << e->read_offset << '\t' << e->write_offset
                          << '\t' << e->input << '\t' << e->output
                          << '\t' << (o.target < 0 ? "-" : vacancy::kind(world.at(o.target).kind))
                          << '\t' << (o.target < 0 ? "-" : vacancy::hex(world.at(o.target).bytes)) << '\n';
            }
            if (tick == 2048) require(world.hash() == argv[3], "2048 hash mismatch");
            if (tick == horizon) require(world.hash() == argv[4], "field hash mismatch");
            if (tick == horizon + 81) require(world.hash() == argv[5], "tail hash mismatch");
        }
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
