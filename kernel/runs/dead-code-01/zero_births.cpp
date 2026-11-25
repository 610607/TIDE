// Post hoc check for dead-code-01, written after the frozen analysis had run; not part of the frozen study.
// Replays one primary world without the observer and counts births whose product holds a zero byte.
// It mirrors study.cpp's byte suppliers and material-parent rule, so it also recounts the M2
// numerator (substitution-free births whose genotype differs from the material parent's) and
// reports how many of those births were all zeros.
// Usage: zero_births ARM retain|empty SEED TICKS; prints one TSV row. Build from the repository root with
//   g++ -O2 -std=c++20 -Ikernel/src -o kernel/build/dead-code/zero_births kernel/runs/dead-code-01/zero_births.cpp kernel/src/vm.cpp
// The founder, lattice and rules are those of study.cpp's initial(); births and the M2 numerator
// must equal the world's world.tsv.
#include "vm.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>
#include <vector>
using namespace tide;

namespace {
constexpr int length = 6;

std::uint64_t pack(const std::string& g) {
    std::uint64_t v = 0;
    for (unsigned char c : g) v = (v << 8) | c;
    return v | (static_cast<std::uint64_t>(g.size()) << 56);
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: zero_births ARM retain|empty SEED TICKS\n");
        return 2;
    }
    std::string arm = argv[1], rec = argv[2];
    Config c;
    c.width = 32; c.height = 32; c.boundary = Boundary::torus; c.placement = Placement::first_free;
    c.max_age = 80; c.mutation_ppm = 20000;
    c.access = {arm != "self", arm == "read_fetch"};
    c.reclamation = rec == "retain" ? Reclamation::retain : Reclamation::empty;
    c.seed = std::strtoull(argv[3], nullptr, 10);
    const bool empty = c.reclamation == Reclamation::empty;
    Tick horizon = std::strtoull(argv[4], nullptr, 10);
    World w(c);
    const int N = c.width * c.height;
    const int founder = w.index(8, 16);
    w.seed_site(founder, "R..CLD");

    // Material genealogy as in study.cpp: one node per individual, holding its genotype; each byte
    // of a bank records the node that supplied it (-1 for none); each actor records the supplier
    // and the input and output of every offset it wrote in the current attempt.
    std::vector<std::uint64_t> node_geno{pack(w.at(founder).bytes)};
    std::vector<int> mat_of(N, -1);
    std::vector<std::array<int, length>> owner(N);
    for (auto& o : owner) o.fill(-1);
    struct Rec { int sup = -1, in = 0, out = 0; };
    std::vector<std::array<Rec, length>> recs(N);
    mat_of[founder] = 0;
    owner[founder].fill(0);

    struct Birth { int actor, child, node; };
    struct Write { int site, offset, sup; };
    std::vector<Event> ev;
    std::vector<Birth> born;
    std::vector<Write> writes;
    std::vector<int> died, reserved, cleared;
    unsigned long long births = 0, with_zero = 0, all_zero = 0, novel = 0, all_zero_novel = 0;
    std::map<std::string, unsigned long long> zero_genotypes;
    while (w.tick() < horizon) {
        ev.clear(); born.clear(); writes.clear(); died.clear(); reserved.clear(); cleared.clear();
        w.step(&ev);
        for (const auto& e : ev) {
            switch (e.effect) {
            case Effect::copy: {
                const int sup = owner[e.read_site][e.read_offset];
                recs[e.actor][e.write_offset] = {sup, e.input, e.output};
                writes.push_back({e.target, e.write_offset, sup});
                break;
            }
            case Effect::birth: {
                const auto& r = recs[e.actor];
                const int me = mat_of[e.actor];
                std::array<int, length> votes{};
                int best = -1, best_votes = 0;
                for (int i = 0; i < length; ++i) {
                    if (r[i].sup < 0) continue;
                    int v = 0;
                    for (int j = 0; j < length; ++j) v += r[j].sup == r[i].sup;
                    votes[i] = v;
                    if (v > best_votes) { best_votes = v; best = r[i].sup; }
                }
                int mparent = best;
                if (best >= 0) {
                    bool exec_tied = false;
                    for (int i = 0; i < length; ++i) exec_tied |= r[i].sup == me && votes[i] == best_votes;
                    if (exec_tied) mparent = me;
                    else
                        for (int i = 0; i < length; ++i)
                            if (r[i].sup >= 0 && votes[i] == best_votes) { mparent = r[i].sup; break; }
                } else mparent = me;
                bool substituted = false;
                for (int i = 0; i < length; ++i) substituted |= r[i].in != r[i].out;
                const std::uint64_t geno = pack(e.product);
                const bool is_novel = !substituted && geno != node_geno[mparent]; // M2
                const bool zeros = e.product.find_first_not_of('\0') == std::string::npos;
                ++births;
                novel += is_novel;
                if (e.product.find('\0') != std::string::npos) {
                    ++with_zero;
                    all_zero += zeros;
                    all_zero_novel += zeros && is_novel;
                    std::string hex;
                    for (unsigned char b : e.product) { char buf[3]; std::snprintf(buf, 3, "%02x", b); hex += buf; }
                    ++zero_genotypes[hex];
                }
                born.push_back({e.actor, e.target, static_cast<int>(node_geno.size())});
                node_geno.push_back(geno);
                break;
            }
            case Effect::failed_division:
                if (e.target >= 0 && empty) cleared.push_back(e.target);
                break;
            case Effect::death:
                died.push_back(e.actor);
                if (empty) { cleared.push_back(e.actor); if (e.target >= 0) cleared.push_back(e.target); }
                break;
            case Effect::reserve: reserved.push_back(e.actor); break;
            default: break;
            }
        }
        // Same order as study.cpp: writes, then births, deaths, cleared banks and reservations.
        for (const auto& x : writes) owner[x.site][x.offset] = x.sup;
        for (const auto& b : born) {
            mat_of[b.child] = b.node;
            owner[b.child].fill(b.node);
            recs[b.actor] = {};
        }
        for (int a : died) { recs[a] = {}; mat_of[a] = -1; }
        for (int x : cleared) owner[x].fill(-1);
        // study.cpp also resets the suppliers of offsets a reservation adds to its bank. Every body
        // has six bytes, so a bank grows only from size zero, whose offsets already have none.
        for (int a : reserved) recs[a] = {};
    }
    std::vector<std::pair<unsigned long long, std::string>> top;
    for (auto& [g, n] : zero_genotypes) top.push_back({n, g});
    std::sort(top.rbegin(), top.rend());
    std::string listed;
    for (size_t i = 0; i < top.size() && i < 5; ++i)
        listed += (i ? ";" : "") + top[i].second + ":" + std::to_string(top[i].first);
    // arm, reclamation, seed, ticks, births, births with a zero byte, all-zero births, the M2
    // numerator, all-zero births counted in it, and the five commonest products holding a zero byte.
    std::printf("%s\t%s\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%s\n", arm.c_str(), rec.c_str(),
                (unsigned long long)c.seed, (unsigned long long)horizon, births, with_zero, all_zero, novel,
                all_zero_novel, listed.empty() ? "-" : listed.c_str());
}
