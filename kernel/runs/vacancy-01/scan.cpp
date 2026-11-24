#include "common.hpp"
#include <iostream>

using namespace vacancy;
namespace {
struct Reader {
    int site, born;
    int attempt = 0, first_donor = -1, births = 0, death = 0;
    std::string first_bank = "-", first_hex = "-", effect = "-";
    int encounter = 0;
};
struct Encounter {
    int id, opening, donor_born, free;
    std::vector<int> eligible;
    std::string start_hash, end_hash;
};
void scan(int seed, bool reverse, std::ostream& seeds, std::ostream& readers, std::ostream& encounters) {
    auto w = initial(seed);
    const std::string cohort = seed <= 576 ? "historical" : "prospective";
    std::array<int,64> index;
    index.fill(-1);
    std::vector<Reader> people;
    std::vector<Encounter> cases;
    std::vector<tide::Event> events;
    int horizon = field_end, births = 0, deaths = 0, recent = 0;
    for (int t = 1; t <= horizon; ++t) {
        if (t <= field_end) {
            for (int i = 0; i < 64; ++i) {
                if (index[i] < 0) continue;
                auto& p = people[index[i]];
                if (p.attempt || p.encounter || t-1-p.born >= 80) continue;
                const auto& cpu = w.at(i).cpu;
                const auto& east = w.at(w.neighbor(i,1));
                if (cpu.bank == i && cpu.pc == 0 && cpu.target < 0 &&
                    east.kind == tide::Bank::occupied && east.bytes == reader) {
                    p.encounter = t;
                    cases.push_back({index[i],t,static_cast<int>(east.born),free_neighbors(w,i),
                                     eligible_sites(w,i),w.hash(),{}});
                    horizon = std::max(horizon,t-1+follow_ticks);
                }
            }
            // Read-only permission and RSCLD make the first C local at offset 2.
            // Its source snapshot may disappear during this step.
            for (int i = 0; i < 64; ++i) {
                if (index[i] < 0) continue;
                auto& p = people[index[i]];
                const auto& c = w.at(i).cpu;
                if (p.attempt || c.bank != i || c.pc != 2 || t-1-p.born >= 80) continue;
                const auto& source = w.at(w.neighbor(i,1));
                p.first_bank = kind(source.kind); p.first_hex = hex(source.bytes);
                p.first_donor = source.kind == tide::Bank::occupied ? static_cast<int>(source.born) : -1;
            }
        }
        w.step(&events, reverse);
        if (t <= field_end) {
            for (const auto& e : events) {
                if (index[e.actor] >= 0) {
                    auto& p = people[index[e.actor]];
                    if (e.op == 'C' && !p.attempt) {
                        require(p.first_bank != "-" && e.read_site == w.neighbor(e.actor,1), "first copy mismatch");
                        p.attempt = t; p.effect = tide::name(e.effect);
                    }
                    p.births += e.effect == tide::Effect::birth;
                    if (e.effect == tide::Effect::death) { p.death = t; index[e.actor] = -1; }
                }
                if (e.effect == tide::Effect::birth) {
                    ++births; recent += t > field_end-80;
                    if (e.product == reader) {
                        index[e.target] = static_cast<int>(people.size());
                        people.push_back({e.target,t});
                    }
                } else if (e.effect == tide::Effect::death) ++deaths;
            }
        }
        if (t == field_end) {
            w.check();
            int living = 0;
            for (int i=0; i<w.size(); ++i) living += w.at(i).kind == tide::Bank::occupied;
            require(living == 1+births-deaths,"field space ledger");
            seeds << cohort << '\t' << seed << '\t' << births << '\t' << deaths << '\t' << living << '\t'
                  << recent << '\t' << (!living?"extinct":recent?"reproducing":"stagnant") << '\t'
                  << people.size() << '\t' << cases.size() << '\t' << w.hash() << '\n';
        }
        for (auto& x : cases) if (t == x.opening-1+follow_ticks) x.end_hash = w.hash();
    }
    for (const auto& p : people)
        readers << cohort << '\t' << seed << '\t' << p.site << '\t' << p.born << '\t' << p.encounter << '\t'
                << p.attempt << '\t' << p.effect << '\t' << p.first_bank << '\t' << p.first_donor << '\t'
                << p.first_hex << '\t' << p.births << '\t' << p.death << '\n';
    for (const auto& x : cases) {
        const auto& p = people[x.id];
        require(!x.end_hash.empty(),"missing end hash");
        encounters << cohort << '\t' << seed << '\t' << p.site << '\t' << p.born << '\t' << x.opening << '\t'
                   << w.neighbor(p.site,1) << '\t' << x.donor_born << '\t' << x.free << '\t'
                   << site_list(x.eligible) << '\t' << x.start_hash << '\t' << x.end_hash << '\n';
    }
}
}
int main(int argc,char** argv) {
    try {
        if ((argc!=2 && argc!=3) || (argc==3 && std::string_view(argv[2])!="--reverse"))
            throw std::invalid_argument("usage: scan OUTPUT_DIR [--reverse]");
        const std::string dir = argv[1];
        auto s = output(dir,"seeds.tsv","cohort\tseed\tbirths\tdeaths\tliving\tfinal80_births\tstatus\treaders\tencounters\tstate_fnv64");
        auto r = output(dir,"readers.tsv","cohort\tseed\tsite\tborn\tencounter_tick\tfirst_copy\teffect\tfirst_bank\tfirst_donor_born\tfirst_source_hex\tbirths\tdeath");
        auto e = output(dir,"encounters.tsv","cohort\tseed\tsite\tborn\topening\tdonor_site\tdonor_born\tfree\teligible_sites\tstart_fnv64\tordinary_end_fnv64");
        for (int seed : {419,561,569}) scan(seed,argc==3,s,r,e);
        for (int seed=577; seed<=1088; ++seed) scan(seed,argc==3,s,r,e);
        s.close(); r.close(); e.close();
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
