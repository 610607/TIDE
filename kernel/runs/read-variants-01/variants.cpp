#include "../vacancy-01/common.hpp"

#include <iostream>
#include <sstream>

void tide::World::replace_newborn(int site, const std::string& original, const std::string& assigned) {
    auto& s = sites_.at(site);
    if (s.kind != Bank::occupied || s.born != tick_ || s.bytes != original ||
        assigned.size() != original.size()) throw std::logic_error("invalid newborn assignment");
    s.bytes = assigned;
}

namespace {
using vacancy::hex;
using vacancy::require;
constexpr std::string_view alphabet = "R.JTSH+>CLDP";
const std::string reader = "RSCLD", padded = "R.SCLD";

struct Files {
    std::ofstream cases, lives, products;
    explicit Files(const std::string& dir) :
        cases(vacancy::output(dir, "cases.tsv", "case_id\tpanel\tseed\tsite\tborn\tassigned\tsecond_source\tbackground_hash\tstart_hash\tordinary_births\tdenied_births\tdependent\tdaughters_tested\tdependent_daughters\tdependent_same_sequence")),
        lives(vacancy::output(dir, "lifetimes.tsv", "case_id\trole\tsite\tborn\tgenome_hex\tpermission\tstart_hash\tend_hash\tdeath\tinitial_living\tworld_births\tworld_deaths\tliving\tfinal80_births\tstatus\tfocal_births\texternal_reads\tblocked_attempts\tslot1_executions")),
        products(vacancy::output(dir, "products.tsv", "case_id\trole\tparent_site\tparent_born\tpermission\tchild_site\tchild_born\tinputs_hex\tproduct_hex\treads")) {}
};

int living(const tide::World& w) {
    int n = 0;
    for (int i = 0; i < w.size(); ++i) n += w.at(i).kind == tide::Bank::occupied;
    return n;
}

struct Newborn {
    int site;
    tide::World field;
};
struct Lifetime {
    int births = 0, blocked = 0;
    std::vector<Newborn> children;
};

Lifetime follow(Files& files, const std::string& label, const tide::World& start, int site,
                bool allow, bool save_children, bool reverse) {
    tide::World w = start;
    const auto born = w.at(site).born;
    const auto genome = w.at(site).bytes;
    require(w.tick() == born && w.at(site).kind == tide::Bank::occupied, "expected newborn");
    const int initial = living(w);
    const auto prefix = label + "\t" + std::to_string(site) + "\t" + std::to_string(born);
    const auto grant = allow ? "on" : "off";
    if (!allow) w.set_access(site, {});
    int births = 0, deaths = 0, recent = 0, external = 0, slot = 0;
    Lifetime focal;
    std::string inputs, sources;
    std::vector<tide::Event> events;
    while (w.at(site).kind == tide::Bank::occupied && w.at(site).born == born) {
        w.step(&events, reverse);
        for (const auto& e : events) {
            births += e.effect == tide::Effect::birth;
            deaths += e.effect == tide::Effect::death;
            recent += e.effect == tide::Effect::birth && e.tick > born + 1;
            if (e.actor != site) continue;
            require(e.actor_born == born, "unexpected CPU at focal site");
            slot += e.fetch_site == site && e.pc == 1 && e.op >= 0;
            if (!allow && e.op == 'C' && e.read_site >= 0 && e.read_site != site) {
                require(e.effect == tide::Effect::failed_copy, "ineffective permission mask");
                ++focal.blocked;
            }
            if (e.effect == tide::Effect::reserve) {
                inputs.clear();
                sources.clear();
            } else if (e.effect == tide::Effect::copy) {
                require(e.write_offset == static_cast<int>(inputs.size()), "unordered writes");
                inputs += static_cast<char>(e.input);
                const bool self = e.read_site == site;
                external += !self;
                const auto kind = self ? "self" : vacancy::kind(e.read_contact.kind);
                if (!sources.empty()) sources += ',';
                sources += std::to_string(e.read_site) + "/" + std::to_string(e.read_offset) + "/" +
                           kind + "/" + std::to_string(self ? born : e.read_contact.born) + "/" +
                           std::to_string(e.tick);
            } else if (e.effect == tide::Effect::birth) {
                require(e.product.size() == inputs.size(), "incomplete copy history");
                ++focal.births;
                files.products << prefix << '\t' << grant << '\t' << e.target << '\t' << e.tick
                               << '\t' << hex(inputs) << '\t' << hex(e.product) << '\t' << sources << '\n';
                if (save_children) focal.children.push_back({e.target, w});
            }
        }
        w.check();
    }
    if (!allow) w.set_access(site, start.config().access);
    const int survivors = living(w);
    require(w.tick() == born + 81 && initial + births - deaths == survivors, "lifetime ledger mismatch");
    files.lives << prefix << '\t' << hex(genome) << '\t' << grant << '\t' << start.hash() << '\t'
                << w.hash() << '\t' << w.tick() << '\t' << initial << '\t' << births << '\t' << deaths
                << '\t' << survivors << '\t' << recent << '\t'
                << (!survivors ? "extinct" : recent ? "reproducing" : "stagnant") << '\t'
                << focal.births << '\t' << external << '\t' << focal.blocked << '\t' << slot << '\n';
    return focal;
}

bool dependent(const Lifetime& ordinary, const Lifetime& denied) {
    if (!ordinary.births || denied.births) return false;
    require(denied.blocked > 0, "lost births without blocking a read");
    return true;
}

void assay(Files& files, const tide::World& start, int site, const std::string& background,
           const std::string& program, const std::string& panel, const std::string& second, bool reverse) {
    const std::string id = std::to_string(start.config().seed) + "-" + std::to_string(site) + "-" +
                           std::to_string(start.tick()) + "-" + hex(program) + "-" + second;
    const auto parent = follow(files, id+"\tfocal", start, site, true, true, reverse);
    const auto denied = follow(files, id+"\tfocal", start, site, false, false, reverse);
    const bool positive = dependent(parent, denied);
    int tested = 0, inherited = 0, retained = 0;
    if (positive || panel == "supplied") {
        for (const auto& kid : parent.children) {
            auto on = follow(files, id+"\tdaughter", kid.field, kid.site, true, false, reverse);
            auto off = follow(files, id+"\tdaughter", kid.field, kid.site, false, false, reverse);
            ++tested;
            if (dependent(on, off)) {
                ++inherited;
                retained += kid.field.at(kid.site).bytes == program;
            }
        }
    }
    files.cases << id << '\t' << panel << '\t' << start.config().seed << '\t' << site << '\t'
                << start.tick() << '\t' << program << '\t' << second << '\t' << background << '\t'
                << start.hash() << '\t' << parent.births << '\t' << denied.births << '\t' << positive
                << '\t' << tested << '\t' << inherited << '\t' << retained << '\n';
}

void natural(Files& files, int seed, int site, int born, const std::string& expected_hash, bool reverse) {
    auto field = vacancy::initial(seed);
    while (field.tick() < static_cast<tide::Tick>(born)) field.step(nullptr, reverse);
    require(field.hash() == expected_hash && field.at(site).bytes == reader, "archived background differs");
    auto assign = [&](const std::string& program, const char* panel) {
        auto w = field;
        w.replace_newborn(site, reader, program);
        assay(files, w, site, expected_hash, program, panel, "-", reverse);
    };
    assign(reader, "control");
    for (size_t i = 0; i < reader.size(); ++i) {
        for (char op : alphabet) {
            if (op == reader[i]) continue;
            std::string program = reader;
            program[i] = op;
            assign(program, "substitution");
        }
    }
    auto order = reader;
    std::sort(order.begin(), order.end());
    do {
        if (order != reader) assign(order, "permutation");
    } while (std::next_permutation(order.begin(), order.end()));
}

void supplied(Files& files, bool reverse) {
    tide::Config c;
    c.width = c.height = 8;
    c.boundary = tide::Boundary::torus;
    c.placement = tide::Placement::first_free;
    c.access.read = true;
    c.max_age = 80;
    for (char symbol : alphabet) {
        std::string variant = padded;
        variant[1] = symbol;
        for (bool match : {false, true}) {
            tide::World w(c);
            const int site = w.index(4,4);
            w.seed_site(site, padded);
            w.seed_site(w.index(2,2), "R.CLD");
            w.seed_site(w.index(5,4), variant);
            w.seed_site(w.index(5,5), match ? variant : padded);
            w.seed_site(w.index(5,6), padded);
            assay(files, w, site, w.hash(), variant, "supplied", match ? "matched" : "original", reverse);
        }
    }
}
}

int main(int argc, char** argv) {
    try {
        if ((argc != 2 && argc != 3) || (argc == 3 && std::string_view(argv[2]) != "--reverse"))
            throw std::invalid_argument("usage: variants OUTPUT_DIR [--reverse] < targets");
        Files files(argv[1]);
        const bool reverse = argc == 3;
        int seed, site, born;
        std::string hash;
        for (std::string line; std::getline(std::cin, line);) {
            std::istringstream row(line);
            std::string extra;
            if (!(row >> seed >> site >> born >> hash) || (row >> extra) || (seed != 3562 && seed != 11942) ||
                site < 0 || site >= 64 || born < 1 || born > 2048) throw std::invalid_argument("invalid target");
            natural(files, seed, site, born, hash, reverse);
        }
        supplied(files, reverse);
        files.cases.close(); files.products.close(); files.lives.close();
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
