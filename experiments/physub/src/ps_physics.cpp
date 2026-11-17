// Spontaneous processes run by the kernel each tick: conservative diffusion of free
// monomers, hydrolysis of code, wall erosion, energy inflow, and block rotation of sites.

#include "ps_core.hpp"

#include <algorithm>
#include <cstdlib>

namespace ps {

namespace {

constexpr uint8_t kEast = 1;
constexpr uint8_t kSouth = 2;
constexpr uint8_t kWest = 3;
constexpr uint8_t kNorth = 0;
constexpr int kEdgesPerSite = 2; // each site stores its east and south edges

} // namespace

// Antisymmetric integer flux with keyed stochastic rounding. For an edge with gradient
// delta and total wall W the expected flux is |delta| / (d_div * (1 + W)); the fractional
// part rounds up with matching probability using one draw shared by both sides, so mass is
// conserved exactly. A positivity guard trims a site's outgoing fluxes, in keyed order,
// when rounding would send out more than the site holds.
void World::diffuse() {
  diffuse_field(free_, cfg_.d_div, kDiffuse, kGuard);
  if (cfg_.e_diffuse) diffuse_field(energy_, cfg_.e_div, kEDiffuse, kEGuard);
}

void World::diffuse_field(std::vector<int32_t>& field, int32_t div, Stream flux_stream,
                          Stream guard_stream) {
  const int32_t sites = cfg_.width * cfg_.height;
  std::vector<int32_t> flux(static_cast<size_t>(sites) * kEdgesPerSite, 0);
  for (int32_t u = 0; u < sites; ++u) {
    for (int k = 0; k < kEdgesPerSite; ++k) {
      const uint8_t dir = k == 0 ? kEast : kSouth;
      const int32_t v = neighbor(u, dir);
      const int32_t delta = field[u] - field[v];
      if (delta == 0) continue;
      const int64_t denom = static_cast<int64_t>(div) * (1 + edge_wall(u, dir));
      const int64_t mag = std::llabs(delta);
      int64_t q = mag / denom;
      const int64_t r = mag % denom;
      const uint64_t edge = static_cast<uint64_t>(u) * kEdgesPerSite + k;
      if (r > 0 && static_cast<int64_t>(key(flux_stream, edge) % denom) < r) q += 1;
      flux[edge] = static_cast<int32_t>(delta > 0 ? q : -q); // positive: u -> v
    }
  }
  // Positivity guard: outgoing flux of a site never exceeds its start-of-tick stock.
  for (int32_t u = 0; u < sites; ++u) {
    struct Out { uint64_t key; size_t edge; };
    Out outs[kDirs];
    int n = 0;
    int64_t total = 0;
    const size_t own_e = static_cast<size_t>(u) * kEdgesPerSite;
    const size_t own_s = own_e + 1;
    const size_t west = static_cast<size_t>(neighbor(u, kWest)) * kEdgesPerSite;
    const size_t north = static_cast<size_t>(neighbor(u, kNorth)) * kEdgesPerSite + 1;
    for (size_t e : {own_e, own_s}) {
      if (flux[e] > 0) { outs[n++] = {key(guard_stream, e), e}; total += flux[e]; }
    }
    for (size_t e : {west, north}) {
      if (flux[e] < 0) { outs[n++] = {key(guard_stream, e), e}; total -= flux[e]; }
    }
    if (total <= field[u]) continue;
    std::sort(outs, outs + n, [](const Out& a, const Out& b) {
      return a.key != b.key ? a.key < b.key : a.edge < b.edge;
    });
    int64_t budget = field[u];
    for (int i = 0; i < n; ++i) {
      const int32_t f = std::abs(flux[outs[i].edge]);
      const int32_t allowed = static_cast<int32_t>(std::min<int64_t>(f, budget));
      budget -= allowed;
      flux[outs[i].edge] = flux[outs[i].edge] > 0 ? allowed : -allowed;
    }
  }
  for (int32_t u = 0; u < sites; ++u) {
    for (int k = 0; k < kEdgesPerSite; ++k) {
      const int32_t f = flux[static_cast<size_t>(u) * kEdgesPerSite + k];
      if (f == 0) continue;
      const int32_t v = neighbor(u, k == 0 ? kEast : kSouth);
      field[u] -= f;
      field[v] += f;
    }
  }
}

void World::hydrolyze() {
  if (t_hydro_ == 0 && t_dead_ == 0) return;
  if (cfg_.hydro_whole) {
    hydrolyze_whole();
    return;
  }
  const int32_t sites = cfg_.width * cfg_.height;
  for (int32_t s = 0; s < sites; ++s) {
    // Same keyed draw for every site; only the threshold depends on activation and, with
    // dead_quiet, on how recently a write reached the site.
    const bool active = site_active(s);
    const bool recent = cfg_.dead_quiet > 0 &&
        static_cast<int64_t>(tick_) - last_write_[s] <= cfg_.dead_quiet;
    const uint64_t t = active || recent ? t_hydro_ : t_dead_;
    if (t == 0) continue;
    uint8_t* mem = site_ptr(s);
    for (int o = 0; o < cfg_.site_len; ++o) {
      if (mem[o] == INERT) continue;
      if ((key(kHydro, static_cast<uint64_t>(s), static_cast<uint64_t>(o)) >> 32) < t) {
        mem[o] = INERT;
        free_[s] += 1;
        if (cfg_.bond_store) energy_[s] += cfg_.e_bond; // released in place
        stats_.hydrolyzed += 1;
      }
    }
  }
}

// Form M: one keyed draw per site with code; the site's rate (p_hydro, or p_dead for an
// inactive site) is chosen as in form P. The activation ends at the wick check.
void World::hydrolyze_whole() {
  const int32_t sites = cfg_.width * cfg_.height;
  for (int32_t s = 0; s < sites; ++s) {
    uint8_t* mem = site_ptr(s);
    int n = 0;
    for (int o = 0; o < cfg_.site_len; ++o) n += mem[o] != INERT;
    if (n == 0) continue;
    const bool active = site_active(s);
    const bool recent = cfg_.dead_quiet > 0 &&
        static_cast<int64_t>(tick_) - last_write_[s] <= cfg_.dead_quiet;
    const uint64_t t = (active || recent ? t_whole_ : t_whole_dead_)[n];
    if (t == 0 || (key(kWhole, static_cast<uint64_t>(s)) >> 32) >= t) continue;
    std::fill(mem, mem + cfg_.site_len, INERT);
    free_[s] += n;
    if (cfg_.bond_store) energy_[s] += n * cfg_.e_bond;
    stats_.hydrolyzed += static_cast<uint64_t>(n);
    stats_.whole_decays += 1;
    stats_.whole_decays_active += active;
  }
}

void World::erode() {
  if (t_erode_ == 0) return;
  const int32_t sites = cfg_.width * cfg_.height;
  for (int32_t s = 0; s < sites; ++s) {
    for (uint8_t d = 0; d < kDirs; ++d) {
      uint8_t& w = wall_[s * kDirs + d];
      if (w == 0) continue;
      if ((key(kErode, static_cast<uint64_t>(s), d) >> 32) < t_erode_) {
        w -= 1;
        free_[s] += 1; // a wall unit returns to the site that deposited it
        stats_.eroded += 1;
      }
    }
  }
}

// Margolus block rotation (Boerlijst and Hogeweg 1991, pp. 18-19; per-block probability as
// in Kulagin and Shapovalov 2023). Blocks are (x0, y0) .. (x0 + 1, y0 + 1) with x0 = o + 2i,
// y0 = o + 2j and o = tick parity; on an odd side the leftover row or column stays. Corners
// a (top left), b (top right), c (bottom right), d (bottom left); clockwise moves the
// contents a->b->c->d->a. The ledger is unchanged because sites are only permuted.
void World::rotate_blocks() {
  moves_log_.clear();
  if (t_rot_ == 0) return;
  const int w = cfg_.width;
  const int h = cfg_.height;
  const int o = static_cast<int>(tick_ % 2);
  for (int j = 0; j < h / 2; ++j) {
    for (int i = 0; i < w / 2; ++i) {
      const int x0 = (o + 2 * i) % w, x1 = (x0 + 1) % w;
      const int y0 = (o + 2 * j) % h, y1 = (y0 + 1) % h;
      const int32_t a = site_index(x0, y0), b = site_index(x1, y0);
      const int32_t c = site_index(x1, y1), d = site_index(x0, y1);
      const uint64_t u = key(kRotate, static_cast<uint64_t>(a)) >> 32;
      if (u >= 2 * t_rot_) continue;
      const uint64_t id = static_cast<uint64_t>(a);
      if (!crosses(a, kEast, kRotWall, id) || !crosses(b, kSouth, kRotWall, id) ||
          !crosses(d, kEast, kRotWall, id) || !crosses(a, kSouth, kRotWall, id)) {
        stats_.rot_walled += 1;
        continue;
      }
      if (u < t_rot_) {
        const int32_t cycle[4] = {a, b, c, d};
        move_cycle(cycle);
      } else {
        const int32_t cycle[4] = {a, d, c, b};
        move_cycle(cycle);
      }
      stats_.rotations += 1;
    }
  }
  if (!moves_log_.empty()) check_copy_cuts();
}

// Contents of s[0] move to s[1], s[1] to s[2], s[2] to s[3], s[3] to s[0].
void World::move_cycle(const int32_t (&s)[4]) {
  auto cycle = [&](auto& v, size_t stride) {
    for (size_t k = 0; k < stride; ++k) {
      auto tmp = v[s[3] * stride + k];
      v[s[3] * stride + k] = v[s[2] * stride + k];
      v[s[2] * stride + k] = v[s[1] * stride + k];
      v[s[1] * stride + k] = v[s[0] * stride + k];
      v[s[0] * stride + k] = tmp;
    }
  };
  const size_t len = static_cast<size_t>(cfg_.site_len);
  cycle(code_, len);
  cycle(writer_, len);
  cycle(written_at_, len);
  cycle(act_, static_cast<size_t>(cfg_.act_cap));
  cycle(lineage_, 1);
  cycle(ignited_at_, 1);
  cycle(last_write_, 1);
  cycle(body_, 1);
  cycle(copy_to_, 1);
  cycle(copy_dir_, 1);
  cycle(copy_cut_, 1);
  for (int k = 0; k < 4; ++k) moves_log_.push_back({s[k], s[(k + 1) % 4]});
}

// A copy is cut when its target no longer lies in the direction it was written through.
void World::check_copy_cuts() {
  const int32_t sites = cfg_.width * cfg_.height;
  for (int32_t s = 0; s < sites; ++s) {
    if (copy_to_[s] < 0 || copy_cut_[s]) continue;
    if (body_[neighbor(s, copy_dir_[s])] != copy_to_[s]) {
      copy_cut_[s] = 1;
      stats_.copies_cut += 1;
    }
  }
}

void World::feed_energy() {
  for (int32_t& e : energy_) {
    const int32_t add = std::max(0, std::min(cfg_.e_in, cfg_.e_max - e));
    e += add;
    energy_in_ += add;
  }
}

} // namespace ps
