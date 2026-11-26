// Lattice-size study (docs/research/lattice-size-rq.md): one world per call.
// Derived from the dead-code study's observer (kernel/runs/dead-code-01/study.cpp). Pass 1 runs the
// field with material and executor lineages, a neutral shadow, MODES timepoints for a list of
// filter lengths on one grid, Bedau activity samples, the mechanism ledger, a census and spatial
// statistics of the focus genotype at every grid level, and counts of the focus genotype's origins.
// An optional extended grid evaluates the primary filter on later levels. Pass 2 replays the field
// and forks first filtered carriers for permission and knockout assays: every genotype filtered at
// the primary filter, plus the focus genotype under any filter. The residue fork and the
// neutrality sample of the dead-code study are not used.
// The observer only reads events; the run's state hash must equal a bare run's.
#include "vm.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace {
using namespace tide;
using u64 = std::uint64_t;

void require(bool ok, const std::string& what) {
    if (!ok) throw std::logic_error(what);
}
constexpr std::string_view alphabet = "R.JTSH+>CLDP";
constexpr int length = 6, genotypes = 4826809; // 13^6: twelve instruction bytes and zero fill
int digit(unsigned char b) {
    if (b == 0) return 0;
    const auto p = alphabet.find(static_cast<char>(b));
    require(p != std::string_view::npos, "byte outside the genome alphabet");
    return static_cast<int>(p) + 1;
}
int encode(const std::string& g) {
    require(g.size() == length, "genome length");
    int code = 0;
    for (int i = length - 1; i >= 0; --i) code = code * 13 + digit(static_cast<unsigned char>(g[i]));
    return code;
}
std::string decode(int code) {
    std::string g(length, '\0');
    for (int i = 0; i < length; ++i, code /= 13) {
        const int d = code % 13;
        g[i] = d ? alphabet[d - 1] : '\0';
    }
    return g;
}
std::string hex(const std::string& bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (unsigned char c : bytes) { out += digits[c >> 4]; out += digits[c & 15]; }
    return out;
}
u64 mix(u64 x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Settings {
    std::string arm, reclamation = "retain", out, focus = "RCCCJD";
    int width = 32, height = 32, seed = 0;
    long horizon = 1L << 22;
    unsigned mutation = 20000;
    int t = 1024, step = 256, window_end = 16384;
    std::vector<int> sensitivity{256, 2048};
    int ext_step = 0, ext_end = 0; // extended grid for the primary filter; 0 disables it
    int sample = 4096;
    u64 shadow_perturb = 0;
    Access access() const {
        if (arm == "self") return {false, false};
        if (arm == "read") return {true, false};
        if (arm == "read_fetch") return {true, true};
        throw std::invalid_argument("unknown arm");
    }
    Reclamation policy() const {
        if (reclamation == "retain") return Reclamation::retain;
        if (reclamation == "empty") return Reclamation::empty;
        throw std::invalid_argument("unknown reclamation");
    }
};
World initial(const Settings& s) {
    Config c;
    c.width = s.width; c.height = s.height; c.boundary = Boundary::torus;
    c.placement = Placement::first_free; c.max_age = 80; c.mutation_ppm = s.mutation;
    c.access = s.access(); c.reclamation = s.policy(); c.seed = static_cast<Tick>(s.seed);
    World w(c);
    w.seed_site(w.index(s.width / 4, s.height / 2), "R..CLD");
    return w;
}

// A pruned genealogy. A node stays while alive, while it has kept children, or while held
// (material lineage: a bank still holds bytes whose provenance is this lifetime).
struct Phylo {
    struct Node {
        int parent = -1, kids = 0, hold = 0, depth = 0, born = 0, site = -1, births = 0;
        bool alive = false;
        std::uint32_t serial = 0, stamp = 0;
        long long geno = 0;
    };
    std::vector<Node> n;
    std::vector<int> spare, living, where;
    std::uint32_t serials = 0, stamps = 0;
    long long depth_sum = 0;
    int add(int parent, long long geno, int depth, int born, int site) {
        int i;
        if (!spare.empty()) { i = spare.back(); spare.pop_back(); }
        else { i = static_cast<int>(n.size()); n.emplace_back(); where.push_back(-1); }
        Node& x = n[i];
        x = Node{};
        x.parent = parent; x.geno = geno; x.depth = depth; x.born = born; x.site = site;
        x.alive = true; x.serial = ++serials;
        if (parent >= 0) { require(n[parent].serial != 0, "parent missing"); ++n[parent].kids; }
        where[i] = static_cast<int>(living.size());
        living.push_back(i);
        depth_sum += depth;
        return i;
    }
    void release(int i) {
        while (i >= 0 && !n[i].alive && n[i].kids == 0 && n[i].hold == 0) {
            const int p = n[i].parent;
            n[i] = Node{};
            spare.push_back(i);
            if (p >= 0) --n[p].kids;
            i = p;
        }
    }
    void kill(int i) {
        require(n[i].alive, "double death");
        n[i].alive = false;
        const int k = where[i], last = living.back();
        living[k] = last; where[last] = k; living.pop_back(); where[i] = -1;
        depth_sum -= n[i].depth;
        release(i);
    }
    void hold(int i) { ++n[i].hold; }
    void unhold(int i) { require(n[i].hold > 0, "hold underflow"); --n[i].hold; release(i); }
    double mean_depth() const {
        return living.empty() ? -1.0 : static_cast<double>(depth_sum) / static_cast<double>(living.size());
    }
    // Stamp every ancestor of the living population (including the living themselves).
    std::uint32_t stamp_ancestors() {
        const std::uint32_t s = ++stamps;
        for (int i : living)
            for (int j = i; j >= 0 && n[j].stamp != s; j = n[j].parent) n[j].stamp = s;
        return s;
    }
};

struct Entry { int idx; std::uint32_t serial; long long geno; int born, site; };
struct Snapshot { int level, tick; double g; std::vector<Entry> e; int open = 0; };
struct Target { int series; long long geno; int level, born, site, births; };

// MODES timepoints for one genealogy: snapshots at each step of mean generation, each looked
// ahead by every filter length in ts.
struct Series {
    std::string name;
    Phylo* p;
    std::vector<int> ts;
    int step, last_level, next_level = 0, primary_t;
    std::deque<Snapshot> snaps;
    int first_snap = 0;
    struct Wait { double target; int snap, t; };
    std::vector<std::deque<Wait>> queues;
    std::ostream *points, *filtered;
    bool labels = false;                    // shadow: components are labels, not genotypes
    int tag = -1;                           // assay series tag; -1 records no targets
    std::vector<Target>* targets = nullptr; // first filtered carriers at the primary t, and of the focus
    std::vector<char> targeted;
    long long focus = -1;                   // genotype assayed at its first carrier under any filter
    Series(std::string name, Phylo* p, std::vector<int> ts, int step, int last_level, int primary_t,
           std::ostream* points, std::ostream* filtered)
        : name(std::move(name)), p(p), ts(std::move(ts)), step(step), last_level(last_level),
          primary_t(primary_t), queues(this->ts.size()), points(points), filtered(filtered) {}
    Snapshot& snap(int k) { return snaps.at(k - first_snap); }
    void record(int tick, double g) {
        while (next_level <= last_level && g >= next_level) {
            Snapshot s{next_level, tick, g, {}, static_cast<int>(ts.size())};
            for (int i : p->living) {
                const auto& x = p->n[i];
                s.e.push_back({i, x.serial, x.geno, x.born, x.site});
            }
            const int k = first_snap + static_cast<int>(snaps.size());
            snaps.push_back(std::move(s));
            for (size_t j = 0; j < ts.size(); ++j) queues[j].push_back({g + ts[j], k, ts[j]});
            next_level += step;
        }
    }
    void evaluate(const Wait& w, int tick, bool extinct) {
        Snapshot& s = snap(w.snap);
        std::uint32_t stamp = extinct ? 0 : p->stamp_ancestors();
        std::map<long long, std::pair<int, size_t>> passing; // genotype -> (count, first carrier)
        int npass = 0;
        for (size_t k = 0; k < s.e.size(); ++k) {
            const auto& e = s.e[k];
            if (extinct || p->n[e.idx].stamp != stamp || p->n[e.idx].serial != e.serial) continue;
            ++npass;
            auto it = passing.find(e.geno);
            if (it == passing.end()) passing.emplace(e.geno, std::make_pair(1, k));
            else {
                ++it->second.first;
                const auto& old = s.e[it->second.second];
                if (e.born < old.born || (e.born == old.born && e.site < old.site)) it->second.second = k;
            }
        }
        *points << name << '\t' << w.t << '\t' << s.level << '\t' << s.tick << '\t' << s.g << '\t'
                << tick << '\t' << (extinct ? -1.0 : p->mean_depth()) << '\t' << s.e.size() << '\t'
                << npass << '\t' << passing.size() << '\n';
        for (const auto& [geno, v] : passing) {
            *filtered << name << '\t' << w.t << '\t' << s.level << '\t'
                      << (labels ? std::to_string(geno) : hex(decode(static_cast<int>(geno)))) << '\t' << v.first << '\n';
            if (targets && (w.t == primary_t || geno == focus) && !targeted[geno]) {
                const auto& e = s.e[v.second];
                targeted[geno] = 1;
                targets->push_back({tag, geno, s.level, e.born, e.site, p->n[e.idx].births});
            }
        }
        if (--s.open == 0)
            while (!snaps.empty() && snaps.front().open == 0) { snaps.pop_front(); ++first_snap; }
    }
    void advance(int tick) {
        const double g = p->mean_depth();
        record(tick, g);
        for (auto& q : queues)
            while (!q.empty() && g >= q.front().target) { evaluate(q.front(), tick, false); q.pop_front(); }
    }
    void extinct(int tick) {
        for (auto& q : queues) {
            while (!q.empty()) { evaluate(q.front(), tick, true); q.pop_front(); }
        }
    }
    int unreached() const {
        int n = 0;
        for (const auto& q : queues) n += static_cast<int>(q.size());
        return n;
    }
    void finish() {
        for (auto& q : queues)
            for (const auto& w : q)
                *points << name << '\t' << w.t << '\t' << snap(w.snap).level << '\t' << snap(w.snap).tick << '\t'
                        << snap(w.snap).g << "\t-1\t-1\t" << snap(w.snap).e.size() << "\t-1\t-1\n";
    }
};

// Bedau activity counters. Dense mode indexes run genotypes directly; a genotype can vanish and
// return with its counter intact. Sparse mode serves shadow labels, which never return once
// absent, so a vanished label's slot is recycled.
struct Activity {
    bool sparse = false;
    std::vector<int> count, start, where;
    std::vector<std::uint32_t> acc;
    std::vector<long long> present; // slots
    std::unordered_map<long long, int> slot_of;
    std::vector<int> spare;
    int slot(long long c, bool create) {
        if (!sparse) {
            if (c >= static_cast<long long>(count.size())) {
                require(create, "unknown component");
                const size_t m = std::max<size_t>(c + 1, count.size() * 2);
                count.resize(m, 0); start.resize(m, 0); where.resize(m, -1); acc.resize(m, 0);
            }
            return static_cast<int>(c);
        }
        if (auto it = slot_of.find(c); it != slot_of.end()) return it->second;
        require(create, "unknown shadow label");
        int k;
        if (!spare.empty()) { k = spare.back(); spare.pop_back(); }
        else { k = static_cast<int>(count.size()); count.push_back(0); start.push_back(0); where.push_back(-1); acc.push_back(0); }
        count[k] = 0; acc[k] = 0;
        slot_of.emplace(c, k);
        return k;
    }
    void born(long long c, int tick) {
        const int k = slot(c, true);
        if (count[k]++ == 0) { start[k] = tick; where[k] = static_cast<int>(present.size()); present.push_back(k); }
    }
    void died(long long c, int tick) {
        const int k = slot(c, false);
        require(count[k] > 0, "activity underflow");
        if (--count[k] == 0) {
            acc[k] += static_cast<std::uint32_t>(tick - start[k]);
            const int i = where[k];
            const long long last = present.back();
            present[i] = last; where[last] = i; present.pop_back(); where[k] = -1;
            if (sparse) { slot_of.erase(c); spare.push_back(k); }
        }
    }
    std::vector<std::uint32_t> sample(int tick) const {
        std::vector<std::uint32_t> a;
        a.reserve(present.size());
        for (long long k : present) a.push_back(acc[k] + static_cast<std::uint32_t>(tick - start[k] + 1));
        return a;
    }
};

struct Shadow {
    Phylo p;
    Activity act;
    long long labels = 0;
    u64 key, counter = 0;
    explicit Shadow(u64 key) : key(key) { act.sparse = true; }
    u64 draw() { return mix(key ^ mix(++counter)); }
};

// Activity bins: 64 per octave for the stored collapsed distributions, 8 per octave (fine / 8)
// for locating the crossing a*.
int bin_of(std::uint32_t a) { return static_cast<int>(std::floor(64.0 * std::log2(static_cast<double>(a)))); }
std::uint32_t bin_lo(int b, double per_octave) {
    return static_cast<std::uint32_t>(std::ceil(std::exp2(b / per_octave) - 1e-9));
}
int floor_div(int a, int b) { return a >= 0 ? a / b : -((-a + b - 1) / b); }

// Lifetime assays. Fork at the focal's birth tick, change only the focal's permission or its bytes
// (a knockout to '.'), and count the focal's births until its age death.
int focal_births(const World& base, int site, Access access, int knockout) {
    World f = base;
    const Tick born = f.at(site).born;
    require(f.at(site).kind == Bank::occupied && born == f.tick(), "fork is not at the focal's birth");
    f.set_access(site, access);
    if (knockout >= 0) { auto b = f.at(site).bytes; b[knockout] = '.'; f.replace_bytes(site, b); }
    const Tick death = born + f.config().max_age + 1;
    require(f.config().max_age > 0, "assay needs an age limit");
    int n = 0;
    while (true) {
        const int target = f.at(site).cpu.target;
        f.step();
        const auto& x = f.at(site);
        if (x.kind != Bank::occupied || x.born != born) {
            require(f.tick() == death, "focal lifetime");
            return n;
        }
        require(f.tick() < death, "focal outlived its age limit");
        if (target >= 0 && f.at(target).kind == Bank::occupied && f.at(target).born == f.tick()) ++n;
    }
}
struct Assay {
    int ord = 0, rd = 0, fd = 0, bd = 0, informative = 0;
    std::array<int, length> ko{};
    std::string cls;
};
// A denial the arm already imposes is a no-op and reuses the matching count.
Assay assay(const World& base, int site, bool knockouts) {
    const Access arm = base.config().access;
    Assay a;
    a.ord = focal_births(base, site, arm, -1);
    a.rd = arm.read ? focal_births(base, site, {false, arm.fetch}, -1) : a.ord;
    a.fd = arm.fetch ? focal_births(base, site, {arm.read, false}, -1) : a.ord;
    a.bd = (arm.read && arm.fetch) ? focal_births(base, site, {false, false}, -1) : (arm.read ? a.rd : a.fd);
    const std::string& g = base.at(site).bytes;
    for (int i = 0; i < static_cast<int>(g.size()) && knockouts; ++i) {
        a.ko[i] = g[i] == '.' ? a.ord : focal_births(base, site, arm, i);
        a.informative += a.ord > 0 && a.ko[i] < a.ord;
    }
    if (a.ord == 0) a.cls = "template_only";
    else if (a.rd > 0 && a.fd > 0 && a.bd > 0) a.cls = "independent";
    else if (a.rd == 0 && a.fd > 0 && a.bd == 0) a.cls = "read_requiring";
    else if (a.rd > 0 && a.fd == 0 && a.bd == 0) a.cls = "fetch_requiring";
    else if (a.rd == 0 && a.fd == 0 && a.bd == 0) a.cls = "both_requiring";
    else if (a.rd > 0 && a.fd > 0 && a.bd == 0) a.cls = "either_sufficient";
    else a.cls = "other";
    return a;
}

// An origin of the focus genotype is a birth of the focus whose material parent is not the focus.
bool origin(long long child, long long parent, long long focus) { return child == focus && parent != focus; }

// Spatial statistics of an indicator on a W x H torus with 4-neighbors (cell x + W * y):
// 4-connected clusters by union-find, ordered neighbor pairs, and the axis-averaged normalized
// two-point correlation rho(r) = (mean over both axes of x_i x_{i+r} - p^2) / (p - p^2) for
// r = 1..floor(min(W, H) / 2). xi is the smallest r with rho(r) < 1/e; it is censored at the
// largest r when no such r exists and undefined (-1) when p is 0 or 1.
struct Spatial {
    int carriers = 0, clusters = 0, largest = 0;
    long pairs = 0;
    std::vector<double> rho;
    int xi = -1;
    bool censored = false;
};
Spatial spatial(const std::vector<char>& x, int W, int H) {
    const int N = W * H;
    require(static_cast<int>(x.size()) == N, "spatial size");
    Spatial r;
    std::vector<int> up(N);
    for (int i = 0; i < N; ++i) up[i] = i;
    auto find = [&](int i) {
        while (up[i] != i) { up[i] = up[up[i]]; i = up[i]; }
        return i;
    };
    auto east = [&](int i, int d) { return (i % W + d) % W + W * (i / W); };
    auto south = [&](int i, int d) { return i % W + W * ((i / W + d) % H); };
    for (int i = 0; i < N; ++i) {
        if (!x[i]) continue;
        ++r.carriers;
        for (int j : {east(i, 1), south(i, 1), east(i, W - 1), south(i, H - 1)}) {
            if (!x[j]) continue;
            ++r.pairs;
            const int a = find(i), b = find(j);
            if (a != b) up[a] = b;
        }
    }
    std::vector<int> size(N, 0);
    for (int i = 0; i < N; ++i)
        if (x[i] && ++size[find(i)] == 1) ++r.clusters;
    for (int v : size) r.largest = std::max(r.largest, v);
    const double p = static_cast<double>(r.carriers) / N;
    const int rmax = std::min(W, H) / 2;
    for (int d = 1; d <= rmax; ++d) {
        long both = 0;
        for (int i = 0; i < N; ++i)
            if (x[i]) both += x[east(i, d)] + x[south(i, d)];
        const double c = static_cast<double>(both) / (2.0 * N) - p * p;
        r.rho.push_back(p > 0 && p < 1 ? c / (p - p * p) : std::numeric_limits<double>::quiet_NaN());
    }
    if (p > 0 && p < 1) {
        for (int d = 1; d <= rmax && r.xi < 0; ++d)
            if (r.rho[d - 1] < std::exp(-1.0)) r.xi = d;
        if (r.xi < 0) { r.xi = rmax; r.censored = true; }
    }
    return r;
}

struct Study {
    Settings s;
    std::vector<Target> targets;
    std::string hash_end;
    std::ofstream points, filtered, bedau, collapsed, assays, worldf, ledgerf, census, spatialf;

    explicit Study(Settings settings) : s(std::move(settings)) {}
    std::ofstream open(const char* name, const char* header) {
        std::ofstream f(s.out + "/" + name);
        require(f.good(), std::string("cannot write ") + name);
        f << header << '\n';
        f.precision(10);
        return f;
    }

    void run() {
        const auto t0 = std::chrono::steady_clock::now();
        points = open("timepoints.tsv", "series\tt\tlevel\tsnap_tick\tsnap_g\teval_tick\teval_g\tn_alive\tn_pass\tn_filtered");
        filtered = open("filtered.tsv", "series\tt\tlevel\tcomponent\tn_pass");
        bedau = open("bedau.tsv", "tick\tpopulation\tD\tA_cum\tmean_cum\tmedian_cum\tA_new\tshadow_D\tshadow_A_cum\tshadow_mean_cum\tshadow_median_cum\tshadow_A_new");
        collapsed = open("collapsed.tsv", "bin\tlo\trun_count\trun_weight_sum\tshadow_count\tshadow_weight_sum");
        assays = open("assays.tsv", "series\tgenotype\tlevel\tborn\tsite\trecorded_births\tordinary\treads_denied\tfetch_denied\tboth_denied\tko0\tko1\tko2\tko3\tko4\tko5\tinformative\tclass\tfocus");
        worldf = open("world.tsv", "arm\treclamation\tseed\twidth\theight\thorizon\tmutation_ppm\tstatus\textinction_tick\tbirths\tdeaths\tliving_end\tlast80_births\tvariation_births\tsubstitution_births\tsubstitution_free_variation_births\tsubstitution_free_novel_births\tdeaths_without_birth\tsubstitution_newborn_deaths\tsubstitution_newborn_deaths_with_birth\thash_end\tevent_digest\tmean_interval_material\tmean_interval_executor\tG_material\tG_executor\tG_shadow\tunreached_material\tunreached_executor\tunreached_shadow\ta_star\ta0\ta1\ta_max\tP4_run\tP4_shadow\tassayed\tfocus\tfocus_births\tfocus_origins\tfocus_substituted_origins\tfirst_origin_tick\tfirst_origin_site\tfirst_origin_executor_site\tfirst_origin_executor_genotype\tfirst_origin_parent_genotype\tfirst_origin_substituted\text_step\text_end\tunreached_material_ext\tpass1_seconds\tpass2_seconds");
        ledgerf = open("ledger.tsv", "focus\toutcome\tsubstitutions\tattempts\twritten\tvariation\tsubstitution_free_variation\tbytes_own\tbytes_living\tbytes_own_reservation_written\tbytes_own_reservation_unwritten\tbytes_other_reservation_written\tbytes_other_reservation_unwritten\tbytes_free\tfetch_living\tfetch_own_reservation_written\tfetch_own_reservation_unwritten\tfetch_other_reservation_written\tfetch_other_reservation_unwritten\tfetch_free\tresidue_bytes\tresidue_fetch\twith_residue_bytes\twith_residue_fetch\twith_fetch\twith_own_reservation_fetch");
        census = open("census.tsv", "level\ttick\talive\treserved\tfree_with_bytes\tfree_empty\tfocus\tfocus_bearing_living\tfocus_bearing_reserved\tfocus_bearing_free_with_bytes\tfocus_bearing_free_empty\tfocus_neighbors_free_with_bytes\tfocus_neighbors_focus");
        spatialf = open("spatial.tsv", "grid\tlevel\ttick\tbirths\tfocus_births\tfocus_origins\tcarriers\tclusters\tlargest\tpairs\txi\txi_censored\trho");

        World w = initial(s);
        const int N = w.size();
        const bool empty = w.config().reclamation == Reclamation::empty;
        const long long focus_code = encode(s.focus);
        Phylo mat, exe;
        Shadow sh(mix(mix(static_cast<u64>(s.seed)) ^ 0x534841444f57ULL ^ s.shadow_perturb));
        Activity act;
        std::vector<int> mat_of(N, -1), exe_of(N, -1), sh_of; // per site
        std::vector<std::string> bytes(N);
        std::vector<std::array<int, length>> owner(N);
        for (auto& o : owner) o.fill(-1);
        struct Rec { int sup = -1, roff = -1; unsigned char in = 0, out = 0; };
        std::vector<std::array<Rec, length>> recs(N);
        auto clear_recs = [&](int a) {
            for (auto& r : recs[a]) { if (r.sup >= 0) mat.unhold(r.sup); r = Rec{}; }
        };
        std::vector<char> victim;

        std::vector<int> primary_ts{s.t};
        for (int t : s.sensitivity) primary_ts.push_back(t);
        Series smat("material", &mat, primary_ts, s.step, s.window_end, s.t, &points, &filtered);
        Series sexe("executor", &exe, {s.t}, s.step, s.window_end, s.t, &points, &filtered);
        Series ssh("shadow", &sh.p, {s.t}, s.step, s.window_end, s.t, &points, &filtered);
        ssh.labels = true;
        smat.tag = 0; smat.targets = &targets; smat.targeted.assign(genotypes, 0); smat.focus = focus_code;
        sexe.tag = 1; sexe.targets = &targets; sexe.targeted.assign(genotypes, 0); sexe.focus = focus_code;
        // Extended grid: the primary filter only, on later levels; no assay targets.
        const bool extended = s.ext_step > 0;
        Series sext("material_ext", &mat, {s.t}, extended ? s.ext_step : 1, extended ? s.ext_end : -1, s.t, &points, &filtered);

        const int founder_site = w.index(s.width / 4, s.height / 2);
        {
            const auto& g = w.at(founder_site).bytes;
            const int code = encode(g);
            mat_of[founder_site] = mat.add(-1, code, 0, 0, founder_site);
            exe_of[founder_site] = exe.add(-1, code, 0, 0, founder_site);
            bytes[founder_site] = g;
            for (int i = 0; i < length; ++i) { owner[founder_site][i] = mat_of[founder_site]; mat.hold(mat_of[founder_site]); }
            act.born(code, 0);
            sh.p.add(-1, sh.labels, 0, 0, -1);
            sh.act.born(sh.labels++, 0);
        }
        // Mechanism ledger. A division attempt runs from a reservation to its birth, its release at
        // D, or the actor's death. Fetched instructions count from the CPU's previous D or birth.
        // Source categories, at the opening snapshot: 0 own body, 1 living neighbor, 2 and 3 the
        // actor's own reservation at a written or unwritten offset, 4 and 5 another reservation at a
        // written or unwritten offset, 6 a free bank. Residue is a supplied byte in categories 3, 5
        // or 6: bytes a lifetime once wrote that no living individual owns.
        std::vector<int> wcount(N, 0); // written offsets of each reservation (mirror of cpu.written)
        auto category = [&](int actor, int site, const Contact& c, int offset) {
            if (site == actor) return 0;
            if (c.kind == Bank::occupied) return 1;
            if (c.kind == Bank::free) return 6;
            const bool written = offset < wcount[site];
            return c.reservation_owner == actor ? (written ? 2 : 3) : (written ? 4 : 5);
        };
        auto residue = [](int cat) { return cat == 3 || cat == 5 || cat == 6; };
        struct Attempt { std::array<long, 7> bytes{}, fetch{}; long residue_bytes = 0, residue_fetch = 0; int subs = 0; };
        struct LedgerRow {
            long attempts = 0, written = 0, variation = 0, free_variation = 0, residue_bytes = 0, residue_fetch = 0,
                 with_residue_bytes = 0, with_residue_fetch = 0, with_fetch = 0, with_own_reservation_fetch = 0;
            std::array<long, 7> bytes{}, fetch{};
        };
        std::vector<Attempt> att(N);
        std::map<std::array<int, 3>, LedgerRow> ledger; // focus genotype, outcome, substituted copies
        auto close = [&](int actor, int outcome, bool variation, bool free_variation) {
            Attempt& a = att[actor];
            const int focus = mat.n[mat_of[actor]].geno == focus_code;
            LedgerRow& r = ledger[{focus, outcome, a.subs}];
            long written = 0, fetched = 0;
            for (int k = 0; k < 7; ++k) {
                r.bytes[k] += a.bytes[k]; r.fetch[k] += a.fetch[k];
                written += a.bytes[k]; fetched += a.fetch[k];
            }
            ++r.attempts; r.written += written; r.variation += variation; r.free_variation += free_variation;
            r.residue_bytes += a.residue_bytes; r.residue_fetch += a.residue_fetch;
            r.with_residue_bytes += a.residue_bytes > 0; r.with_residue_fetch += a.residue_fetch > 0;
            r.with_fetch += fetched > 0; r.with_own_reservation_fetch += (a.fetch[2] + a.fetch[3]) > 0;
            a = Attempt{};
        };
        // Lifetime tallies for rescue (M1) and realized load (M3), over every death in (0, H].
        std::vector<char> life_subst(N, 0);
        std::vector<int> life_births(N, 0);
        long substitution_births = 0, free_variations = 0, free_novel = 0, deaths_no_birth = 0, subst_deaths = 0, subst_deaths_birth = 0;
        u64 digest = 14695981039346656037ULL; // FNV-style fold of every event's fields, packed into words
        auto fold = [&](u64 v) { digest = (digest ^ v) * 1099511628211ULL; };
        auto field = [](int v, int shift) { return static_cast<u64>(static_cast<std::uint16_t>(v + 1)) << shift; };
        // Census at each material window level, for RCCCJD's local surroundings.
        auto take_census = [&](int level, long tick) {
            std::array<long, 4> kinds{}; // alive, reserved, free with bytes, free empty
            std::array<long, 7> focus{};
            for (int i = 0; i < N; ++i) {
                const auto& x = w.at(i);
                kinds[x.kind == Bank::occupied ? 0 : x.kind == Bank::reserved ? 1 : x.bytes.empty() ? 3 : 2]++;
                if (x.kind != Bank::occupied || x.bytes != s.focus) continue;
                ++focus[0];
                const int b = w.neighbor(i, x.cpu.bearing);
                const auto& y = w.at(b);
                focus[y.kind == Bank::occupied ? 1 : y.kind == Bank::reserved ? 2 : y.bytes.empty() ? 4 : 3]++;
                for (int d = 0; d < 4; ++d) {
                    const auto& z = w.at(w.neighbor(i, d));
                    focus[5] += z.kind == Bank::free && !z.bytes.empty();
                    focus[6] += z.kind == Bank::occupied && z.bytes == s.focus;
                }
            }
            require(!empty || kinds[2] == 0, "free bank holds bytes under empty reclamation");
            census << level << '\t' << tick;
            for (long k : kinds) census << '\t' << k;
            for (long k : focus) census << '\t' << k;
            census << '\n';
        };
        // Spatial statistics of living focus carriers, and cumulative birth and origin counts.
        long births = 0, focus_births = 0, origins = 0, subst_origins = 0;
        struct First { long tick = -1; int site = -1, exe_site = -1; long long exe_geno = -1, parent_geno = -1; bool subst = false; } first;
        std::vector<char> carrier(N, 0);
        auto take_spatial = [&](const char* grid, int level, long tick) {
            for (int i = 0; i < N; ++i) carrier[i] = w.at(i).kind == Bank::occupied && w.at(i).bytes == s.focus;
            const Spatial sp = spatial(carrier, s.width, s.height);
            spatialf << grid << '\t' << level << '\t' << tick << '\t' << births << '\t' << focus_births << '\t' << origins << '\t'
                     << sp.carriers << '\t' << sp.clusters << '\t' << sp.largest << '\t' << sp.pairs << '\t' << sp.xi << '\t'
                     << sp.censored << '\t';
            for (size_t k = 0; k < sp.rho.size(); ++k) {
                if (k) spatialf << ',';
                if (std::isnan(sp.rho[k])) spatialf << "nan";
                else { std::ostringstream v; v.precision(6); v << std::fixed << sp.rho[k]; spatialf << v.str(); }
            }
            spatialf << '\n';
        };
        take_census(0, 0);
        take_spatial("main", 0, 0);
        smat.advance(0); sexe.advance(0); ssh.advance(0);
        if (extended) { sext.advance(0); take_spatial("ext", 0, 0); }

        long deaths = 0, last80 = 0, variations = 0, extinction = -1;
        double interval_mat = 0, interval_exe = 0;
        std::vector<std::vector<std::uint32_t>> run_samples, shadow_samples;
        std::vector<int> sample_ticks, sample_pop;
        std::vector<Event> events;
        struct Birth { int actor, child, mparent; long long geno; bool variation, substituted; };
        struct Write { int site, offset, sup; unsigned char out; };
        std::vector<Birth> born;
        std::vector<Write> writes;
        std::vector<int> died, reserved, cleared;

        for (long tick = 1; tick <= s.horizon; ++tick) {
            w.step(&events);
            born.clear(); writes.clear(); died.clear(); reserved.clear(); cleared.clear();
            fold(static_cast<u64>(tick));
            for (const auto& e : events) {
                fold(field(e.actor, 0) | field(static_cast<int>(e.effect), 16) | field(e.op, 32) | field(e.fetch_site, 48));
                fold(field(e.pc, 0) | field(e.read_site, 16) | field(e.read_offset, 32) | field(e.target, 48));
                fold(field(e.write_offset, 0) | field(e.input, 16) | field(e.output, 32) | field(static_cast<int>(e.actor_born), 48));
                for (unsigned char c : e.product) fold(c);
                if (e.fetch_site >= 0 && e.fetch_site != e.actor && e.effect != Effect::bad_fetch) {
                    const int cat = category(e.actor, e.fetch_site, e.fetch_contact, e.pc);
                    ++att[e.actor].fetch[cat];
                    att[e.actor].residue_fetch += residue(cat) && owner[e.fetch_site][e.pc] >= 0;
                }
                switch (e.effect) {
                case Effect::copy: {
                    require(e.read_site >= 0 && e.read_offset < static_cast<int>(bytes[e.read_site].size()) &&
                            static_cast<unsigned char>(bytes[e.read_site][e.read_offset]) == e.input,
                            "mirror input mismatch");
                    const int sup = owner[e.read_site][e.read_offset];
                    require(e.write_offset >= 0 && e.write_offset < length, "write offset");
                    auto& rec = recs[e.actor][e.write_offset];
                    if (sup >= 0) mat.hold(sup); // a rec keeps its supplier until the birth resolves
                    if (rec.sup >= 0) mat.unhold(rec.sup);
                    rec = {sup, e.read_offset, static_cast<unsigned char>(e.input), static_cast<unsigned char>(e.output)};
                    writes.push_back({e.target, e.write_offset, sup, static_cast<unsigned char>(e.output)});
                    const int cat = category(e.actor, e.read_site, e.read_contact, e.read_offset);
                    ++att[e.actor].bytes[cat];
                    att[e.actor].residue_bytes += residue(cat) && sup >= 0;
                    att[e.actor].subs += e.input != e.output;
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
                    bool substituted = false, aligned = r[0].sup >= 0;
                    std::string input(length, '\0');
                    for (int i = 0; i < length; ++i) {
                        substituted |= r[i].in != r[i].out;
                        aligned &= r[i].sup == r[0].sup && r[i].roff == i;
                        input[i] = static_cast<char>(r[i].in);
                    }
                    aligned = aligned && input == decode(static_cast<int>(mat.n[r[0].sup].geno));
                    const long long geno = encode(e.product);
                    born.push_back({e.actor, e.target, mparent, geno, substituted || !aligned, substituted});
                    close(e.actor, 0, substituted || !aligned, !substituted && !aligned);
                    break;
                }
                case Effect::failed_division:
                    if (e.target >= 0) {
                        close(e.actor, 1, false, false);
                        if (empty) cleared.push_back(e.target);
                    } else att[e.actor] = Attempt{};
                    break;
                case Effect::death:
                    died.push_back(e.actor);
                    if (e.target >= 0) close(e.actor, 2, false, false);
                    att[e.actor] = Attempt{};
                    if (empty) { cleared.push_back(e.actor); if (e.target >= 0) cleared.push_back(e.target); }
                    break;
                case Effect::reserve: reserved.push_back(e.actor); break;
                default: break;
                }
            }
            // Births create genealogy nodes while every parent is still held.
            std::vector<std::pair<int, int>> newborn; // site -> (mat, exe) set after writes
            std::vector<int> sh_parents, sh_victims;
            const int sh_alive = static_cast<int>(sh.p.living.size());
            for (const auto& b : born) {
                require(bytes[b.child] == decode(static_cast<int>(b.geno)), "mirror product mismatch");
                const int ep = exe_of[b.actor];
                const int mi = mat.add(b.mparent, b.geno, mat.n[b.mparent].depth + 1, static_cast<int>(tick), b.child);
                const int ei = exe.add(ep, b.geno, exe.n[ep].depth + 1, static_cast<int>(tick), b.child);
                ++mat.n[mat_of[b.actor]].births;
                ++exe.n[ep].births;
                interval_mat += tick - mat.n[b.mparent].born;
                interval_exe += tick - exe.n[ep].born;
                newborn.push_back({mi, ei});
                if (b.geno == focus_code) {
                    ++focus_births;
                    if (origin(b.geno, mat.n[b.mparent].geno, focus_code)) {
                        ++origins; subst_origins += b.substituted;
                        if (first.tick < 0)
                            first = {tick, b.child, b.actor, exe.n[ep].geno, mat.n[b.mparent].geno, b.substituted};
                    }
                }
                ++births; last80 += tick > s.horizon - 80; variations += b.variation;
                substitution_births += b.substituted; free_variations += b.variation && !b.substituted;
                free_novel += !b.substituted && b.geno != mat.n[b.mparent].geno; // M2
                require(sh_alive > 0, "shadow parent pool empty");
                sh_parents.push_back(sh.p.living[sh.draw() % static_cast<u64>(sh_alive)]);
            }
            if (victim.size() < sh.p.n.size()) victim.resize(sh.p.n.size(), 0);
            for (size_t k = 0; k < died.size(); ++k) {
                require(sh_alive > static_cast<int>(k), "shadow victim pool empty");
                int v;
                do v = sh.p.living[sh.draw() % static_cast<u64>(sh_alive)];
                while (victim[v]);
                victim[v] = 1;
                sh_victims.push_back(v);
            }
            for (int v : sh_victims) victim[v] = 0;
            for (const auto& x : writes) {
                require(x.site >= 0 && x.offset < static_cast<int>(bytes[x.site].size()), "write outside bank");
                bytes[x.site][x.offset] = static_cast<char>(x.out);
                wcount[x.site] = x.offset + 1;
                int& o = owner[x.site][x.offset];
                if (x.sup >= 0) mat.hold(x.sup);
                if (o >= 0) mat.unhold(o);
                o = x.sup;
            }
            for (size_t k = 0; k < born.size(); ++k) {
                const auto& b = born[k];
                const int c = b.child;
                mat_of[c] = newborn[k].first; exe_of[c] = newborn[k].second;
                for (int i = 0; i < length; ++i) {
                    mat.hold(mat_of[c]);
                    if (owner[c][i] >= 0) mat.unhold(owner[c][i]);
                    owner[c][i] = mat_of[c];
                }
                clear_recs(b.actor);
                ++life_births[b.actor];
                life_subst[c] = b.substituted; life_births[c] = 0;
                act.born(b.geno, static_cast<int>(tick));
                const int sp = sh_parents[k];
                const long long label = b.variation ? sh.labels++ : sh.p.n[sp].geno;
                sh.p.add(sp, label, sh.p.n[sp].depth + 1, static_cast<int>(tick), -1);
                sh.act.born(label, static_cast<int>(tick));
            }
            for (int a : died) {
                deaths_no_birth += life_births[a] == 0;
                subst_deaths += life_subst[a];
                subst_deaths_birth += life_subst[a] && life_births[a] > 0;
                life_subst[a] = 0; life_births[a] = 0;
                act.died(mat.n[mat_of[a]].geno, static_cast<int>(tick));
                clear_recs(a);
                mat.kill(mat_of[a]); exe.kill(exe_of[a]);
                mat_of[a] = exe_of[a] = -1;
                ++deaths;
            }
            for (int v : sh_victims) {
                sh.act.died(sh.p.n[v].geno, static_cast<int>(tick));
                sh.p.kill(v);
            }
            for (int x : cleared) { // empty reclamation: released banks lose their bytes
                for (size_t i = 0; i < bytes[x].size(); ++i)
                    if (owner[x][i] >= 0) { mat.unhold(owner[x][i]); owner[x][i] = -1; }
                bytes[x].clear();
            }
            for (int a : reserved) {
                const int dest = w.at(a).cpu.target;
                require(dest >= 0 && w.at(dest).kind == Bank::reserved && w.at(dest).owner == a, "reservation");
                const size_t len = bytes[a].size();
                for (size_t i = len; i < bytes[dest].size(); ++i)
                    if (owner[dest][i] >= 0) { mat.unhold(owner[dest][i]); owner[dest][i] = -1; }
                for (size_t i = bytes[dest].size(); i < len; ++i) owner[dest][i] = -1;
                bytes[dest].resize(len, '\0');
                wcount[dest] = 0;
                clear_recs(a);
            }
            require(static_cast<int>(mat.living.size()) == static_cast<int>(sh.p.living.size()), "shadow size");
            if (mat.living.empty()) {
                if (extinction < 0) {
                    extinction = tick;
                    smat.extinct(static_cast<int>(tick)); sexe.extinct(static_cast<int>(tick)); ssh.extinct(static_cast<int>(tick));
                    if (extended) sext.extinct(static_cast<int>(tick));
                }
            } else {
                const int before = smat.next_level;
                smat.advance(static_cast<int>(tick)); sexe.advance(static_cast<int>(tick)); ssh.advance(static_cast<int>(tick));
                for (int L = before; L < smat.next_level; L += s.step) { take_census(L, tick); take_spatial("main", L, tick); }
                if (extended) {
                    const int ebefore = sext.next_level;
                    sext.advance(static_cast<int>(tick));
                    for (int L = ebefore; L < sext.next_level; L += s.ext_step) take_spatial("ext", L, tick);
                }
            }
            if (tick % s.sample == 0) {
                run_samples.push_back(act.sample(static_cast<int>(tick)));
                shadow_samples.push_back(sh.act.sample(static_cast<int>(tick)));
                sample_ticks.push_back(static_cast<int>(tick));
                sample_pop.push_back(static_cast<int>(mat.living.size()));
                w.check();
                for (int i = 0; i < N; ++i) {
                    const auto& site = w.at(i);
                    require(site.bytes == bytes[i], "byte mirror diverged");
                    require((site.kind == Bank::occupied) == (mat_of[i] >= 0), "occupancy mirror diverged");
                    if (mat_of[i] >= 0) require(static_cast<long>(site.born) == mat.n[mat_of[i]].born &&
                                                encode(site.bytes) == mat.n[mat_of[i]].geno, "lifetime mirror diverged");
                    if (site.kind == Bank::reserved) require(wcount[i] == w.at(site.owner).cpu.written, "write mirror diverged");
                }
            }
        }
        hash_end = w.hash();
        smat.finish(); sexe.finish(); ssh.finish();
        if (extended) sext.finish();
        const double pass1 = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

        // Bedau thresholds from the time-collapsed run and shadow distributions (logarithmic bins).
        std::map<int, std::array<double, 4>> bins; // fine bin: run count, run weight sum, shadow count, shadow weight sum
        double tot_run = 0, tot_sh = 0;
        std::uint32_t amax = 0;
        const double S = static_cast<double>(run_samples.size());
        for (size_t k = 0; k < run_samples.size(); ++k) {
            const double Dr = static_cast<double>(run_samples[k].size()), Ds = static_cast<double>(shadow_samples[k].size());
            for (auto a : run_samples[k]) { auto& b = bins[bin_of(a)]; b[0] += 1; b[1] += a / (Dr * S); tot_run += 1; amax = std::max(amax, a); }
            for (auto a : shadow_samples[k]) { auto& b = bins[bin_of(a)]; b[2] += 1; b[3] += a / (Ds * S); tot_sh += 1; amax = std::max(amax, a); }
        }
        for (const auto& [b, v] : bins)
            collapsed << b << '\t' << bin_lo(b, 64) << '\t' << v[0] << '\t' << v[1] << '\t' << v[2] << '\t' << v[3] << '\n';
        std::map<int, std::array<double, 2>> coarse;
        for (const auto& [b, v] : bins) { auto& c = coarse[floor_div(b, 8)]; c[0] += v[0]; c[1] += v[2]; }
        double astar = std::numeric_limits<double>::quiet_NaN();
        if (tot_run > 0 && tot_sh > 0) {
            int sign0 = 0;
            for (const auto& [b, v] : coarse) {
                const double d = v[0] / tot_run - v[1] / tot_sh;
                const int sg = (d > 0) - (d < 0);
                if (!sg) continue;
                if (!sign0) sign0 = sg;
                else if (sg != sign0) { astar = bin_lo(b, 8); break; }
            }
        }
        const double a0 = astar - 0.05 * (amax - astar), a1 = astar + 0.05 * (amax - astar);
        auto anew = [&](const std::vector<std::uint32_t>& v) {
            if (v.empty() || std::isnan(astar)) return v.empty() ? 0.0 : std::numeric_limits<double>::quiet_NaN();
            double sum = 0;
            for (auto a : v) if (a >= a0 && a <= a1) sum += a;
            return sum / static_cast<double>(v.size());
        };
        auto stats = [](std::vector<std::uint32_t> v, double& acum, double& mean, double& median) {
            acum = 0;
            for (auto a : v) acum += a;
            mean = v.empty() ? 0 : acum / v.size();
            if (v.empty()) { median = 0; return; }
            std::sort(v.begin(), v.end());
            median = v.size() % 2 ? v[v.size() / 2] : 0.5 * (static_cast<double>(v[v.size() / 2 - 1]) + v[v.size() / 2]);
        };
        double p4r = 0, p4s = 0;
        for (size_t k = 0; k < run_samples.size(); ++k) {
            double ar, mr, medr, as, ms, meds;
            stats(run_samples[k], ar, mr, medr);
            stats(shadow_samples[k], as, ms, meds);
            const double nr = anew(run_samples[k]), ns = anew(shadow_samples[k]);
            p4r += nr / S; p4s += ns / S;
            bedau << sample_ticks[k] << '\t' << sample_pop[k] << '\t' << run_samples[k].size() << '\t' << ar << '\t' << mr
                  << '\t' << medr << '\t' << nr << '\t' << shadow_samples[k].size() << '\t' << as << '\t' << ms << '\t'
                  << meds << '\t' << ns << '\n';
        }

        // Pass 2: replay and fork first filtered carriers.
        const auto t1 = std::chrono::steady_clock::now();
        std::sort(targets.begin(), targets.end(), [](const Target& a, const Target& b) {
            return a.born != b.born ? a.born < b.born : (a.site != b.site ? a.site < b.site : a.series < b.series);
        });
        World r = initial(s);
        Assay a;
        long last_born = -1;
        int last_site = -1;
        for (const auto& tg : targets) {
            while (static_cast<long>(r.tick()) < tg.born) r.step();
            const auto& site = r.at(tg.site);
            require(site.kind == Bank::occupied && static_cast<long>(site.born) == tg.born &&
                    site.bytes == decode(static_cast<int>(tg.geno)), "fork does not match carrier");
            if (tg.born != last_born || tg.site != last_site) a = assay(r, tg.site, true); // same carrier in both series
            last_born = tg.born; last_site = tg.site;
            require(a.ord == tg.births, "ordinary fork births differ from the field");
            const std::string g = decode(static_cast<int>(tg.geno));
            assays << (tg.series ? "executor" : "material") << '\t' << hex(g) << '\t' << tg.level << '\t' << tg.born << '\t' << tg.site << '\t' << tg.births << '\t' << a.ord
                   << '\t' << a.rd << '\t' << a.fd << '\t' << a.bd;
            for (int v : a.ko) assays << '\t' << v;
            assays << '\t' << a.informative << '\t' << a.cls << '\t' << (tg.geno == focus_code) << '\n';
        }
        for (const auto& [key, v] : ledger) {
            require(!empty || (v.bytes[6] == 0 && v.fetch[6] == 0 && v.residue_bytes == 0 && v.residue_fetch == 0),
                    "residue used under empty reclamation");
            ledgerf << key[0] << '\t' << (key[1] == 0 ? "birth" : key[1] == 1 ? "failed_division" : "death") << '\t'
                    << key[2] << '\t' << v.attempts << '\t' << v.written << '\t' << v.variation << '\t' << v.free_variation;
            for (int k = 0; k < 7; ++k) ledgerf << '\t' << v.bytes[k];
            for (int k = 1; k < 7; ++k) ledgerf << '\t' << v.fetch[k];
            ledgerf << '\t' << v.residue_bytes << '\t' << v.residue_fetch << '\t' << v.with_residue_bytes << '\t'
                    << v.with_residue_fetch << '\t' << v.with_fetch << '\t' << v.with_own_reservation_fetch << '\n';
        }
        const double pass2 = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();

        const long living = static_cast<long>(mat.living.size());
        require(1 + births - deaths == living, "population balance");
        const char* status = extinction >= 0 ? "extinct" : (last80 ? "reproducing" : "stagnant");
        std::ostringstream dg;
        dg << std::hex << digest;
        worldf << s.arm << '\t' << s.reclamation << '\t' << s.seed << '\t' << s.width << '\t' << s.height << '\t' << s.horizon << '\t'
               << s.mutation << '\t' << status << '\t' << extinction << '\t' << births << '\t' << deaths << '\t' << living << '\t'
               << last80 << '\t' << variations << '\t' << substitution_births << '\t' << free_variations << '\t' << free_novel << '\t'
               << deaths_no_birth << '\t' << subst_deaths << '\t' << subst_deaths_birth << '\t' << hash_end << '\t' << dg.str()
               << '\t' << (births ? interval_mat / births : 0) << '\t'
               << (births ? interval_exe / births : 0) << '\t' << mat.mean_depth() << '\t' << exe.mean_depth() << '\t'
               << sh.p.mean_depth() << '\t' << smat.unreached() << '\t' << sexe.unreached() << '\t' << ssh.unreached() << '\t'
               << astar << '\t' << a0 << '\t' << a1 << '\t' << amax << '\t' << p4r << '\t' << p4s << '\t' << targets.size()
               << '\t' << s.focus << '\t' << focus_births << '\t' << origins << '\t' << subst_origins << '\t' << first.tick << '\t'
               << first.site << '\t' << first.exe_site << '\t' << (first.tick < 0 ? "" : hex(decode(static_cast<int>(first.exe_geno))))
               << '\t' << (first.tick < 0 ? "" : hex(decode(static_cast<int>(first.parent_geno)))) << '\t' << first.subst << '\t'
               << s.ext_step << '\t' << s.ext_end << '\t' << (extended ? sext.unreached() : 0) << '\t' << pass1 << '\t' << pass2 << '\n';
        for (auto* f : {&points, &filtered, &bedau, &collapsed, &assays, &worldf, &ledgerf, &census, &spatialf}) {
            f->flush();
            require(f->good(), "output write failed");
        }
    }
};

// Bare run: same world without events or observer.
std::string bare_hash(const Settings& s) {
    World w = initial(s);
    for (long t = 0; t < s.horizon; ++t) w.step();
    return w.hash();
}

// Controls, printed as tab-separated lines for run.py to compare with expected values.
// Classifier: the stage-1 fixed programs in their fixture arenas from kernel/tests/vm_tests.cpp
// (default 5 x 5 bounded world, directed placement, no substitution, focal at bearing E of its
// donor), with the age limit set to 80 so that the assay ends.
// Spatial: hand-built 8 x 8 tori with known clusters and correlations.
// Origin: the origin rule on genotype pairs.
void controls() {
    struct Case { const char* name; const char* focal; const char* donor; int donor_pc; Access access; int x, y; const char* expected; };
    for (const auto& c : {Case{"R..CLD", "R..CLD", nullptr, 0, {false, false}, 1, 1, "independent"},
                          Case{"RSCLD", "RSCLD", "RSCLDP", 5, {true, false}, 1, 1, "read_requiring"},
                          Case{"RJD", "RJD", "CCCTP", 4, {false, true}, 0, 0, "fetch_requiring"}}) {
        Config cfg;
        cfg.access = c.access;
        cfg.max_age = 80;
        World w(cfg);
        const int a = w.index(c.x, c.y);
        w.seed_site(a, c.focal);
        if (c.donor) w.seed_site(w.index(c.x + 1, c.y), c.donor, c.donor_pc);
        const Assay r = assay(w, a, true);
        std::cout << "classifier\t" << c.name << '\t' << r.ord << '\t' << r.rd << '\t' << r.fd << '\t' << r.bd << '\t'
                  << r.informative << '\t' << r.cls << '\n';
        require(r.cls == c.expected, std::string("classifier control failed for ") + c.name);
    }
    constexpr int W = 8, H = 8;
    auto grid = [&](auto on) {
        std::vector<char> x(W * H, 0);
        for (int y = 0; y < H; ++y)
            for (int i = 0; i < W; ++i) x[i + W * y] = on(i, y) ? 1 : 0;
        return x;
    };
    struct Fixture { const char* name; std::vector<char> x; };
    const std::vector<Fixture> fixtures{
        {"empty", grid([](int, int) { return false; })},
        {"wrap_pair_and_single", grid([](int i, int y) { return (y == 3 && (i == 0 || i == 7)) || (i == 4 && y == 0); })},
        {"row", grid([](int, int y) { return y == 0; })},
        {"checkerboard", grid([](int i, int y) { return (i + y) % 2 == 0; })},
        {"stripes2", grid([](int i, int) { return i % 4 < 2; })},
    };
    for (const auto& f : fixtures) {
        const Spatial sp = spatial(f.x, W, H);
        std::cout << "spatial\t" << f.name << '\t' << sp.carriers << '\t' << sp.clusters << '\t' << sp.largest << '\t'
                  << sp.pairs << '\t' << sp.xi << '\t' << sp.censored << '\t';
        for (size_t k = 0; k < sp.rho.size(); ++k) {
            std::ostringstream v; v.precision(4); v << std::fixed << sp.rho[k];
            std::cout << (k ? "," : "") << v.str();
        }
        std::cout << '\n';
    }
    const long long f = encode("RCCCJD"), a = encode("R..CLD");
    std::cout << "origin\tfrom_other\t" << origin(f, a, f) << "\norigin\tfrom_focus\t" << origin(f, f, f)
              << "\norigin\tother_child\t" << origin(a, f, f) << '\n';
}

// Replay the bare field to the recorded first origin and report the executor's bytes and whether
// the event at that tick is a birth of the focus genotype at the recorded site by that executor.
void check_origin(const Settings& s, long tick, int site, int executor) {
    World w = initial(s);
    while (static_cast<long>(w.tick()) < tick - 1) w.step();
    const std::string exe_bytes = w.at(executor).bytes;
    const bool exe_alive = w.at(executor).kind == Bank::occupied;
    std::vector<Event> events;
    w.step(&events);
    bool birth = false;
    for (const auto& e : events)
        birth |= e.effect == Effect::birth && e.actor == executor && e.target == site && e.product == s.focus;
    const auto& c = w.at(site);
    std::cout << hex(exe_bytes) << '\t' << exe_alive << '\t' << birth << '\t'
              << (c.kind == Bank::occupied && static_cast<long>(c.born) == tick && c.bytes == s.focus) << '\n';
}
}

int main(int argc, char** argv) {
    try {
        std::vector<std::string> args(argv + 1, argv + argc);
        if (args.size() == 1 && args[0] == "--controls") { controls(); return 0; }
        Settings s;
        bool bare = false;
        long origin_tick = -1;
        int origin_site = -1, origin_executor = -1;
        for (size_t i = 0; i < args.size(); ++i) {
            auto next = [&]() -> const std::string& {
                if (i + 1 >= args.size()) throw std::invalid_argument("missing value for " + args[i]);
                return args[++i];
            };
            const auto& a = args[i];
            if (a == "--arm") s.arm = next();
            else if (a == "--reclamation") s.reclamation = next();
            else if (a == "--seed") s.seed = std::stoi(next());
            else if (a == "--size") { s.width = std::stoi(next()); s.height = std::stoi(next()); }
            else if (a == "--horizon") s.horizon = std::stol(next());
            else if (a == "--mutation") s.mutation = static_cast<unsigned>(std::stoul(next()));
            else if (a == "--filter") { s.t = std::stoi(next()); s.step = std::stoi(next()); s.window_end = std::stoi(next()); }
            else if (a == "--sensitivity") {
                s.sensitivity.clear();
                std::stringstream ss(next());
                for (std::string x; std::getline(ss, x, ',');) if (!x.empty()) s.sensitivity.push_back(std::stoi(x));
            }
            else if (a == "--shadow-perturb") s.shadow_perturb = std::stoull(next());
            else if (a == "--extend") { s.ext_step = std::stoi(next()); s.ext_end = std::stoi(next()); }
            else if (a == "--focus") s.focus = next();
            else if (a == "--check-origin") {
                origin_tick = std::stol(next()); origin_site = std::stoi(next()); origin_executor = std::stoi(next());
            }
            else if (a == "--out") s.out = next();
            else if (a == "--bare") bare = true;
            else throw std::invalid_argument("unknown argument " + a);
        }
        s.access(); s.policy();
        encode(s.focus);
        require(s.ext_step >= 0 && (s.ext_step == 0 || s.ext_end >= s.ext_step), "extended grid");
        if (bare) { std::cout << bare_hash(s) << '\n'; return 0; }
        if (origin_tick > 0) { check_origin(s, origin_tick, origin_site, origin_executor); return 0; }
        require(!s.out.empty(), "--out required");
        Study study(s);
        study.run();
        std::cout << study.hash_end << '\n';
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\n';
        return 1;
    }
}
