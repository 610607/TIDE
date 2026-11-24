// Read-only census on the four stationary fields from the split-bearing experiment.
#include "../spatial-transport-01/transport.hpp"
#include "../vacancy-01/common.hpp"

#include <iostream>
#include <map>
#include <vector>

namespace {
using namespace tide;
using vacancy::require;
constexpr int end_tick=2048, age_ticks=81;
constexpr std::array arms{"east","read","place","bearing"};
using Identity=std::pair<int,int>; // site and birth tick

struct Neighbor {
    std::string bytes;
    int first=0,last=0,ticks=0;
    int facing=0, free=0, held=0, facing_room=0, pointer_held=0, selected=0;
    int reserve_won=0, blocked_full=0, blocked_contest=0;
};
struct Focal {
    Identity id, maker;
    std::string hex;
    int observed=0;
    std::map<Identity,Neighbor> neighbors;
    int global_s=0, distant_s=0, other_selected=0, neighbor_selected=0;
    int death() const { return id.second+age_ticks; }
    int maker_death() const { return maker.second+age_ticks; }
};
struct Write {int tick,site,born,offset,input,output; char kind;};
struct Attempt {
    int focal,actor,born,target;
    std::array<Write,6> writes{};
    int n=0, substitutions=0, failed_reads=0, finish=0;
    bool aligned=true;
    std::string status="cutoff", product;
    Attempt(int f,const Event& e):focal(f),actor(e.actor),born(int(e.actor_born)),target(e.target) {}
};
struct Files {
    std::ofstream fields, windows, neighbors, attempts, availability;
    explicit Files(const std::string& dir):
        fields(vacancy::output(dir,"fields.tsv","seed\tarm\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tstate_fnv64")),
        windows(vacancy::output(dir,"windows.tsv","seed\tarm\tfocal_site\tfocal_born\tproduct\tmaker_site\tmaker_born\topen_ticks\tcomplete")),
        neighbors(vacancy::output(dir,"neighbors.tsv","seed\tarm\tfocal_site\tfocal_born\tsite\tborn\tgenome\tfirst\tlast\tticks\tfacing\tfree\theld\tfacing_room\tpointer_held\tselected\treserve_won\tblocked_full\tblocked_contest")),
        attempts(vacancy::output(dir,"attempts.tsv","seed\tarm\tfocal_site\tfocal_born\tactor\tactor_born\ttarget\tn_writes\taligned\tsubstitutions\tfailed_reads\tstatus\tfinish\tproduct\ttrace")),
        availability(vacancy::output(dir,"availability.tsv","seed\tarm\tfocal_site\tfocal_born\tglobal_s_ticks\tdistant_s_ticks\tother_executed_s_ticks\tneighbor_executed_s_ticks")) {}
};

Config configuration(int seed) {
    Config c;
    c.width=16; c.height=4; c.seed=seed; c.max_age=80; c.mutation_ppm=20000;
    c.boundary=Boundary::torus; c.placement=Placement::first_free; c.access.read=true;
    return c;
}
struct Facing {int actor; Neighbor* record;};
class Observer {
    int seed;
    std::string arm;
    World w;
    SpatialExperiment space;
    std::vector<Focal>& focals;
    std::vector<Attempt> attempts;
    std::array<int,64> pending{}, watched{};
    std::vector<Facing> facing;
    int births=0, deaths=0, recent=0;

    void opening(int tick) {
        watched.fill(-1);
        facing.clear();
        int all_carriers=-1;
        for (int i=0;i<int(focals.size());++i) {
            Focal& f=focals[i];
            if (tick<=f.maker_death() || tick>f.death()) continue;
            int site=f.id.first;
            require(watched[site]<0 && w.at(site).kind==Bank::occupied &&
                    int(w.at(site).born)==f.id.second,"missing live focal");
            watched[site]=i;
            ++f.observed;
            if (all_carriers<0) {
                all_carriers=0;
                for (int j=0;j<w.size();++j) {
                    const auto& bank=w.at(j);
                    all_carriers+=bank.kind==Bank::occupied && bank.bytes.find('S')!=std::string::npos;
                }
            }
            int other=all_carriers-(w.at(site).bytes.find('S')!=std::string::npos);
            int adjacent_carriers=0;
            f.global_s+=other>0;
            for (int d=0;d<4;++d) {
                int adj=space.near[site][d];
                const auto& s=w.at(adj);
                if (s.kind!=Bank::occupied) continue;
                adjacent_carriers+=s.bytes.find('S')!=std::string::npos;
                Identity who{adj,int(s.born)};
                require(who!=f.maker,"maker survived cutoff");
                auto& n=f.neighbors[who];
                if (!n.ticks) {n.bytes=s.bytes; n.first=tick;}
                require(n.bytes==s.bytes,"changed occupied neighbor");
                ++n.ticks;
                n.last=tick;
                bool faces=s.cpu.bearing==(d+2)%4;
                bool held=s.cpu.target>=0;
                bool free=std::any_of(space.near[adj].begin(),space.near[adj].end(),
                                      [&](int target){return w.at(target).kind==Bank::free;});
                n.facing+=faces; n.held+=held; n.free+=free;
                n.facing_room+=faces && (held || free);
                n.pointer_held+=held && s.cpu.source==site;
                if (faces) facing.push_back({adj,&n});
            }
            f.distant_s+=other>adjacent_carriers;
        }
    }
    void copy(const Event& e) {
        int& index=pending[e.actor];
        bool local=e.read_site==e.actor;
        if (index<0) {
            if (local || e.write_offset || e.read_offset || watched[e.read_site]<0) return;
            int fi=watched[e.read_site];
            auto& neighbor=focals[fi].neighbors.at({e.actor,int(e.actor_born)});
            require(neighbor.bytes.find('S')!=std::string::npos && neighbor.pointer_held>0,"unaddressed read");
            index=int(attempts.size());
            attempts.emplace_back(fi,e);
        }
        auto& a=attempts[index];
        require(a.n<6 && a.n==e.write_offset && a.target==e.target && a.born==int(e.actor_born),"allocation mismatch");
        const auto& f=focals[a.focal];
        Bank kind=local?Bank::occupied:e.read_contact.kind;
        int born=local?int(e.actor_born):kind==Bank::occupied?int(e.read_contact.born):-1;
        bool same=e.read_site==f.id.first && kind==Bank::occupied && born==f.id.second;
        if (same) require(vacancy::hex(e.read_contact.bytes)==f.hex && int(e.tick)<=f.death(),"source audit");
        a.aligned &= same && e.read_offset==a.n;
        a.substitutions+=e.input!=e.output;
        a.writes[a.n++]={int(e.tick),e.read_site,born,e.read_offset,e.input,e.output,
                         kind==Bank::occupied?'o':kind==Bank::reserved?'r':'f'};
    }
    void close(const Event& e,const char* status) {
        int& index=pending[e.actor];
        if (index<0) return;
        auto& a=attempts[index];
        require(a.born==int(e.actor_born),"stale actor");
        a.finish=int(e.tick); a.status=status;
        if (e.effect==Effect::birth) {
            require(a.n==6 && a.target==e.target,"incomplete birth");
            for (int i=0;i<6;++i)
                require(a.writes[i].output==static_cast<unsigned char>(e.product.at(i)),"written product");
            a.product=vacancy::hex(e.product);
            if (a.aligned && !a.substitutions) require(a.product==focals[a.focal].hex,"exact product");
        }
        index=-1;
    }
public:
    Observer(int seed,const std::string& arm,std::vector<Focal>& focals):
        seed(seed),arm(arm),w(configuration(seed)),space(w),focals(focals) {
        pending.fill(-1); w.seed_site(36,"R..CLD");
    }
    void run(bool reverse) {
        std::vector<Event> events;
        for (int t=1;t<=end_tick;++t) {
            opening(t);
            w.step(&events,reverse);
            std::array<const Event*,64> by_site{};
            int executed_s=0;
            for (const auto& e:events) {
                by_site[e.actor]=&e;
                executed_s+=e.op=='S';
                switch (e.effect) {
                case Effect::copy: copy(e); break;
                case Effect::failed_copy:
                    if (pending[e.actor]>=0) ++attempts[pending[e.actor]].failed_reads;
                    break;
                case Effect::reserve: require(pending[e.actor]<0,"unclosed prior allocation"); break;
                case Effect::failed_division: close(e,"failed_division"); break;
                case Effect::death: ++deaths; close(e,"death"); break;
                case Effect::birth: {
                    close(e,"birth"); ++births; recent+=t>end_tick-80;
                    int draw=int(SpatialExperiment::draw(seed,t,128+e.target)%4);
                    w.set_birth_bearings(e.target,arm=="read" || arm=="bearing"?draw:1,
                                        arm=="place" || arm=="bearing"?draw:1);
                    break;
                }
                default: break;
                }
            }
            for (auto [site,n]:facing) {
                const auto& e=*by_site[site];
                n->selected+=e.op=='S';
                n->reserve_won+=e.effect==Effect::reserve;
                n->blocked_full+=e.effect==Effect::busy && e.target<0;
                n->blocked_contest+=e.effect==Effect::busy && e.target>=0;
            }
            for (auto& f:focals) {
                if (t>f.maker_death() && t<=f.death() && executed_s) {
                    const auto is_s=[&](int site){return by_site[site] && by_site[site]->op=='S';};
                    f.other_selected+=executed_s>int(is_s(f.id.first));
                    const auto& near=space.near[f.id.first];
                    f.neighbor_selected+=std::any_of(near.begin(),near.end(),is_s);
                }
                if (t==f.id.second) {
                    const auto* e=by_site[f.maker.first];
                    require(e && e->effect==Effect::birth && e->target==f.id.first &&
                            int(e->actor_born)==f.maker.second && vacancy::hex(e->product)==f.hex,"focal birth");
                }
                if (t==f.death() || t==f.maker_death()) {
                    auto id=t==f.death()?f.id:f.maker;
                    const auto* e=by_site[id.first];
                    require(e && e->effect==Effect::death && int(e->actor_born)==id.second,"age death");
                }
            }
        }
        w.check();
    }
    void write(Files& out) const {
        int alive=0; for (int i=0;i<64;++i) alive+=w.at(i).kind==Bank::occupied;
        require(alive==births+1-deaths,"population balance");
        out.fields<<seed<<'\t'<<arm<<'\t'<<births<<'\t'<<deaths<<'\t'<<alive<<'\t'<<recent
                  <<'\t'<<(!alive?"extinct":recent?"reproducing":"stagnant")<<'\t'<<w.hash()<<'\n';
        auto key=[&](std::ostream& out,const Focal& f)->std::ostream& {
            return out<<seed<<'\t'<<arm<<'\t'<<f.id.first<<'\t'<<f.id.second;
        };
        for (const auto& f:focals) {
            require(f.observed==std::max(0,std::min(end_tick,f.death())-f.maker_death()),"window length");
            key(out.windows,f)<<'\t'<<f.hex<<'\t'<<f.maker.first<<'\t'<<f.maker.second<<'\t'
                              <<f.observed<<'\t'<<(f.death()<=end_tick)<<'\n';
            key(out.availability,f)<<'\t'<<f.global_s<<'\t'<<f.distant_s<<'\t'<<f.other_selected
                                   <<'\t'<<f.neighbor_selected<<'\n';
            for (const auto& [id,n]:f.neighbors) {
                auto& os=key(out.neighbors,f);
                os<<'\t'<<id.first<<'\t'<<id.second<<'\t'<<vacancy::hex(n.bytes);
                for (int x:{n.first,n.last,n.ticks,n.facing,n.free,n.held,n.facing_room,n.pointer_held,
                            n.selected,n.reserve_won,n.blocked_full,n.blocked_contest}) os<<'\t'<<x;
                os<<'\n';
            }
        }
        for (const auto& a:attempts) {
            auto& os=key(out.attempts,focals[a.focal]);
            for (int x:{a.actor,a.born,a.target,a.n,int(a.aligned),a.substitutions,a.failed_reads}) os<<'\t'<<x;
            os<<'\t'<<a.status<<'\t'<<a.finish<<'\t'<<a.product<<'\t';
            for (int i=0;i<a.n;++i) {
                auto& r=a.writes[i];
                if (i) os<<',';
                os<<r.tick<<'/'<<r.site<<'/'<<r.born<<'/'<<r.kind<<'/'<<r.offset<<'/'<<r.input<<'/'<<r.output;
            }
            os<<'\n';
        }
    }
};
}

int main(int argc,char** argv) {
    try {
        if ((argc!=4 && argc!=5) || (argc==5 && std::string_view(argv[4])!="--reverse"))
            throw std::invalid_argument("usage: observe FIRST LAST OUT [--reverse] < focal-list");
        const int first=std::stoi(argv[1]),last=std::stoi(argv[2]);
        require(first>=19521 && last<=21568 && first<=last,"seed range");
        std::map<std::pair<int,std::string>,std::vector<Focal>> inputs;
        int seed,site,born,maker,created; std::string arm,hex;
        while (std::cin>>seed>>arm>>site>>born>>maker>>created>>hex) {
            require(seed>=first && seed<=last && std::find(arms.begin(),arms.end(),arm)!=arms.end() &&
                    site>=0 && site<64 && maker>=0 && maker<64 && born>created && born<=end_tick && hex.size()==12,
                    "invalid focal");
            inputs[{seed,arm}].push_back({{site,born},{maker,created},hex,0,{}});
        }
        require(std::cin.eof(),"unreadable focal input");
        Files files(argv[3]);
        for (seed=first;seed<=last;++seed) for (const auto* group:arms) {
            Observer study(seed,group,inputs[{seed,group}]); study.run(argc==5); study.write(files);
        }
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
