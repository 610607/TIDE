// Natural pedigrees and focal lifetime counterfactuals in one stationary six-byte field.
#include "../vacancy-01/common.hpp"
#include <iostream>
#include <map>
#include <vector>

namespace {
using namespace tide;
using vacancy::require;
constexpr int age=81, length=6;
World initial(int seed,unsigned mutation=20000) {
    Config c; c.width=16; c.height=4; c.boundary=Boundary::torus; c.placement=Placement::first_free;
    c.max_age=80; c.access.read=true; c.mutation_ppm=mutation; c.seed=seed;
    World w(c); w.seed_site(36,"R..CLD"); return w;
}
struct Byte {int tick,site,born,offset,person; char kind;};
struct Material {
    std::array<Byte,length> trace{};
    std::string input,output;
    int external=0, substitutions=0;
    void append(const Event& e,int source,int born,char kind) {
        require(e.write_offset==int(input.size()) && e.write_offset<length,"unordered writes");
        trace[e.write_offset]={int(e.tick),e.read_site,born,e.read_offset,source,kind};
        input+=static_cast<char>(e.input); output+=static_cast<char>(e.output);
        external+=e.read_site!=e.actor; substitutions+=e.input!=e.output;
    }
    int aligned_supplier() const {
        require(input.size()==length,"incomplete division");
        int id=trace[0].person;
        for (int i=0;i<length;++i) if (trace[i].person!=id || trace[i].offset!=i) return -1;
        return id;
    }
};
struct Life {
    int site,born,actor,donor;
    std::string genome;
    Material material;
    bool absent=false,confirmed=false,material_path=false;
    int exposed=0, denied=-1, blocked=-1;
    std::string checkpoint="-";
    std::vector<int> children;
    Life(int site,int born,int actor,int donor,std::string genome,Material material,bool absent):
        site(site),born(born),actor(actor),donor(donor),genome(std::move(genome)),material(std::move(material)),absent(absent) {}
};
struct Assay { int births=0,blocked=0; };
Assay assay(World w,const Life& focal,const std::vector<Life>& lives,bool deny,bool reverse) {
    require(w.tick()==Tick(focal.born) && w.at(focal.site).kind==Bank::occupied &&
            w.at(focal.site).bytes==focal.genome && w.at(focal.site).born==w.tick(),"incorrect fork");
    if (deny) w.set_access(focal.site,{});
    Assay score;
    std::vector<Event> events;
    for (int t=focal.born+1;t<=focal.born+age;++t) {
        w.step(&events,reverse);
        auto it=std::find_if(events.begin(),events.end(),[&](const Event& e){return e.actor==focal.site;});
        require(it!=events.end() && it->actor_born==Tick(focal.born),"missing focal");
        const auto& e=*it;
        if (deny && e.op=='C' && e.read_site>=0 && e.read_site!=focal.site) {
            require(e.effect==Effect::failed_copy,"ineffective permission"); ++score.blocked;
        }
        if (e.effect==Effect::birth) {
            if (!deny) {
                const auto& child=lives.at(focal.children.at(score.births));
                require(child.born==t && child.site==e.target && child.genome==e.product,"unmatched ordinary birth");
            }
            ++score.births;
        }
        require((e.effect==Effect::death)==(t==focal.born+age),"focal lifetime");
    }
    if (!deny) require(score.births==int(focal.children.size()),"ordinary birth total");
    return score;
}
struct Field {
    int seed,horizon;
    bool reverse;
    std::vector<Life> lives;
    std::array<int,64> ids{};
    std::array<Material,64> writes{};
    std::map<std::string,int> stock;
    int births=0,deaths=0,living=0,recent=0;
    std::string at2048,at_end,at_tail;
    Field(int seed,int horizon,bool reverse):seed(seed),horizon(horizon),reverse(reverse) {
        ids.fill(-1); ids[36]=0; stock["R..CLD"]=1;
        lives.emplace_back(36,0,-1,-1,"R..CLD",Material{},true);
    }
    void observe() {
        auto w=initial(seed);
        std::vector<Event> events;
        for (int t=1;t<=horizon+age;++t) {
            auto opening=ids;
            w.step(&events,reverse);
            for (const auto& e:events) {
                const int actor=opening[e.actor];
                require(actor>=0 && int(e.actor_born)==lives[actor].born,"actor mismatch");
                if (e.effect==Effect::reserve) writes[e.actor]=Material{};
                if (e.effect==Effect::copy) {
                    int src=opening[e.read_site],born=src<0?-1:lives[src].born;
                    char kind=e.actor==e.read_site?'s':e.read_contact.kind==Bank::occupied?'o':
                              e.read_contact.kind==Bank::reserved?'r':'f';
                    if (src>=0) require((kind=='s' || kind=='o') &&
                        static_cast<unsigned char>(lives[src].genome.at(e.read_offset))==e.input,"wrong living input");
                    if (e.actor!=e.read_site) require(e.read_contact.site==e.read_site &&
                        (src<0?kind!='o':int(e.read_contact.born)==born) &&
                        static_cast<unsigned char>(e.read_contact.bytes.at(e.read_offset))==e.input,"wrong external input");
                    writes[e.actor].append(e,src,born,kind);
                }
                if (e.effect==Effect::birth) {
                    const auto& m=writes[e.actor];
                    auto donor=m.aligned_supplier();
                    require(opening[e.target]<0 && m.output==e.product &&
                            (donor<0 || m.input==lives[donor].genome),"invalid parentage");
                    int id=int(lives.size());
                    lives[actor].children.push_back(id);
                    lives[actor].exposed+=m.external>0;
                    lives.emplace_back(e.target,t,actor,donor,e.product,m,stock[e.product]==0);
                    ids[e.target]=id;
                    if (t<=horizon) {++births; recent+=t>horizon-80;}
                }
                if (e.effect==Effect::death) {
                    require(t==lives[actor].born+age,"age ledger");
                    ids[e.actor]=-1; deaths+=t<=horizon;
                }
            }
            for (const auto& e:events) {
                if (e.effect==Effect::birth) ++stock[e.product];
                if (e.effect==Effect::death) require(--stock[lives[opening[e.actor]].genome]>=0,"negative stock");
            }
            if (t%256==0 || t==horizon+age) w.check();
            if (t==2048) at2048=w.hash();
            if (t==horizon) {
                at_end=w.hash();
                for (int id:ids) living+=id>=0;
                require(1+births-deaths==living,"population balance");
            }
        }
        at_tail=w.hash();
    }
    void confirm() {
        auto replay=initial(seed);
        size_t next=0;
        for (int t=0;t<=horizon+age;++t) {
            if (t) replay.step(nullptr,reverse);
            if (t==2048) require(replay.hash()==at2048,"early field replay");
            if (t==horizon) require(replay.hash()==at_end,"field replay");
            while (next<lives.size() && lives[next].born==t) {
                auto& p=lives[next++];
                if (p.born>horizon || !p.exposed) continue;
                p.checkpoint=replay.hash();
                auto ordinary=assay(replay,p,lives,false,reverse);
                auto denied=assay(replay,p,lives,true,reverse);
                p.denied=denied.births; p.blocked=denied.blocked;
                p.confirmed=ordinary.births>0 && !p.denied && p.blocked>0;
            }
        }
        require(replay.hash()==at_tail && next==lives.size(),"tail replay");
    }
    bool earlier_ancestor(int id,const std::vector<int>& previous) const {
        std::vector<bool> ancestor(id,false);
        for (int i=id;i>=0;--i) if (i==id || ancestor[i]) {
            for (int parent:{lives[i].actor,lives[i].donor}) if (parent>=0) ancestor[parent]=true;
        }
        return std::any_of(previous.begin(),previous.end(),[&](int old){return ancestor[old];});
    }
    void write(const std::string& dir) {
        auto fields=vacancy::output(dir,"world.tsv","seed\thorizon\tbirths\tdeaths\tliving\tlast80_births\tstatus\thash2048\thash_end\thash_tail");
        fields<<seed<<'\t'<<horizon<<'\t'<<births<<'\t'<<deaths<<'\t'<<living<<'\t'<<recent<<'\t'
              <<(!living?"extinct":recent?"reproducing":"stagnant")<<'\t'<<at2048<<'\t'<<at_end<<'\t'<<at_tail<<'\n';
        auto nodes=vacancy::output(dir,"nodes.tsv","seed\tid\tsite\tborn\tgenome\tactor\tdonor\tinputs\texternal\tsubstitutions\tborn_absent\tordinary_births\texposed_births\tdenied_births\tblocked\tconfirmed\tmaterial_path\tcheckpoint\twrites");
        auto returns=vacancy::output(dir,"returns.tsv","seed\tid\tsite\tborn\tgenome\tprior_confirmed\tancestor_present");
        std::map<std::string,std::vector<int>> previous;
        for (int i=1;i<int(lives.size());++i) {
            auto& p=lives[i];
            auto& prior=previous[p.genome];
            if (p.confirmed && p.absent && p.material.input!=p.genome && !prior.empty()) {
                auto end=std::lower_bound(prior.begin(),prior.end(),p.born,
                                          [&](int old,int tick){return lives[old].born<tick;});
                std::vector<int> earlier(prior.begin(),end);
                if (!earlier.empty())
                    returns<<seed<<'\t'<<i<<'\t'<<p.site<<'\t'<<p.born<<'\t'<<vacancy::hex(p.genome)<<'\t'
                           <<earlier.size()<<'\t'<<earlier_ancestor(i,earlier)<<'\n';
            }
            if (p.confirmed) prior.push_back(i);
            p.material_path=p.born<=horizon && (p.confirmed || (p.donor>=0 && lives[p.donor].material_path));
            bool direct=lives[p.actor].confirmed || (p.donor>=0 && lives[p.donor].confirmed);
            if (!direct && !p.material_path && !(p.exposed && p.born<=horizon)) continue;
            nodes<<seed<<'\t'<<i<<'\t'<<p.site<<'\t'<<p.born<<'\t'<<vacancy::hex(p.genome)<<'\t'<<p.actor<<'\t'
                 <<p.donor<<'\t'<<vacancy::hex(p.material.input)<<'\t'<<p.material.external<<'\t'<<p.material.substitutions
                 <<'\t'<<p.absent<<'\t'<<p.children.size()<<'\t'<<p.exposed<<'\t'<<p.denied<<'\t'<<p.blocked<<'\t'
                 <<p.confirmed<<'\t'<<p.material_path<<'\t'<<p.checkpoint<<'\t';
            for (int j=0;j<length;++j) {
                const auto& b=p.material.trace[j];
                if (j) nodes<<',';
                nodes<<b.tick<<'/'<<b.site<<'/'<<b.born<<'/'<<b.kind<<'/'<<b.offset<<'/'<<b.person;
            }
            nodes<<'\n';
        }
    }
};
void controls() {
    auto w=initial(1,0);
    std::vector<Life> lives;
    lives.emplace_back(36,0,-1,-1,"R..CLD",Material{},true);
    auto ordinary=w;
    std::vector<Event> events;
    for (int t=1;t<=age;++t) {
        ordinary.step(&events);
        for (const auto& e:events) if (e.actor==36 && e.effect==Effect::birth) {
            lives[0].children.push_back(int(lives.size()));
            lives.emplace_back(e.target,t,0,0,e.product,Material{},false);
        }
    }
    auto a=assay(w,lives[0],lives,false,false), b=assay(w,lives[0],lives,true,true);
    require(a.births==3 && a.births==b.births && !b.blocked,"independent ancestor control");
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls();return 0;}
        if ((argc!=3 && argc!=4) || (argc==4 && std::string_view(argv[3])!="--reverse"))
            throw std::invalid_argument("usage: field SEED DIRECTORY [--reverse]");
        int seed=std::stoi(argv[1]);
        require(seed==19995 || (seed>=25665 && seed<=26688),"seed outside protocol");
        Field study(seed,seed==19995?2048:8192,argc==4);
        study.observe(); study.confirm(); study.write(argv[2]);
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
