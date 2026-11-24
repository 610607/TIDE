#include "../vacancy-01/common.hpp"
#include <iostream>
#include <optional>

using vacancy::require;

namespace tide {
void World::introduce_reader(int id, int bearing) {
    auto& bank = sites_.at(id);
    require(bank.kind == Bank::free && bearing >= 0 && bearing < 4, "invalid introduction");
    bank = Site{};
    bank.kind = Bank::occupied;
    bank.bytes = vacancy::reader;
    bank.born = tick_;
    bank.cpu.bank = bank.cpu.source = id;
    bank.cpu.bearing = bearing;
}
}

namespace {
using tide::Bank;
using tide::Effect;
using tide::World;
struct Start { World world; int center, crowd; };

int living(const World& w) {
    int count=0;
    for(int i=0; i<w.size(); ++i) count += w.at(i).kind == Bank::occupied;
    return count;
}

std::optional<Start> select(int seed, bool reverse) {
    auto w=vacancy::initial(seed);
    std::optional<Start> chosen;
    for(int tick=1; tick<=256; ++tick) {
        w.step(nullptr,reverse);
        if(tick<64) continue;
        int best=0;
        for(int i=0; i<w.size(); ++i) {
            if(w.at(i).kind!=Bank::free || vacancy::free_neighbors(w,i)!=4) continue;
            int ring=0;
            for(int j=0; j<w.size(); ++j) {
                int dx=std::abs(i%16-j%16), dy=std::abs(i/16-j/16);
                if(std::min(dx,16-dx)+std::min(dy,4-dy)==2) ring+=w.at(j).kind==Bank::occupied;
            }
            if(ring>best) { best=ring; chosen=Start{w,i,ring}; }
        }
    }
    return chosen;
}

struct Tables {
    std::ofstream setups, branches, copies, births;
    explicit Tables(const std::string& dir) :
        setups(vacancy::output(dir,"setups.tsv","seed\ttick\tcenter\tring_living\tbackground_living\tbackground_hash")),
        branches(vacancy::output(dir,"branches.tsv","seed\tdir\tarm\tmother\tmother_born\ttarget\tinitial_hash\topening_effect\trestored_hash\tmother_births\tfirst_link\tdaughter_born\tregistered_hash\tdaughter_births\tlive_births\tmaternal_births\tmother_failed_copies\tdaughter_failed_copies\tworld_births\tworld_deaths\tworld_living\tfinal80_births\tstatus\tend_hash")),
        copies(vacancy::output(dir,"copies.tsv","seed\tdir\tarm\trole\tactor_site\tactor_born\ttick\teffect\treservation\twrite_offset\tsource\tread_offset\tbank\tsource_born\towner\tsource_hex\tinput\toutput\tmother_alive")),
        births(vacancy::output(dir,"births.tsv","seed\tdir\tarm\trole\tparent_site\tparent_born\ttick\tchild_site\tinputs_hex\tproduct_hex\tsingle_live_reader\tsupplier\tsupplier_born")) {}
};

struct Allocation {
    std::string inputs;
    int supplier=-1, born=-1;
    bool single=true;
    void copy(const tide::Event& e) {
        require(static_cast<int>(inputs.size())==e.write_offset,"copy order");
        const auto& c=e.read_contact;
        if(inputs.empty()) { supplier=c.site; born=static_cast<int>(c.born); }
        single=single && c.kind==Bank::occupied && c.site==supplier &&
               static_cast<int>(c.born)==born && c.site!=e.actor && c.bytes==vacancy::reader &&
               e.read_offset==e.write_offset;
        inputs.push_back(static_cast<char>(e.input));
    }
    bool intact(const tide::Event& e) const {
        require(inputs.size()==e.product.size(),"incomplete birth provenance");
        return single && inputs==vacancy::reader && e.product==vacancy::reader;
    }
};

struct Result {
    bool first_link=false;
    int daughter_born=-1, live_births=0, maternal_births=0;
    std::string registered="-";
};

Result run(const Start& s,int dir,std::string_view arm,bool reverse,Tables& out) {
    auto w=s.world;
    const int mother=s.center, donor=w.neighbor(mother,1), target=w.neighbor(mother,dir);
    const int start=static_cast<int>(w.tick()), seed=static_cast<int>(w.config().seed);
    const std::string key=std::to_string(seed)+"\t"+"NESW"[dir]+"\t"+std::string(arm);
    w.introduce_reader(mother,(dir+1)%4);
    w.introduce_reader(donor,1);
    require(living(w)==living(s.world)+2,"introduction ledger");
    if(arm=="mother_denied") w.set_access(mother,{});
    std::string initial=w.hash(), restored, opening;
    bool won=false;
    Result result;
    int mb=0, db=0, mf=0, df=0, births=0, deaths=0, recent=0;
    Allocation mother_copy, daughter_copy;
    std::vector<tide::Event> events;
    for(int k=1; k<=256; ++k) {
        const bool mother_alive=w.at(mother).kind==Bank::occupied && static_cast<int>(w.at(mother).born)==start;
        w.step(&events,reverse);
        if(k==1) { w.face_east(mother); restored=w.hash(); }
        for(const auto& e:events) {
            births+=e.effect==Effect::birth;
            recent+=e.effect==Effect::birth && k>176;
            deaths+=e.effect==Effect::death;
            const bool m=e.actor==mother && static_cast<int>(e.actor_born)==start;
            const bool d=e.actor==target && static_cast<int>(e.actor_born)==result.daughter_born;
            if(!m && !d) continue;
            if(k==1 && m) {
                require(e.op=='R' && e.target==target,"unexpected first proposal");
                opening=tide::name(e.effect); won=e.effect==Effect::reserve;
            }
            if(e.effect==Effect::death) {
                if((m && arm=="mother_denied") || (d && arm=="daughter_denied"))
                    w.set_access(e.actor,w.config().access);
                continue;
            }
            auto& alloc=m?mother_copy:daughter_copy;
            if(e.effect==Effect::reserve) alloc={};
            auto identity=key+"\t"+(m?"mother":"daughter")+"\t"+std::to_string(e.actor)+"\t"+std::to_string(e.actor_born);
            if(e.op=='C') {
                if(e.effect==Effect::copy) alloc.copy(e);
                if(e.effect==Effect::failed_copy) { if(m) ++mf; else ++df; }
                const auto& c=e.read_contact;
                out.copies<<identity<<'\t'<<e.tick<<'\t'<<tide::name(e.effect)<<'\t'<<e.target<<'\t'
                    <<e.write_offset<<'\t'<<e.read_site<<'\t'<<e.read_offset<<'\t'
                    <<(c.site<0?"-":vacancy::kind(c.kind))<<'\t'<<c.born<<'\t'<<c.reservation_owner<<'\t'
                    <<(c.site<0?"-":vacancy::hex(c.bytes))<<'\t'<<e.input<<'\t'<<e.output<<'\t'<<mother_alive<<'\n';
            }
            if(e.effect!=Effect::birth) continue;
            bool intact=alloc.intact(e);
            out.births<<identity<<'\t'<<e.tick<<'\t'<<e.target<<'\t'<<vacancy::hex(alloc.inputs)<<'\t'
                <<vacancy::hex(e.product)<<'\t'<<intact<<'\t'<<(intact?alloc.supplier:-1)<<'\t'
                <<(intact?alloc.born:-1)<<'\n';
            if(m) {
                ++mb;
                if(mb==1 && won && e.target==target && intact && alloc.supplier==donor && alloc.born==start) {
                    result.first_link=true; result.daughter_born=static_cast<int>(e.tick);
                    result.registered=w.hash();
                    require(w.at(target).cpu.bearing==1,"newborn orientation differs");
                    if(arm=="daughter_denied") w.set_access(target,{});
                }
            } else {
                ++db; result.live_births+=intact;
                result.maternal_births+=intact && alloc.supplier==mother && alloc.born==start;
            }
        }
        w.check();
    }
    require(!opening.empty() && living(w)==living(s.world)+2+births-deaths,"world ledger mismatch");
    if(arm=="mother_denied") require(!mb,"mother permission failed");
    if(arm=="daughter_denied") require(result.first_link && !db,"daughter permission failed");
    out.branches<<key<<'\t'<<mother<<'\t'<<start<<'\t'<<target<<'\t'<<initial<<'\t'<<opening<<'\t'<<restored
        <<'\t'<<mb<<'\t'<<result.first_link<<'\t'<<result.daughter_born<<'\t'<<result.registered<<'\t'<<db
        <<'\t'<<result.live_births<<'\t'<<result.maternal_births<<'\t'<<mf<<'\t'<<df<<'\t'<<births
        <<'\t'<<deaths<<'\t'<<living(w)<<'\t'<<recent<<'\t'<<(!living(w)?"extinct":recent?"reproducing":"stagnant")
        <<'\t'<<w.hash()<<'\n';
    return result;
}
}
int main(int argc,char** argv) {
    try {
        if(argc<2 || argc>3 || (argc==3 && std::string_view(argv[2])!="--reverse"))
            throw std::invalid_argument("usage: placement OUT_DIR [--reverse]");
        Tables out(argv[1]);
        for(int seed=577;seed<=640;++seed) {
            auto s=select(seed,argc==3);
            if(!s) { out.setups<<seed<<"\t-\t-\t-\t-\t-\n"; continue; }
            out.setups<<seed<<'\t'<<s->world.tick()<<'\t'<<s->center<<'\t'<<s->crowd<<'\t'
                      <<living(s->world)<<'\t'<<s->world.hash()<<'\n';
            for(int dir:{3,0,2}) {
                auto ordinary=run(*s,dir,"ordinary",argc==3,out);
                run(*s,dir,"mother_denied",argc==3,out);
                if(ordinary.first_link) {
                    auto denied=run(*s,dir,"daughter_denied",argc==3,out);
                    require(ordinary.registered==denied.registered,"daughter fork diverged before intervention");
                }
            }
        }
        out.setups.close(); out.branches.close(); out.copies.close(); out.births.close();
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
