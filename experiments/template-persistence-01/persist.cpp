// Turnover and resource exchange around the original two-symbol attachment engine.
#include "chamber.hpp"

namespace {
constexpr int horizon=2048, feed_interval=4, break_interval=8, break_denominator=16;
constexpr std::array<int,8> checkpoints{0,32,64,128,256,512,1024,horizon};
using Pieces=std::array<int,2>;
void account(Pieces& ledger,int sequence,int size) {
    int ones=std::popcount(static_cast<unsigned>(sequence));
    ledger[0]+=size-ones; ledger[1]+=ones;
}
bool breaks(int seed,int age,bool partial,int id) {
    Word key=(Word(seed)<<48)|(Word(age)<<32)|(Word(partial)<<31)|Word(id);
    return uniform(key,break_denominator)==0;
}
std::string tails(const Chamber& w) {
    std::string s;
    for (const End& e:w.ends) {
        if (!s.empty()) s+=',';
        s+=bits(e.sequence,e.n)+"/"+std::to_string(e.guide);
    }
    return s;
}
struct Life {
    int seq,born,guide,interrupted,depth,death=-1;
};
struct Field {
    Chamber w;
    int seed,origin_tick;
    std::vector<Life> lives;
    std::array<int,4> interrupted{-1,-1,-1,-1};
    Pieces supplied{},overflow{},full_waste{},partial_waste{};
    int exact=1,loss=-1,post_return=0,max_depth=0;
    Field(const Chamber& base,int seed,int tick):w(base),seed(seed),origin_tick(tick) {
        require(w.products()==1 && w.chains[1].born==tick && w.chains[1].guide==-1,"origin identity");
        lives.push_back({-1,-1,-1,-1,-1});
        lives.push_back({w.chains[1].sequence,0,-1,-1,0});
    }
    void break_end(int slot) {
        auto& e=w.ends[slot];
        require(e.n>=2,"partial without bonds");
        account(partial_waste,e.sequence,e.n);
        if (e.guide>=0) w.chains[e.guide].docked=false;
        e=End{};
        interrupted[slot]=-1;
    }
    void break_chain(int id,int age) {
        auto& c=w.chains[id];
        auto& p=lives[id];
        require(c.sequence==p.seq && p.death<0,"chain already lost");
        if (c.docked) {
            auto end=std::find_if(w.ends.begin(),w.ends.end(),[&](const End& e){return e.guide==id;});
            require(end!=w.ends.end(),"unmatched dock");
            if (end->n>0) interrupted[end-w.ends.begin()]=id;
            end->guide=-1;
        }
        account(full_waste,c.sequence,length);
        c.sequence=-1; c.docked=false; p.death=age;
        if (p.depth>=0 && --exact==0) {
            require(loss<0,"regrown exact family");
            loss=age;
        }
    }
    void turn_over(int age) {
        for (int j=0;j<4;++j) {
            int i=w.reverse?3-j:j;
            if (w.ends[i].n>=2 && breaks(seed,age,true,i)) break_end(i);
        }
        int last=w.products();
        for (int j=1;j<=last;++j) {
            int id=w.reverse?last+1-j:j;
            if (w.chains[id].sequence>=0 && breaks(seed,age,false,id)) break_chain(id,age);
        }
    }
    void feed() {
        for (int i=0;i<2;++i) {
            ++supplied[i];
            if (w.free[i]<stock) ++w.free[i];
            else ++overflow[i];
        }
    }
    void attach(int age,const Proposal& choice) {
        int before=w.products();
        w.step(origin_tick+age,choice);
        if (w.products()==before) return;
        const auto& c=w.chains.back();
        int gap=interrupted[choice.end];
        interrupted[choice.end]=-1;
        int depth=-1;
        if (c.guide>0) {
            const auto& parent=lives[c.guide];
            require(gap<0 && parent.death<0,"nonliving or interrupted guide");
            if (parent.depth>=0 && (parent.seq^c.sequence)==63) depth=parent.depth+1;
        }
        if (depth>=0) {
            require(exact>0 && loss<0,"false exact return");
            ++exact; max_depth=std::max(max_depth,depth);
            if (c.sequence==lives[1].seq && lives[1].death>=0 && age>lives[1].death) ++post_return;
        }
        lives.push_back({c.sequence,age,c.guide,gap,depth});
    }
    void audit(int age) const {
        Pieces live{};
        std::vector<int> docks(lives.size(),0);
        int families=0;
        for (int j=0;j<4;++j) {
            const auto& e=w.ends[j];
            account(live,e.sequence,e.n);
            if (e.guide>=0) ++docks.at(e.guide);
            if (interrupted[j]>=0) require(e.n>0 && e.guide<0 && lives[interrupted[j]].death>=0,"prefix");
        }
        for (int id=1;id<=w.products();++id) {
            const auto& c=w.chains[id];
            const auto& p=lives[id];
            require(docks[id]==int(c.docked) && (c.sequence>=0)==(p.death<0),"dock or lifetime");
            if (c.sequence<0) continue;
            account(live,c.sequence,length);
            families+=p.depth>=0;
        }
        for (int i=0;i<2;++i)
            require(stock+supplied[i]==w.free[i]+live[i]+overflow[i]+full_waste[i]+partial_waste[i],"mass balance");
        require(families==exact && w.accepted+w.rejected+w.missing==origin_tick+age,"family or encounter balance");
    }
};
std::ofstream table(const std::filesystem::path& dir,const char* name,const char* header) {
    std::ofstream out;
    out.exceptions(std::ios::badbit|std::ios::failbit);
    out.open(dir/name); out<<header<<'\n'; return out;
}
struct Tables {
    std::ofstream screen,worlds,chains,snaps,history;
    explicit Tables(const std::filesystem::path& dir):
        screen(table(dir,"screen.tsv","seed\ttick\tsequence\tpartial\tfree0\tfree1")),
        worlds(table(dir,"worlds.tsv","seed\tarm\torigin_death\tloss\texact_final\tpost_return\tmax_depth\taccepted\trejected\tmissing\tfeed0\tfeed1\toverflow0\toverflow1\tfull_waste0\tfull_waste1\tpartial_waste0\tpartial_waste1\tfree0\tfree1\tpartials")),
        chains(table(dir,"chains.tsv","seed\tarm\tid\tsequence\tborn\tdeath\tguide\tinterrupted\tdepth")),
        snaps(table(dir,"snapshots.tsv","seed\tarm\tage\tlive\texact")),
        history(table(dir,"history.tsv","seed\tproducts\tfree0\tfree1\taccepted\trejected\tmissing\tpartials")) {}
};
void snapshot(const Field& f,int age,const std::string& key,Tables& out) {
    f.audit(age);
    auto live=std::count_if(f.lives.begin()+1,f.lives.end(),[](const Life& p){return p.death<0;});
    out.snaps<<key<<'\t'<<age<<'\t'<<live<<'\t'<<f.exact<<'\n';
}
void run(const Chamber& base,int seed,int tick,bool fed,bool decay,Tables& out,bool rotated=false) {
    Field f(base,seed,tick);
    std::string arm=std::string(fed?"fed":"closed")+(decay?"_break":"_stable");
    if (rotated) arm+="_rotated";
    std::string key=std::to_string(seed)+'\t'+arm;
    auto historical=[&] {
        const auto& w=f.w;
        out.history<<seed<<'\t'<<w.products()<<'\t'<<w.free[0]<<'\t'<<w.free[1]
                   <<'\t'<<w.accepted<<'\t'<<w.rejected<<'\t'<<w.missing<<'\t'<<tails(w)<<'\n';
    };
    if (tick==budget && !fed && !decay) historical();
    snapshot(f,0,key,out);
    for (int age=1;age<=horizon;++age) {
        if (decay && age%break_interval==0) f.turn_over(age);
        if (fed && age%feed_interval==0) f.feed();
        f.attach(age,proposal(seed,1,tick+age));
        if (std::binary_search(checkpoints.begin(),checkpoints.end(),age)) snapshot(f,age,key,out);
        if (tick+age==budget && !fed && !decay) historical();
    }
    for (int id=1;id<=f.w.products();++id) {
        const auto& p=f.lives[id];
        out.chains<<key<<'\t'<<id<<'\t'<<p.seq<<'\t'<<p.born<<'\t'<<p.death<<'\t'
                  <<p.guide<<'\t'<<p.interrupted<<'\t'<<p.depth<<'\n';
    }
    out.worlds<<key<<'\t'<<f.lives[1].death<<'\t'<<f.loss<<'\t'<<f.exact<<'\t'<<f.post_return
              <<'\t'<<f.max_depth<<'\t'<<f.w.accepted<<'\t'<<f.w.rejected<<'\t'<<f.w.missing;
    for (auto pieces:{f.supplied,f.overflow,f.full_waste,f.partial_waste,f.w.free})
        out.worlds<<'\t'<<pieces[0]<<'\t'<<pieces[1];
    out.worlds<<'\t'<<tails(f.w)<<'\n';
}
void controls() {
    Chamber w(-1,false,false);
    for (int t=1;t<=6;++t) w.step(t,{0,0,0,0});
    Field f(w,first_seed,6);
    f.attach(1,{0,1,0,0}); f.attach(2,{0,1,0,0});
    f.break_chain(1,3);
    for (int t=3;t<=6;++t) f.attach(t,{0,1,0,0});
    f.audit(6);
    require(f.loss==3 && f.lives[2].depth==-1 && f.lives[2].interrupted==1,"interrupted matching birth");
    f.attach(7,{0,0,0,0}); f.attach(8,{0,0,0,0});
    f.break_end(0); f.feed(); f.audit(8);
    require(!f.w.chains[2].docked && f.partial_waste[0]==2,"partial loss did not release guide");
    Field bound(w,first_seed,6);
    bound.attach(1,{0,0,7,0}); bound.break_chain(1,2);
    bound.attach(2,{1,1,0,0}); bound.audit(2);
    require(bound.interrupted[0]<0 && bound.w.ends[0].guide<0,"empty dock after loss");
    Field replacement(w,first_seed,6);
    for (int t=1;t<=6;++t) replacement.attach(t,{0,1,0,0});
    replacement.break_chain(1,7);
    for (int t=7;t<=12;++t) replacement.attach(t,{0,0,0,0});
    replacement.audit(12);
    require(replacement.post_return==1 && replacement.lives[3].depth==2 && replacement.loss<0,"post-loss birth");
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls();return 0;}
        require(argc==2 || (argc==3 && std::string_view(argv[2])=="--reverse"),"usage: persist DIR [--reverse]");
        std::filesystem::create_directories(argv[1]);
        Tables out(argv[1]);
        for (int seed=first_seed;seed<=last_seed;++seed) {
            Chamber w(-1,false,argc==3);
            int tick=0;
            while (tick<budget && !w.products()) {++tick; w.step(tick,proposal(seed,1,tick));}
            w.audit(tick);
            out.screen<<seed<<'\t'<<(w.products()?tick:-1)<<'\t'<<(w.products()?w.chains[1].sequence:-1)
                      <<'\t'<<tails(w)<<'\t'<<w.free[0]<<'\t'<<w.free[1]<<'\n';
            if (!w.products()) continue;
            for (bool fed:{false,true}) for (bool decay:{false,true}) run(w,seed,tick,fed,decay,out);
            int original=w.chains[1].sequence;
            w.chains[1].sequence=((original<<1)&63)|(original>>5);
            run(w,seed,tick,true,true,out,true);
        }
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
