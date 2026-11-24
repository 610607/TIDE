#include "assay.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace {
std::string hex(const std::string& s) {
    constexpr char alphabet[] = "0123456789abcdef";
    std::string out;
    for (unsigned char c : s) {
        out += alphabet[c >> 4];
        out += alphabet[c & 15];
    }
    return out;
}
const char* type(tide::Bank kind) {
    if (kind == tide::Bank::occupied) return "occupied";
    if (kind == tide::Bank::reserved) return "reserved";
    return "free";
}
struct Identity { int width, seed, site, born; };
enum class Mode { ordinary, deny_own, deny_all };
void follow(const tide::World& start, Identity id, Mode mode, bool reverse, std::ostream& scores,
            std::ostream& products, std::ostream& windows) {
    tide::World w = start;
    const std::string key = std::to_string(id.width)+"\t"+std::to_string(id.seed)+"\t"+
        std::to_string(id.site)+"\t"+std::to_string(id.born);
    const char* label = mode == Mode::ordinary ? "ordinary" : mode == Mode::deny_own ? "deny_own" : "deny_all";
    const auto digest = w.hash();
    int denied = 0, first_denied = 0, births = 0, reader_births = 0, reads = 0, own_reads = 0;
    std::string inputs;
    int writes_from_own = 0;
    bool first_copy_pending = true;
    std::vector<tide::Event> events;
    while (w.at(id.site).kind == tide::Bank::occupied && w.at(id.site).born == static_cast<tide::Tick>(id.born)) {
        if (w.tick() > static_cast<tide::Tick>(id.born + 80)) throw std::logic_error("focal age overflow");
        const auto& focal = w.at(id.site);
        const auto& c = focal.cpu;
        const auto& code = w.at(c.bank).bytes;
        const bool eligible = w.tick() - focal.born < w.config().max_age;
        const bool external_copy = eligible && c.pc < static_cast<int>(code.size()) && code[c.pc] == 'C' &&
                                   c.source >= 0 && c.source != id.site;
        const bool from_own = external_copy && c.source == c.target;
        const bool block = external_copy && (mode == Mode::deny_all || (mode == Mode::deny_own && from_own));
        if (block) {
            ++denied;
            if (first_denied == 0) first_denied = static_cast<int>(w.tick()+1);
            w.set_access(id.site, {});
        }
        const bool trace = mode == Mode::ordinary && first_copy_pending;
        if (trace) {
            const auto& east = w.at(w.neighbor(id.site,1));
            int free = 0;
            for (int d=0; d<4; ++d) free += w.at(w.neighbor(id.site,d)).kind == tide::Bank::free;
            windows << key << '\t' << w.tick()+1 << '\t' << type(east.kind) << '\t' << east.born << '\t'
                    << east.owner << '\t' << hex(east.bytes) << '\t' << free << '\t';
        }
        w.step(&events, reverse);
        w.check();
        if (block) w.set_access(id.site, start.config().access);
        const auto it = std::find_if(events.begin(),events.end(),[&](const auto& e){ return e.actor == id.site; });
        if (it == events.end()) throw std::logic_error("missing focal attempt");
        const auto& e = *it;
        if (trace) windows << e.op << '\t' << tide::name(e.effect) << '\t' << e.target << '\n';
        if (e.op == 'C') first_copy_pending = false;
        if (block && e.effect != tide::Effect::failed_copy) throw std::logic_error("ineffective mask");
        if (e.effect == tide::Effect::reserve) {
            inputs.clear();
            writes_from_own = 0;
        }
        if (e.effect == tide::Effect::copy) {
            if (e.write_offset != static_cast<int>(inputs.size())) throw std::logic_error("out of order copy");
            inputs.push_back(static_cast<char>(e.input));
            reads += e.read_contact.site >= 0;
            own_reads += from_own;
            writes_from_own += from_own;
        }
        if (e.effect == tide::Effect::birth) {
            ++births;
            reader_births += e.product == "RSCLD";
            if (inputs.size() != e.product.size()) throw std::logic_error("incomplete copy provenance");
            products << key << '\t' << label << '\t' << e.tick << '\t' << e.target << '\t' << hex(inputs)
                     << '\t' << hex(e.product) << '\t' << writes_from_own << '\n';
        }
    }
    scores << key << '\t' << label << '\t' << digest << '\t' << w.tick() << '\t' << denied << '\t'
           << first_denied << '\t' << reads << '\t' << own_reads << '\t' << births << '\t' << reader_births << '\n';
}

void run(Identity id, bool reverse, std::ostream& scores, std::ostream& products, std::ostream& windows) {
    tide::Config cfg;
    cfg.width = id.width; cfg.height = 64/id.width;
    cfg.access.read = true; cfg.boundary = tide::Boundary::torus;
    cfg.placement = tide::Placement::first_free; cfg.seed = id.seed;
    cfg.max_age = 80; cfg.mutation_ppm = 20000;
    tide::World world(cfg);
    world.seed_site(36,tide::ancestor);
    for (int t = 0; t < id.born; ++t) world.step(nullptr,reverse);
    const auto& focal = world.at(id.site);
    if (focal.kind != tide::Bank::occupied || focal.born != static_cast<tide::Tick>(id.born) ||
        focal.bytes != "RSCLD") throw std::logic_error("focal reconstruction differs");
    for (auto mode : {Mode::ordinary,Mode::deny_own,Mode::deny_all})
        follow(world,id,mode,reverse,scores,products,windows);
}
}
int main(int argc, char** argv) {
    try {
        if ((argc != 4 && argc != 5) || (argc == 5 && std::string_view(argv[4]) != "--reverse"))
            throw std::invalid_argument("usage: fork SCORES.tsv PRODUCTS.tsv WINDOWS.tsv [--reverse] < targets");
        std::ofstream scores(argv[1]), products(argv[2]), windows(argv[3]);
        for (auto* out : {&scores,&products,&windows}) {
            out->exceptions(std::ios::failbit | std::ios::badbit);
            *out << "width\tseed\tsite\tborn\t";
        }
        scores << "branch\tstart_fnv64\tdeath\tblocked_attempts\tfirst_block\treads\town_reads\tbirths\treader_births\n";
        products << "branch\ttick\tchild_site\tinputs_hex\tproduct_hex\town_reserved_bytes\n";
        windows << "tick\teast_kind\teast_born\teast_owner\teast_hex\tfree_neighbors\top\teffect\ttarget\n";
        for (std::string line; std::getline(std::cin,line);) {
            std::istringstream row(line);
            Identity id;
            std::string extra;
            if (!(row>>id.width>>id.seed>>id.site>>id.born) || (row>>extra) ||
                (id.width!=4 && id.width!=8 && id.width!=16) || id.seed<321 || id.seed>576 ||
                id.site<0 || id.site>=64 || id.born<1 || id.born>2048)
                throw std::invalid_argument("invalid target identity");
            run(id,argc==5,scores,products,windows);
        }
        scores.close(); products.close(); windows.close();
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
