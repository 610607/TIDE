#include "../vacancy-01/common.hpp"

#include <iostream>
#include <optional>
#include <sstream>

namespace {
using vacancy::hex;
using vacancy::require;
using tide::Bank;
using tide::Effect;
using tide::World;

struct Files {
    std::ofstream lives, births, copies, template_uses;
    explicit Files(const std::string& dir) :
        lives(vacancy::output(dir, "lifetimes.tsv",
            "case_id\tarm\trole\tpermission\tsite\tborn\tgenome_hex\tstart_hash\tdeath\tend_hash\tinitial_living\tworld_births\tworld_deaths\tliving\tfinal80_births\tstatus\treserve_requests\treservations\tfocal_births\texternal_reads\tblocked_attempts\tfirst_reserve\tpin_tick\tpin_site\tpin_hash\twithdrawal\tfirst_outcome\ttemplate_bytes")),
        births(vacancy::output(dir, "births.tsv",
            "case_id\tarm\trole\tpermission\tparent_site\tparent_born\tallocation\tsite\tborn\topening_hex\tinputs_hex\tproduct_hex\texternal_bytes\ttemplate_bytes")),
        copies(vacancy::output(dir, "copies.tsv",
            "case_id\tarm\trole\tpermission\tsite\tborn\tallocation\ttick\ttarget\twrite_offset\tsource\tread_offset\tbank\tbank_hex\tbank_born\towner\tsupplied\tinput_hex\toutput_hex")),
        template_uses(vacancy::output(dir, "template-uses.tsv",
            "case_id\tarm\ttemplate_site\ttemplate_born\ttemplate_hex\tcopier_site\tcopier_born\tproduct_site\tproduct_born\tproduct_hex\tbytes_from_template\taligned_bytes\tcopy_ticks")) {}
};

int living(const World& w) {
    int count = 0;
    for (int i=0; i<w.size(); ++i) count += w.at(i).kind == Bank::occupied;
    return count;
}

struct Newborn { int site; World field; };
struct Life {
    int births = 0, blocked = 0;
    std::optional<Newborn> first;
};

struct TemplateUse {
    int bytes=0, aligned=0;
    std::string ticks;
};

Life follow(Files& files, const std::string& id, const std::string& arm, const std::string& role,
            const World& start, int site, bool allow, bool reverse) {
    World w = start;
    const auto born = w.tick();
    const auto genome = w.at(site).bytes;
    require(w.at(site).born == born && w.at(site).kind == Bank::occupied, "expected a newborn");
    const bool daughter = role == "daughter";
    const bool treat = daughter && arm == "matched";
    const std::string key = id+"\t"+arm+"\t"+role+"\t"+(allow ? "on" : "off");
    if (!allow) w.set_access(site, {});
    const int initial = living(w);
    Life result;
    int population_births=0, deaths=0, recent=0, requests=0, allocations=0;
    int external=0, supplied=0, product_external=0, product_supplied=0;
    int first_reserve=-1, pin_tick=-1, withdrawal=-1;
    std::string pin_hash="-", outcome="no_allocation", inputs, opening;
    bool first_active = false;
    tide::ReadTemplate buffer{site,-1,genome};
    std::vector<tide::Event> events;
    std::vector<TemplateUse> uses(w.size());
    while (w.at(site).kind == Bank::occupied && w.at(site).born == born) {
        const auto& cpu = w.at(site).cpu;
        const auto& code = w.at(cpu.bank).bytes;
        if (daughter && first_active && buffer.source < 0 && w.tick()-born < w.config().max_age &&
            cpu.pc < static_cast<int>(code.size()) && code[cpu.pc] == 'C' &&
            cpu.source >= 0 && cpu.source != site) {
            buffer.source = cpu.source;
            pin_tick = static_cast<int>(w.tick()+1);
            pin_hash = w.hash();
        }
        const bool active = treat && first_active && buffer.source >= 0;
        w.step(&events, reverse, active ? &buffer : nullptr);
        for (const auto& e : events) {
            population_births += e.effect == Effect::birth;
            deaths += e.effect == Effect::death;
            recent += e.effect == Effect::birth && e.tick > born+1;
            if (e.supplied_template) require(active && e.actor == site && e.read_site == buffer.source &&
                                              allow && e.effect == Effect::copy, "template escaped scope");
            if (!daughter && allow && e.actor != site) {
                auto& use = uses[e.actor];
                if (e.effect == Effect::reserve) use = {};
                if (e.effect == Effect::copy && e.read_site == site &&
                    e.read_contact.kind == Bank::occupied && e.read_contact.born == born) {
                    require(e.read_contact.bytes==genome, "grandchild template changed");
                    ++use.bytes;
                    use.aligned += e.read_offset==e.write_offset;
                    if (!use.ticks.empty()) use.ticks += ',';
                    use.ticks += std::to_string(e.tick);
                }
                if (e.effect == Effect::birth && use.bytes) {
                    files.template_uses << id << '\t' << arm << '\t' << site << '\t' << born << '\t'
                        << hex(genome) << '\t' << e.actor << '\t' << e.actor_born << '\t' << e.target << '\t'
                        << e.tick << '\t' << hex(e.product) << '\t' << use.bytes << '\t' << use.aligned
                        << '\t' << use.ticks << '\n';
                }
            }
            if (e.actor != site) continue;
            require(e.actor_born == born, "focal identity changed");
            if (!allow && e.op=='C' && e.read_site>=0 && e.read_site!=site) {
                require(e.effect==Effect::failed_copy, "denied copy succeeded");
                ++result.blocked;
            }
            requests += e.effect == Effect::reserve || e.effect == Effect::busy;
            if (e.effect == Effect::reserve) {
                ++allocations;
                first_active = allocations == 1;
                if (first_active) first_reserve = static_cast<int>(e.tick);
                opening = w.at(e.target).bytes;
                inputs.clear();
                product_external = product_supplied = 0;
            } else if (e.effect == Effect::copy) {
                const bool self = e.read_site == site;
                const auto& bank_bytes = self ? genome : e.read_contact.bytes;
                const auto& seen = e.supplied_template ? genome : bank_bytes;
                require(e.write_offset == static_cast<int>(inputs.size()) &&
                        static_cast<unsigned char>(seen.at(e.read_offset)) == e.input, "input trace mismatch");
                require(e.supplied_template == (active && e.read_site == buffer.source), "template was bypassed");
                const std::string byte(1, static_cast<char>(e.input));
                inputs += byte;
                external += !self; product_external += !self;
                supplied += e.supplied_template; product_supplied += e.supplied_template;
                files.copies << key << '\t' << site << '\t' << born << '\t' << allocations << '\t'
                             << e.tick << '\t' << e.target << '\t' << e.write_offset << '\t'
                             << e.read_site << '\t' << e.read_offset << '\t'
                             << (self ? "self" : vacancy::kind(e.read_contact.kind)) << '\t' << hex(bank_bytes)
                             << '\t' << (self ? born : e.read_contact.born) << '\t'
                             << (self ? -1 : e.read_contact.reservation_owner) << '\t' << e.supplied_template
                             << '\t' << hex(byte) << '\t' << hex(std::string(1,static_cast<char>(e.output))) << '\n';
            } else if (e.effect == Effect::birth) {
                ++result.births;
                require(inputs.size() == e.product.size(), "incomplete birth trace");
                files.births << key << '\t' << site << '\t' << born << '\t' << allocations << '\t'
                             << e.target << '\t' << e.tick << '\t' << hex(opening) << '\t' << hex(inputs) << '\t' << hex(e.product)
                             << '\t' << product_external << '\t' << product_supplied << '\n';
                if (daughter && first_active) result.first.emplace(Newborn{e.target,w});
            }
            if (first_active && (e.effect == Effect::birth || e.effect == Effect::failed_division ||
                                 e.effect == Effect::death)) {
                withdrawal = static_cast<int>(e.tick);
                outcome = tide::name(e.effect);
                first_active = false;
            }
        }
        w.check();
    }
    if (!allow) w.set_access(site, start.config().access);
    const int survivors = living(w);
    require(w.tick() == born+81 && initial+population_births-deaths == survivors, "lifetime ledger differs");
    files.lives << key << '\t' << site << '\t' << born << '\t' << hex(genome) << '\t' << start.hash()
                << '\t' << w.tick() << '\t' << w.hash() << '\t' << initial << '\t' << population_births
                << '\t' << deaths << '\t' << survivors << '\t' << recent << '\t'
                << (!survivors ? "extinct" : recent ? "reproducing" : "stagnant") << '\t'
                << requests << '\t' << allocations << '\t' << result.births << '\t' << external << '\t'
                << result.blocked << '\t' << first_reserve << '\t' << pin_tick << '\t' << buffer.source
                << '\t' << pin_hash << '\t' << withdrawal << '\t' << outcome << '\t' << supplied << '\n';
    return result;
}

void controls(Files& files, bool reverse) {
    tide::Config cfg;
    cfg.max_age = 80;
    cfg.access.read = true;
    World start(cfg);
    const int site = start.index(2,2);
    start.seed_site(site,"R.SCLD");
    auto baseline = follow(files,"control","ordinary","daughter",start,site,true,reverse);
    auto matched = follow(files,"control","matched","daughter",start,site,true,reverse);
    auto denied = follow(files,"control","matched","daughter",start,site,false,reverse);
    require(!baseline.births && matched.first && !denied.births && denied.blocked &&
            matched.first->field.at(matched.first->site).bytes == "R.SCLD" &&
            matched.first->field.at(start.neighbor(site,1)).bytes.empty(), "empty-bank control failed");
}
}

int main(int argc, char** argv) {
    try {
        if ((argc!=2 && argc!=3) || (argc==3 && std::string_view(argv[2])!="--reverse"))
            throw std::invalid_argument("usage: pulse OUT [--reverse] < archived-targets");
        Files files(argv[1]);
        const bool reverse = argc==3;
        controls(files,reverse);
        for (std::string line; std::getline(std::cin,line);) {
            std::istringstream in(line);
            int seed, site, born;
            std::string genome, hash, extra;
            if (!(in>>seed>>site>>born>>genome>>hash) || in>>extra) throw std::invalid_argument("invalid target");
            tide::Config cfg;
            cfg.width=16; cfg.height=4; cfg.seed=seed; cfg.max_age=80; cfg.mutation_ppm=20000;
            cfg.access.read=true; cfg.boundary=tide::Boundary::torus; cfg.placement=tide::Placement::first_free;
            World w(cfg);
            w.seed_site(36,"R..CLD");
            while (w.tick()<static_cast<tide::Tick>(born)) w.step(nullptr,reverse);
            require(w.hash()==hash && hex(w.at(site).bytes)==genome, "archived daughter differs");
            const std::string id = std::to_string(seed)+"-"+std::to_string(site)+"-"+std::to_string(born);
            for (const std::string arm : {"ordinary","matched"}) {
                auto daughter = follow(files,id,arm,"daughter",w,site,true,reverse);
                if (daughter.first) {
                    const auto& kid = *daughter.first;
                    follow(files,id,arm,"grandchild",kid.field,kid.site,true,reverse);
                    follow(files,id,arm,"grandchild",kid.field,kid.site,false,reverse);
                }
            }
        }
        files.lives.close(); files.births.close(); files.copies.close(); files.template_uses.close();
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
