#include "common.hpp"
#include <iostream>

using namespace vacancy;

static void rejected(tide::World& w, int id) {
    auto before = w.state();
    try { w.release_idle_for_experiment(id); }
    catch (const std::logic_error&) {
        require(w.state() == before,"rejected intervention changed the state");
        return;
    }
    throw std::runtime_error("unexpected release");
}
static void contested_reservation() {
    tide::World start({});
    const int south=start.index(1,0), north=start.index(1,2), target=start.index(1,1);
    const int other=start.index(3,0), other_target=start.index(3,1);
    start.seed_site(south,"RCP",0,1); start.seed_site(north,"RCP",0,3);
    start.seed_site(other,"RCP",0,1); start.seed_site(start.index(3,2),"RCP",0,3);
    auto normal=start, granted=start, reversed=start, redundant=start;
    normal.step(); granted.step_with_preferred_claimant(nullptr,false,north);
    reversed.step_with_preferred_claimant(nullptr,true,north);
    redundant.step_with_preferred_claimant(nullptr,false,south);
    require(normal.at(target).owner==south && granted.at(target).owner==north &&
            granted.at(south).cpu.target==-1 && granted.at(south).cpu.pc==0 &&
            granted.at(north).cpu.pc==1, "wrong contested reservation");
    require(normal.at(other_target).owner==other && granted.at(other_target).owner==other,
            "unrelated contest changed");
    require(normal.state()==redundant.state() && granted.state()==reversed.state(),
            "neutral or reversed priority replay diverged");
}
int main() {
    tide::World w({});
    const int a = w.index(1,1), north = w.neighbor(a,0), b = w.neighbor(a,1);
    w.seed_site(a,"RC"); w.seed_site(b,"P");
    w.step();
    rejected(w,north); rejected(w,a); rejected(w,w.index(0,0)); rejected(w,-1);
    auto fork = w;
    fork.release_idle_for_experiment(b);
    require(fork.at(b).bytes == "P" && fork.at(b).kind == tide::Bank::free &&
            fork.at(north).owner == a && fork.tick() == w.tick() && w.at(b).kind == tide::Bank::occupied,
            "one-bank fork contract failed");
    tide::Config cfg; cfg.reclamation = tide::Reclamation::empty;
    tide::World empty(cfg); empty.seed_site(0,"P"); rejected(empty,0);
    contested_reservation();
    std::cout << "Release, contested reservation and traversal checks passed\n";
}
