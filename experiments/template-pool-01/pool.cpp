// An exploratory two-symbol pool. A guide affects one proposed attachment at a time.
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {
constexpr int length=6, stock=64, budget=160, founder=0b001011, reorder=0b011100;
constexpr int first_seed=27713, last_seed=29760;
using Word=std::uint64_t;
void require(bool ok,const char* message) {
    if (!ok) throw std::logic_error(message);
}
Word mix(Word x) {
    x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL;
    return x^(x>>31);
}
Word random_key(int seed,int round,int tick,int stream) {
    return (Word(seed)<<32) | (Word(round)<<24) | (Word(tick)<<8) | Word(stream);
}
int uniform(Word key,int count) {
    require(count>0,"empty choice");
    const Word n=count, discard=(Word(0)-n)%n;
    for (;;) {
        Word x=mix(key);
        if (x>=discard) return int(x%n);
        key+=0x9e3779b97f4a7c15ULL;
    }
}
std::string bits(int value,int n) {
    if (!n || value<0) return "-";
    std::string s(n,'0');
    for (int i=0;i<n;++i) s[n-1-i]+=((value>>i)&1);
    return s;
}
struct Chain {
    int sequence,guide,born;
    bool blind=false, docked=false;
};
struct End {
    int n=0,sequence=0,guide=-1;
};
struct Proposal {int end,piece,draw; Word choice;};
Proposal proposal(int seed,int round,int tick) {
    return {uniform(random_key(seed,round,tick,0),4), uniform(random_key(seed,round,tick,1),2),
            uniform(random_key(seed,round,tick,2),8), random_key(seed,round,tick,3)};
}
struct Chamber {
    // ID 0 denotes the supplied chain when present. Products have IDs 1,2,...
    std::vector<Chain> chains;
    std::array<End,4> ends{};
    std::array<int,2> free{stock,stock};
    int rejected=0,missing=0,accepted=0;
    bool reverse;
    Chamber(int supplied,bool blind,bool reverse):chains{{supplied,-1,0,blind}},reverse(reverse) {}
    int available_guide(Word choice) const {
        auto available=[](const Chain& g){return g.sequence>=0 && !g.docked;};
        int count=int(std::count_if(chains.begin(),chains.end(),available));
        if (!count) return -1;
        int rank=uniform(choice,count);
        if (reverse) rank=count-1-rank;
        int size=int(chains.size());
        for (int j=0;j<size;++j) {
            int id=reverse?size-j-1:j;
            if (available(chains[id]) && rank--==0) return id;
        }
        throw std::logic_error("guide rank");
    }
    void step(int tick,const Proposal& p) {
        End& e=ends[p.end];
        if (e.n==0 && e.guide<0) {
            e.guide=available_guide(p.choice);
            if (e.guide>=0) chains[e.guide].docked=true;
        }
        if (!free[p.piece]) {++missing; return;}
        int threshold=1;
        if (e.guide>=0) {
            const auto& g=chains[e.guide];
            int template_piece=(g.sequence>>(length-1-e.n))&1;
            if (g.blind) threshold=4;
            else if (template_piece!=p.piece) threshold=7;
        }
        if (p.draw>=threshold) {++rejected; return;}
        --free[p.piece];
        ++accepted; ++e.n; e.sequence=2*e.sequence+p.piece;
        if (e.n==length) {
            if (e.guide>=0) chains[e.guide].docked=false;
            chains.push_back({e.sequence,e.guide,tick});
            e=End{};
        }
    }
    int products() const {return int(chains.size())-1;}
    void audit(int ticks) const {
        std::array<int,2> used{};
        std::vector<int> attachments(chains.size(),0);
        auto add=[&](int seq,int n) {
            int ones=std::popcount(static_cast<unsigned>(seq));
            used[0]+=n-ones; used[1]+=ones;
        };
        for (int j=0;j<4;++j) {
            const auto& end=ends[reverse?3-j:j];
            require(end.n>=0 && end.n<length && end.sequence<(1<<end.n),"invalid partial chain");
            add(end.sequence,end.n);
            if (end.guide>=0) ++attachments.at(end.guide);
        }
        for (int id=0;id<int(chains.size());++id) {
            const auto& c=chains[id];
            require(attachments[id]==int(c.docked),"guide shared between ends");
            if (!id) continue;
            require(c.guide<id && (c.guide<0 || (chains[c.guide].sequence>=0 && chains[c.guide].born<c.born)),
                    "invalid guide identity");
            add(c.sequence,length);
        }
        require(free[0]+used[0]==stock && free[1]+used[1]==stock && used[0]+used[1]==accepted,
                "piece balance");
        require(ticks==accepted+missing+rejected,"encounter balance");
    }
};
Chamber run(int seed,int round,int supplied,bool blind,bool reverse) {
    Chamber w(supplied,blind,reverse);
    for (int t=1;t<=budget;++t) w.step(t,proposal(seed,round,t));
    w.audit(budget);
    return w;
}
void controls() {
    Chamber guided(founder,false,false), bare(-1,false,true);
    int tick=0;
    for (int j=0;j<length;++j) {
        int original=(founder>>(length-1-j))&1;
        for (int piece:{original,1-original}) {
            Proposal p{0,piece,6,0};
            ++tick;
            guided.step(tick,p); bare.step(tick,p);
            guided.audit(tick); bare.audit(tick);
        }
    }
    require(!bare.products() && guided.products()==1 && guided.chains[1].sequence==(63^founder) &&
            guided.chains[1].guide==0 && !guided.chains[0].docked,"one-piece copying control");
    // Masking a guide's positions must remove any dependence on its order.
    auto blind=run(first_seed,1,founder,true,false), swapped=run(first_seed,1,reorder,true,true);
    require(blind.free==swapped.free && blind.products()==swapped.products(),"blind availability control");
    for (int id=1;id<=blind.products();++id)
        require(blind.chains[id].sequence==swapped.chains[id].sequence &&
                blind.chains[id].guide==swapped.chains[id].guide && blind.chains[id].born==swapped.chains[id].born,
                "blind sequence control");
    // Bare ends can also assemble a chain. Once the stock is exhausted attempts cannot add mass.
    Chamber limited(-1,false,false);
    for (int t=1;t<=stock+8;++t) limited.step(t,{0,0,0,0});
    limited.audit(stock+8);
    require(limited.chains[1].guide==-1 && limited.free[0]==0 && limited.missing==8,"stock control");
}
std::ofstream output(const std::string& dir,const char* file,const char* header) {
    std::ofstream out;
    out.exceptions(std::ios::badbit|std::ios::failbit);
    out.open(std::filesystem::path(dir)/file);
    out<<header<<'\n';
    return out;
}
void record(const Chamber& w,int seed,std::string_view arm,std::string_view branch,int selected,
            std::ostream& worlds,std::ostream& products) {
    worlds<<seed<<'\t'<<arm<<'\t'<<branch<<'\t'<<bits(w.chains[0].sequence,length)<<'\t'<<selected
          <<'\t'<<w.products()<<'\t'<<w.free[0]<<'\t'<<w.free[1]<<'\t'<<w.accepted<<'\t'<<w.rejected
          <<'\t'<<w.missing<<'\t';
    for (int j=0;j<4;++j) {
        if (j) worlds<<',';
        worlds<<bits(w.ends[j].sequence,w.ends[j].n)<<'/'<<w.ends[j].guide;
    }
    worlds<<'\n';
    for (int id=1;id<=w.products();++id) {
        const auto& c=w.chains[id];
        products<<seed<<'\t'<<arm<<'\t'<<branch<<'\t'<<id<<'\t'<<c.born<<'\t'<<bits(c.sequence,length)
                <<'\t'<<c.guide<<'\n';
    }
}
void study(const std::string& dir,bool reverse) {
    std::filesystem::create_directories(dir);
    auto worlds=output(dir,"worlds.tsv","seed\tarm\tbranch\tsupplied\tselected_first_id\tproducts\tfree0\tfree1\taccepted\trejected\tmissing\tpartials");
    auto products=output(dir,"products.tsv","seed\tarm\tbranch\tid\ttick\tsequence\tguide");
    for (int seed=first_seed;seed<=last_seed;++seed) {
        for (std::string_view arm:{"empty","pattern","reorder","blind"}) {
            int seq=arm=="empty"?-1:arm=="reorder"?reorder:founder;
            auto first=run(seed,1,seq,arm=="blind",reverse);
            int selected=first.products()?1+uniform(random_key(seed,0,0,4),first.products()):-1;
            record(first,seed,arm,"first",selected,worlds,products);
            int transferred=selected>=0?first.chains[selected].sequence:-1;
            for (bool blind:{false,true}) {
                auto second=run(seed,2,transferred,blind,reverse);
                record(second,seed,arm,blind?"transfer_blind":"transfer_active",selected,worlds,products);
            }
        }
    }
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls();return 0;}
        require(argc==2 || (argc==3 && std::string_view(argv[2])=="--reverse"),"usage: pool DIRECTORY [--reverse]");
        study(argv[1],argc==3);
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
