#include "../vacancy-01/common.hpp"
#include <iostream>

int main() {
    std::cout << "seed\tbirths\tdeaths\tliving\tfinal80_births\tstatus\treaders\tstate_fnv64\n";
    for (int seed = 3137; seed <= 11328; ++seed) {
        auto w = vacancy::initial(seed);
        int births=0, deaths=0, recent=0, readers=0;
        std::vector<tide::Event> events;
        for (int t=1; t<=vacancy::field_end; ++t) {
            w.step(&events);
            for (const auto& e : events) {
                deaths += e.effect == tide::Effect::death;
                if (e.effect == tide::Effect::birth) {
                    ++births;
                    recent += t > vacancy::field_end-80;
                    readers += e.product == vacancy::reader;
                }
            }
        }
        w.check();
        int living=0;
        for(int i=0; i<w.size(); ++i) living += w.at(i).kind == tide::Bank::occupied;
        vacancy::require(living == 1+births-deaths, "unbalanced reference world");
        std::cout << seed << '\t' << births << '\t' << deaths << '\t' << living << '\t' << recent << '\t'
                  << (!living ? "extinct" : recent ? "reproducing" : "stagnant") << '\t' << readers
                  << '\t' << w.hash() << '\n';
    }
}
