// Read-only observations around calls to the v1 VM.
#include "assay.hpp"

#include <charconv>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
std::string hex(const std::string& bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (unsigned char b : bytes) {
        out += digits[b >> 4];
        out += digits[b & 15];
    }
    return out;
}
char kind(tide::Bank b) {
    switch (b) {
    case tide::Bank::free: return 'f';
    case tide::Bank::reserved: return 'r';
    case tide::Bank::occupied: return 'o';
    }
    throw std::logic_error("invalid bank kind");
}

void survey(const tide::World& world, const std::vector<bool>& attempted) {
    std::vector<int> readers;
    for (int id = 0; id < world.size(); ++id) {
        const auto& s = world.at(id);
        if (s.kind == tide::Bank::occupied && s.bytes == "RSCLD") readers.push_back(id);
    }
    for (int id : readers) {
        if (attempted[id]) continue;
        std::cout << "view\t" << world.tick() << '\t' << id << '\t' << world.at(id).born
                  << '\t' << readers.size() - 1;
        for (int dir = 0; dir < 4; ++dir) {
            const auto& s = world.at(world.neighbor(id, dir));
            std::cout << '\t' << kind(s.kind) << ':' << hex(s.bytes);
        }
        std::cout << '\n';
    }
}

void run(bool read, tide::Tick seed, bool reverse) {
    tide::Config cfg;
    cfg.access = {read, !read};
    cfg.width = cfg.height = 8;
    cfg.boundary = tide::Boundary::torus;
    cfg.placement = tide::Placement::first_free;
    cfg.max_age = 80;
    cfg.mutation_ppm = 20000;
    cfg.seed = seed;
    tide::World world(cfg);
    world.seed_site(world.index(4,4), tide::ancestor);
    std::vector<bool> attempted(world.size()), contacted(world.size());
    std::vector<std::string> inputs(world.size());
    std::vector<tide::Event> events;
    const int end = read ? 512 : 4096;
    for (int t = 1; t <= end; ++t) {
        if (read) survey(world, attempted);
        world.step(&events, reverse);
        world.check();
        for (const auto& e : events) {
            const int id = e.actor;
            const auto& hit = read ? e.read_contact : e.fetch_contact;
            if (hit.site >= 0 && (read || !contacted[id])) {
                std::cout << "hit\t" << t << '\t' << id << '\t' << e.actor_born << '\t'
                          << hit.site << '\t' << kind(hit.kind) << '\t' << hex(hit.bytes) << '\n';
                contacted[id] = true;
            }
            if (read && e.op == 'C' && !attempted[id] && world.at(id).bytes == "RSCLD") {
                if (e.fetch_site != id || e.read_site != world.neighbor(id, 1))
                    throw std::logic_error("reader selected unexpected address");
                std::cout << "attempt\t" << t << '\t' << id << '\t' << e.actor_born << '\t'
                          << tide::name(e.effect) << '\n';
                attempted[id] = true;
            }
            if (e.effect == tide::Effect::reserve) inputs[id].clear();
            if (e.effect == tide::Effect::copy) {
                if (e.write_offset != static_cast<int>(inputs[id].size()))
                    throw std::logic_error("nonsequential copy in allocation");
                inputs[id].push_back(static_cast<char>(e.input));
            }
            if (e.effect == tide::Effect::birth) {
                if (inputs[id].size() != e.product.size()) throw std::logic_error("incomplete copy");
                std::cout << "birth\t" << t << '\t' << id << '\t' << e.actor_born << '\t'
                          << e.target << '\t' << hex(e.product) << '\t' << hex(inputs[id]) << '\n';
                attempted[e.target] = contacted[e.target] = false;
                inputs[e.target].clear();
            } else if (e.effect == tide::Effect::death) {
                std::cout << "death\t" << t << '\t' << id << '\t' << e.actor_born << '\n';
            }
        }
        if (t == 512 || t == 1024 || t == 2048 || t == 4096)
            std::cout << "checkpoint\t" << t << '\t' << world.hash() << '\n';
    }
    if (read) survey(world, attempted);
}
}

int main(int argc, char** argv) {
    try {
        if ((argc != 3 && argc != 4) || (argc == 4 && std::string_view(argv[3]) != "--reverse"))
            throw std::invalid_argument("usage: field read|fetch SEED [--reverse]");
        const std::string_view arm = argv[1], arg = argv[2];
        tide::Tick seed = 0;
        auto parsed = std::from_chars(arg.data(), arg.data()+arg.size(), seed);
        if ((arm != "read" && arm != "fetch") || parsed.ec != std::errc{} ||
            parsed.ptr != arg.data()+arg.size() || seed == 0)
            throw std::invalid_argument("invalid field configuration");
        run(arm == "read", seed, argc == 4);
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n';
        return 1;
    }
}
