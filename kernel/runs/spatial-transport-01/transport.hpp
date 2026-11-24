#pragma once
#include "vm.hpp"

#include <array>
#include <stdexcept>
#include <utility>

namespace tide {
// Study-local access is granted by the generated header in the build directory.
struct SpatialExperiment {
    using Grid = std::array<std::array<int,4>,64>;
    using Pair = std::pair<int,int>;
    Grid near{};
    std::array<std::array<Pair,32>,4> matches{};

    explicit SpatialExperiment(const World& w) {
        if (w.config().width!=16 || w.config().height!=4 || w.config().boundary!=Boundary::torus ||
            w.config().access.fetch) throw std::logic_error("unsupported experimental field");
        std::array<int,4> used{};
        for (int i=0;i<64;++i) {
            for (int d=0;d<4;++d) near[i][d]=w.neighbor(i,d);
            int h=(i%16)%2, v=2+(i/16)%2;
            matches[h][used[h]++]={i,near[i][1]};
            matches[v][used[v]++]={i,near[i][0]};
        }
    }
    static Tick mix(Tick x) {
        x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
        x=(x^(x>>27))*0x94d049bb133111ebULL;
        return x^(x>>31);
    }
    static Tick draw(int seed,int tick,int key) {
        // A unique packed counter for each seed, tick and stream in this study.
        return mix((Tick(seed)<<32) | (Tick(tick)<<10) | static_cast<unsigned>(key));
    }
    static void orient(World& w,int site,int bearing) { w.sites_.at(site).cpu.bearing=bearing; }
    int direction(int origin,int dest) const {
        for (int d=0;d<4;++d) if (near[origin][d]==dest) return d;
        throw std::logic_error("nonlocal pointer");
    }
    void relocate(Site& s,int from,int to) const {
        if (s.kind!=Bank::occupied) return;
        if (s.cpu.bank!=from || s.cpu.target>=0) throw std::logic_error("nonlocal execution or reservation");
        s.cpu.bank=to;
        if (s.cpu.source==from) s.cpu.source=to;
        else if (s.cpu.source>=0) s.cpu.source=near[to][direction(from,s.cpu.source)];
    }
    bool exchange(World& w,int a,int b) const {
        auto& x=w.sites_[a];
        auto& y=w.sites_[b];
        if (x.kind==Bank::reserved || y.kind==Bank::reserved ||
            (x.kind==Bank::free && y.kind==Bank::free) || x.cpu.target>=0 || y.cpu.target>=0) return false;
        relocate(x,a,b);
        relocate(y,b,a);
        std::swap(x,y);
        return true;
    }
    int transport(World& w,std::array<int,64>& people,int threshold,bool reverse) const {
        if (!threshold) return 0;
        int seed=static_cast<int>(w.config().seed), t=static_cast<int>(w.tick());
        const auto& matching=matches[draw(seed,t,0)%4];
        int moves=0;
        for (int i=0;i<32;++i) {
            auto [a,b]=matching[reverse?31-i:i];
            if (static_cast<int>(draw(seed,t,1+a)%64)>=threshold) continue;
            if (exchange(w,a,b)) {
                moves+=(people[a]>=0)+(people[b]>=0);
                std::swap(people[a],people[b]);
            }
        }
        return moves;
    }
};
}
