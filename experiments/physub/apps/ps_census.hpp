// Replicator census shared by ps_probe and ps_scan: genotype keys and the isolated trial.
// Observation only: trial worlds never touch a run's world.

#pragma once

#include "ps_core.hpp"

#include <algorithm>
#include <string>
#include <vector>

namespace ps::census {

// A seeded program and the offsets it rewrites while it runs (counters, direction, probe).
// Those offsets are masked out of genotype keys and reset to the program's values in
// trials. ops: offsets of the program's opcode bytes.
struct Reference {
  std::string name;
  const std::vector<uint8_t>* program = nullptr;
  std::vector<int> volatile_offsets;
  std::vector<int> ops;

  bool is_volatile(int k) const {
    return std::find(volatile_offsets.begin(), volatile_offsets.end(), k) !=
           volatile_offsets.end();
  }
};

// "polite" or "copier" (ancestor()); nullptr for any other name.
inline const Reference* reference_named(const std::string& name) {
  static const Reference kPolite{"polite", &polite(), {31, 32, 33, 44},
                                 {0, 3, 6, 8, 11, 13, 15, 18, 20, 22, 24, 26, 28}};
  static const Reference kCopier{"copier", &ancestor(), {24, 25, 26},
                                 {0, 3, 6, 8, 11, 13, 15, 17, 19, 21}};
  if (name == kPolite.name) return &kPolite;
  if (name == kCopier.name) return &kCopier;
  return nullptr;
}

// Genotype key: the site's bytes with the reference's volatile offsets zeroed.
inline std::string masked(const World& w, int32_t s, const Reference& ref) {
  std::string t(reinterpret_cast<const char*>(w.bytes_at(s)), w.config().site_len);
  for (int v : ref.volatile_offsets) t[v] = 0;
  return t;
}

// Self: the parent re-ignites its own site. Copy: most of the child's code was written by
// the parent since the child's last ignition. Reignite: the child's code was already there.
enum Kind { kSelfIgnite = 0, kCopy = 1, kReignite = 2, kKinds = 3 };

inline int classify(const World::Birth& b) {
  if (b.parent == b.child) return kSelfIgnite;
  return b.code > 0 && 2 * b.written >= b.code ? kCopy : kReignite;
}

// Sources of the offsets where a child differs from its parent at birth (volatile offsets
// excluded). The observer records writers by site (World::Birth), not by activation:
//   written: last written from the parent's site since the child's previous ignition (by the
//            parent, or by an earlier occupant of that site);
//   foreign: last written from another site in that time;
//   residue: not written in that time and non-inert in the child (left by an earlier occupant,
//            for instance where a fill-mode write was refused);
//   gap:     not written in that time and inert in the child (the copy did not reach the
//            offset, or the write failed: no free monomer, a wall, or a lost conflict).
// The birth's class: env when any difference is foreign or residue; else multi when at least
// kMultiMin differences are written (not copy errors alone: with copy error u per byte and
// m copied bytes, three or more errors in one copy have probability ~C(m,3)u^3, 2.7e-4 at
// u = 0.003 and m = 40; a misaligned copy, or writes left by an earlier occupant of the
// parent's site); else gap when any is gap; else point when any is written (one or two copy
// errors); else exact.
enum DiffSrc { kSrcWritten = 0, kSrcForeign, kSrcResidue, kSrcGap, kDiffSrcs };
inline constexpr const char* kDiffSrcName[kDiffSrcs] = {"written", "foreign", "residue", "gap"};
enum DiffClass { kClsExact = 0, kClsPoint, kClsGap, kClsMulti, kClsEnv, kDiffClasses };
inline constexpr const char* kDiffClsName[kDiffClasses] = {"exact", "point", "gap", "multi",
                                                           "env"};
constexpr int kMultiMin = 3;

struct Diff {
  int n[kDiffSrcs] = {};
  int cls = kClsExact;
};

inline Diff diff_sources(const World& w, const World::Birth& b, const Reference& ref) {
  Diff d;
  const uint8_t* c = w.bytes_at(b.child);
  const uint8_t* p = w.bytes_at(b.parent);
  for (int k = 0; k < w.config().site_len; ++k) {
    if (ref.is_volatile(k) || c[k] == p[k]) continue;
    const uint64_t bit = uint64_t{1} << k;
    if (b.by_other & bit) d.n[kSrcForeign] += 1;
    else if (b.by_parent & bit) d.n[kSrcWritten] += 1;
    else if (c[k] != INERT) d.n[kSrcResidue] += 1;
    else d.n[kSrcGap] += 1;
  }
  if (d.n[kSrcForeign] + d.n[kSrcResidue] > 0) d.cls = kClsEnv;
  else if (d.n[kSrcWritten] >= kMultiMin) d.cls = kClsMulti;
  else if (d.n[kSrcGap] > 0) d.cls = kClsGap;
  else if (d.n[kSrcWritten] > 0) d.cls = kClsPoint;
  return d;
}

// Offsets inside the reference program that are inert there and not volatile: pointer
// directions that mean "own site". A fill-mode write from a neighbor can make them non-inert.
inline bool ref_inert_filled(const uint8_t* bytes, const Reference& ref) {
  const auto& p = *ref.program;
  for (int k = 0; k < static_cast<int>(p.size()); ++k) {
    if (p[k] == INERT && !ref.is_volatile(k) && bytes[k] != INERT) return true;
  }
  return false;
}

// Trial: the program, with the volatile offsets reset to the reference's values, is seeded
// alone in a fresh 9x9 world with the run's physics but no mutation, hydrolysis, erosion,
// p_dead or rotation. It is a replicator when at least two active sites carry its key after
// kTrialTicks. ip_span: distinct offsets the founder's ip visits in the last kSpanTicks (-1
// if the founder stopped). op_mask: offsets where the founder executed an instruction.
// depth: longest chain of copy births from the founder (a child of the founder is 1, a
// grandchild 2); other births pass the parent's generation on unchanged. founder_copies:
// copy births by the founder; founder_exact: those whose child carries the tested key. A
// strict replicator is a replicator all of whose founder copies are exact (the two-carrier
// test alone passes a program whose first copy is exact and later ones are not).
constexpr int kTrialSize = 9;
constexpr uint64_t kTrialTicks = 2000;
constexpr uint64_t kSpanTicks = 500;

struct TrialResult {
  bool replicator = false;
  int ip_span = -1;
  uint64_t op_mask = 0;
  int depth = 0;
  int founder_copies = 0, founder_exact = 0;

  bool strict() const {
    return replicator && founder_copies > 0 && founder_exact == founder_copies;
  }
};

inline TrialResult run_trial(const Config& run_cfg, const std::string& key,
                             const Reference& ref) {
  Config c = run_cfg;
  c.width = kTrialSize;
  c.height = kTrialSize;
  c.p_mut = 0.0;
  c.p_hydro = 0.0;
  c.p_erode = 0.0;
  c.p_dead = 0.0;
  c.dead_quiet = 0;
  c.p_rot = 0.0;
  c.seed = 1;
  World t(c);
  TrialResult r;
  std::vector<uint8_t> program(key.begin(), key.end());
  for (int v : ref.volatile_offsets) program[v] = (*ref.program)[v];
  const int32_t center = t.site_index(kTrialSize / 2, kTrialSize / 2);
  if (!t.seed_program(kTrialSize / 2, kTrialSize / 2, program)) return r;
  std::vector<bool> visited(c.site_len, false);
  std::vector<int> gen(kTrialSize * kTrialSize, 0);
  for (uint64_t k = 0; k < kTrialTicks; ++k) {
    // Nothing can ignite once no site is active, so the result is final (a speed-up only).
    if (t.active_count() == 0) break;
    const int at = t.first_ip(center);  // the instruction this tick executes
    if (at >= 0) r.op_mask |= uint64_t{1} << at;
    t.run(1);
    for (const auto& b : t.births_this_tick()) {
      const bool copy = classify(b) == kCopy;
      gen[b.child] = gen[b.parent] + copy;
      r.depth = std::max(r.depth, gen[b.child]);
      if (copy && b.parent == center) {
        r.founder_copies += 1;
        r.founder_exact += masked(t, b.child, ref) == key;
      }
    }
    if (k < kTrialTicks - kSpanTicks) continue;
    const int ip = t.first_ip(center);
    if (ip >= 0) visited[ip] = true;
  }
  if (t.site_active(center)) {
    r.ip_span = 0;
    for (bool v : visited) r.ip_span += v;
  }
  int carriers = 0;
  for (int32_t s = 0; s < kTrialSize * kTrialSize; ++s) {
    carriers += t.site_active(s) && masked(t, s, ref) == key;
  }
  r.replicator = carriers >= 2;
  return r;
}

} // namespace ps::census
