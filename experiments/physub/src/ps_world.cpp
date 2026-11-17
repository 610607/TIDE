// World construction, geometry, keyed randomness, ledger, digest, and the ancestor.

#include "ps_core.hpp"

#include <algorithm>
#include <sstream>

namespace ps {

namespace {

constexpr int8_t kDx[kDirs] = {0, 1, 0, -1};
constexpr int8_t kDy[kDirs] = {-1, 0, 1, 0};
constexpr uint64_t kGolden = 0x9e3779b97f4a7c15ULL;
constexpr uint64_t kFnvOffset = 14695981039346656037ULL;
constexpr uint64_t kFnvPrime = 1099511628211ULL;
constexpr double kTwoPow32 = 4294967296.0;
constexpr int64_t kNeverWritten = -(int64_t{1} << 40);

uint64_t mix(uint64_t z) {
  z += kGolden;
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
  return z ^ (z >> 31);
}

uint64_t threshold(double p) {
  if (p <= 0.0) return 0;
  if (p >= 1.0) return static_cast<uint64_t>(kTwoPow32);
  return static_cast<uint64_t>(p * kTwoPow32);
}

// Thresholds for whole-program decay by non-inert count n: 1 - (1 - r)^n, built by repeated
// multiplication so every platform gets the same values.
std::vector<uint64_t> whole_thresholds(double r, int len) {
  std::vector<uint64_t> t(static_cast<size_t>(len) + 1, 0);
  if (r <= 0.0) return t;
  double survive = 1.0;
  for (int n = 1; n <= len; ++n) {
    survive *= 1.0 - std::min(r, 1.0);
    t[n] = threshold(1.0 - survive);
  }
  return t;
}

void fnv(uint64_t& h, uint64_t v) {
  h ^= v;
  h *= kFnvPrime;
}

Config sanitize(Config cfg) {
  cfg.site_len = std::clamp(cfg.site_len, kMinSiteLen, kMaxSiteLen);
  cfg.d_div = std::max<int32_t>(cfg.d_div, 2 * kDirs);
  cfg.act_cap = std::max(cfg.act_cap, 1);
  cfg.dead_quiet = std::max<int32_t>(cfg.dead_quiet, 0);
  cfg.p_rot = std::clamp(cfg.p_rot, 0.0, 1.0);
  return cfg;
}

} // namespace

World::World(const Config& cfg) : cfg_(sanitize(cfg)) {
  const size_t sites = static_cast<size_t>(cfg_.width) * cfg_.height;
  code_.assign(sites * cfg_.site_len, INERT);
  free_.assign(sites, cfg_.mass0);
  energy_.assign(sites, std::min(cfg_.e0, cfg_.e_max));
  wall_.assign(sites * kDirs, 0);
  act_.assign(sites * cfg_.act_cap, Activation{});
  fresh_.assign(act_.size(), false);
  lineage_.assign(sites, 0);
  writer_.assign(code_.size(), -1);
  written_at_.assign(code_.size(), 0);
  ignited_at_.assign(sites, -1);
  last_write_.assign(sites, kNeverWritten);
  body_.resize(sites);
  for (size_t s = 0; s < sites; ++s) body_[s] = static_cast<int32_t>(s);
  copy_to_.assign(sites, -1);
  copy_dir_.assign(sites, kSelf);
  copy_cut_.assign(sites, 0);
  mass_total_ = static_cast<int64_t>(sites) * cfg_.mass0;
  energy_initial_ = static_cast<int64_t>(sites) * energy_[0];
  t_hydro_ = threshold(cfg_.p_hydro);
  t_dead_ = cfg_.p_dead < 0.0 ? t_hydro_ : threshold(cfg_.p_dead);
  t_erode_ = threshold(cfg_.p_erode);
  t_mut_ = threshold(cfg_.p_mut);
  if (cfg_.hydro_whole) {
    t_whole_ = whole_thresholds(cfg_.p_hydro, cfg_.site_len);
    t_whole_dead_ = whole_thresholds(cfg_.p_dead < 0.0 ? cfg_.p_hydro : cfg_.p_dead,
                                     cfg_.site_len);
  }
  t_rot_ = threshold(cfg_.p_rot / 2.0);
}

int32_t World::neighbor(int32_t site, uint8_t dir) const {
  const int x = site % cfg_.width;
  const int y = site / cfg_.width;
  const int nx = (x + kDx[dir] + cfg_.width) % cfg_.width;
  const int ny = (y + kDy[dir] + cfg_.height) % cfg_.height;
  return ny * cfg_.width + nx;
}

uint8_t World::wrap(int v) const {
  const int len = cfg_.site_len;
  return static_cast<uint8_t>(((v % len) + len) % len);
}

int32_t World::edge_wall(int32_t site, uint8_t dir) const {
  const int32_t other = neighbor(site, dir);
  const uint8_t back = static_cast<uint8_t>((dir + 2) % kDirs);
  return wall_[site * kDirs + dir] + wall_[other * kDirs + back];
}

uint64_t World::key(uint64_t stream, uint64_t a, uint64_t b) const {
  uint64_t h = mix(cfg_.seed ^ (stream * kGolden));
  h = mix(h ^ tick_);
  h = mix(h ^ a);
  return mix(h ^ b);
}

// Passive reciprocity: a crossing through total wall W succeeds with probability 1/(W+1).
bool World::crosses(int32_t site, uint8_t dir, uint64_t stream, uint64_t id) const {
  const int32_t w = edge_wall(site, dir);
  if (w == 0) return true;
  return key(stream, id, static_cast<uint64_t>(site) * kDirs + dir) % (w + 1) == 0;
}

bool World::seed_program(int x, int y, const std::vector<uint8_t>& program) {
  if (x < 0 || x >= cfg_.width || y < 0 || y >= cfg_.height) return false;
  if (program.size() > static_cast<size_t>(cfg_.site_len)) return false;
  const int32_t site = site_index(x, y);
  // Seeded code is assembled from the site's free monomers so the ledger stays closed.
  const int32_t slot = free_slot(site);
  if (active_at(site) > 0 || slot < 0 || !place_bytes(site, program)) return false;
  act_[slot] = Activation{true, 0};
  lineage_[site] = next_lineage_++;
  ignited_at_[site] = static_cast<int64_t>(tick_);
  return true;
}

int World::first_ip(int32_t site) const {
  for (int k = 0; k < cfg_.act_cap; ++k) {
    const Activation& a = act_[site * cfg_.act_cap + k];
    if (a.on) return a.ip;
  }
  return -1;
}

// Test and seeding helper: replaces a site's bytes, settling the difference in monomers.
bool World::place_bytes(int32_t site, const std::vector<uint8_t>& program) {
  if (program.size() > static_cast<size_t>(cfg_.site_len)) return false;
  int32_t need = 0;
  for (uint8_t b : program) need += (b != INERT);
  for (int i = 0; i < cfg_.site_len; ++i) need -= (site_ptr(site)[i] != INERT);
  if (free_[site] < need) return false;
  free_[site] -= need;
  if (cfg_.bond_store) energy_initial_ += static_cast<int64_t>(need) * cfg_.e_bond;
  std::fill(site_ptr(site), site_ptr(site) + cfg_.site_len, INERT);
  std::copy(program.begin(), program.end(), site_ptr(site));
  return true;
}

void World::set_free_mass(int32_t site, int32_t v) {
  mass_total_ += v - free_[site];
  free_[site] = v;
}

void World::set_energy(int32_t site, int32_t v) {
  energy_initial_ += v - energy_[site];
  energy_[site] = v;
}

void World::set_wall(int32_t site, uint8_t dir, uint8_t units) {
  // Test helper: places wall units directly and adjusts the closed mass total to match.
  mass_total_ += static_cast<int64_t>(units) - wall_[site * kDirs + dir];
  wall_[site * kDirs + dir] = units;
}

std::vector<uint8_t> World::site_bytes(int32_t site) const {
  const uint8_t* p = site_ptr(site);
  return std::vector<uint8_t>(p, p + cfg_.site_len);
}

Ledger World::ledger() const {
  Ledger l;
  for (int32_t v : free_) l.free_mass += v;
  for (uint8_t b : code_) l.code_mass += (b != INERT);
  for (uint8_t w : wall_) l.wall_mass += w;
  for (int32_t e : energy_) l.energy += e;
  if (cfg_.bond_store) l.bond_energy = l.code_mass * cfg_.e_bond;
  return l;
}

bool World::ledger_ok() const {
  const Ledger l = ledger();
  const bool mass = l.total_mass() == mass_total_;
  const bool energy = l.energy + l.bond_energy == energy_initial_ + energy_in_ - energy_spent_;
  bool nonneg = true;
  for (int32_t v : free_) nonneg = nonneg && v >= 0;
  for (int32_t e : energy_) nonneg = nonneg && e >= 0;
  return mass && energy && nonneg;
}

uint64_t World::digest() const {
  uint64_t h = kFnvOffset;
  fnv(h, tick_);
  for (uint8_t b : code_) fnv(h, b);
  for (int32_t v : free_) fnv(h, static_cast<uint32_t>(v));
  for (int32_t e : energy_) fnv(h, static_cast<uint32_t>(e));
  for (uint8_t w : wall_) fnv(h, w);
  for (const Activation& t : act_) {
    fnv(h, t.on);
    fnv(h, t.ip);
  }
  // Only dynamic state when dead_quiet is on; skipping it otherwise keeps earlier digests.
  if (cfg_.dead_quiet > 0) {
    for (int64_t t : last_write_) fnv(h, static_cast<uint64_t>(t));
  }
  return h;
}

namespace {
constexpr uint8_t op(Op o) { return static_cast<uint8_t>(o + 1); }
} // namespace

const std::vector<uint8_t>& ancestor() {
  // Self-copier for site_len 64 (256 must be a multiple of site_len). The source and
  // destination offsets count 192..255 and wrap to 0 (INERT), which ends the loop and
  // leaves the destination pointing at offset 0 of the copy.
  //  0 MOV 27 29   so = K           (pointer 27 -> K, pointer 29 -> so)
  //  3 MOV 27 31   do = K
  //  6 RND 25      random direction (non-inert = a neighbor)
  //  8 MOV 23 25   copy loop: src pointer (23) -> dst pointer (25)
  // 11 INC 24      so++
  // 13 INC 26      do++
  // 15 JZ 26       do wrapped to 0: skip the jump back
  // 17 JMP 33      ip = 8
  // 19 IGNITE 25   excite the copy at offset 0
  // 21 JMP 23      ip = [23] = 0
  // 23 . so        src pointer (own site)      25 dd do  dst pointer
  // 27 . 34        pointer -> K               29 . 24   pointer -> so
  // 31 . 26        pointer -> do              33 8      loop address    34 192 K
  constexpr uint8_t kStart = 192;
  static const std::vector<uint8_t> kAncestor = {
      op(MOV), 27, 29, op(MOV), 27, 31, op(RND), 25,
      op(MOV), 23, 25, op(INC), 24, op(INC), 26, op(JZ), 26, op(JMP), 33,
      op(IGNITE), 25, op(JMP), 23,
      INERT, kStart, 1, kStart, INERT, 34, INERT, 24, INERT, 26, 8, kStart};
  return kAncestor;
}

// Polite copier: reads byte 0 of the target into a probe cell and copies only if it is
// INERT; otherwise it draws a new direction. Built from the same nine instructions.
//  0 MOV 34 36  so = K        3 MOV 34 38  do = K        6 RND 32   direction
//  8 MOV 32 40  probe = target[0]   11 JZ 44 (empty: skip)   13 JMP 45 -> 6
// 15 MOV 30 32  copy   18 INC 31   20 INC 33   22 JZ 33   24 JMP 43 -> 15
// 26 IGNITE 32   28 JMP 30 -> 0
// data: 30 . so | 32 dd do | 34 . 42 (->K) | 36 . 31 (->so) | 38 . 33 (->do)
//       40 . 44 (->probe) | 42 K=192 | 43 15 | 44 probe | 45 6
const std::vector<uint8_t>& polite() {
  static const std::vector<uint8_t> kPolite = {
    op(MOV), 34, 36, op(MOV), 34, 38, op(RND), 32, op(MOV), 32, 40, op(JZ), 44,
    op(JMP), 45, op(MOV), 30, 32, op(INC), 31, op(INC), 33, op(JZ), 33, op(JMP), 43,
    op(IGNITE), 32, op(JMP), 30,
    INERT, 192, 1, 192, INERT, 42, INERT, 31, INERT, 33, INERT, 44, 192, 15, INERT, 6};

  return kPolite;
}

std::string disassemble(const std::vector<uint8_t>& bytes) {
  static constexpr const char* kNames[kOps] = {
      "mov", "inc", "dec", "jz", "jmp", "rnd", "ignite", "wall", "unwall"};
  std::ostringstream oss;
  for (size_t i = 0; i < bytes.size(); ++i) {
    oss << (i ? " " : "");
    if (bytes[i] == INERT) oss << '.';
    else oss << static_cast<int>(bytes[i]) << ':' << kNames[(bytes[i] - 1) % kOps];
  }
  return oss.str();
}

} // namespace ps
