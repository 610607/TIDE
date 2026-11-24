// Paired one-time relocations in otherwise stationary, archived digital fields.
#include "match.hpp"
#include <iostream>

namespace {
using namespace contact;
constexpr std::array arms{"east","read","place","bearing"};
Config configuration(int seed) {
    Config c; c.width=16; c.height=4; c.seed=seed; c.max_age=80; c.mutation_ppm=20000;
    c.boundary=Boundary::torus; c.placement=Placement::first_free; c.access.read=true;
    return c;
}
void orient(World& w,const std::string& arm,const Event& e) {
    int draw=int(SpatialExperiment::draw(int(w.config().seed),int(e.tick),128+e.target)%4);
    w.set_birth_bearings(e.target,arm=="read" || arm=="bearing"?draw:1,arm=="place" || arm=="bearing"?draw:1);
}
int population(const World& w) {
    int count=0;
    for (int i=0;i<w.size();++i) count+=w.at(i).kind==Bank::occupied;
    return count;
}
const char* status(int living,int recent) {
    return !living?"extinct":recent?"reproducing":"stagnant";
}
std::string prefix(int seed,const std::string& arm,const Focal& f) {
    return std::to_string(seed)+"\t"+arm+"\t"+std::to_string(f.site)+"\t"+std::to_string(f.born);
}
struct Files {
    std::ofstream fields,screen,branches,attempts,reuse,reuse_attempts;
    explicit Files(const std::string& dir):
        fields(vacancy::output(dir,"fields.tsv","seed\tarm\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tstate_fnv64")),
        screen(vacancy::output(dir,"screen.tsv","seed\tarm\tfocal_site\tfocal_born\tproduct\tmaker_born\tstatus\ttick\treader_origin\treader_born\tnext_natural_s\tcontact\tsham\tdx\tdy\tbank\tsame_bytes\tfree_neighbors\treader\tbearing\tcheckpoint")),
        branches(vacancy::output(dir,"branches.tsv","seed\tarm\tfocal_site\tfocal_born\tbranch\treader_at\tend\tinitial_living\tbirths\tdeaths\tliving\tfinal80_births\tstatus\tfinal_hash\tfinal_copies\toverlap\tfacing\troom\tfacing_room\theld\tpointed_held\texecuted_s\tselected_focal\treserve_won\tblocked_full\tblocked_contest\tselected_first\tselected_six\tselected_exact\tany_first\tany_six\tany_exact")),
        attempts(vacancy::output(dir,"attempts.tsv","seed\tarm\tfocal_site\tfocal_born\tbranch\tactor\tactor_born\tselected\ttarget\tn_writes\taligned\tsubstitutions\tstatus\tfinish\tproduct\ttrace")),
        reuse(vacancy::output(dir,"reuse.tsv","seed\tarm\tfocal_site\tfocal_born\tchild_site\tchild_born\tchild_genome\tmaker_site\tmaker_born\twindow_complete\tend\tinitial_living\tbirths\tdeaths\tliving\tfinal_hash\tfirst\tsix\texact\tmaker_exact\tother_exact\tpost_death_exact")),
        reuse_attempts(vacancy::output(dir,"reuse-attempts.tsv","seed\tarm\tfocal_site\tfocal_born\tchild_site\tchild_born\tbranch\tactor\tactor_born\tselected\ttarget\tn_writes\taligned\tsubstitutions\tstatus\tfinish\tproduct\ttrace")) {}
};
struct Write {int tick,site,born,offset,input,output; char kind;};
struct Attempt {
    int actor,born,target;
    bool selected, aligned=true;
    int n=0,changes=0,finish=0;
    std::string status="cutoff",product;
    std::array<Write,6> trace{};
    Attempt(const Event& e,bool chosen):actor(e.actor),born(int(e.actor_born)),target(e.target),selected(chosen) {}
};
struct Outcome {
    int reader_at=0, initial=0, births=0,deaths=0,alive=0,recent=0,copies=0;
    int overlap=0,facing=0,room=0,facing_room=0,held=0,pointed=0,executed_s=0,selected_focal=0;
    int won=0,full=0,contest=0,selected_first=0,selected_six=0,selected_exact=0,any_six=0,any_exact=0;
    std::string hash;
    std::vector<Attempt> attempts;
};
struct BornCopy { Focal child; Match maker; World opening; };
Outcome follow(World w,const SpatialExperiment& space,const std::string& arm,const Focal& f,const Match& m,
               int dest,int prior_recent,bool reverse,std::vector<BornCopy>* copies=nullptr) {
    Outcome o; o.initial=population(w); o.recent=prior_recent; o.reader_at=dest;
    require(w.tick()+1==Tick(m.tick) && w.at(m.origin).born==Tick(m.born) && w.at(m.origin).kind==Bank::occupied,
            "opening identity or tick");
    auto reader_bytes=w.at(m.origin).bytes;
    if (dest!=m.origin) {
        int expected=room_after(w,space,m.origin,dest);
        require(space.exchange(w,m.origin,dest),"ineligible placement");
        auto& neighbors=space.near[dest];
        require(std::count_if(neighbors.begin(),neighbors.end(),[&](int i){return w.at(i).kind==Bank::free;})==expected,
                "post-exchange room mismatch");
    }
    w.check();
    require(w.at(dest).bytes==reader_bytes && w.at(dest).born==Tick(m.born) && w.at(f.site).born==Tick(f.born) &&
            vacancy::hex(w.at(f.site).bytes)==f.hex && population(w)==o.initial,"placement conservation");
    std::array<int,64> pending; pending.fill(-1);
    std::vector<Event> events;
    std::vector<int> born_copies;
    for (int t=m.tick;t<=f.end();++t) {
        const auto& reader=w.at(dest);
        bool living_focal=t<=f.death();
        bool overlap=living_focal && reader.kind==Bank::occupied && int(reader.born)==m.born;
        if (living_focal) require(w.at(f.site).kind==Bank::occupied && int(w.at(f.site).born)==f.born,"focal identity");
        bool faces=false;
        if (overlap) {
            ++o.overlap; faces=space.near[dest][reader.cpu.bearing]==f.site;
            bool held=reader.cpu.target>=0;
            bool room=held || std::any_of(space.near[dest].begin(),space.near[dest].end(),
                                          [&](int i){return w.at(i).kind==Bank::free;});
            o.facing+=faces; o.held+=held; o.room+=room; o.facing_room+=faces && room;
            o.pointed+=held && reader.cpu.source==f.site;
        }
        w.step(&events,reverse);
        born_copies.clear();
        for (const auto& e:events) {
            bool chosen=e.actor==dest && int(e.actor_born)==m.born;
            if (overlap && chosen) {
                o.executed_s+=e.op=='S'; o.selected_focal+=e.op=='S' && faces;
                o.won+=e.effect==Effect::reserve;
                o.full+=e.effect==Effect::busy && e.target<0;
                o.contest+=e.effect==Effect::busy && e.target>=0;
            }
            auto& index=pending[e.actor];
            if (e.effect==Effect::copy) {
                bool focal_source=e.read_site==f.site && e.actor!=f.site &&
                    e.read_contact.kind==Bank::occupied && int(e.read_contact.born)==f.born;
                if (index<0) {
                    if (!focal_source || e.read_offset!=0 || e.write_offset!=0) continue;
                    index=int(o.attempts.size()); o.attempts.emplace_back(e,chosen);
                    o.selected_first+=chosen;
                }
                auto& a=o.attempts[index];
                require(a.actor==e.actor && a.born==int(e.actor_born) && a.target==e.target &&
                        a.n<6 && e.write_offset==a.n,"allocation discontinuity");
                bool self=e.read_site==e.actor;
                auto kind=self?Bank::occupied:e.read_contact.kind;
                int born=self?int(e.actor_born):kind==Bank::occupied?int(e.read_contact.born):-1;
                if (focal_source) require(t<=f.death() && vacancy::hex(e.read_contact.bytes)==f.hex,"focal source audit");
                a.aligned &= focal_source && e.read_offset==a.n;
                a.changes+=e.input!=e.output;
                a.trace[a.n++]={t,e.read_site,born,e.read_offset,e.input,e.output,
                                kind==Bank::occupied?'o':kind==Bank::reserved?'r':'f'};
            }
            if (e.effect==Effect::reserve) require(index<0,"stale allocation");
            if (e.effect==Effect::birth || e.effect==Effect::death || e.effect==Effect::failed_division) {
                if (index>=0) {
                    auto& a=o.attempts[index];
                    require(a.born==int(e.actor_born),"wrong executor");
                    a.finish=t;
                    a.status=e.effect==Effect::birth?"birth":e.effect==Effect::death?"death":"failed_division";
                    if (e.effect==Effect::birth) {
                        require(a.n==6 && a.target==e.target,"incomplete birth");
                        a.product=vacancy::hex(e.product);
                        for (int i=0;i<6;++i) require(a.trace[i].output==static_cast<unsigned char>(e.product.at(i)),"wrong product");
                        if (a.aligned && !a.changes) {
                            require(a.product==f.hex,"exact bytes mismatch");
                            ++o.any_exact; o.selected_exact+=a.selected;
                            if (copies) born_copies.push_back(index);
                        }
                    }
                    index=-1;
                }
                if (e.effect==Effect::birth) {++o.births; o.recent+=t>f.end()-80; orient(w,arm,e);}
                if (e.effect==Effect::death) ++o.deaths;
            }
        }
        // Newborn bearings are assigned from all committed births before the next opening.
        for (int index:born_copies) {
            const auto& a=o.attempts[index];
            Match maker; maker.tick=t+1; maker.origin=a.actor; maker.born=a.born;
            copies->push_back({{a.target,t,a.born,a.product},maker,w});
        }
    }
    for (const auto& a:o.attempts) if (a.n==6 && a.aligned) {++o.any_six; o.selected_six+=a.selected;}
    w.check(); o.alive=population(w); o.hash=w.hash();
    require(o.initial+o.births-o.deaths==o.alive,"branch population balance");
    for (int i=0;i<w.size();++i) o.copies+=w.at(i).kind==Bank::occupied && vacancy::hex(w.at(i).bytes)==f.hex;
    return o;
}
void write_attempts(std::ostream& out,const std::string& key,const std::string& branch,const Outcome& o);
void record(Files& files,const std::string& key,const Focal& f,const std::string& branch,const Outcome& o) {
    auto& os=files.branches;
    os<<key<<'\t'<<branch;
    for (int x:{o.reader_at,f.end(),o.initial,o.births,o.deaths,o.alive,o.recent}) os<<'\t'<<x;
    os<<'\t'<<status(o.alive,o.recent)<<'\t'<<o.hash;
    for (int x:{o.copies,o.overlap,o.facing,o.room,o.facing_room,o.held,o.pointed,o.executed_s,o.selected_focal,
                o.won,o.full,o.contest,o.selected_first,o.selected_six,o.selected_exact,int(o.attempts.size()),
                o.any_six,o.any_exact}) os<<'\t'<<x;
    os<<'\n';
    write_attempts(files.attempts,key,branch,o);
}
void write_attempts(std::ostream& out,const std::string& key,const std::string& branch,const Outcome& o) {
    for (const auto& a:o.attempts) {
        out<<key<<'\t'<<branch;
        for (int x:{a.actor,a.born,int(a.selected),a.target,a.n,int(a.aligned),a.changes}) out<<'\t'<<x;
        out<<'\t'<<a.status<<'\t'<<a.finish<<'\t'<<a.product<<'\t';
        for (int i=0;i<a.n;++i) {
            const auto& r=a.trace[i]; if (i) out<<',';
            out<<r.tick<<'/'<<r.site<<'/'<<r.born<<'/'<<r.kind<<'/'<<r.offset<<'/'<<r.input<<'/'<<r.output;
        }
        out<<'\n';
    }
}
void follow_copy(Files& files,const std::string& key,const BornCopy& copy,const SpatialExperiment& space,
                 const std::string& arm,bool reverse) {
    const auto& child=copy.child;
    const auto& maker=copy.maker;
    auto outcome=follow(copy.opening,space,arm,child,maker,maker.origin,0,reverse);
    int post=0;
    for (const auto& a:outcome.attempts)
        post+=a.status=="birth" && a.aligned && !a.changes && !a.selected && a.trace[0].tick>maker.born+lifespan;
    auto child_key=key+'\t'+std::to_string(child.site)+'\t'+std::to_string(child.born);
    auto& out=files.reuse;
    out<<child_key<<'\t'<<child.hex;
    for (int x:{maker.origin,maker.born,int(child.death()<=end_tick),child.end(),outcome.initial,outcome.births,
                outcome.deaths,outcome.alive}) out<<'\t'<<x;
    out<<'\t'<<outcome.hash;
    for (int x:{int(outcome.attempts.size()),outcome.any_six,outcome.any_exact,outcome.selected_exact,
                outcome.any_exact-outcome.selected_exact,post}) out<<'\t'<<x;
    out<<'\n';
    write_attempts(files.reuse_attempts,child_key,"contact",outcome);
}
void run(int seed,const std::string& arm,const std::vector<Focal>& focals,bool reverse,Files& files) {
    World w(configuration(seed)); w.seed_site(36,"R..CLD");
    SpatialExperiment space(w);
    std::array<bool,end_tick+1> opening{},endpoints{};
    for (const auto& f:focals) {
        for (int t=f.first();t<=f.death();++t) opening[t]=true;
        endpoints[f.end()]=true;
    }
    std::map<int,Frame> frames;
    std::map<int,std::string> hashes;
    std::array<int,end_tick+1> births{};
    std::vector<Event> events;
    int deaths=0;
    for (int t=1;t<=end_tick;++t) {
        Frame* frame=opening[t]?&frames.try_emplace(t,w).first->second:nullptr;
        births[t]=births[t-1];
        w.step(&events,reverse);
        for (const auto& e:events) {
            if (frame && e.op=='S') frame->active.emplace_back(e.actor,int(e.actor_born));
            if (e.effect==Effect::birth) {++births[t]; orient(w,arm,e);}
            deaths+=e.effect==Effect::death;
        }
        if (endpoints[t]) hashes[t]=w.hash();
    }
    w.check();
    int alive=population(w), recent=births[end_tick]-births[end_tick-80];
    require(1+births.back()-deaths==alive,"baseline population balance");
    files.fields<<seed<<'\t'<<arm<<'\t'<<births.back()<<'\t'<<deaths<<'\t'<<alive<<'\t'<<recent
                <<'\t'<<status(alive,recent)<<'\t'<<w.hash()<<'\n';
    for (const auto& f:focals) {
        auto m=choose(frames,f,space);
        auto key=prefix(seed,arm,f);
        auto& out=files.screen;
        out<<key<<'\t'<<f.hex<<'\t'<<f.maker_born<<'\t'<<m.status()<<'\t'<<m.tick<<'\t'<<m.origin<<'\t'<<m.born
           <<'\t'<<m.ordinary_s<<'\t'<<m.near<<'\t'<<m.sham;
        if (!m.tick) {out<<"\t-1\t-1\t-\t-1\t-1\t-\t-1\t-\n"; continue;}
        const World& fork=frames.at(m.tick).world;
        auto [dx,dy]=distance(m.origin,m.near);
        require(distance(m.origin,m.sham)==std::make_pair(dx,dy) && adjacent(m.near,f.site) &&
                !adjacent(m.sham,f.site) && m.sham!=f.site,"branch geometry");
        int free=room_after(fork,space,m.origin,m.near);
        require(fork.at(m.sham).kind==fork.at(m.near).kind && free==room_after(fork,space,m.origin,m.sham),"match");
        out<<'\t'<<dx<<'\t'<<dy<<'\t'<<(fork.at(m.near).kind==Bank::free?"free":"occupied")
           <<'\t'<<(fork.at(m.near).bytes==fork.at(m.sham).bytes)<<'\t'<<free<<'\t'<<vacancy::hex(fork.at(m.origin).bytes)
           <<'\t'<<fork.at(m.origin).cpu.bearing<<'\t'<<fork.hash()<<'\n';
        int prior_recent=std::max(0,births[m.tick-1]-births[std::max(0,f.end()-80)]);
        for (auto [name,dest]:{std::pair{"ordinary",m.origin},{"contact",m.near},{"sham",m.sham}}) {
            std::vector<BornCopy> copies;
            auto outcome=follow(fork,space,arm,f,m,dest,prior_recent,reverse,name==std::string_view("contact")?&copies:nullptr);
            if (dest==m.origin) require(outcome.hash==hashes.at(f.end()) && !outcome.any_exact,"ordinary replay");
            record(files,key,f,name,outcome);
            for (const auto& copy:copies) follow_copy(files,key,copy,space,arm,reverse);
        }
    }
}
void controls() {
    Config c=configuration(11); c.mutation_ppm=0;
    World w(c); w.seed_site(21,".....P"); w.seed_site(29,".....P"); w.seed_site(33,"RS.CLD",0,2);
    SpatialExperiment space(w);
    Focal f{21,0,-81,vacancy::hex(".....P")};
    Match m; m.tick=1; m.origin=33; m.born=0; m.near=37; m.sham=45;
    require(distance(33,37)==distance(33,45) && room_after(w,space,33,37)==room_after(w,space,33,45),
            "fixture geometry and room");
    auto contact=follow(w,space,"east",f,m,m.near,0,false);
    auto sham=follow(w,space,"east",f,m,m.sham,0,false);
    require(contact.selected_exact>0 && !sham.selected_first,"fixed-program placement");
    Focal twin{29,0,-81,f.hex};
    require(follow(w,space,"east",twin,m,m.sham,0,false).selected_exact>0,"sham twin attribution");
    require(contact.hash==follow(w,space,"east",f,m,m.near,0,true).hash,"reverse control");
    std::cout<<"Paired placement controls passed\n";
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls(); return 0;}
        if ((argc!=4 && argc!=5) || (argc==5 && std::string_view(argv[4])!="--reverse"))
            throw std::invalid_argument("usage: trial FIRST LAST OUT [--reverse] < focal-list");
        int first=std::stoi(argv[1]),last=std::stoi(argv[2]);
        require(first>=19521 && last<=21568 && first<=last,"seed range");
        std::map<std::pair<int,std::string>,std::vector<Focal>> inputs;
        int seed; std::string arm; Focal f{};
        while (std::cin>>seed) {
            require(bool(std::cin>>arm>>f.site>>f.born>>f.maker_born>>f.hex),"incomplete focal");
            require(seed>=first && seed<=last && std::find(arms.begin(),arms.end(),arm)!=arms.end() && f.site>=0 &&
                    f.site<64 && f.maker_born>=0 && f.born>f.maker_born && f.death()<=end_tick && f.hex.size()==12,
                    "invalid focal");
            inputs[{seed,arm}].push_back(f);
        }
        require(std::cin.eof(),"invalid seed");
        Files files(argv[3]);
        for (seed=first;seed<=last;++seed) for (const char* group:arms)
            run(seed,group,inputs[{seed,group}],argc==5,files);
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
