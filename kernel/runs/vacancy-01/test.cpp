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
    std::cout << "One-bank release and failed transitions verified\n";
}
