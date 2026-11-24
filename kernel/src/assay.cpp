#include "assay.hpp"

#include <set>

namespace tide {
Assay assay(std::string focal, const std::string& donor, int direction, Access arm,
            Access focal_access, int donor_pc, const FocalTrace& trace) {
    Assay result;
    Config cfg;
    cfg.access = arm;
    cfg.placement = Placement::first_free;
    for (int generation = 0; generation < 3; ++generation) {
        World arena(cfg);
        const int id = arena.index(2, 2);
        arena.seed_site(id, focal);
        arena.set_access(id, focal_access);
        arena.seed_site(arena.neighbor(id, direction), donor, donor_pc);
        std::set<std::string> seen;
        seen.insert(arena.dynamics());
        std::vector<Event> events;
        bool used = false;
        bool birth = false;
        for (int t = 0; t < 64; ++t) {
            arena.step(&events);
            ++result.elapsed;
            for (const auto& e : events) {
                if (e.actor != id) continue;
                if (trace) trace(generation + 1, e);
                used |= (arm.read && e.read_contact.site >= 0) ||
                        (arm.fetch && e.fetch_contact.site >= 0);
                if (e.effect == Effect::birth) {
                    focal = e.product;
                    ++result.generations;
                    result.generations_using_channel += used;
                    birth = true;
                }
            }
            if (birth) break;
            if (!seen.insert(arena.dynamics()).second) {
                result.cycle = true;
                return result;
            }
        }
        if (!birth) return result;
    }
    return result;
}
}
