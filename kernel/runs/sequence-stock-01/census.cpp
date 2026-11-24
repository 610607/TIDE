// Observe committed bank stocks and the six actual writes behind every natural birth.
#include "../vacancy-01/common.hpp"

#include <iostream>
#include <unordered_map>

namespace {
using vacancy::require;
using tide::Bank;
using tide::Effect;
constexpr int end_tick = 2048, length = 6;
constexpr std::array routes{"self", "live", "residual", "assembly", "substitution"};
enum Route { self, live, residual, assembly, substitution };
using Counts = std::array<int,3>; // occupied, reserved, free
int total(const Counts& x) { return x[0]+x[1]+x[2]; }
int bucket(Bank b) { return b==Bank::occupied ? 0 : b==Bank::reserved ? 1 : 2; }

struct Span {
    int start=-1, longest=0, ticks=0, runs=0;
    void advance(bool present, int t) {
        if (present && start<0) { start=t; ++runs; }
        if (!present && start>=0) {
            longest=std::max(longest,t-start);
            ticks+=t-start;
            start=-1;
        }
    }
};
struct Sequence {
    std::string bytes, hex;
    Counts count{}, next{}, area{};
    Span occupied, stored;
    int last=0, peak_occupied=0, peak_stored=0;
    std::array<int,5> births{}, returns{};
    int external=0, same_executor=0, different_live=0;
    int self_depth=0, live_depth=0, self_span=0, live_span=0;
    explicit Sequence(const std::string& bytes) : bytes(bytes), hex(vacancy::hex(bytes)) {}
    void integrate(int t) {
        for (int i=0;i<3;++i) area[i]+=(t-last)*count[i];
        last=t;
    }
};
struct Cell { int seq=-1, kind=2; };
struct Carrier {
    int seq, born, self_root, live_root, self_depth=0, live_depth=0;
    Carrier(int seq,int born):seq(seq),born(born),self_root(born),live_root(born){}
};
struct Write { int tick,site,offset,kind,born,owner,seq,carrier,input,output; };
struct Allocation {
    int size=0;
    std::array<Write,length> writes{};
};

class Census {
    std::unordered_map<std::string,int> ids;
    std::vector<Sequence> sequences;
    std::array<Cell,64> cells{};
    std::vector<Carrier> people;
    std::array<int,64> occupant{};
    std::array<Allocation,64> allocations{};
    std::ofstream stocks, products, summaries, world;
    std::vector<int> touched;
    std::vector<int> marked;
    int births=0, deaths=0, recent=0;

    int intern(const std::string& bytes) {
        if (bytes.empty()) return -1;
        require(bytes.size()==length,"unexpected bank length");
        auto [it,added]=ids.try_emplace(bytes,static_cast<int>(sequences.size()));
        if (added) { sequences.emplace_back(bytes); marked.push_back(-1); }
        return it->second;
    }
    void adjust(int id,int kind,int delta,int tick) {
        if (id<0) return;
        if (marked[id]!=tick) { marked[id]=tick; touched.push_back(id); }
        sequences[id].next[kind]+=delta;
    }
    void snapshot(const tide::World& w,int tick) {
        touched.clear();
        for (int site=0;site<w.size();++site) {
            const auto& bank=w.at(site);
            auto& prev=cells[site];
            int id=prev.seq;
            if (id<0 || sequences[id].bytes!=bank.bytes) id=intern(bank.bytes);
            int kind=bucket(bank.kind);
            if (prev.seq==id && prev.kind==kind) continue;
            adjust(prev.seq,prev.kind,-1,tick);
            adjust(id,kind,1,tick);
            prev={id,kind};
        }
        for (int id:touched) {
            auto& s=sequences[id];
            if (s.count==s.next) continue;
            require(*std::min_element(s.next.begin(),s.next.end())>=0,"negative stock");
            s.integrate(tick);
            s.count=s.next;
            s.occupied.advance(s.count[0]>0,tick);
            s.stored.advance(total(s.count)>0,tick);
            s.peak_occupied=std::max(s.peak_occupied,s.count[0]);
            s.peak_stored=std::max(s.peak_stored,total(s.count));
            stocks<<tick<<'\t'<<s.hex<<'\t'<<s.count[0]<<'\t'<<s.count[1]<<'\t'<<s.count[2]<<'\n';
        }
    }
    void copy(const tide::Event& e) {
        auto& a=allocations[e.actor];
        const auto src=cells[e.read_site];
        const bool own=e.actor==e.read_site;
        require(a.size==e.write_offset && a.size<length && src.seq>=0,"unordered copy");
        const int carrier=src.kind==0 ? occupant[e.read_site] : -1;
        const int born=carrier>=0 ? people[carrier].born : -1;
        require(static_cast<unsigned char>(sequences[src.seq].bytes.at(e.read_offset))==e.input,
                "source byte mismatch");
        if (!own) require(e.read_contact.bytes==sequences[src.seq].bytes &&
                          bucket(e.read_contact.kind)==src.kind && (carrier<0 || born==static_cast<int>(e.read_contact.born)),
                          "source snapshot mismatch");
        a.writes[a.size++]={static_cast<int>(e.tick),e.read_site,e.read_offset,src.kind,born,
                            own?-1:e.read_contact.reservation_owner,src.seq,carrier,e.input,e.output};
    }
    void birth(const tide::Event& e) {
        const int t=static_cast<int>(e.tick), id=intern(e.product), parent=occupant[e.actor];
        const auto& a=allocations[e.actor];
        require(a.size==length && people[parent].born==static_cast<int>(e.actor_born),"invalid parent");
        const auto& first=a.writes[0];
        bool intact=true, single_living=true, all_inactive=true;
        int mutations=0, external=0;
        for (int i=0;i<length;++i) {
            const auto& r=a.writes[i];
            require(r.output==static_cast<unsigned char>(e.product[i]),"committed byte differs");
            intact &= r.seq==id && r.offset==i && r.site==first.site;
            single_living &= r.carrier>=0 && r.carrier==first.carrier;
            all_inactive &= r.kind!=0;
            mutations+=r.input!=r.output;
            external+=r.site!=e.actor;
        }
        Route route=assembly;
        if (mutations) route=substitution;
        else if (intact && single_living) route=external ? live : self;
        else if (intact && all_inactive) route=residual;
        auto& seq=sequences[id];
        const bool restored=seq.count[0]==0 && seq.occupied.runs>0;
        ++seq.births[route];
        seq.returns[route]+=restored;
        seq.same_executor+=people[parent].seq==id;
        seq.external+=external>0;
        seq.different_live+=route==live && people[parent].seq!=id;
        Carrier child(id,t);
        if (route==self || route==live) {
            const auto& supplier=people[first.carrier];
            require(supplier.seq==id,"material identity mismatch");
            if (route==self) {
                child.self_depth=supplier.self_depth+1; child.self_root=supplier.self_root;
                seq.self_depth=std::max(seq.self_depth,child.self_depth);
                seq.self_span=std::max(seq.self_span,t-child.self_root);
            } else {
                child.live_depth=supplier.live_depth+1; child.live_root=supplier.live_root;
                seq.live_depth=std::max(seq.live_depth,child.live_depth);
                seq.live_span=std::max(seq.live_span,t-child.live_root);
            }
        }
        products<<t<<'\t'<<e.target<<'\t'<<e.actor<<'\t'<<e.actor_born<<'\t'<<sequences[people[parent].seq].hex
                <<'\t'<<seq.hex<<'\t'<<routes[route]<<'\t'<<restored<<'\t'<<external<<'\t'<<mutations<<'\t';
        for (int i=0;i<length;++i) {
            const auto& r=a.writes[i];
            if (i) products<<',';
            products<<r.tick<<'/'<<r.site<<'/'<<r.offset<<'/'<<"orf"[r.kind]<<'/'<<r.born<<'/'
                    <<r.owner<<'/'<<sequences[r.seq].hex;
        }
        products<<'\n';
        occupant[e.target]=static_cast<int>(people.size());
        people.push_back(child);
        ++births;
        recent+=t>end_tick-80;
    }
public:
    explicit Census(const std::string& dir):
        stocks(vacancy::output(dir,"stocks.tsv","tick\tsequence\toccupied\treserved\tfree")),
        products(vacancy::output(dir,"births.tsv","tick\tproduct_site\texecutor_site\texecutor_born\texecutor\tproduct\troute\trestored\texternal_bytes\tsubstitutions\tsources")),
        summaries(vacancy::output(dir,"sequences.tsv","sequence\toccupied_end\treserved_end\tfree_end\toccupied_copy_ticks\treserved_copy_ticks\tfree_copy_ticks\tpeak_occupied\tpeak_stored\toccupied_ticks\tstored_ticks\toccupied_runs\tmax_occupied_run\tmax_stored_run\tself\tlive\tresidual\tassembly\tsubstitution\treturn_self\treturn_live\treturn_residual\treturn_assembly\treturn_substitution\texternal_births\tsame_executor\tdifferent_live\tself_depth\tlive_depth\tself_span\tlive_span")),
        world(vacancy::output(dir,"world.tsv","seed\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tstate_fnv64")) {}
    void run(int seed,bool reverse) {
        tide::Config cfg;
        cfg.width=16; cfg.height=4; cfg.boundary=tide::Boundary::torus;
        cfg.placement=tide::Placement::first_free; cfg.access.read=true; cfg.max_age=80;
        cfg.mutation_ppm=20000; cfg.seed=seed;
        tide::World w(cfg);
        w.seed_site(36,"R..CLD");
        snapshot(w,0);
        occupant.fill(-1); occupant[36]=0;
        people.emplace_back(cells[36].seq,0);
        std::vector<tide::Event> events;
        for (int t=1;t<=end_tick;++t) {
            w.step(&events,reverse);
            for (const auto& e:events) {
                if (e.effect==Effect::reserve) allocations[e.actor].size=0;
                else if (e.effect==Effect::copy) copy(e);
                else if (e.effect==Effect::birth) birth(e);
                else if (e.effect==Effect::death) ++deaths;
            }
            snapshot(w,t);
        }
        int living=0;
        for (int i=0;i<w.size();++i) living+=w.at(i).kind==Bank::occupied;
        w.check();
        require(living==1+births-deaths,"unbalanced population");
        world<<seed<<'\t'<<births<<'\t'<<deaths<<'\t'<<living<<'\t'<<recent<<'\t'
             <<(!living?"extinct":recent?"reproducing":"stagnant")<<'\t'<<w.hash()<<'\n';
        for (auto& s:sequences) {
            s.integrate(end_tick+1);
            s.occupied.advance(false,end_tick+1);
            s.stored.advance(false,end_tick+1);
            summaries<<s.hex;
            for (int n:s.count) summaries<<'\t'<<n;
            for (int n:s.area) summaries<<'\t'<<n;
            summaries<<'\t'<<s.peak_occupied<<'\t'<<s.peak_stored<<'\t'<<s.occupied.ticks
                     <<'\t'<<s.stored.ticks<<'\t'<<s.occupied.runs<<'\t'<<s.occupied.longest<<'\t'<<s.stored.longest;
            for (int n:s.births) summaries<<'\t'<<n;
            for (int n:s.returns) summaries<<'\t'<<n;
            summaries<<'\t'<<s.external<<'\t'<<s.same_executor<<'\t'<<s.different_live<<'\t'<<s.self_depth<<'\t'
                     <<s.live_depth<<'\t'<<s.self_span<<'\t'<<s.live_span<<'\n';
        }
        summaries.close(); stocks.close(); products.close(); world.close();
    }
};
}

int main(int argc,char** argv) {
    try {
        if ((argc!=3 && argc!=4) || (argc==4 && std::string_view(argv[3])!="--reverse"))
            throw std::invalid_argument("usage: census SEED OUT [--reverse]");
        const int seed=std::stoi(argv[1]);
        require(seed>=19521 && seed<=21568,"seed outside cohort");
        Census(argv[2]).run(seed,argc==4);
    } catch (const std::exception& e) {
        std::cerr<<e.what()<<'\n'; return 1;
    }
}
