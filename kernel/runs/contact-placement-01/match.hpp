#pragma once
#include "../spatial-transport-01/transport.hpp"
#include "../vacancy-01/common.hpp"

#include <map>
#include <tuple>
#include <vector>

namespace contact {
using namespace tide;
using vacancy::require;
constexpr int end_tick=2048, lifespan=81;
using Identity=std::pair<int,int>; // site and birth tick in the ordinary field
struct Focal {
    int site,born,maker_born;
    std::string hex;
    int first() const {return maker_born+lifespan+1;}
    int death() const {return born+lifespan;}
    int end() const {return std::min(end_tick,death()+lifespan);}
};
struct Frame {
    World world;
    std::vector<Identity> active;
    explicit Frame(const World& opening):world(opening) {}
};
struct Match {
    int tick=0, origin=-1, born=-1, near=-1, sham=-1, ordinary_s=0;
    bool mobile=false, destination=false, geometry=false;
    const char* status() const {
        if (tick) return "paired";
        if (geometry) return "no_matched_room";
        if (destination) return "no_matched_distance_kind";
        if (mobile) return "no_contact_destination";
        return "reader_pinned";
    }
};
inline std::pair<int,int> distance(int a,int b) {
    int x=std::abs(a%16-b%16), y=std::abs(a/16-b/16);
    return {std::min(x,16-x),std::min(y,4-y)};
}
inline bool adjacent(int a,int b) {
    auto [x,y]=distance(a,b);
    return x+y==1;
}
inline bool movable_destination(const Site& s) {
    return s.kind==Bank::free || (s.kind==Bank::occupied && s.cpu.target<0 && s.bytes.find('S')==std::string::npos);
}
inline int room_after(const World& w,const SpatialExperiment& space,int origin,int dest) {
    int free=0;
    for (int i:space.near[dest]) free+=(i==origin?w.at(dest).kind:w.at(i).kind)==Bank::free;
    return free;
}
inline Match choose(const std::map<int,Frame>& frames,const Focal& f,const SpatialExperiment& space) {
    std::map<Identity,std::vector<int>> active;
    for (int t=f.first();t<=f.death();++t) {
        const auto& frame=frames.at(t);
        require(frame.world.at(f.site).born==Tick(f.born) && frame.world.at(f.site).kind==Bank::occupied,
                "focal window mismatch");
        for (auto who:frame.active) {
            if (who.first==f.site) continue;
            require(!adjacent(who.first,f.site),"natural local S in distant-only case");
            active[who].push_back(t);
        }
    }
    require(!active.empty(),"missing archived active reader");
    Match result;
    for (int t=f.first();t<=f.death();++t) {
        const auto& w=frames.at(t).world;
        std::tuple<bool,Tick,int,int,int> best;
        for (const auto& [id,times]:active) {
            auto [src,born]=id;
            const auto& reader=w.at(src);
            if (reader.kind!=Bank::occupied || int(reader.born)!=born || reader.cpu.target>=0 || times.back()<t)
                continue;
            result.mobile=true;
            for (int a:space.near[f.site]) {
                if (!movable_destination(w.at(a))) continue;
                result.destination=true;
                auto displacement=distance(src,a);
                for (int b=0;b<w.size();++b) {
                    if (b==src || b==f.site || adjacent(b,f.site) || distance(src,b)!=displacement ||
                        !movable_destination(w.at(b)) || w.at(b).kind!=w.at(a).kind) continue;
                    result.geometry=true;
                    if (room_after(w,space,src,a)!=room_after(w,space,src,b)) continue;
                    Tick context=SpatialExperiment::draw(int(w.config().seed),t,f.site);
                    Tick packed=(Tick(f.born)<<18)|(Tick(src)<<12)|(Tick(a)<<6)|Tick(b);
                    auto rank=std::make_tuple(w.at(a).bytes!=w.at(b).bytes,SpatialExperiment::mix(context^packed),src,a,b);
                    if (result.tick && !(rank<best)) continue;
                    best=rank;
                    result.tick=t; result.origin=src; result.born=born; result.near=a; result.sham=b;
                    result.ordinary_s=*std::lower_bound(times.begin(),times.end(),t);
                }
            }
        }
        if (result.tick) return result;
    }
    return result;
}
}
