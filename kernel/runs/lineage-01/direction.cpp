// Fork one existing allocation before its first copy. Each row starts from its own factual world.
#include "../vacancy-01/common.hpp"
#include <iostream>
#include <sstream>

using vacancy::require;

namespace {
constexpr int seed = 2437, mother = 20, mother_born = 1663;

struct Window {
    int site, born, number, child, birth, first, last, mother_death, overlap, maternal_reads;
    char direction;
    std::string inputs, product;
};

void follow(tide::World w, const Window& x, std::string_view arm, bool reverse) {
    const auto& focal = w.at(x.site);
    const auto& cpu = focal.cpu;
    require(focal.born == static_cast<tide::Tick>(x.born) && focal.bytes == vacancy::reader &&
            cpu.pc == 2 && cpu.bank == x.site && cpu.written == 0 && cpu.read == 0 &&
            cpu.target == x.child && cpu.source == w.neighbor(x.site,1), "wrong fork state");
    const auto dir = std::string_view("NESW").find(x.direction);
    require(dir < 4 && w.neighbor(x.site,static_cast<int>(dir)) == mother, "mother is not adjacent");
    const auto start = w.hash();
    if (arm != "ordinary") w.aim_for_study(x.site,static_cast<int>(dir));
    if (arm == "maternal_denied") w.set_access(x.site,{});
    const auto fork_hash = w.hash();

    std::vector<tide::Event> events;
    int live = 0, failures = 0;
    std::string inputs, product, provenance, result;
    while (result.empty()) {
        require(w.tick() <= static_cast<tide::Tick>(x.born + w.config().max_age), "past age limit");
        w.step(&events,reverse);
        w.check();
        auto focal_event = std::find_if(events.begin(),events.end(),[&](const auto& e) {
            return e.actor == x.site && e.actor_born == static_cast<tide::Tick>(x.born);
        });
        require(focal_event != events.end(), "missing focal event");
        const auto& e = *focal_event;
        if (e.effect == tide::Effect::copy) {
            const auto& contact = e.read_contact;
            require(contact.site == (arm == "ordinary" ? w.neighbor(x.site,1) : mother) &&
                    e.write_offset == static_cast<int>(inputs.size()) && e.read_offset == e.write_offset,
                    "unexpected source or offset");
            inputs.push_back(static_cast<char>(e.input));
            live += contact.kind == tide::Bank::occupied && contact.site == mother && contact.born == mother_born;
            if (!provenance.empty()) provenance += ',';
            provenance += std::to_string(e.tick) + "/" + std::to_string(contact.site) + "/" +
                vacancy::kind(contact.kind) + "/" + std::to_string(contact.born) + "/" +
                std::to_string(contact.reservation_owner);
        }
        failures += e.effect == tide::Effect::failed_copy;
        if (e.effect == tide::Effect::birth) {
            require(e.target == x.child, "allocation target changed");
            result = "birth";
            product = e.product;
        }
        if (e.effect == tide::Effect::death) result = "death";
    }
    if (arm == "ordinary") require(result == "birth" && w.tick() == static_cast<tide::Tick>(x.birth) &&
        product == x.product && inputs == x.inputs && live == x.maternal_reads, "ordinary history differs");
    if (arm == "maternal_denied")
        require(result == "death" && inputs.empty() && failures > 0, "ineffective read denial");
    const bool exact = inputs == vacancy::reader && product == vacancy::reader && live == 5;
    std::cout << seed << '\t' << x.site << '\t' << x.born << '\t' << x.number << '\t' << x.first
        << '\t' << x.child << '\t' << arm << '\t' << start << '\t' << fork_hash << '\t' << result
        << '\t' << w.tick() << '\t' << (inputs.empty() ? "-" : vacancy::hex(inputs))
        << '\t' << (product.empty() ? "-" : vacancy::hex(product)) << '\t' << live << '\t' << exact
        << '\t' << failures << '\t' << (provenance.empty() ? "-" : provenance) << '\t' << w.hash() << '\n';
}
}

int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 3 || (argc == 3 && std::string_view(argv[2]) != "--reverse"))
            throw std::invalid_argument("usage: direction daughter-windows.tsv [--reverse]");
        std::ifstream stream(argv[1]);
        std::string line;
        require(static_cast<bool>(std::getline(stream,line)), "missing daughter windows");
        std::cout << "seed\tdaughter_site\tdaughter_born\tbirth_number\tfirst_copy\treservation\tarm\tstart_hash"
            "\tfork_hash\tresult\tend_tick\tinputs_hex\tproduct_hex\tlive_maternal_bytes\texact_live_birth"
            "\tfailed_copies\tprovenance\tend_hash\n";
        while (std::getline(stream,line)) {
            Window x{};
            std::istringstream row(line);
            std::string extra;
            int s;
            require(static_cast<bool>(row >> s >> x.site >> x.born >> x.number >> x.child >> x.birth >>
                x.first >> x.last >> x.direction >> x.mother_death >> x.overlap >> x.maternal_reads >>
                x.inputs >> x.product) && !(row >> extra) && s == seed, "bad window");
            auto w = vacancy::initial(seed);
            while (static_cast<int>(w.tick()) < x.first - 1) w.step(nullptr,argc == 3);
            for (auto arm : {"ordinary","maternal","maternal_denied"}) follow(w,x,arm,argc == 3);
        }
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
