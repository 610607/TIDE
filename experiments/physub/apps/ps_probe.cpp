// Birth probe: classifies every birth of a run seeded with one reference program (polite by
// default) by parent integrity, copy differences, child lifespan and child fertility.
// Observation only.
// Usage: ps_probe ticks=N seed=S p_mut=X p_hydro=Y rival=0|1 [mass0=M] [census=0|1]
//        [hydro_whole=0|1|live|dead] [p_rot=P] [physics=0|1]
//        [decay_table=T decay_ratio=R] [classes=T1,T2,...] [anc=polite|copier]
//        [fidelity=W] [fate=1] [trace=1] [inert_operand=zero|fail] [census_topup=1|0]

#include "ps_census.hpp"
#include "ps_core.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>

using namespace ps;
using census::classify;
using census::kCopy;
using census::kKinds;
using census::kReignite;
using census::kSelfIgnite;
using census::TrialResult;

namespace {

// Reference program (anc=): the seeded ancestor, the text that "intact" and distances refer
// to, and the source of the volatile offsets (see ps_census.hpp).
const census::Reference* g_ref = census::reference_named("polite");

const std::vector<uint8_t>& ref_program() { return *g_ref->program; }

bool is_volatile(int k) { return g_ref->is_volatile(k); }

int text_distance(const uint8_t* bytes, const std::vector<uint8_t>& ref, int len) {
  int d = 0;
  for (int k = 0; k < len; ++k) {
    const uint8_t r = k < static_cast<int>(ref.size()) ? ref[k] : INERT;
    d += !is_volatile(k) && bytes[k] != r;
  }
  return d;
}

// Program-region match: the ancestor's own length only, so leftover bytes in the tail of a
// recycled site do not count as alterations.
bool prefix_intact(const uint8_t* bytes) {
  const auto& ref = ref_program();
  for (int k = 0; k < static_cast<int>(ref.size()); ++k) {
    if (!is_volatile(k) && bytes[k] != ref[k]) return false;
  }
  return true;
}

// Sources of child-parent differences in copies made by prefix-intact parents.
// F: last written by another site; D: written by the parent, now inert (decayed);
// M: written by the parent with another value (mutation, or the parent changed since);
// R: not written since the child's previous ignition (residue or failed write).
enum Src { kF = 0, kD = 1, kM = 2, kR = 3, kSrcs = 4 };
constexpr const char* kSrcName[kSrcs] = {"foreign", "decay", "mut", "residue"};

struct ErrTally {
  uint64_t births = 0;
  uint64_t n[kSrcs] = {};
  uint64_t residue_parent_inert = 0;  // residue where the parent byte is inert
  std::map<int, uint64_t> at[kSrcs];
};

void tally_errors(const World& w, const World::Birth& b, int len, ErrTally& t) {
  t.births += 1;
  const uint8_t* c = w.bytes_at(b.child);
  const uint8_t* p = w.bytes_at(b.parent);
  for (int k = 0; k < len; ++k) {
    if (is_volatile(k) || c[k] == p[k]) continue;
    const uint64_t bit = uint64_t{1} << k;
    Src s = kR;
    if (b.by_other & bit) s = kF;
    else if (b.by_parent & bit) s = (c[k] == INERT && p[k] != INERT) ? kD : kM;
    t.n[s] += 1;
    t.at[s][k] += 1;
    if (s == kR && p[k] == INERT) t.residue_parent_inert += 1;
  }
}

void print_errors(const ErrTally& t) {
  const double b = t.births ? static_cast<double>(t.births) : 1.0;
  std::cout << "intact-parent copy diffs per birth (n=" << t.births << "):";
  for (int s = 0; s < kSrcs; ++s) std::cout << ' ' << kSrcName[s] << '=' << t.n[s] / b;
  std::cout << " (residue where parent inert: " << t.residue_parent_inert / b << ")\n";
  for (int s = 0; s < kSrcs; ++s) {
    std::multimap<uint64_t, int, std::greater<>> top;
    for (auto [k, n] : t.at[s]) top.insert({n, k});
    std::cout << "  " << kSrcName[s] << " top offsets:";
    int shown = 0;
    for (auto [n, k] : top) {
      if (shown++ == 10) break;
      std::cout << ' ' << k << ':' << n;
    }
    std::cout << '\n';
  }
}

struct Record {
  uint64_t born = 0;
  uint64_t died = 0;
  int offspring = 0;
  bool parent_intact = false;
  int child_text = 0;  // child text distance to the ancestor at birth
  int copy_diff = 0;   // child vs parent, volatile offsets excluded
  int kind = 0;        // see Kind
};

constexpr const char* kKindName[kKinds] = {"self", "copy", "reignite"};

struct Window {
  uint64_t births = 0, exact = 0, intact = 0, copies = 0, reignites = 0, intact_copies = 0;
  uint64_t pfx_copies = 0;
};

struct Group {
  uint64_t n = 0, lifespan = 0, fertile = 0, offspring = 0, intact_child = 0, copy_diff = 0;
};

// Program text of a site with the reference's volatile offsets masked.
std::string masked(const World& w, int32_t s) { return census::masked(w, s, *g_ref); }

void print_window(const World& w, const Window& win, const Stats& prev) {
  std::map<std::string, int> counts;
  const int32_t n = w.config().width * w.config().height;
  for (int32_t s = 0; s < n; ++s) if (w.site_active(s)) counts[masked(w, s)] += 1;
  std::string top;
  int best = 0;
  for (auto& [t, c] : counts) if (c > best) { best = c; top = t; }
  const int dist = best ? text_distance(reinterpret_cast<const uint8_t*>(top.data()), ref_program(),
                                        w.config().site_len) : -1;
  // Space census: blank = inactive and all bytes inert; open0 = byte 0 inert (a polite
  // copy target); dead = inactive with any non-inert byte.
  int blank = 0, open0 = 0, dead = 0, pfx_active = 0;
  for (int32_t s = 0; s < n; ++s) {
    const uint8_t* bs = w.bytes_at(s);
    bool any = false;
    for (int k = 0; k < w.config().site_len && !any; ++k) any = bs[k] != INERT;
    open0 += bs[0] == INERT;
    if (!w.site_active(s)) { blank += !any; dead += any; }
    else pfx_active += prefix_intact(bs);
  }
  const double b = win.births ? static_cast<double>(win.births) : 1.0;
  std::cout << w.tick() << '\t' << w.active_count() << '\t' << win.births << '\t'
            << 100.0 * win.exact / b << '\t' << 100.0 * win.intact / b << '\t' << best << '\t'
            << dist << '\t' << counts.size() << '\t' << win.copies << '\t' << win.reignites
            << '\t' << win.intact_copies << '\t' << blank << '\t' << open0 << '\t' << dead
            << '\t' << pfx_active << '\t' << win.pfx_copies << '\t'
            << w.stats().ext_erasures - prev.ext_erasures << '\t'
            << w.stats().stalls - prev.stalls << '\t'
            << w.stats().deaths_starve - prev.deaths_starve << '\t' << w.ledger().energy
            << std::endl;
}

// Replicator census (census=1): every distinct active program is tested alone in a trial
// world (census::run_trial in ps_census.hpp). Trial worlds never touch the run's world, so
// the run's dynamics and digest are unchanged. Results are cached by text. census_topup=1
// (the default) tops up the trial founder's site so that keys past mass0 bytes can be
// seeded; census_topup=0 gives the earlier seed-limited verdict.
bool g_census_topup = true;

TrialResult run_trial(const Config& run_cfg, const std::string& key) {
  return census::run_trial(run_cfg, key, *g_ref, g_census_topup);
}

// Kind of the activation now running at a site; seeded founders count as self.
int activation_kind(const std::vector<Record>& recs, const std::vector<int>& current, int32_t s) {
  return current[s] >= 0 ? recs[current[s]].kind : kSelfIgnite;
}

void print_census(const World& w, const std::vector<Record>& recs,
                  const std::vector<int>& current, std::map<std::string, TrialResult>& cache) {
  const int32_t n = w.config().width * w.config().height;
  int rep = 0, rep_pfx = 0;
  int other[kKinds] = {};
  uint64_t age[2] = {}, count[2] = {}, span[2] = {}, spanned[2] = {};
  std::map<std::string, bool> seen;  // genotypes active now -> replicator
  for (int32_t s = 0; s < n; ++s) {
    if (!w.site_active(s)) continue;
    const std::string key = masked(w, s);
    auto it = cache.find(key);
    if (it == cache.end()) it = cache.emplace(key, run_trial(w.config(), key)).first;
    const bool r = it->second.replicator;
    seen[key] = r;
    rep += r;
    rep_pfx += r && prefix_intact(w.bytes_at(s));
    if (!r) other[activation_kind(recs, current, s)] += 1;
    if (current[s] >= 0) {
      age[r] += w.tick() - recs[current[s]].born;
      count[r] += 1;
    }
    if (it->second.ip_span >= 0) {
      span[r] += it->second.ip_span;
      spanned[r] += 1;
    }
  }
  int rep_genotypes = 0;
  for (auto& [k, r] : seen) rep_genotypes += r;
  auto mean = [](uint64_t a, uint64_t b) { return b ? static_cast<double>(a) / b : 0.0; };
  std::cout << "# census tick=" << w.tick() << " active=" << w.active_count()
            << " replicators=" << rep << " pfx_replicators=" << rep_pfx
            << " genotypes=" << seen.size() << " replicator_genotypes=" << rep_genotypes
            << " nonrep_self/copy/reignite=" << other[kSelfIgnite] << '/' << other[kCopy] << '/'
            << other[kReignite] << " mean_age_rep/nonrep="
            << (count[1] ? age[1] / count[1] : 0) << '/' << (count[0] ? age[0] / count[0] : 0)
            << " ip_span_rep/nonrep=" << mean(span[1], spanned[1]) << '/'
            << mean(span[0], spanned[0]) << " trials=" << cache.size() << std::endl;
}

// Per-op decay classes (classes=...): for each listed table, the share of non-inert bytes in
// fast classes and the hazard h(x) = n_f r_f + n_s r_s at the run's p_hydro and decay_ratio,
// for replicators and non-replicators (census verdicts) and for all code. Replicator bytes are
// split into opcode bytes (offsets where the census founder executed an instruction) and the
// others (operands and data). Observation only; tables need not be the run's decay_table.
struct ClassSums {
  uint64_t sites = 0, bytes = 0, fast = 0, op = 0, op_fast = 0, data = 0, data_fast = 0;
  double h = 0.0;
};

// Substitutions in replicators at the reference's own offsets, by the reference's role of the
// offset (opcode or other) and by direction between the table's classes.
enum Dir { kF2S = 0, kS2F, kF2F, kS2S, kToInert, kFromInert, kDirsN };
constexpr const char* kDirName[kDirsN] = {"f2s", "s2f", "f2f", "s2s", "to_inert", "from_inert"};

std::string pct(uint64_t a, uint64_t b) {
  std::ostringstream o;
  o.precision(4);
  o << (b ? 100.0 * static_cast<double>(a) / static_cast<double>(b) : 0.0);
  return o.str();
}

void print_classes(const World& w, const std::map<std::string, TrialResult>& cache,
                   const std::vector<int>& tables) {
  const Config& c = w.config();
  const int32_t n = c.width * c.height;
  const auto& ref = ref_program();
  uint64_t ref_op = 0;
  for (int k : g_ref->ops) ref_op |= uint64_t{1} << k;
  for (int table : tables) {
    const auto fast = decay_fast_classes(table);
    double rs = 0.0, rf = 0.0;
    decay_rates(c.p_hydro, c.decay_ratio, rs, rf);
    ClassSums sum[2], all;  // [0] non-replicators, [1] replicators (active sites only)
    uint64_t subst[2][kDirsN] = {};  // [0] reference data offsets, [1] its opcode offsets
    int pfx_sites = 0;
    for (int32_t s = 0; s < n; ++s) {
      const uint8_t* b = w.bytes_at(s);
      ClassSums x;
      for (int k = 0; k < c.site_len; ++k) {
        if (b[k] == INERT) continue;
        x.bytes += 1;
        x.fast += fast[op_class(b[k])];
      }
      if (x.bytes == 0) continue;
      all.sites += 1;
      all.bytes += x.bytes;
      all.fast += x.fast;
      if (!w.site_active(s)) continue;
      const auto it = cache.find(masked(w, s));
      if (it == cache.end()) continue;
      const bool rep = it->second.replicator;
      ClassSums& g = sum[rep];
      g.sites += 1;
      g.bytes += x.bytes;
      g.fast += x.fast;
      g.h += static_cast<double>(x.fast) * rf + static_cast<double>(x.bytes - x.fast) * rs;
      if (!rep) continue;
      for (int k = 0; k < c.site_len; ++k) {
        if (b[k] == INERT) continue;
        const bool f = fast[op_class(b[k])];
        if (it->second.op_mask >> k & 1) {
          g.op += 1;
          g.op_fast += f;
        } else {
          g.data += 1;
          g.data_fast += f;
        }
      }
      pfx_sites += 1;
      for (int k = 0; k < static_cast<int>(ref.size()); ++k) {
        if (is_volatile(k) || b[k] == ref[k]) continue;
        const int role = ref_op >> k & 1;
        Dir d;
        if (b[k] == INERT) d = kToInert;
        else if (ref[k] == INERT) d = kFromInert;
        else {
          const bool f0 = fast[op_class(ref[k])], f1 = fast[op_class(b[k])];
          d = f0 ? (f1 ? kF2F : kF2S) : (f1 ? kS2F : kS2S);
        }
        subst[role][d] += 1;
      }
    }
    auto mean = [](double a, uint64_t b) { return b ? a / static_cast<double>(b) : 0.0; };
    std::cout << "# classes tick=" << w.tick() << " table=" << table
              << " rep_sites=" << sum[1].sites << " rep_len=" << mean(sum[1].bytes, sum[1].sites)
              << " rep_fast%=" << pct(sum[1].fast, sum[1].bytes)
              << " rep_op_fast%=" << pct(sum[1].op_fast, sum[1].op)
              << " rep_op_len=" << mean(sum[1].op, sum[1].sites)
              << " rep_data_fast%=" << pct(sum[1].data_fast, sum[1].data)
              << " rep_data_len=" << mean(sum[1].data, sum[1].sites)
              << " rep_h=" << mean(sum[1].h, sum[1].sites)
              << " nonrep_sites=" << sum[0].sites << " nonrep_len=" << mean(sum[0].bytes, sum[0].sites)
              << " nonrep_fast%=" << pct(sum[0].fast, sum[0].bytes)
              << " nonrep_h=" << mean(sum[0].h, sum[0].sites)
              << " code_sites=" << all.sites << " code_fast%=" << pct(all.fast, all.bytes)
              << std::endl;
    std::cout << "# subst tick=" << w.tick() << " table=" << table << " rep_sites=" << pfx_sites;
    for (int role = 1; role >= 0; --role) {
      std::cout << (role ? " op:" : " data:");
      for (int d = 0; d < kDirsN; ++d) {
        std::cout << ' ' << kDirName[d] << '=' << mean(subst[role][d], pfx_sites);
      }
    }
    std::cout << std::endl;
  }
}

// Fidelity window (fidelity=W, needs census=1): every copy birth in the last W ticks before
// each checkpoint is kept with the keys of parent and child at birth, the class of their
// differences (census::diff_sources) and whether the parent's reference-inert offsets were
// filled (census::ref_inert_filled). At the checkpoint every key gets a census verdict.
// Status of a key: rep (strict replicator), loose (replicator by the two-carrier test only),
// prop (not a replicator, but its trial reached copy depth kPropDepth: a child of the founder
// made a copy) or other. Reignite births are sampled (the first kReigniteSample in the
// window) to bound the number of trials.
using census::Diff;
using census::kDiffClasses;
using census::kDiffClsName;
using census::kDiffSrcName;
using census::kDiffSrcs;

constexpr int kPropDepth = 2;
constexpr uint64_t kReigniteSample = 300;
constexpr uint64_t kGenoMin = 10;  // copy births for a genotype to enter the quartiles
constexpr int kTopGenotypes = 3;

enum Status { kRep = 0, kLoose, kProp, kOther, kStatuses };
constexpr const char* kStatusName[kStatuses] = {"rep", "loose", "prop", "other"};

int status_of(const TrialResult& r) {
  if (r.replicator) return r.strict() ? kRep : kLoose;
  return r.depth >= kPropDepth ? kProp : kOther;
}

struct FidBirth {
  std::string parent, child;
  int kind = 0;
  Diff diff;
  bool parent_filled = false;
  int parent_len = 0;  // non-inert bytes at the parent site
};

struct FidWindow {
  std::vector<FidBirth> births;
  uint64_t all = 0, reignites_seen = 0;
  uint64_t kinds[kKinds] = {};
  Stats start;  // run counters when the window opened
};

FidBirth observe_fid(const World& w, const World::Birth& b, int kind) {
  FidBirth f;
  f.parent = masked(w, b.parent);
  f.child = masked(w, b.child);
  f.kind = kind;
  f.diff = census::diff_sources(w, b, *g_ref);
  f.parent_filled = census::ref_inert_filled(w.bytes_at(b.parent), *g_ref);
  for (int k = 0; k < w.config().site_len; ++k) f.parent_len += w.bytes_at(b.parent)[k] != INERT;
  return f;
}

std::string hex(const std::string& key) {
  static const char* kDigits = "0123456789abcdef";
  std::string h;
  for (unsigned char ch : key) {
    h += kDigits[ch >> 4];
    h += kDigits[ch & 15];
  }
  return h;
}

// Copy births grouped by parent; children counted by census verdict (rep = census
// replicator, strict = strict replicator).
struct FidTab {
  uint64_t births = 0, child_rep = 0, child_strict = 0, child_prop = 0, len = 0;
  uint64_t cls[kDiffClasses] = {}, cls_strict[kDiffClasses] = {};
  uint64_t src[kDiffSrcs] = {};
  uint64_t filled = 0, filled_strict = 0;

  void add(const FidBirth& f, const TrialResult& child) {
    const bool strict = child.strict();
    births += 1;
    child_rep += child.replicator;
    child_strict += strict;
    child_prop += status_of(child) == kProp;
    len += f.parent_len;
    cls[f.diff.cls] += 1;
    cls_strict[f.diff.cls] += strict;
    for (int i = 0; i < kDiffSrcs; ++i) src[i] += f.diff.n[i];
    filled += f.parent_filled;
    filled_strict += f.parent_filled && strict;
  }
  // exact=n(s) ...: births of each class and, in parentheses, those with a strict child.
  void print_classes(std::ostream& o) const {
    for (int c = 0; c < kDiffClasses; ++c) {
      o << ' ' << kDiffClsName[c] << '=' << cls[c] << '(' << cls_strict[c] << ')';
    }
    o << " parent_filled=" << filled << '(' << filled_strict << ')';
  }
};

void print_fidelity(const World& w, const FidWindow& fw, uint64_t window,
                    std::map<std::string, TrialResult>& cache) {
  auto verdict = [&](const std::string& key) -> const TrialResult& {
    auto it = cache.find(key);
    if (it == cache.end()) it = cache.emplace(key, run_trial(w.config(), key)).first;
    return it->second;
  };
  auto mean = [](uint64_t a, uint64_t b) { return b ? static_cast<double>(a) / b : 0.0; };
  const Stats& s = w.stats();
  std::cout << "# fidelity tick=" << w.tick() << " window=" << window << " births=" << fw.all
            << " self/copy/reignite=" << fw.kinds[kSelfIgnite] << '/' << fw.kinds[kCopy] << '/'
            << fw.kinds[kReignite]
            << " reignite_tested=" << std::min(fw.reignites_seen, kReigniteSample)
            << " no_mass=" << s.write_no_mass - fw.start.write_no_mass
            << " ext_blocked=" << s.ext_blocked - fw.start.ext_blocked
            << " conflicts=" << s.write_conflict - fw.start.write_conflict
            << " walled=" << s.write_walled - fw.start.write_walled << std::endl;

  FidTab tab[kStatuses], reig;
  uint64_t reig_igniter_rep = 0, reig_same = 0;
  struct Geno {
    FidTab tab;
    int len = 0;
    int status = kRep;
  };
  std::map<std::string, Geno> genos;  // census-replicator parents (rep and loose)
  for (const FidBirth& f : fw.births) {
    const int ps = status_of(verdict(f.parent));
    const TrialResult& child = verdict(f.child);
    if (f.kind == kReignite) {
      reig.add(f, child);
      reig_igniter_rep += ps == kRep || ps == kLoose;
      reig_same += f.child == f.parent;
      continue;
    }
    tab[ps].add(f, child);
    if (ps != kRep && ps != kLoose) continue;
    Geno& g = genos[f.parent];
    g.tab.add(f, child);
    g.len = f.parent_len;
    g.status = ps;
  }
  for (int ps = 0; ps < kStatuses; ++ps) {
    const FidTab& t = tab[ps];
    std::cout << "# fidcopy tick=" << w.tick() << " parent=" << kStatusName[ps]
              << " births=" << t.births << " child_rep%=" << pct(t.child_rep, t.births)
              << " child_strict%=" << pct(t.child_strict, t.births)
              << " child_prop%=" << pct(t.child_prop, t.births)
              << " parent_len=" << mean(t.len, t.births);
    t.print_classes(std::cout);
    std::cout << " diffs/birth:";
    for (int i = 0; i < kDiffSrcs; ++i) std::cout << ' ' << kDiffSrcName[i] << '=' << mean(t.src[i], t.births);
    std::cout << std::endl;
  }
  // Per strict-replicator parent genotype: quartiles of the strict share of its copies.
  std::vector<double> shares;
  uint64_t covered = 0, strict_genos = 0;
  for (auto& [key, g] : genos) {
    if (g.status != kRep) continue;
    strict_genos += 1;
    if (g.tab.births < kGenoMin) continue;
    shares.push_back(100.0 * mean(g.tab.child_strict, g.tab.births));
    covered += g.tab.births;
  }
  std::sort(shares.begin(), shares.end());
  auto q = [&](double f) {
    return shares.empty() ? 0.0 : shares[static_cast<size_t>(f * (shares.size() - 1) + 0.5)];
  };
  std::cout << "# fidgeno tick=" << w.tick() << " rep_parent_genotypes=" << strict_genos
            << " with_min" << kGenoMin << '=' << shares.size() << " their_births=" << covered
            << " child_strict%_q25/q50/q75=" << q(0.25) << '/' << q(0.5) << '/' << q(0.75)
            << std::endl;
  // The census-replicator parent genotypes with the most copy births in the window.
  std::multimap<uint64_t, const std::string*, std::greater<>> top;
  for (auto& [key, g] : genos) top.insert({g.tab.births, &key});
  int rank = 0;
  for (auto& [n, key] : top) {
    if (rank++ == kTopGenotypes) break;
    const Geno& g = genos[*key];
    const TrialResult& v = verdict(*key);
    std::cout << "# fidtop tick=" << w.tick() << " rank=" << rank << " status="
              << kStatusName[g.status] << " births=" << n
              << " child_strict%=" << pct(g.tab.child_strict, n) << " len=" << g.len;
    g.tab.print_classes(std::cout);
    std::cout << " founder_exact/copies=" << v.founder_exact << '/' << v.founder_copies
              << " hex=" << hex(*key) << std::endl;
  }
  std::cout << "# fidreig tick=" << w.tick() << " tested=" << reig.births
            << " child_rep%=" << pct(reig.child_rep, reig.births)
            << " child_strict%=" << pct(reig.child_strict, reig.births)
            << " child_prop%=" << pct(reig.child_prop, reig.births)
            << " igniter_rep%=" << pct(reig_igniter_rep, reig.births)
            << " same_as_igniter%=" << pct(reig_same, reig.births) << std::endl;
}

// Active sites by status, and those whose reference-inert offsets are filled.
void print_lineage(const World& w, std::map<std::string, TrialResult>& cache) {
  const int32_t n = w.config().width * w.config().height;
  uint64_t sites[kStatuses] = {}, depth[kStatuses] = {}, filled[kStatuses] = {};
  std::map<std::string, int> genos;
  for (int32_t s = 0; s < n; ++s) {
    if (!w.site_active(s)) continue;
    const std::string key = masked(w, s);
    auto it = cache.find(key);
    if (it == cache.end()) it = cache.emplace(key, run_trial(w.config(), key)).first;
    const int st = status_of(it->second);
    sites[st] += 1;
    depth[st] += static_cast<uint64_t>(it->second.depth);
    filled[st] += census::ref_inert_filled(w.bytes_at(s), *g_ref);
    genos[key] = st;
  }
  uint64_t g[kStatuses] = {};
  for (auto& [key, st] : genos) g[st] += 1;
  auto mean = [](uint64_t a, uint64_t b) { return b ? static_cast<double>(a) / b : 0.0; };
  std::cout << "# lineage tick=" << w.tick();
  for (int st = 0; st < kStatuses; ++st) {
    const std::string name = kStatusName[st];
    std::cout << ' ' << name << "_sites=" << sites[st] << ' ' << name << "_genotypes=" << g[st]
              << ' ' << name << "_depth=" << mean(depth[st], sites[st]) << ' ' << name
              << "_filled=" << filled[st];
  }
  std::cout << std::endl;
}

// Activation fates (fate=1, needs census=1 and p_rot 0). Every activation gets the status of
// its key at birth (census trial, cached). The status of a rep, loose or prop activation is
// re-evaluated whenever a non-volatile byte of its live site changes without a birth ("in
// place"). Changes of other activations are counted but not tested (they are about 98% of
// all in-place changes); the census at each checkpoint finds any that became a replicator
// and counts them as found_at_census, so the strict balance stays exact. After each tick
// every tracked site is compared with a snapshot. Bytes change only by writes, apart from
// whole-program decay, which empties the site and ends its activation, so each changed byte
// was written this tick and World::byte_writer names the writing site. An activation ends by
// decay when its site holds no non-inert byte after the tick, otherwise by wick: its ip
// reached an inert byte (starvation would also land here; the window's starvation count is
// printed). Flows of strict-replicator activations are printed at each checkpoint and checked
// against the census. Observation only. The observer keeps its own trial cache and reads the
// census cache, so the census output (including its trial count) is unchanged; prime() hands
// the census the verdicts it would compute for the active sites.
enum End { kEndDecay = 0, kEndWick, kEnds };
constexpr const char* kEndName[kEnds] = {"decay", "wick"};
// Writer of an in-place change: the site itself, or the status of the foreign writer's
// activation (kWNone: the writer's site is not active).
enum Writer { kWSelf = kStatuses, kWNone, kWriters };
constexpr const char* kWriterName[kWriters] = {"rep", "loose", "prop", "other", "self", "none"};

struct Fate {
  bool on = false;
  bool converted = false;  // was strict, lost strict status in place
  int status = kOther;
  int start_ip = 0;        // ignition offset
  bool fill = false;       // converted by a foreign write to the source-pointer direction alone
  uint64_t converted_at = 0;
  uint64_t born_at = 0;    // trace: tick of the ignition
  int kind = kKinds;       // trace: birth kind (kKinds: seeded founder)
};

// trace=1: how the site's previous activation ended (kept after it ends).
struct LastEnd {
  bool set = false;
  int status = kOther;
  int cause = 0;
  bool start0 = true;
  uint64_t tick = 0;
};

// trace=1 counters per checkpoint window. Age of an activation: ticks since its ignition,
// in buckets < 1,000, 1,000-9,999 and >= 10,000.
constexpr int kAges = 3;
inline int age_bucket(uint64_t age) { return age < 1000 ? 0 : age < 10000 ? 1 : 2; }
struct TraceTally {
  // Strict -> not strict in place, credited to a foreign writer (as in FateTally).
  uint64_t fo_n = 0;
  uint64_t fo_writer[kWriters][kAges] = {};  // writer status x age
  uint64_t fo_wkind[kKinds + 1] = {};         // writer's birth kind (self/copy/reignite/seeded)
  uint64_t fo_wstart0 = 0;                    // writer ignited at offset 0
  uint64_t fo_wip[64] = {};                   // offset of the writer's instruction
  uint64_t fo_not_mov = 0;                    // that byte is not a MOV
  uint64_t fo_src_own = 0;                    // the MOV's source pointer names the writer's site
  uint64_t fo_off[64] = {};                   // every changed non-volatile offset
  uint64_t fo_dir = 0;       // a changed byte was INERT and is a pointer direction of the victim
  uint64_t fo_dir_only = 0;  // every changed non-volatile byte is such
  uint64_t fo_dir_off[64] = {};
  uint64_t fo_victim_start0 = 0;  // the victim activation was ignited at offset 0
  // Strict births: [ignited off offset 0][kind].
  uint64_t rb[2][kKinds] = {};
  uint64_t rb_ign[kWriters][kAges] = {};  // off offset 0: igniter status x age
  uint64_t rb_ign_ip[64] = {};            // off offset 0: offset of the igniter's instruction
  uint64_t rb_entry[64] = {};             // off offset 0: entry offset
  uint64_t rb_same = 0;                   // off offset 0: igniter carries the child's key
  // Off offset 0: the site's previous activation was strict and ended by wick, ignited at 0
  // or not; and the summed ticks since that end.
  uint64_t rb_prev_wick[2] = {};
  uint64_t rb_prev_gap = 0;
  uint64_t all_off = 0, all_births = 0;  // births of any status, and those off offset 0
  // Ends of strict activations by entry: [off offset 0][cause], lifetimes, and copy births
  // made by strict activations by entry.
  uint64_t re[2][kEnds] = {};
  uint64_t re_life[2] = {};
  uint64_t re_copies[2] = {};
  // Census seeding limit: a key with more than mass0 non-inert bytes after the volatile reset
  // cannot be seeded in the trial (census::run_trial). Strict -> not strict in place by
  // writer [self, foreign]; those whose new key cannot be seeded; and the topped-up verdict
  // of those keys.
  uint64_t lo_n[2] = {};
  uint64_t lo_unseeded[2] = {};
  uint64_t lo_topped[2][kStatuses] = {};
  // Copy births by any parent, and by a parent whose key cannot be seeded; with the child
  // carrying the parent's key.
  uint64_t cp_n = 0, cp_same = 0, cp_unseeded = 0, cp_unseeded_same = 0;
};

struct FateTally {
  uint64_t born[kStatuses][kKinds] = {};
  uint64_t ends[kStatuses][kEnds] = {};
  uint64_t ends_converted[kEnds] = {};
  uint64_t change[kStatuses][kStatuses] = {};  // in-place key changes, from -> to status
  uint64_t other_changes = 0;                   // key changes of other activations (untested)
  uint64_t found[kStatuses] = {};               // other -> status, found at the census
  uint64_t change_writer[kStatuses][kWriters] = {};  // the same changes by writer
  // Strict -> not strict in place, by writer and by status after.
  uint64_t out_writer[kWriters] = {};
  uint64_t out_to[kStatuses][kWriters] = {};
  uint64_t out_at[2][64] = {};  // changed offsets, by a foreign writer [0] or the site [1]
  uint64_t out_src = 0, out_src_only = 0;  // the source-pointer direction byte among them
  uint64_t src_writer[kWriters] = {};  // who wrote that byte
  uint64_t src_names_writer = 0;       // a foreign writer, and the new direction names it
  uint64_t out_start0 = 0;             // the lost activation was ignited at offset 0
  // Strict losses written by the site itself: ignited at offset 0, and the offset of the
  // instruction that executed in that tick.
  uint64_t self_start0 = 0;
  uint64_t self_at[64] = {};
  uint64_t born_rep_start0 = 0;  // strict births ignited at offset 0
  uint64_t out_jump[3] = {};  // its new value v: ip after the closing jump, v mod len, is
                              // 0 / another reference opcode offset / elsewhere
  uint64_t vol_foreign_rep = 0;  // foreign writes into volatile offsets of strict sites
  uint64_t stale = 0;            // changed bytes whose last write was not this tick
  uint64_t replaced = 0;         // a birth into a site whose tracked activation was on
  // Copy births by converted activations.
  uint64_t conv_copies = 0, conv_child_rep = 0, conv_child_same = 0, conv_child_src = 0;
  // The same for activations converted by a foreign fill of the source pointer alone, with
  // their ends and the summed ticks from conversion to end.
  uint64_t fill_copies = 0, fill_child_rep = 0, fill_child_same = 0, fill_child_src = 0;
  uint64_t fill_ends[kEnds] = {};
  uint64_t fill_life = 0;
  uint64_t start_starve = 0;
};

class FateObserver {
public:
  FateObserver(const World& w, const std::map<std::string, TrialResult>& census,
               bool trace = false)
      : w_(w), census_(census), len_(w.config().site_len),
        sites_(w.config().width * w.config().height),
        src_ptr_(g_ref->name == "polite" ? 30 : 23),
        fate_(sites_), snap_(static_cast<size_t>(sites_) * len_), next_ip_(sites_, 0),
        trace_(trace), prev_ip_(sites_, 0), last_(sites_) {
    // The seeded founders are activations that no birth announced.
    for (int32_t s = 0; s < sites_; ++s) {
      if (w.site_active(s)) start(s);
    }
    rep_prev_ = count(kRep);
  }

  int status_of_key(const std::string& key) {
    const auto c = census_.find(key);
    if (c != census_.end()) return status_of(c->second);
    auto it = cache_.find(key);
    if (it == cache_.end()) it = cache_.emplace(key, run_trial(w_.config(), key)).first;
    return status_of(it->second);
  }

  // Before a census: copy this observer's verdicts for the active sites' keys into the census
  // cache (the trial is deterministic, so the census would compute the same verdicts).
  void prime(std::map<std::string, TrialResult>& census) const {
    for (int32_t s = 0; s < sites_; ++s) {
      if (!w_.site_active(s)) continue;
      const std::string key = masked(w_, s);
      if (census.count(key)) continue;
      const auto it = cache_.find(key);
      if (it != cache_.end()) census.emplace(key, it->second);
    }
  }

  // Call after every tick, before reading the census.
  void observe() {
    if (trace_) prev_ip_ = next_ip_;  // the instruction each tracked activation just ran
    for (const auto& b : w_.births_this_tick()) {
      Fate& f = fate_[b.child];
      if (f.on) t_.replaced += 1;
      const int kind = classify(b);
      const Fate parent = fate_[b.parent];
      const LastEnd prev = last_[b.child];
      start(b.child);
      t_.born[fate_[b.child].status][kind] += 1;
      t_.born_rep_start0 += fate_[b.child].status == kRep && fate_[b.child].start_ip == 0;
      if (kind == kCopy && parent.on && parent.converted) note_converted_copy(b, parent);
      if (trace_) trace_birth(b, kind, parent, prev);
    }
    for (int32_t s = 0; s < sites_; ++s) {
      Fate& f = fate_[s];
      if (!f.on) continue;
      if (!w_.site_active(s)) {
        end(s);
        continue;
      }
      uint8_t* old = &snap_[static_cast<size_t>(s) * len_];
      const uint8_t* now = w_.bytes_at(s);
      if (std::memcmp(old, now, len_) != 0) changed(s, old, now);
      next_ip_[s] = static_cast<int16_t>(w_.first_ip(s));
    }
  }

  // Checkpoint: flows since the last one, checked against the census of active sites.
  void print(std::ostream& o) {
    uint64_t mismatch = 0, untracked = 0;
    for (int32_t s = 0; s < sites_; ++s) {
      if (!w_.site_active(s)) continue;
      if (!fate_[s].on) { untracked += 1; continue; }
      const int now = status_of_key(masked(w_, s));
      if (now == fate_[s].status) continue;
      if (fate_[s].status == kOther) {
        t_.found[now] += 1;
        fate_[s].status = now;
      } else {
        mismatch += 1;
      }
    }
    const uint64_t rep_now = count(kRep);
    uint64_t born = 0, ended = 0, out = 0, in = 0;
    for (int k = 0; k < kKinds; ++k) born += t_.born[kRep][k];
    for (int e = 0; e < kEnds; ++e) ended += t_.ends[kRep][e];
    for (int st = 0; st < kStatuses; ++st) {
      if (st == kRep) continue;
      out += t_.change[kRep][st];
      in += t_.change[st][kRep];
    }
    in += t_.found[kRep];
    const int64_t balance = static_cast<int64_t>(rep_prev_ + born + in) -
                            static_cast<int64_t>(ended + out);
    const uint64_t tick = w_.tick();
    o << "# fate tick=" << tick << " rep_prev=" << rep_prev_ << " rep_now=" << rep_now
      << " born_copy/reignite/self=" << t_.born[kRep][kCopy] << '/' << t_.born[kRep][kReignite]
      << '/' << t_.born[kRep][kSelfIgnite] << " end_decay=" << t_.ends[kRep][kEndDecay]
      << " end_wick=" << t_.ends[kRep][kEndWick] << " out_in_place=" << out
      << " in_in_place=" << in << " (found_at_census=" << t_.found[kRep] << ")"
      << " balance=" << balance << " census_mismatch=" << mismatch
      << " untracked=" << untracked << " stale=" << t_.stale << " replaced=" << t_.replaced
      << " starved=" << w_.stats().deaths_starve - t_.start_starve << std::endl;
    o << "# fateborn tick=" << tick;
    for (int st = 0; st < kStatuses; ++st) {
      o << ' ' << kStatusName[st] << '=' << t_.born[st][kCopy] << '/' << t_.born[st][kReignite]
        << '/' << t_.born[st][kSelfIgnite];
    }
    o << " (copy/reignite/self)" << std::endl;
    o << "# fateend tick=" << tick;
    for (int st = 0; st < kStatuses; ++st) {
      o << ' ' << kStatusName[st] << '=' << t_.ends[st][kEndDecay] << '/' << t_.ends[st][kEndWick];
    }
    o << " converted=" << t_.ends_converted[kEndDecay] << '/' << t_.ends_converted[kEndWick]
      << " (decay/wick)" << std::endl;
    o << "# fatechange tick=" << tick;
    for (int a = 0; a < kStatuses; ++a) {
      o << ' ' << kStatusName[a] << ">";
      for (int b = 0; b < kStatuses; ++b) o << (b ? "/" : "") << t_.change[a][b];
    }
    o << " (to rep/loose/prop/other) other_untested=" << t_.other_changes << " found_at_census="
      << t_.found[kRep] << '/' << t_.found[kLoose] << '/' << t_.found[kProp] << " writers";
    for (int a = 0; a < kStatuses; ++a) {
      o << ' ' << kStatusName[a] << ':';
      for (int k = 0; k < kWriters; ++k) o << (k ? "/" : "") << t_.change_writer[a][k];
    }
    o << " (rep/loose/prop/other/self/none)" << std::endl;
    o << "# fateout tick=" << tick << " n=" << out << " writer";
    for (int k = 0; k < kWriters; ++k) o << ' ' << kWriterName[k] << '=' << t_.out_writer[k];
    o << " by_to";
    for (int a = kLoose; a < kStatuses; ++a) {
      o << ' ' << kStatusName[a] << ':';
      for (int k = 0; k < kWriters; ++k) o << (k ? "/" : "") << t_.out_to[a][k];
    }
    o << " src_ptr=" << src_ptr_ << " with_src=" << t_.out_src << " only_src=" << t_.out_src_only
      << " src_writer=";
    for (int k = 0; k < kWriters; ++k) o << (k ? "/" : "") << t_.src_writer[k];
    o << " src_names_writer=" << t_.src_names_writer
      << " jump_0/op/other=" << t_.out_jump[0] << '/' << t_.out_jump[1] << '/' << t_.out_jump[2]
      << " vol_foreign_rep=" << t_.vol_foreign_rep;
    int shown = 0;
    for (int w = 0; w < 2; ++w) {
      o << (w == 0 ? " offsets_foreign:" : " offsets_self:");
      std::multimap<uint64_t, int, std::greater<>> top;
      for (int k = 0; k < len_; ++k) if (t_.out_at[w][k]) top.insert({t_.out_at[w][k], k});
      shown = 0;
      for (auto [n, k] : top) {
        if (shown++ == 8) break;
        o << ' ' << k << ':' << n;
      }
    }
    o << std::endl;
    std::multimap<uint64_t, int, std::greater<>> at;
    uint64_t self = t_.out_writer[kWSelf];
    for (int k = 0; k < len_; ++k) if (t_.self_at[k]) at.insert({t_.self_at[k], k});
    uint64_t born_rep = 0;
    for (int k = 0; k < kKinds; ++k) born_rep += t_.born[kRep][k];
    o << "# fatestart tick=" << tick << " out_start0=" << t_.out_start0 << '/' << out
      << " self_start0=" << t_.self_start0 << '/' << self << " born_rep_start0="
      << t_.born_rep_start0 << '/' << born_rep << " self_instr_at:";
    shown = 0;
    for (auto [n, k] : at) {
      if (shown++ == 10) break;
      o << ' ' << k << ':' << n;
    }
    o << std::endl;
    uint64_t conv_alive = 0, fill_alive = 0;
    for (int32_t s = 0; s < sites_; ++s) {
      conv_alive += fate_[s].on && fate_[s].converted;
      fill_alive += fate_[s].on && fate_[s].fill;
    }
    o << "# fateconv tick=" << tick << " alive=" << conv_alive << " copies=" << t_.conv_copies
      << " child_rep=" << t_.conv_child_rep << " child_same=" << t_.conv_child_same
      << " child_src=" << t_.conv_child_src << " fill: alive=" << fill_alive
      << " copies=" << t_.fill_copies << " child_rep=" << t_.fill_child_rep
      << " child_same=" << t_.fill_child_same << " child_src=" << t_.fill_child_src
      << " ends_decay/wick=" << t_.fill_ends[kEndDecay] << '/' << t_.fill_ends[kEndWick]
      << " life_sum=" << t_.fill_life << std::endl;
    if (trace_) print_trace(o);
    rep_prev_ = rep_now;
    t_ = FateTally{};
    t_.start_starve = w_.stats().deaths_starve;
  }

private:
  const World& w_;
  const std::map<std::string, TrialResult>& census_;
  std::map<std::string, TrialResult> cache_;
  std::map<std::string, int> topped_;  // trace: topped-up verdicts (seed limit check)
  const int len_;
  const int32_t sites_;
  const int src_ptr_;
  std::vector<Fate> fate_;
  std::vector<uint8_t> snap_;
  std::vector<int16_t> next_ip_;  // ip of each tracked activation for the next tick
  FateTally t_;
  uint64_t rep_prev_ = 0;
  const bool trace_;
  std::vector<int16_t> prev_ip_;  // trace: ip each tracked activation ran in this tick
  std::vector<LastEnd> last_;     // trace: how each site's previous activation ended
  TraceTally x_;

  uint64_t count(int status) const {
    uint64_t n = 0;
    for (const Fate& f : fate_) n += f.on && f.status == status;
    return n;
  }

  void start(int32_t s) {
    Fate& f = fate_[s];
    f.on = true;
    f.converted = false;
    f.fill = false;
    f.status = status_of_key(masked(w_, s));
    f.start_ip = w_.first_ip(s);
    f.born_at = w_.tick();
    f.kind = kKinds;
    next_ip_[s] = static_cast<int16_t>(f.start_ip);
    std::memcpy(&snap_[static_cast<size_t>(s) * len_], w_.bytes_at(s), len_);
  }

  void end(int32_t s) {
    Fate& f = fate_[s];
    const uint8_t* b = w_.bytes_at(s);
    const int cause = std::all_of(b, b + len_, [](uint8_t v) { return v == INERT; })
                          ? kEndDecay : kEndWick;
    t_.ends[f.status][cause] += 1;
    if (f.converted) t_.ends_converted[cause] += 1;
    if (f.fill) {
      t_.fill_ends[cause] += 1;
      t_.fill_life += w_.tick() - f.converted_at;
    }
    if (trace_) {
      if (f.status == kRep) {
        x_.re[f.start_ip != 0][cause] += 1;
        x_.re_life[f.start_ip != 0] += w_.tick() - f.born_at;
      }
      last_[s] = LastEnd{true, f.status, cause, f.start_ip == 0, w_.tick()};
    }
    f.on = false;
  }

  int writer_class(int32_t writer, int32_t s) const {
    if (writer == s) return kWSelf;
    if (writer < 0 || !fate_[writer].on) return kWNone;
    return fate_[writer].status;
  }

  void changed(int32_t s, uint8_t* old, const uint8_t* now) {
    Fate& f = fate_[s];
    uint64_t mask = 0;
    int32_t foreign = -1;
    for (int k = 0; k < len_; ++k) {
      if (old[k] == now[k]) continue;
      const int32_t wr = w_.byte_writer(s, k);
      if (w_.byte_written_at(s, k) + 1 != w_.tick()) t_.stale += 1;
      if (is_volatile(k)) {
        t_.vol_foreign_rep += wr != s && f.status == kRep;
        continue;
      }
      mask |= uint64_t{1} << k;
      if (wr != s && foreign < 0) foreign = wr;
    }
    if (mask != 0 && f.status == kOther) {
      t_.other_changes += 1;
      t_.change_writer[kOther][writer_class(foreign < 0 ? s : foreign, s)] += 1;
    } else if (mask != 0) {
      const int before = f.status;
      const int after = status_of_key(masked(w_, s));
      const int wc = writer_class(foreign < 0 ? s : foreign, s);
      t_.change[before][after] += 1;
      t_.change_writer[before][wc] += 1;
      if (before == kRep && after != kRep) {
        if (trace_ && wc != kWSelf) trace_foreign(s, old, now, mask, foreign, wc);
        if (trace_) trace_unseeded(masked(w_, s), wc != kWSelf);
        f.converted = true;
        t_.out_writer[wc] += 1;
        t_.out_to[after][wc] += 1;
        t_.out_start0 += f.start_ip == 0;
        if (wc == kWSelf) {
          t_.self_start0 += f.start_ip == 0;
          if (next_ip_[s] >= 0) t_.self_at[next_ip_[s]] += 1;  // the instruction that ran
        }
        for (int k = 0; k < len_; ++k) t_.out_at[wc == kWSelf][k] += mask >> k & 1;
        if (mask >> src_ptr_ & 1) {
          t_.out_src += 1;
          t_.out_src_only += mask == uint64_t{1} << src_ptr_;
          const uint8_t v = now[src_ptr_];
          const int32_t sw = w_.byte_writer(s, src_ptr_);
          t_.src_writer[writer_class(sw, s)] += 1;
          t_.src_names_writer += sw != s && v != INERT && neighbor_named(s, v) == sw;
          if (sw != s && mask == uint64_t{1} << src_ptr_ && !f.fill) {
            f.fill = true;
            f.converted_at = w_.tick();
          }
          const int ip = v % len_;
          const auto& ops = g_ref->ops;
          t_.out_jump[ip == 0 ? 0 : std::find(ops.begin(), ops.end(), ip) != ops.end() ? 1 : 2] += 1;
        }
      }
      f.status = after;
    }
    std::memcpy(old, now, len_);
  }

  // Trial verdict for a key: the census cache, else this observer's cache (filled on demand).
  const TrialResult& trial_of(const std::string& key) {
    const auto c = census_.find(key);
    if (c != census_.end()) return c->second;
    auto it = cache_.find(key);
    if (it == cache_.end()) it = cache_.emplace(key, run_trial(w_.config(), key)).first;
    return it->second;
  }

  // Offsets that a key's executed MOV and IGNITE instructions read as pointer directions in
  // its census trial (op_mask). An INERT operand names no pointer under inert_operand=fail.
  uint64_t pointer_dirs(const std::string& key, uint64_t op_mask) const {
    const bool fail = w_.config().inert_operand == InertOperand::Fail;
    uint64_t m = 0;
    auto add = [&](int at) {
      const uint8_t v = static_cast<uint8_t>(key[at % len_]);
      if (v == INERT && fail) return;
      m |= uint64_t{1} << (v % len_);
    };
    for (int i = 0; i < len_; ++i) {
      if (!(op_mask >> i & 1) || key[i] == INERT) continue;
      const uint8_t op = op_class(static_cast<uint8_t>(key[i]));
      if (op == MOV) { add(i + 1); add(i + 2); }
      else if (op == IGNITE) add(i + 1);
    }
    return m;
  }

  bool seedable(const std::string& key) const {
    return census::trial_bytes(key, *g_ref) <= w_.config().mass0;
  }

  // Verdict of a trial whose founder site is topped up to the key's byte count. Under
  // census_topup=1 that is the census verdict; otherwise a separate cache, so the census
  // cache and its trial counts are untouched.
  int topped_status(const std::string& key) {
    if (g_census_topup) return status_of(trial_of(key));
    auto it = topped_.find(key);
    if (it == topped_.end()) {
      it = topped_.emplace(key, status_of(census::run_trial(w_.config(), key, *g_ref, true)))
               .first;
    }
    return it->second;
  }

  void trace_unseeded(const std::string& key, bool foreign) {
    x_.lo_n[foreign] += 1;
    if (seedable(key)) return;
    x_.lo_unseeded[foreign] += 1;
    x_.lo_topped[foreign][topped_status(key)] += 1;
  }

  // A strict activation lost strict status by a change credited to a foreign writer.
  void trace_foreign(int32_t s, const uint8_t* old, const uint8_t* now, uint64_t mask,
                     int32_t writer, int wc) {
    x_.fo_n += 1;
    x_.fo_victim_start0 += fate_[s].start_ip == 0;
    const Fate& wf = fate_[writer];
    const int age = wf.on ? age_bucket(w_.tick() - wf.born_at) : 0;
    x_.fo_writer[wc][age] += 1;
    if (wf.on) {
      x_.fo_wkind[wf.kind] += 1;
      x_.fo_wstart0 += wf.start_ip == 0;
      const int ip = prev_ip_[writer];
      if (ip >= 0) {
        x_.fo_wip[ip] += 1;
        const uint8_t* wb = w_.bytes_at(writer);
        if (wb[ip] == INERT || op_class(wb[ip]) != MOV) {
          x_.fo_not_mov += 1;
        } else {
          x_.fo_src_own += wb[wb[(ip + 1) % len_] % len_] == INERT;
        }
      }
    }
    std::string key(reinterpret_cast<const char*>(old), len_);
    for (int v : g_ref->volatile_offsets) key[v] = 0;
    const uint64_t dirs = pointer_dirs(key, trial_of(key).op_mask);
    uint64_t hit = 0;
    for (int k = 0; k < len_; ++k) {
      if (!(mask >> k & 1)) continue;
      x_.fo_off[k] += 1;
      if (old[k] == INERT && now[k] != INERT && (dirs >> k & 1)) {
        hit |= uint64_t{1} << k;
        x_.fo_dir_off[k] += 1;
      }
    }
    x_.fo_dir += hit != 0;
    x_.fo_dir_only += hit == mask;
  }

  void trace_birth(const World::Birth& b, int kind, const Fate& parent, const LastEnd& prev) {
    Fate& c = fate_[b.child];
    c.kind = kind;
    const bool off = c.start_ip != 0;
    if (kind == kCopy && parent.on) {
      const std::string pk = masked(w_, b.parent);
      const bool same = masked(w_, b.child) == pk;
      x_.cp_n += 1;
      x_.cp_same += same;
      if (!seedable(pk)) {
        x_.cp_unseeded += 1;
        x_.cp_unseeded_same += same;
      }
    }
    x_.all_births += 1;
    x_.all_off += off;
    if (kind == kCopy && parent.on && parent.status == kRep) {
      x_.re_copies[parent.start_ip != 0] += 1;
    }
    if (c.status != kRep) return;
    x_.rb[off][kind] += 1;
    if (!off) return;
    const int wc = kind == kSelfIgnite ? kWSelf
                   : parent.on ? parent.status : kWNone;
    x_.rb_ign[wc][parent.on ? age_bucket(w_.tick() - parent.born_at) : 0] += 1;
    const int ip = prev_ip_[b.parent];
    if (parent.on && ip >= 0) x_.rb_ign_ip[ip] += 1;
    x_.rb_entry[c.start_ip] += 1;
    x_.rb_same += masked(w_, b.parent) == masked(w_, b.child);
    if (prev.set && prev.status == kRep && prev.cause == kEndWick) {
      x_.rb_prev_wick[!prev.start0] += 1;
      x_.rb_prev_gap += w_.tick() - prev.tick;
    }
  }

  static void top(std::ostream& o, const char* name, const uint64_t* a, int n, int k) {
    std::multimap<uint64_t, int, std::greater<>> m;
    for (int i = 0; i < n; ++i) if (a[i]) m.insert({a[i], i});
    o << ' ' << name << ':';
    int shown = 0;
    for (auto [v, i] : m) {
      if (shown++ == k) break;
      o << ' ' << i << ':' << v;
    }
  }

  void print_trace(std::ostream& o) {
    const uint64_t tick = w_.tick();
    o << "# traceout tick=" << tick << " n=" << x_.fo_n << " victim_start0=" << x_.fo_victim_start0
      << " writer(status:age<1k/1k-10k/>=10k)";
    for (int k = 0; k < kWriters; ++k) {
      if (k == kWSelf) continue;
      o << ' ' << kWriterName[k] << ':' << x_.fo_writer[k][0] << '/' << x_.fo_writer[k][1] << '/'
        << x_.fo_writer[k][2];
    }
    o << " writer_kind(self/copy/reignite/seeded)=" << x_.fo_wkind[kSelfIgnite] << '/'
      << x_.fo_wkind[kCopy] << '/' << x_.fo_wkind[kReignite] << '/' << x_.fo_wkind[kKinds]
      << " writer_start0=" << x_.fo_wstart0 << " not_mov=" << x_.fo_not_mov
      << " src_own=" << x_.fo_src_own << " dir=" << x_.fo_dir << " dir_only=" << x_.fo_dir_only;
    top(o, "writer_ip", x_.fo_wip, 64, 10);
    top(o, "offsets", x_.fo_off, 64, 24);
    top(o, "dir_offsets", x_.fo_dir_off, 64, 10);
    o << std::endl;
    o << "# traceign tick=" << tick << " births=" << x_.all_births << " off0=" << x_.all_off
      << " rep_start0(self/copy/reignite)=" << x_.rb[0][kSelfIgnite] << '/' << x_.rb[0][kCopy] << '/'
      << x_.rb[0][kReignite] << " rep_off0(self/copy/reignite)=" << x_.rb[1][kSelfIgnite] << '/'
      << x_.rb[1][kCopy] << '/' << x_.rb[1][kReignite] << " igniter(status:age<1k/1k-10k/>=10k)";
    for (int k = 0; k < kWriters; ++k) {
      o << ' ' << kWriterName[k] << ':' << x_.rb_ign[k][0] << '/' << x_.rb_ign[k][1] << '/'
        << x_.rb_ign[k][2];
    }
    o << " same_key=" << x_.rb_same << " prev_rep_wick(start0/off0)=" << x_.rb_prev_wick[0] << '/'
      << x_.rb_prev_wick[1] << " prev_gap_sum=" << x_.rb_prev_gap;
    top(o, "igniter_ip", x_.rb_ign_ip, 64, 10);
    top(o, "entry", x_.rb_entry, 64, 12);
    o << std::endl;
    o << "# traceend tick=" << tick << " rep_start0: decay/wick=" << x_.re[0][kEndDecay] << '/'
      << x_.re[0][kEndWick] << " life_sum=" << x_.re_life[0] << " copies=" << x_.re_copies[0]
      << " rep_off0: decay/wick=" << x_.re[1][kEndDecay] << '/' << x_.re[1][kEndWick]
      << " life_sum=" << x_.re_life[1] << " copies=" << x_.re_copies[1] << std::endl;
    // Matter by holder: code bytes of active sites by status, and of inactive sites (with how
    // many of those carry a key already known as strict; no new trials).
    uint64_t act_bytes[kStatuses] = {}, act_sites[kStatuses] = {};
    uint64_t dead_sites = 0, dead_bytes = 0, dead_strict = 0, dead_strict_bytes = 0, dead_open0 = 0;
    for (int32_t s = 0; s < sites_; ++s) {
      const uint8_t* b = w_.bytes_at(s);
      const uint64_t n = static_cast<uint64_t>(
          std::count_if(b, b + len_, [](uint8_t v) { return v != INERT; }));
      if (n == 0) continue;
      if (w_.site_active(s) && fate_[s].on) {
        act_bytes[fate_[s].status] += n;
        act_sites[fate_[s].status] += 1;
        continue;
      }
      dead_sites += 1;
      dead_bytes += n;
      dead_open0 += b[0] == INERT;
      const std::string key = masked(w_, s);
      auto c = census_.find(key);
      const TrialResult* r = c != census_.end() ? &c->second : nullptr;
      if (!r) {
        auto it = cache_.find(key);
        if (it != cache_.end()) r = &it->second;
      }
      if (r && status_of(*r) == kRep) {
        dead_strict += 1;
        dead_strict_bytes += n;
      }
    }
    const Ledger l = w_.ledger();
    o << "# tracemass tick=" << tick << " free=" << l.free_mass << " code=" << l.code_mass
      << " wall=" << l.wall_mass << " active_bytes(rep/loose/prop/other)=";
    for (int st = 0; st < kStatuses; ++st) o << (st ? "/" : "") << act_bytes[st];
    o << " active_sites=";
    for (int st = 0; st < kStatuses; ++st) o << (st ? "/" : "") << act_sites[st];
    o << " inactive_sites=" << dead_sites << " inactive_bytes=" << dead_bytes
      << " inactive_open0=" << dead_open0 << " inactive_strict_key=" << dead_strict
      << " inactive_strict_bytes=" << dead_strict_bytes << std::endl;
    print_seed_limit(o, tick);
    x_ = TraceTally{};
  }

  // Active sites by status and by the non-inert bytes their key seeds in a trial; the sites
  // whose key exceeds mass0 (not seedable, so the census calls them non-replicators) with
  // their topped-up verdict; strict losses in place and copy births against the same limit.
  void print_seed_limit(std::ostream& o, uint64_t tick) {
    constexpr int kBins = 7;  // <=40, 41-44, 45-48, 49-52, 53-56, 57-60, 61-64
    uint64_t need[kStatuses][kBins] = {}, unseeded[kStatuses] = {};
    uint64_t topped[kStatuses] = {};
    std::set<std::string> keys;
    for (int32_t s = 0; s < sites_; ++s) {
      if (!w_.site_active(s) || !fate_[s].on) continue;
      const std::string key = masked(w_, s);
      const int st = fate_[s].status;
      const int n = census::trial_bytes(key, *g_ref);
      need[st][n <= 40 ? 0 : std::min(kBins - 1, (n - 41) / 4 + 1)] += 1;
      if (n <= w_.config().mass0) continue;
      unseeded[st] += 1;
      keys.insert(key);
      topped[topped_status(key)] += 1;
    }
    o << "# tracekey tick=" << tick << " mass0=" << w_.config().mass0
      << " bins=<=40,41-44,45-48,49-52,53-56,57-60,61-64";
    for (int st = 0; st < kStatuses; ++st) {
      o << ' ' << kStatusName[st] << "_bytes=";
      for (int k = 0; k < kBins; ++k) o << (k ? "/" : "") << need[st][k];
    }
    o << " unseeded_sites(rep/loose/prop/other)=";
    for (int st = 0; st < kStatuses; ++st) o << (st ? "/" : "") << unseeded[st];
    o << " unseeded_keys=" << keys.size() << " unseeded_topped(rep/loose/prop/other)=";
    for (int st = 0; st < kStatuses; ++st) o << (st ? "/" : "") << topped[st];
    o << " loss(self/foreign)=" << x_.lo_n[0] << '/' << x_.lo_n[1] << " loss_unseeded="
      << x_.lo_unseeded[0] << '/' << x_.lo_unseeded[1] << " loss_unseeded_topped_rep="
      << x_.lo_topped[0][kRep] << '/' << x_.lo_topped[1][kRep] << " copies=" << x_.cp_n
      << " copies_same=" << x_.cp_same << " copies_unseeded=" << x_.cp_unseeded
      << " copies_unseeded_same=" << x_.cp_unseeded_same << std::endl;
  }

  // A copy by a converted activation: is the child strict, a copy of the parent, or a copy of
  // the neighbor that the parent's source pointer names?
  void note_converted_copy(const World::Birth& b, const Fate& parent) {
    const std::string child = masked(w_, b.child);
    const bool rep = fate_[b.child].status == kRep;
    const bool same = child == masked(w_, b.parent);
    const uint8_t v = w_.bytes_at(b.parent)[src_ptr_];
    const bool src = v != INERT && child == masked(w_, neighbor_named(b.parent, v));
    t_.conv_copies += 1;
    t_.conv_child_rep += rep;
    t_.conv_child_same += same;
    t_.conv_child_src += src;
    if (!parent.fill) return;
    t_.fill_copies += 1;
    t_.fill_child_rep += rep;
    t_.fill_child_same += same;
    t_.fill_child_src += src;
  }

  // The neighbor that a non-inert pointer direction byte v names (torus, as World::pointer).
  int32_t neighbor_named(int32_t s, uint8_t v) const {
    const int dir = (v - 1) % kDirs;
    const Config& c = w_.config();
    static constexpr int kDx[kDirs] = {0, 1, 0, -1}, kDy[kDirs] = {-1, 0, 1, 0};
    const int x = s % c.width, y = s / c.width;
    return ((y + kDy[dir] + c.height) % c.height) * c.width + (x + kDx[dir] + c.width) % c.width;
  }
};

// Cumulative counters of the optional physics (hydro_whole, p_rot).
void print_physics(const World& w) {
  const Stats& s = w.stats();
  std::cout << "# physics tick=" << w.tick() << " whole_decays=" << s.whole_decays
            << " whole_decays_active=" << s.whole_decays_active << " wick=" << s.deaths_wick
            << " rotations=" << s.rotations << " rot_walled=" << s.rot_walled
            << " copies_started=" << s.copies_started << " copies_cut=" << s.copies_cut
            << " copies_born=" << s.copies_born << " copies_born_cut=" << s.copies_born_cut
            << " births=" << s.births;
  if (w.config().inert_operand == InertOperand::Fail) {
    std::cout << " operand_inert=" << s.operand_inert;
  }
  std::cout << std::endl;
}

void print_top_programs(const World& w) {
  std::map<std::string, int> counts;
  const int32_t n = w.config().width * w.config().height;
  for (int32_t s = 0; s < n; ++s) if (w.site_active(s)) counts[masked(w, s)] += 1;
  std::multimap<int, std::string, std::greater<>> top;
  for (auto& [t, c] : counts) top.insert({c, t});
  int shown = 0;
  for (auto& [c, t] : top) {
    if (shown++ == 3) break;
    std::vector<uint8_t> bytes(t.begin(), t.end());
    std::cout << "# " << c << " active, dist " << text_distance(bytes.data(), ref_program(), w.config().site_len)
              << ": " << disassemble(bytes) << '\n';
  }
}

} // namespace

int main(int argc, char** argv) {
  Config cfg;
  cfg.mass0 = 48;
  uint64_t ticks = 20000;
  bool rival = false;
  bool census = false;
  bool physics = false;  // print the physics counters even with hydro_whole and p_rot off
  uint64_t interval = 10000;
  std::vector<int> class_tables;  // classes=...: per-op class measures (needs census=1)
  uint64_t fidelity = 0;          // fidelity=W: copy-birth window before each checkpoint
  bool fate = false;              // fate=1: activation fates (needs census=1, p_rot 0)
  bool trace = false;             // trace=1: writers, igniters and matter (needs fate=1)
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    const auto eq = a.find('=');
    if (eq == std::string::npos || a.find(' ') != std::string::npos) {
      std::cerr << "bad argument (zsh needs ${=args}): " << a << '\n';
      return 1;
    }
    const std::string k = a.substr(0, eq), v = a.substr(eq + 1);
    if (k == "ticks") ticks = std::atoll(v.c_str());
    else if (k == "seed") cfg.seed = std::atoll(v.c_str());
    else if (k == "p_mut") cfg.p_mut = std::atof(v.c_str());
    else if (k == "p_hydro") cfg.p_hydro = std::atof(v.c_str());
    else if (k == "p_dead") cfg.p_dead = std::atof(v.c_str());
    else if (k == "dead_quiet") cfg.dead_quiet = std::atoi(v.c_str());
    else if (k == "hydro_whole") {
      if (!parse_whole(v, cfg.hydro_whole)) {
        std::cerr << "bad hydro_whole: " << v << '\n';
        return 1;
      }
    }
    else if (k == "p_rot") cfg.p_rot = std::atof(v.c_str());
    else if (k == "decay_table") cfg.decay_table = std::atoi(v.c_str());
    else if (k == "decay_ratio") cfg.decay_ratio = std::atof(v.c_str());
    else if (k == "classes") {
      std::stringstream list(v);
      std::string item;
      while (std::getline(list, item, ',')) class_tables.push_back(std::atoi(item.c_str()));
    }
    else if (k == "mass0") cfg.mass0 = std::atoi(v.c_str());
    else if (k == "rival") rival = v == "1";
    else if (k == "census") census = v == "1";
    else if (k == "physics") physics = v == "1";
    else if (k == "e_erase") cfg.e_erase = std::atoi(v.c_str());
    else if (k == "e_ignite") cfg.e_ignite = std::atoi(v.c_str());
    else if (k == "e_max") cfg.e_max = std::atoi(v.c_str());
    else if (k == "e_in") cfg.e_in = std::atoi(v.c_str());
    else if (k == "e_basal") cfg.e_basal = std::atoi(v.c_str());
    else if (k == "e_bond") cfg.e_bond = std::atoi(v.c_str());
    else if (k == "e_div") cfg.e_div = std::atoi(v.c_str());
    else if (k == "e_act") cfg.e_act = std::atoi(v.c_str());
    else if (k == "e_diffuse") cfg.e_diffuse = std::atoi(v.c_str()) != 0;
    else if (k == "bond_store") cfg.bond_store = std::atoi(v.c_str()) != 0;
    else if (k == "inert_operand") {
      if (!parse_inert_operand(v, cfg.inert_operand)) {
        std::cerr << "bad inert_operand: " << v << '\n';
        return 1;
      }
    }
    else if (k == "ext_write") {
      if (!parse_ext_write(v, cfg.ext_write)) {
        std::cerr << "bad ext_write: " << v << '\n';
        return 1;
      }
    }
    else if (k == "width") cfg.width = std::atoi(v.c_str());
    else if (k == "height") cfg.height = std::atoi(v.c_str());
    else if (k == "interval") interval = std::max<long long>(1, std::atoll(v.c_str()));
    else if (k == "fidelity") fidelity = std::max<long long>(0, std::atoll(v.c_str()));
    else if (k == "fate") fate = v == "1";
    else if (k == "trace") trace = v == "1";
    else if (k == "census_topup") g_census_topup = v == "1";
    else if (k == "anc") {
      g_ref = census::reference_named(v);
      if (!g_ref) {
        std::cerr << "bad anc: " << v << '\n';
        return 1;
      }
    }
    else {
      std::cerr << "unknown key: " << k << '\n';
      return 1;
    }
  }
  if (const char* e = decay_table_error(cfg)) {
    std::cerr << e << '\n';
    return 1;
  }
  if (!class_tables.empty() && !census) {
    std::cerr << "classes needs census=1\n";
    return 1;
  }
  if (fidelity > 0 && (!census || fidelity > interval)) {
    std::cerr << "fidelity needs census=1 and a window no longer than interval\n";
    return 1;
  }
  if (trace && !fate) {
    std::cerr << "trace needs fate=1\n";
    return 1;
  }
  if (fate && (!census || cfg.p_rot > 0.0)) {
    std::cerr << "fate needs census=1 and p_rot 0\n";
    return 1;
  }
  World w(cfg);
  const int ax = rival ? cfg.width / 4 : cfg.width / 2;
  w.seed_program(ax, cfg.height / 2, ref_program());
  if (rival) w.seed_program(3 * cfg.width / 4, cfg.height / 2, ancestor());
  const int L = cfg.site_len;
  std::vector<Record> recs;
  std::vector<int> current(cfg.width * cfg.height, -1); // record of the site's activation
  std::map<int, uint64_t> diff_at;                       // offset -> count of copy differences
  std::map<std::string, uint64_t> altered_kinds;         // parent text change -> births
  Window win;
  Stats prev_stats;
  ErrTally errs;
  std::map<std::string, TrialResult> census_cache;  // program text -> trial (census=1)
  FidWindow fid;
  std::unique_ptr<FateObserver> fates;
  if (fate) fates = std::make_unique<FateObserver>(w, census_cache, trace);
  std::cout << "tick\tactive\tbirths\texact%\tintact_parent%\ttop_count\ttop_dist\tdistinct"
               "\tcopies\treignites\tintact_copies\tblank\topen0\tdead\tpfx_active\tpfx_copies\text_erased\tstalls\tstarved\tenergy\n";
  const bool physics_line = physics || cfg.hydro_whole != Whole::Off || cfg.p_rot > 0.0;
  std::vector<int> moved(current.size(), -1);
  while (w.tick() < ticks && w.active_count() > 0) {
    w.run(1);
    // Rotations run at the start of a tick, before its births: records follow their sites.
    if (!w.moves_this_tick().empty()) {
      for (auto [from, to] : w.moves_this_tick()) moved[to] = current[from];
      for (const auto& m : w.moves_this_tick()) current[m.second] = moved[m.second];
    }
    if (w.tick() % interval == 0) {
      print_window(w, win, prev_stats);
      win = Window{};
      prev_stats = w.stats();
    }
    for (const auto& b : w.births_this_tick()) {
      Record r;
      r.born = w.tick();
      r.parent_intact = text_distance(w.bytes_at(b.parent), ref_program(), L) == 0;
      if (!r.parent_intact) {
        std::string sig;
        const uint8_t* pb = w.bytes_at(b.parent);
        for (int k = 0; k < L && sig.size() < 60; ++k) {
          const uint8_t ref = k < static_cast<int>(ref_program().size()) ? ref_program()[k] : INERT;
          if (!is_volatile(k) && pb[k] != ref) {
            sig += std::to_string(k) + ":" + std::to_string(ref) + ">" + std::to_string(pb[k]) + " ";
          }
        }
        altered_kinds[sig] += 1;
      }
      r.child_text = text_distance(w.bytes_at(b.child), ref_program(), L);
      for (int k = 0; k < L; ++k) {
        if (!is_volatile(k) && w.bytes_at(b.child)[k] != w.bytes_at(b.parent)[k]) {
          r.copy_diff += 1;
          diff_at[k] += 1;
        }
      }
      r.kind = classify(b);
      if (fidelity > 0 && (interval - w.tick() % interval) % interval < fidelity) {
        fid.all += 1;
        fid.kinds[r.kind] += 1;
        const bool sample = r.kind == kReignite && fid.reignites_seen++ < kReigniteSample;
        if (r.kind == kCopy || sample) fid.births.push_back(observe_fid(w, b, r.kind));
      }
      win.births += 1;
      win.exact += r.copy_diff == 0;
      win.intact += r.parent_intact;
      win.copies += r.kind == kCopy;
      win.reignites += r.kind == kReignite;
      win.intact_copies += r.kind == kCopy && r.parent_intact;
      win.pfx_copies += r.kind == kCopy && prefix_intact(w.bytes_at(b.parent));
      if (r.kind == kCopy && prefix_intact(w.bytes_at(b.parent))) tally_errors(w, b, L, errs);
      if (current[b.parent] >= 0) recs[current[b.parent]].offspring += 1;
      if (current[b.child] >= 0 && recs[current[b.child]].died == 0) recs[current[b.child]].died = w.tick();
      current[b.child] = static_cast<int>(recs.size());
      recs.push_back(r);
    }
    for (size_t s = 0; s < current.size(); ++s) {
      const int c = current[s];
      if (c >= 0 && recs[c].died == 0 && !w.site_active(static_cast<int32_t>(s))) recs[c].died = w.tick();
    }
    if (fates) fates->observe();
    if (census && w.tick() % interval == 0) {
      if (fates) fates->prime(census_cache);
      print_census(w, recs, current, census_cache);
      if (!class_tables.empty()) print_classes(w, census_cache, class_tables);
      if (fidelity > 0) {
        print_lineage(w, census_cache);
        print_fidelity(w, fid, fidelity, census_cache);
        fid = FidWindow{};
      }
      if (fates) fates->print(std::cout);
    }
    if (fidelity > 0 && (w.tick() + fidelity) % interval == 0) fid.start = w.stats();
    if (physics_line && w.tick() % interval == 0) print_physics(w);
  }
  Group g[2][kKinds];
  for (const Record& r : recs) {
    Group& x = g[r.parent_intact][r.kind];
    x.n += 1;
    x.lifespan += (r.died ? r.died : w.tick()) - r.born;
    x.fertile += r.offspring > 0;
    x.offspring += r.offspring;
    x.intact_child += r.child_text == 0;
    x.copy_diff += r.copy_diff;
  }
  for (int i = 1; i >= 0; --i) for (int k = 0; k < kKinds; ++k) {
    const Group& x = g[i][k];
    if (!x.n) continue;
    std::cout << (i ? "parent intact " : "parent altered") << ' ' << kKindName[k] << " births=" << x.n
              << " intact_child=" << 100.0 * x.intact_child / x.n << "%"
              << " mean_copy_diff=" << static_cast<double>(x.copy_diff) / x.n
              << " mean_life=" << x.lifespan / x.n
              << " fertile=" << 100.0 * x.fertile / x.n << "%\n";
  }
  std::cout << "copy differences by offset (top):";
  std::multimap<uint64_t, int, std::greater<>> top;
  for (auto [k, n] : diff_at) top.insert({n, k});
  int shown = 0;
  for (auto [n, k] : top) {
    if (shown++ == 12) break;
    std::cout << ' ' << k << ':' << n;
  }
  std::multimap<uint64_t, std::string, std::greater<>> kinds;
  for (auto& [sig, n] : altered_kinds) kinds.insert({n, sig});
  std::cout << "\naltered parents with most births (offset:ancestor>now):\n";
  shown = 0;
  for (auto& [n, sig] : kinds) {
    if (shown++ == 6) break;
    std::cout << "  " << n << "  " << sig << '\n';
  }
  print_errors(errs);
  print_top_programs(w);
  const Ledger l = w.ledger();
  std::cout << "final tick=" << w.tick() << " active=" << w.active_count()
            << " free=" << l.free_mass << " code=" << l.code_mass
            << " ext_blocked=" << w.stats().ext_blocked
            << " ext_erased=" << w.stats().ext_erasures << '\n';
  if (physics_line) print_physics(w);
  return 0;
}
