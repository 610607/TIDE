#pragma once
#include "transport.hpp"

#include <bit>
#include <cstdint>

namespace tide {
struct ExchangeSchedule {
    int seed, offset;
    bool burst;
    int sweeps=0, active_ticks=0, offers=0, swaps=0;
    std::uint64_t digest=14695981039346656037ULL;

    ExchangeSchedule(int seed,bool burst):seed(seed),offset(SpatialExperiment::draw(seed,0,512)%32),burst(burst) {}
    int phase(int tick) const { return (tick-1-offset+32)%32; }
    int sweeps_due(int tick) const { return burst?(phase(tick)<8?4:0):1; }
    int advance(World& w,const SpatialExperiment& space,std::array<int,64>& ids,bool reverse) {
        int tick=static_cast<int>(w.tick()), count=sweeps_due(tick), moved=0;
        active_ticks+=count>0;
        for (int j=0;j<count;++j) {
            ++sweeps;
            auto axis=SpatialExperiment::draw(seed,sweeps,0)%4;
            const auto& edges=space.matches[axis];
            std::uint32_t mask=0;
            for (int i=0;i<32;++i) {
                int index=reverse?31-i:i;
                auto [a,b]=edges[index];
                if (SpatialExperiment::draw(seed,sweeps,1+a)%64>=16) continue;
                mask|=std::uint32_t{1}<<index;
                if (!space.exchange(w,a,b)) continue;
                ++swaps;
                moved+=(ids[a]>=0)+(ids[b]>=0);
                std::swap(ids[a],ids[b]);
            }
            offers+=std::popcount(mask);
            digest=(digest^((axis<<32)|mask))*1099511628211ULL;
        }
        if (tick%32==0 && sweeps!=tick) throw std::logic_error("unequal block budget");
        return moved;
    }
};
}
