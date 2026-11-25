// A single delivery into a replayed field. All subsequent steps use the reference VM.
#include "lifetime.hpp"
#include "../spatial-transport-01/transport.hpp"
#include <cstdlib>

namespace tide {
struct PartnerPlacement {
    static void plant(World& w,int site,const std::string& genome) {
        vacancy::require(w.at(site).kind==Bank::free,"delivery requires a vacancy");
        World newborn(w.config());
        newborn.seed_site(site,genome);
        w.sites_.at(site)=newborn.at(site);
        w.sites_.at(site).born=w.tick();
    }
};
}

namespace {
constexpr int window=324;
struct Case {
    std::string block,genome,maker_genome,checkpoint;
    int seed,site,born,maker,maker_born,ordinary,denied,blocked;
    std::string key() const {
        return std::to_string(seed)+"-"+std::to_string(site)+"-"+std::to_string(born);
    }
};
int distance(int a,int b) {
    int x=std::abs(a%16-b%16), y=std::abs(a/16-b/16);
    return std::min(x,16-x)+std::min(y,4-y);
}
struct Plan {
    int near=-1,far=-1;
    std::vector<std::pair<int,int>> moves;
    std::string status="eligible";
};
Plan plan(const World& w,const Case& c) {
    Plan p;
    auto available=[&](int i) {return i!=c.site && i!=c.maker && w.at(i).kind!=Bank::reserved && w.at(i).cpu.target<0;};
    for (int d:{1,2,3,0}) {
        int i=w.neighbor(c.site,d);
        if (available(i)) {p.near=i; break;}
    }
    auto rank=[&](int i) {return std::tuple{w.at(i).kind!=Bank::free,-distance(i,c.site),i};};
    for (int i=0;i<w.size();++i)
        if (available(i) && distance(i,c.site)>=4 && (p.far<0 || rank(i)<rank(p.far))) p.far=i;
    if (p.near<0) p.status="no_near_site";
    else if (p.far<0) p.status="no_far_site";
    else {
        int park=0;
        for (int site:{p.near,p.far}) {
            if (w.at(site).kind==Bank::free) continue;
            while (park<w.size() && (!available(park) || w.at(park).kind!=Bank::free ||
                                     park==p.near || park==p.far)) ++park;
            if (park==w.size()) {p.status="no_parking"; break;}
            p.moves.emplace_back(site,park++);
        }
    }
    return p;
}

struct Branch {
    const Case& c;
    const World start;
    const std::string arm;
    bool reverse;
    int root=-1,match=-1,initial_count=0,births=0,deaths=0,living=0,recent=0;
    int partner_reads=0,first_partner_read=-1;
    std::string end_hash,tail_hash;
    std::vector<Life> lives;
    std::array<Material,64> writes{};
    std::array<int,64> ids{};

    Branch(const Case& c,const World& w,std::string arm,int matching_site,bool reverse):
        c(c),start(w),arm(std::move(arm)),reverse(reverse) {
        ids.fill(-1);
        for (int i=0;i<w.size();++i) {
            const auto& s=w.at(i);
            if (s.kind!=Bank::occupied) continue;
            ids[i]=int(lives.size());
            lives.emplace_back(i,int(s.born),-1,-1,s.bytes,Material{},false);
            if (i==c.site) root=ids[i];
            if (i==matching_site) match=ids[i];
            // A pre-delivery input cannot have been supplied by this newborn root.
            if (s.cpu.written) {
                auto& m=writes[i];
                m.output=w.at(s.cpu.target).bytes.substr(0,s.cpu.written);
                m.input.assign(s.cpu.written,'?');
                for (int j=0;j<s.cpu.written;++j) m.trace[j]={-1,-1,-1,-1,-1,'?'};
            }
        }
        initial_count=int(lives.size());
        require(root>=0 && lives[root].born==c.born,"missing root");
    }
    void observe() {
        World w=start;
        std::vector<Event> events;
        for (int t=c.born+1;t<=c.born+window+age;++t) {
            auto opening=ids;
            w.step(&events,reverse);
            for (const auto& e:events) {
                int actor=opening[e.actor];
                require(actor>=0 && lives[actor].born==int(e.actor_born),"actor identity");
                auto& m=writes[e.actor];
                if (e.effect==Effect::reserve) m=Material{};
                if (e.effect==Effect::copy) {
                    int src=opening[e.read_site];
                    char kind=e.actor==e.read_site?'s':e.read_contact.kind==Bank::occupied?'o':
                              e.read_contact.kind==Bank::reserved?'r':'f';
                    if (src>=0) require(static_cast<unsigned char>(lives[src].genome.at(e.read_offset))==e.input &&
                                         (kind=='s' || (kind=='o' && int(e.read_contact.born)==lives[src].born)),
                                         "living source mismatch");
                    m.append(e,src,src<0?-1:lives[src].born,kind);
                    if (actor==root && match>=0 && src==match) {
                        if (!partner_reads) first_partner_read=t;
                        ++partner_reads;
                    }
                }
                if (e.effect==Effect::birth) {
                    int donor=m.aligned_supplier(), id=int(lives.size());
                    require(opening[e.target]<0 && m.output==e.product &&
                            (donor<0 || m.input==lives[donor].genome),"untraced division");
                    lives[actor].children.push_back(id);
                    lives[actor].exposed+=m.external>0;
                    lives.emplace_back(e.target,t,actor,donor,e.product,m,false);
                    ids[e.target]=id;
                    if (t<=c.born+window) {++births; recent+=t>c.born+window-80;}
                }
                if (e.effect==Effect::death) {
                    require(t==lives[actor].born+age,"incorrect age");
                    ids[e.actor]=-1;
                    deaths+=t<=c.born+window;
                }
            }
            if (t==c.born+window) {
                end_hash=w.hash();
                for (int id:ids) living+=id>=0;
                require(initial_count+births-deaths==living,"population ledger");
            }
        }
        w.check(); tail_hash=w.hash();
    }
    void test_focal(const World& replay,Life& p) {
        const auto ordinary=assay(replay,p,lives,false,reverse);
        const auto denied=assay(replay,p,lives,true,reverse);
        p.denied=denied.births; p.blocked=denied.blocked;
        p.confirmed=p.exposed>0 && ordinary.births>0 && !p.denied && p.blocked>0;
        p.checkpoint=replay.hash();
    }
    void analyze(std::ostream& branches,std::ostream& nodes) {
        World replay=start;
        test_focal(replay,lives[root]);
        const auto& focal=lives[root];
        if (arm=="ordinary") require(focal.confirmed && int(focal.children.size())==c.ordinary &&
                                     focal.denied==c.denied && focal.blocked==c.blocked,"historical assay mismatch");
        std::vector<bool> path(lives.size()),via_match(lives.size());
        path[root]=focal.confirmed;
        int intact=0,direct=0,primary=0,primary_via_match=0,witness=-1;
        size_t next=initial_count;
        for (int t=c.born+1;t<=c.born+window;++t) {
            replay.step(nullptr,reverse);
            while (next<lives.size() && lives[next].born==t) {
                int id=int(next++);
                auto& p=lives[id];
                bool exact=p.genome==focal.genome;
                bool from_match=p.actor==root && match>=0 && p.donor==match &&
                                p.material.substitutions==0 && exact;
                intact+=from_match;
                bool linked=path[p.actor] || (p.donor>=0 && path[p.donor]);
                if (linked && p.exposed) test_focal(replay,p);
                path[id]=linked && p.confirmed;
                via_match[id]=path[id] && (from_match || via_match[p.actor] ||
                                           (p.donor>=0 && via_match[p.donor]));
                direct+=path[id] && exact && (p.actor==root || p.donor==root);
                bool qualifies=path[id] && exact && t>c.born+age;
                primary+=qualifies; primary_via_match+=qualifies && via_match[id];
                if (qualifies && witness<0) witness=id;
                if (!linked && p.actor!=root && p.donor!=root) continue;
                nodes<<c.key()<<'\t'<<arm<<'\t'<<id<<'\t'<<p.site<<'\t'<<t<<'\t'<<vacancy::hex(p.genome)
                     <<'\t'<<p.actor<<'\t'<<p.donor<<'\t'<<vacancy::hex(p.material.input)
                     <<'\t'<<p.material.substitutions<<'\t'<<p.material.external
                     <<'\t'<<p.children.size()<<'\t'<<p.exposed<<'\t'<<p.denied<<'\t'<<p.blocked<<'\t'<<path[id]
                     <<'\t'<<from_match<<'\t'<<via_match[id]<<'\t'<<qualifies<<'\t'<<p.checkpoint<<'\t';
                for (int j=0;j<length;++j) {
                    const auto& b=p.material.trace[j];
                    if (j) nodes<<',';
                    nodes<<b.tick<<'/'<<b.site<<'/'<<b.born<<'/'<<b.kind<<'/'<<b.offset<<'/'<<b.person;
                }
                nodes<<'\n';
            }
        }
        require(replay.hash()==end_hash,"enrollment hash mismatch");
        for (int i=0;i<age;++i) replay.step(nullptr,reverse);
        require(replay.hash()==tail_hash,"tail hash mismatch");
        branches<<c.key()<<'\t'<<arm<<'\t'<<root<<'\t'<<match<<'\t'<<initial_count<<'\t'<<births<<'\t'<<deaths
                <<'\t'<<living<<'\t'<<recent<<'\t'<<(!living?"extinct":recent?"reproducing":"stagnant")
                <<'\t'<<focal.children.size()<<'\t'<<focal.exposed<<'\t'<<focal.denied<<'\t'<<focal.blocked
                <<'\t'<<focal.confirmed<<'\t'<<partner_reads<<'\t'<<first_partner_read<<'\t'<<intact
                <<'\t'<<direct<<'\t'<<primary<<'\t'<<primary_via_match<<'\t'<<witness
                <<'\t'<<start.hash()<<'\t'<<end_hash<<'\t'<<tail_hash<<'\n';
    }
};
void study(const Case& c,bool reverse,std::ostream& sites,std::ostream& branches,std::ostream& nodes) {
    World field=initial(c.seed);
    while (field.tick()<Tick(c.born)) field.step(nullptr,reverse);
    const auto target=field.at(c.site).bytes, decoy=field.at(c.maker).bytes;
    require(field.hash()==c.checkpoint && vacancy::hex(target)==c.genome && vacancy::hex(decoy)==c.maker_genome &&
            field.at(c.maker).born==Tick(c.maker_born) && target!=decoy,"archive mismatch");
    auto run=[&](const World& w,const std::string& arm,int match) {
        w.check();
        Branch branch(c,w,arm,match,reverse);
        branch.observe(); branch.analyze(branches,nodes);
    };
    auto p=plan(field,c);
    sites<<c.key()<<'\t'<<p.status<<'\t'<<p.near<<'\t'<<p.far<<'\t';
    if (p.status=="eligible" && !p.moves.empty()) {
        for (size_t i=0;i<p.moves.size();++i) {
            if (i) sites<<',';
            sites<<p.moves[i].first<<'/'<<p.moves[i].second;
        }
    } else sites<<'-';
    sites<<'\n';
    run(field,"ordinary",-1);
    if (p.status!="eligible") return;
    SpatialExperiment spatial(field);
    for (auto [from,to]:p.moves) require(spatial.exchange(field,from,to),"parking exchange failed");
    for (bool together:{true,false}) {
        World w=field;
        int match=together?p.near:p.far, other=together?p.far:p.near;
        PartnerPlacement::plant(w,match,target);
        PartnerPlacement::plant(w,other,decoy);
        run(w,together?"together":"apart",match);
    }
}
}
int main(int argc,char** argv) {
    try {
        require(argc==2 || (argc==3 && std::string_view(argv[2])=="--reverse"),"usage: field DIR [--reverse]");
        auto sites=vacancy::output(argv[1],"placement.tsv","case\tstatus\tnear\tfar\tparked_from_to");
        auto branches=vacancy::output(argv[1],"branches.tsv","case\tarm\troot\tmatch\tinitial_living\tbirths\tdeaths\tliving\tlast80_births\tstatus\troot_births\troot_exposed\troot_denied\troot_blocked\troot_confirmed\tpartner_reads\tfirst_partner_read\tintact\tdirect\tprimary\tprimary_via_match\twitness\tstart_hash\tend_hash\ttail_hash");
        auto nodes=vacancy::output(argv[1],"nodes.tsv","case\tarm\tid\tsite\tborn\tgenome\tactor\tdonor\tinputs\tsubstitutions\texternal\tbirths\texposed\tdenied\tblocked\ton_path\tfrom_match\tvia_match\tprimary\tcheckpoint\twrites");
        Case c;
        int count=0;
        while (std::cin>>c.block>>c.seed>>c.site>>c.born>>c.genome>>c.maker>>c.maker_born>>c.maker_genome>>
               c.checkpoint>>c.ordinary>>c.denied>>c.blocked) {
            study(c,argc==3,sites,branches,nodes); ++count;
        }
        require(count>0 && std::cin.eof(),"invalid case list");
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
