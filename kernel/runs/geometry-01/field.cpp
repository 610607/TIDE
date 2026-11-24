// Observe a single equal-area geometry run through opening snapshots and resolved VM events.
#include "assay.hpp"

#include <charconv>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
constexpr std::string_view reader = "RSCLD";

std::string bytes(const std::string& value) {
    constexpr char digit[] = "0123456789abcdef";
    std::string result;
    for (unsigned char c : value) {
        result += digit[c >> 4];
        result += digit[c & 15];
    }
    return result;
}
char bank_type(tide::Bank kind) {
    switch (kind) {
    case tide::Bank::occupied: return 'o';
    case tide::Bank::reserved: return 'r';
    case tide::Bank::free: return 'f';
    }
    throw std::logic_error("unknown bank");
}
struct Copies {
    std::string inputs, sources;
    void accept(const tide::Event& e) {
        if (e.write_offset != static_cast<int>(inputs.size()))
            throw std::logic_error("nonsequential copy");
        inputs.push_back(static_cast<char>(e.input));
        // Save external writes with their destination offset. Unlisted offsets
        // read the executing CPU's own bank.
        if (e.read_site == e.actor) return;
        const auto& hit = e.read_contact;
        if (!sources.empty()) sources += ',';
        sources += std::to_string(e.write_offset) + "/" + std::to_string(e.tick) + "/" +
            std::to_string(e.read_site) + "/" + std::to_string(e.read_offset) + "/" +
            bank_type(hit.kind) + "/" + std::to_string(hit.born) + "/" +
            std::to_string(hit.reservation_owner);
    }
};
void window(const tide::World& world, const std::vector<bool>& attempted) {
    std::vector<int> readers;
    for (int id = 0; id < world.size(); ++id) {
        const auto& s = world.at(id);
        if (s.kind == tide::Bank::occupied && s.bytes == reader) readers.push_back(id);
    }
    for (int id : readers) {
        if (attempted[id]) continue;
        std::cout << "window\t" << world.tick() << '\t' << id << '\t' << world.at(id).born
                  << '\t' << readers.size()-1;
        for (int d = 0; d < 4; ++d) {
            const auto& s = world.at(world.neighbor(id, d));
            std::cout << '\t' << bank_type(s.kind) << ':' << bytes(s.bytes);
        }
        std::cout << '\n';
    }
}
void run(int width, tide::Tick seed, bool reverse) {
    tide::Config cfg;
    cfg.width = width;
    cfg.height = 64 / width;
    cfg.access.read = true;
    cfg.boundary = tide::Boundary::torus;
    cfg.placement = tide::Placement::first_free;
    cfg.seed = seed;
    cfg.max_age = 80;
    cfg.mutation_ppm = 20000;
    tide::World world(cfg);
    world.seed_site(36, tide::ancestor);
    std::vector<bool> attempted(world.size());
    std::vector<Copies> allocations(world.size());
    std::vector<tide::Event> events;
    for (int t = 1; t <= 2048; ++t) {
        world.step(&events, reverse);
        world.check();
        for (const auto& e : events) {
            auto& writes = allocations[e.actor];
            if (e.effect == tide::Effect::reserve) writes = {};
            if (e.effect == tide::Effect::copy) writes.accept(e);
            if (e.read_contact.site >= 0) {
                const auto& c = e.read_contact;
                std::cout << "read\t" << t << '\t' << e.actor << '\t' << e.actor_born << '\t' << c.site
                          << '\t' << bank_type(c.kind) << '\t' << bytes(c.bytes) << '\n';
            }
            if (e.op == 'C' && !attempted[e.actor] && world.at(e.actor).bytes == reader) {
                if (e.read_site != world.neighbor(e.actor, 1) || e.fetch_site != e.actor)
                    throw std::logic_error("unexpected reader address");
                attempted[e.actor] = true;
                std::cout << "attempt\t" << t << '\t' << e.actor << '\t' << e.actor_born << '\t'
                          << tide::name(e.effect) << '\n';
            }
            if (e.effect == tide::Effect::birth) {
                if (writes.inputs.size() != e.product.size()) throw std::logic_error("incomplete birth");
                std::cout << "birth\t" << t << '\t' << e.actor << '\t' << e.actor_born << '\t' << e.target
                          << '\t' << bytes(e.product) << '\t' << bytes(writes.inputs) << '\t'
                          << (writes.sources.empty() ? "-" : writes.sources) << '\n';
                attempted[e.target] = false;
                allocations[e.target] = {};
            } else if (e.effect == tide::Effect::death) {
                std::cout << "death\t" << t << '\t' << e.actor << '\t' << e.actor_born << '\n';
            }
        }
        window(world, attempted);
        if (t == 512 || t == 2048)
            std::cout << "hash\t" << t << '\t' << world.hash() << '\n';
    }
}
}
int main(int argc, char** argv) {
    try {
        if ((argc != 3 && argc != 4) || (argc == 4 && std::string_view(argv[3]) != "--reverse"))
            throw std::invalid_argument("usage: field WIDTH SEED [--reverse]");
        auto integer = [](std::string_view text) {
            int n = 0;
            auto result = std::from_chars(text.data(), text.data()+text.size(), n);
            if (result.ec != std::errc{} || result.ptr != text.data()+text.size() || n <= 0)
                throw std::invalid_argument("expected positive integer");
            return n;
        };
        int width = integer(argv[1]);
        if (width != 4 && width != 8 && width != 16) throw std::invalid_argument("invalid field width");
        run(width, integer(argv[2]), argc == 4);
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
