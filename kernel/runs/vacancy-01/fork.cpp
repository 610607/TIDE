#include "common.hpp"
#include <iostream>
#include <limits>
#include <sstream>

using namespace vacancy;
namespace {
struct Case {
    std::string cohort;
    int seed, site, born, opening, east, east_born, free;
    std::string eligible, start_hash, end_hash;
};
int distance(const tide::World& w, int a, int b) {
    const int width=w.config().width, height=w.config().height;
    int dx=std::abs(a%width-b%width), dy=std::abs(a/width-b/width);
    return std::min(dx,width-dx) + std::min(dy,height-dy);
}
int mismatches(std::string_view a,std::string_view b) {
    int n=static_cast<int>(std::max(a.size(),b.size()) - std::min(a.size(),b.size()));
    for (size_t j=0; j<std::min(a.size(),b.size()); ++j) n += a[j]!=b[j];
    return n;
}
int matched_remote(const tide::World& w, const Case& c, int local) {
    const auto& x=w.at(local);
    std::tuple<int,int,int> best{1000,0,-1};
    for (int i=0; i<w.size(); ++i) {
        const auto& y=w.at(i);
        if (distance(w,c.site,i)<3 || distance(w,c.east,i)<2 || !can_release(y)) continue;
        best=std::min(best,std::tuple{mismatches(x.bytes,y.bytes),
            std::abs(static_cast<int>(x.born)-static_cast<int>(y.born)),i});
    }
    return std::get<2>(best);
}
bool same_site(const tide::Site& a,const tide::Site& b) {
    auto fields=[](const tide::Site& s) {
        const auto& p=s.cpu;
        return std::tie(s.kind,s.bytes,s.born,s.owner,p.bank,p.pc,p.resume,p.bearing,p.source,p.read,p.target,p.written);
    };
    return fields(a)==fields(b);
}
enum class Arm { ordinary, local, remote, local_denied };
const char* label(Arm arm) {
    switch(arm) {
    case Arm::ordinary: return "ordinary";
    case Arm::local: return "local";
    case Arm::remote: return "remote";
    case Arm::local_denied: return "local_denied";
    }
    throw std::logic_error("unknown arm");
}
struct Copies {
    std::string inputs, provenance;
    int original=0, other_live=0, own=0, other_reserved=0, residual=0;
    int size() const { return static_cast<int>(inputs.size()); }
    int external() const { return original+other_live+own+other_reserved+residual; }
    void record(const tide::Event& e,const Case& c) {
        require(e.write_offset==size(),"nonsequential copy");
        inputs.push_back(static_cast<char>(e.input));
        if (!provenance.empty()) provenance+=',';
        const auto& h=e.read_contact;
        provenance+=std::to_string(e.tick)+"/"+std::to_string(e.read_site)+"/"+std::to_string(e.read_offset)+"/";
        if (h.site<0) {
            provenance+="self";
            return;
        }
        provenance+=std::string(kind(h.kind))+"/"+std::to_string(h.born)+"/"+std::to_string(h.reservation_owner);
        if (h.kind==tide::Bank::occupied) {
            if (h.site==c.east && h.born==static_cast<tide::Tick>(c.east_born)) ++original;
            else ++other_live;
        } else if (h.kind==tide::Bank::free) ++residual;
        else if (h.reservation_owner==e.actor) ++own;
        else ++other_reserved;
    }
};
struct Member {
    bool family=false, live_chain=false;
    int depth=-1;
    Copies copies;
};
struct Outputs {
    std::ofstream branches, products, claims;
    explicit Outputs(const std::string& dir) :
        branches(output(dir,"branches.tsv","cohort\tseed\tsite\tborn\topening\tlocal_option\tpreferred\tarm\treleased\tvictim_born\tvictim_hex\tmatch_byte_differences\tmatch_age_difference\tstart_fnv64\tpost_fnv64\topening_effect\topening_target\tfirst_reserve\tfirst_copy_attempt\tfirst_copy_success\tfirst_birth\tfirst_live_intact\tfounder_births\tfounder_reader_births\tfamily_births\treader_transmissions\toriginal_donor_transmissions\tmax_reader_depth\tmax_all_live_depth\treader_living\tfamily_living\tworld_births\tworld_deaths_after_fork\tworld_living\tfinal80_births\tstatus\tend_fnv64")),
        products(output(dir,"products.tsv","cohort\tseed\tsite\tborn\topening\tlocal_option\tarm\tparent_site\tparent_born\tparent_depth\ttick\tchild_site\tinputs_hex\tproduct_hex\toriginal_live_bytes\tother_live_bytes\town_reserved_bytes\tother_reserved_bytes\tfree_bytes\tchild_depth\tall_live_path\tcopy_provenance")),
        claims(output(dir,"claims.tsv","cohort\tseed\tsite\tborn\topening\tlocal_option\tarm\ttick\torigin\tactor_born\teffect\tproposal"))
    {}
};
int live_count(const tide::World& w) {
    int living=0;
    for(int i=0;i<w.size();++i) living+=w.at(i).kind==tide::Bank::occupied;
    return living;
}

void follow(const tide::World& start,const Case& c,int local,bool preferred,Arm arm,int victim,
            bool reverse,Outputs& out) {
    auto w=start;
    if(victim>=0) {
        w.release_idle_for_experiment(victim);
        for(int i=0;i<w.size();++i) if(i!=victim) require(same_site(w.at(i),start.at(i)),"collateral state change");
        require(w.tick()==start.tick() && w.at(victim).bytes==start.at(victim).bytes &&
                w.at(victim).kind==tide::Bank::free && live_count(w)==live_count(start)-1,"bad vacancy ledger");
    }
    if(arm==Arm::local_denied) w.set_access(c.site,{});
    int initial_live=live_count(w);
    std::string post=w.hash(), key=c.cohort+"\t"+std::to_string(c.seed)+"\t"+std::to_string(c.site)+"\t"+
        std::to_string(c.born)+"\t"+std::to_string(c.opening)+"\t"+std::to_string(local);
    std::array<Member,64> members;
    members[c.site].family=true; members[c.site].depth=0; members[c.site].live_chain=true;
    int reserve=0, attempt=0, copy=0, first_birth=0, founder_births=0, founder_reader_births=0;
    int primary=0, family_births=0, transmissions=0, donor_births=0, depth=0, live_depth=0;
    int births=0,deaths=0,recent=0,opening_target=-1;
    std::string opening_effect;
    std::vector<tide::Event> events;
    for(int k=0;k<follow_ticks;++k) {
        w.step(&events,reverse); w.check();
        const int t=static_cast<int>(w.tick());
        for(const auto& e:events) {
            const bool founder=e.actor==c.site && e.actor_born==static_cast<tide::Tick>(c.born);
            auto& p=members[e.actor];
            if(k==0) {
                if(founder) {opening_effect=tide::name(e.effect);opening_target=e.target;}
                if(e.op=='R' && (founder || (victim>=0 && e.target==victim)))
                    out.claims<<key<<'\t'<<label(arm)<<'\t'<<t<<'\t'<<e.actor<<'\t'<<e.actor_born
                              <<'\t'<<tide::name(e.effect)<<'\t'<<e.target<<'\n';
            }
            if(founder) {
                if(!reserve && e.effect==tide::Effect::reserve) reserve=t;
                if(!attempt && e.op=='C') attempt=t;
                if(!copy && e.effect==tide::Effect::copy) copy=t;
            }
            if(e.effect==tide::Effect::death) {
                ++deaths; p={};
                if(founder && arm==Arm::local_denied) w.set_access(c.site,start.config().access);
            }
            if(p.depth>=0 && e.effect==tide::Effect::reserve) p.copies={};
            if(p.depth>=0 && e.effect==tide::Effect::copy) p.copies.record(e,c);
            if(e.effect!=tide::Effect::birth) continue;
            ++births; recent+=k>=follow_ticks-80;
            auto& child=members[e.target];
            child={};
            if(!p.family) continue;
            child.family=true; ++family_births;
            if(p.depth<0) continue;
            const auto& b=p.copies;
            require(b.size()==static_cast<int>(e.product.size()),"missing copy records");
            const bool intact=b.inputs==reader && e.product==reader && b.external()==5;
            if(intact) {
                ++transmissions;
                donor_births+=b.original==5;
                child.depth=p.depth+1;
                child.live_chain=p.live_chain && b.original+b.other_live==5;
                depth=std::max(depth,child.depth);
                if(child.live_chain) live_depth=std::max(live_depth,child.depth);
            }
            if(founder) {
                ++founder_births; founder_reader_births+=e.product==reader;
                if(!first_birth) {first_birth=t; primary=intact && b.original==5;}
            }
            out.products<<key<<'\t'<<label(arm)<<'\t'<<e.actor<<'\t'<<e.actor_born<<'\t'<<p.depth<<'\t'<<t
                <<'\t'<<e.target<<'\t'<<hex(b.inputs)<<'\t'<<hex(e.product)<<'\t'<<b.original<<'\t'<<b.other_live
                <<'\t'<<b.own<<'\t'<<b.other_reserved<<'\t'<<b.residual<<'\t'<<child.depth<<'\t'<<child.live_chain
                <<'\t'<<b.provenance<<'\n';
        }
    }
    int living=live_count(w),family_live=0,reader_live=0;
    for (const auto& p:members) { family_live+=p.family; reader_live+=p.depth>=0; }
    require(initial_live+births-deaths==living && !opening_effect.empty(),"invalid follow-up ledger");
    if(arm==Arm::ordinary) require(w.hash()==c.end_hash,"ordinary follow-up diverged");
    if(arm==Arm::local_denied) require(founder_births==0 && !copy,"focal permission control failed");
    const bool remote=arm==Arm::remote;
    const int diff=remote?mismatches(start.at(local).bytes,start.at(victim).bytes):-1;
    const int age_diff=remote?std::abs(static_cast<int>(start.at(local).born)-static_cast<int>(start.at(victim).born)):-1;
    out.branches<<key<<'\t'<<preferred<<'\t'<<label(arm)<<'\t'<<victim<<'\t';
    if(victim<0) out.branches<<"-\t-";
    else out.branches<<start.at(victim).born<<'\t'<<hex(start.at(victim).bytes);
    out.branches<<'\t'<<diff<<'\t'<<age_diff<<'\t'<<c.start_hash<<'\t'<<post<<'\t'<<opening_effect<<'\t'
        <<opening_target<<'\t'<<reserve<<'\t'<<attempt<<'\t'<<copy<<'\t'<<first_birth<<'\t'<<primary<<'\t'
        <<founder_births<<'\t'<<founder_reader_births<<'\t'<<family_births<<'\t'<<transmissions<<'\t'<<donor_births
        <<'\t'<<depth<<'\t'<<live_depth<<'\t'<<reader_live<<'\t'<<family_live<<'\t'<<births<<'\t'<<deaths
        <<'\t'<<living<<'\t'<<recent<<'\t'<<(!living?"extinct":recent?"reproducing":"stagnant")<<'\t'<<w.hash()<<'\n';
}

void run(const Case& c, bool reverse, Outputs& out) {
    auto start=initial(c.seed);
    for(int t=1;t<c.opening;++t) start.step(nullptr,reverse);
    start.check();
    require(start.hash()==c.start_hash && start.at(c.site).born==static_cast<tide::Tick>(c.born) &&
            start.at(c.site).bytes==reader && start.neighbor(c.site,1)==c.east &&
            start.at(c.east).kind==tide::Bank::occupied && start.at(c.east).bytes==reader &&
            start.at(c.east).born==static_cast<tide::Tick>(c.east_born),"bad fork reconstruction");
    auto options=eligible_sites(start,c.site);
    require(free_neighbors(start,c.site)==c.free && site_list(options)==c.eligible,"eligibility changed");
    follow(start,c,-1,false,Arm::ordinary,-1,reverse,out);
    if(c.free) return;
    for(int local:options) {
        bool preferred=local==options.front();
        if(!preferred && c.cohort=="prospective") break;
        follow(start,c,local,preferred,Arm::local,local,reverse,out);
        int far=matched_remote(start,c,local);
        if(far>=0) follow(start,c,local,preferred,Arm::remote,far,reverse,out);
        follow(start,c,local,preferred,Arm::local_denied,local,reverse,out);
    }
}
}
int main(int argc,char** argv) {
    try {
        if((argc!=2 && argc!=3) || (argc==3 && std::string_view(argv[2])!="--reverse"))
            throw std::invalid_argument("usage: fork OUTPUT_DIR [--reverse]");
        std::ifstream in(std::string(argv[1])+"/encounters.tsv");
        std::string line;
        require(static_cast<bool>(std::getline(in,line)),"missing encounter table");
        Outputs out(argv[1]);
        while(std::getline(in,line)) {
            std::istringstream row(line); Case c; std::string extra;
            if(!(row>>c.cohort>>c.seed>>c.site>>c.born>>c.opening>>c.east>>c.east_born>>c.free>>c.eligible>>
                 c.start_hash>>c.end_hash) || (row>>extra)) throw std::invalid_argument("bad encounter record");
            run(c,argc==3,out);
        }
        out.branches.close(); out.products.close(); out.claims.close();
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
