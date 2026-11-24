// Compare local physical transport and newborn bearing on the same natural fields.
#include "transport.hpp"
#include "../vacancy-01/common.hpp"

#include <algorithm>
#include <iostream>
#include <vector>

namespace {
using namespace tide;
using vacancy::require;
constexpr int end_tick=2048;
enum ContactFlag { faced=1, room=2, read=4, produced=8 };
struct ContactRecord { int donor, flags=0; };
struct Allocation {
    int size=0, first=-1, direction=-1;
    bool aligned=true, unchanged=true, one_identity=true, external=false, started_unlike=false, switched=false;
    std::array<int,6> times{}, sites{};
};
struct Life {
    int origin, born;
    std::string bytes;
    bool reader, enrolled=false, self_copy=false, supplied=false;
    std::vector<ContactRecord> contacts;
    Allocation writes;
    Life(int site,int t,std::string seq):origin(site),born(t),bytes(std::move(seq)),
        reader(bytes.find('S')!=std::string::npos) {}
    ContactRecord& contact(int donor,bool insert=false) {
        for (auto& item:contacts) if (item.donor==donor) return item;
        require(insert,"read without a recorded local encounter");
        contacts.push_back({donor,0});
        return contacts.back();
    }
};
struct Product {int child, actor, donor, site; Allocation writes;};
struct Study {
    World world;
    SpatialExperiment space;
    int seed, threshold;
    bool random_birth, reverse;
    std::array<int,64> ids{};
    std::vector<Life> lives;
    std::vector<Product> products;
    int deaths=0, recent=0, exposure=0, moves=0, started=0, switched=0, external_births=0;
    std::array<int,4> directions{}, initial_bearings{};

    static Config config(int seed,unsigned mutation=20000) {
        Config cfg;
        cfg.seed=seed; cfg.width=16; cfg.height=4; cfg.boundary=Boundary::torus;
        cfg.placement=Placement::first_free; cfg.access.read=true; cfg.max_age=80; cfg.mutation_ppm=mutation;
        return cfg;
    }
    Study(int seed,const std::string& arm,bool reverse):world(config(seed)),space(world),seed(seed),
        threshold(arm=="low"?1:arm=="high"?16:0),random_birth(arm=="bearing"),reverse(reverse) {
        ids.fill(-1); ids[36]=0;
        world.seed_site(36,"R..CLD");
        lives.emplace_back(36,0,"R..CLD");
    }
    void encounters() {
        for (int site=0;site<64;++site) {
            int id=ids[site];
            if (id<0) continue;
            ++exposure;
            auto& reader=lives[id];
            if (!reader.reader) continue;
            const auto& cpu=world.at(site).cpu;
            for (int d=0;d<4;++d) {
                int donor=ids[space.near[site][d]];
                if (donor<0 || lives[donor].bytes==reader.bytes) continue;
                auto& found=reader.contact(donor,true);
                if (d!=cpu.bearing) continue;
                found.flags|=faced;
                if (cpu.target>=0 || std::any_of(space.near[site].begin(),space.near[site].end(),
                    [&](int other){return world.at(other).kind==Bank::free;})) found.flags|=room;
            }
        }
    }
    void copy(const Event& e,const std::array<int,64>& opening) {
        int actor=opening[e.actor], donor=opening[e.read_site];
        auto& reader=lives[actor];
        auto& a=reader.writes;
        require(e.write_offset==a.size && a.size<6,"copy order");
        const bool external=e.read_site!=e.actor;
        a.external |= external;
        if (external && donor>=0) {
            require(e.read_contact.kind==Bank::occupied && e.read_contact.born==Tick(lives[donor].born)
                    && e.read_contact.bytes==lives[donor].bytes,"opening donor");
            if (reader.bytes!=lives[donor].bytes) reader.contact(donor).flags|=read;
        }
        if (!a.size) {
            a.first=donor;
            a.direction=external?space.direction(e.actor,e.read_site):-1;
            a.started_unlike=external && donor>=0 && lives[donor].bytes!=reader.bytes;
            started+=a.started_unlike;
        }
        if (a.started_unlike && a.first!=donor && !a.switched) {++switched; a.switched=true;}
        a.one_identity &= donor>=0 && donor==a.first;
        a.aligned &= e.read_offset==a.size;
        a.unchanged &= e.input==e.output;
        a.times[a.size]=static_cast<int>(e.tick);
        a.sites[a.size++]=e.read_site;
    }
    void birth(const Event& e,const std::array<int,64>& opening) {
        const int t=static_cast<int>(e.tick), actor=opening[e.actor], child=static_cast<int>(lives.size());
        const Allocation a=lives[actor].writes;
        require(a.size==6 && opening[e.target]<0 && ids[e.target]<0,"invalid birth");
        ids[e.target]=child;
        lives.emplace_back(e.target,t,e.product);
        recent+=t>end_tick-80;
        external_births+=a.external;
        int bearing=random_birth?static_cast<int>(SpatialExperiment::draw(seed,t,128+e.target)%4):1;
        SpatialExperiment::orient(world,e.target,bearing);
        ++initial_bearings[bearing];
        if (!a.one_identity || !a.aligned || !a.unchanged) return;
        int donor=a.first;
        require(donor>=0 && lives[donor].bytes==e.product,"exact copy mismatch");
        if (actor==donor) { lives[actor].self_copy=true; return; }
        lives[donor].supplied=true;
        if (lives[actor].bytes==e.product) return;
        lives[actor].contact(donor).flags|=produced;
        lives[child].enrolled=true;
        ++directions[a.direction];
        products.push_back({child,actor,donor,e.actor,a});
    }
    void run() {
        std::vector<Event> events;
        for (int t=1;t<=end_tick;++t) {
            encounters();
            const auto opening=ids;
            world.step(&events,reverse);
            for (const auto& e:events) {
                require(opening[e.actor]>=0 && Tick(lives[opening[e.actor]].born)==e.actor_born,"opening actor");
                switch(e.effect) {
                case Effect::reserve:
                    lives[opening[e.actor]].writes=Allocation{};
                    break;
                case Effect::copy: copy(e,opening); break;
                case Effect::birth: birth(e,opening); break;
                case Effect::death: ids[e.actor]=-1; ++deaths; break;
                default: break;
                }
            }
            moves+=space.transport(world,ids,threshold,reverse);
            if (t%64==0) {
                world.check();
                for (int i=0;i<64;++i) {
                    const auto& s=world.at(i);
                    require((s.kind==Bank::occupied)==(ids[i]>=0),"identity occupancy");
                    if (ids[i]>=0) require(s.bytes==lives[ids[i]].bytes && s.born==Tick(lives[ids[i]].born),
                                           "identity transport");
                }
            }
        }
    }
    void write(const std::string& arm,const std::string& dir) const {
        auto seeds=vacancy::output(dir,"seed.tsv","seed\tarm\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tstate_fnv64\tliving_ticks\tindividual_moves\tencounters\tfacing_pairs\tfacing_room_pairs\tread_pairs\tproductive_pairs\tstarted_unlike\tswitched_supplier\texternal_births\texact_births\tnorth\teast\tsouth\twest\tcomplete\tself_again\ttemplate_again\tany_again\tincomplete\tborn_n\tborn_e\tborn_s\tborn_w\treaders");
        auto ledger=vacancy::output(dir,"products.tsv","seed\tarm\tchild_site\tchild_born\tproduct\texecutor_birth_site\texecutor_born\texecutor\tdonor_birth_site\tdonor_born\texecutor_site\tfirst_direction\tread_ticks\tread_sites\tcomplete\tself_again\ttemplate_again");
        int pairs=0, facing=0, available=0, actual=0, productive=0, complete=0, again=0, self=0, donor_again=0;
        for (const auto& p:lives) {
            for (const auto& c:p.contacts) {
                ++pairs; facing+=bool(c.flags&faced); available+=bool(c.flags&room);
                actual+=bool(c.flags&read); productive+=bool(c.flags&produced);
            }
            if (p.enrolled && p.born+81<=end_tick) {
                ++complete; self+=p.self_copy; donor_again+=p.supplied; again+=p.self_copy||p.supplied;
            }
        }
        const int living=static_cast<int>(std::count_if(ids.begin(),ids.end(),[](int v){return v>=0;}));
        require(int(lives.size())-deaths==living,"population imbalance");
        seeds<<seed<<'\t'<<arm<<'\t'<<lives.size()-1<<'\t'<<deaths<<'\t'<<living<<'\t'<<recent<<'\t'
             <<(!living?"extinct":recent?"reproducing":"stagnant")<<'\t'<<world.hash();
        for (int v:{exposure,moves,pairs,facing,available,actual,productive,started,switched,external_births,int(products.size())})
            seeds<<'\t'<<v;
        for (int v:directions) seeds<<'\t'<<v;
        for (int v:{complete,self,donor_again,again,int(products.size())-complete}) seeds<<'\t'<<v;
        for (int v:initial_bearings) seeds<<'\t'<<v;
        seeds<<'\t'<<std::count_if(lives.begin(),lives.end(),[](const Life& p){return p.reader && p.born<end_tick;})<<'\n';
        for (const auto& entry:products) {
            const auto& c=lives[entry.child]; const auto& p=lives[entry.actor]; const auto& d=lives[entry.donor];
            ledger<<seed<<'\t'<<arm<<'\t'<<c.origin<<'\t'<<c.born<<'\t'<<vacancy::hex(c.bytes)
                  <<'\t'<<p.origin<<'\t'<<p.born<<'\t'<<vacancy::hex(p.bytes)<<'\t'<<d.origin<<'\t'<<d.born
                  <<'\t'<<entry.site<<'\t'<<"NESW"[entry.writes.direction]<<'\t';
            for (int i=0;i<6;++i) ledger<<(i?",":"")<<entry.writes.times[i];
            ledger<<'\t';
            for (int i=0;i<6;++i) ledger<<(i?",":"")<<entry.writes.sites[i];
            ledger<<'\t'<<(c.born+81<=end_tick)<<'\t'<<c.self_copy<<'\t'<<c.supplied<<'\n';
        }
    }
};
void controls() {
    World w(Study::config(1,0)); SpatialExperiment s(w);
    w.seed_site(17,"S....P"); w.seed_site(18,".....P");
    w.step();
    require(w.at(17).cpu.source==18,"control reads east");
    require(s.exchange(w,17,33),"move to free site");
    require(w.at(33).bytes=="S....P" && w.at(33).cpu.source==34 && w.at(33).cpu.pc==1 &&
            w.at(17).kind==Bank::free,"relative pointer and CPU travel");
    require(s.exchange(w,18,34) && s.exchange(w,33,34),"living exchange");
    require(w.at(34).bytes=="S....P" && w.at(33).bytes==".....P","two sequences conserved");
    w.check();
    World locked(Study::config(2,0)); locked.seed_site(17,"R..CLD"); locked.step();
    int dest=locked.at(17).cpu.target;
    const auto before=locked.state();
    require(dest>=0 && !s.exchange(locked,17,18) && !s.exchange(locked,dest,s.near[dest][1]) &&
            before==locked.state(),"reservation exclusion");
    World reading(Study::config(3,0));
    reading.seed_site(17,"RS.CLD"); reading.seed_site(18,".....P");
    reading.step(); reading.step();
    require(reading.at(17).cpu.source==18 && s.exchange(reading,18,19) && reading.at(17).cpu.source==18,
            "a pinned reader tracks the address");
    reading.step(); reading.step();
    require(reading.at(17).cpu.written==0,"vacated source has no available byte");
    World aging(Study::config(4,0)); aging.seed_site(17,"R..CLD"); aging.seed_site(18,".....P");
    for (int t=1;t<=81;++t) aging.step();
    require(aging.at(18).kind==Bank::free && aging.at(18).bytes==".....P","retained control bytes");
    // Pair the retained bank with an adjacent, mobile individual that has a nonzero birth tick.
    bool verified=false;
    for (int id:s.near[18]) {
        const auto old=aging.at(id);
        if (old.kind!=Bank::occupied || !old.born || old.cpu.target>=0) continue;
        require(s.exchange(aging,id,18) && aging.at(18).born==old.born && aging.at(18).bytes==old.bytes &&
                aging.at(id).kind==Bank::free && aging.at(id).bytes==".....P","age and residual conservation");
        verified=true; break;
    }
    require(verified,"missing age control"); aging.check();
    for (const auto& matching:s.matches) {
        std::array<int,64> uses{};
        for (auto [a,b]:matching) {++uses[a]; ++uses[b]; s.direction(a,b);}
        require(std::all_of(uses.begin(),uses.end(),[](int n){return n==1;}),"invalid matching");
    }
    std::cout<<"Transport controls passed\n";
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls(); return 0;}
        if ((argc!=4 && argc!=5) || (argc==5 && std::string_view(argv[4])!="--reverse"))
            throw std::invalid_argument("usage: field SEED east|bearing|low|high DIR [--reverse]");
        std::string arm=argv[2];
        require(arm=="east" || arm=="bearing" || arm=="low" || arm=="high","unknown arm");
        int seed=std::stoi(argv[1]);
        require(seed>=19521 && seed<=21568,"seed outside cohort");
        Study study(seed,arm,argc==5); study.run(); study.write(arm,argv[3]);
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
