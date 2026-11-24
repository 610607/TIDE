// Linked only into study forks. The census uses the reference VM directly.
#include "vm.hpp"
#include <stdexcept>

namespace tide {
void World::release_idle_for_experiment(int site) {
    auto& s = sites_.at(site);
    if (cfg_.reclamation != Reclamation::retain || s.kind != Bank::occupied || s.cpu.target != -1)
        throw std::invalid_argument("release requires one occupied, allocation-free bank under retain");
    s.kind = Bank::free;
    s.born = 0;
    s.cpu = Cpu{};
    // The occupied site's owner is already -1. Keep its bytes and permissions.
    check();
}
}
