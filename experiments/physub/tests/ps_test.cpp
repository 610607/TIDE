// Mechanism checks for the physical-substrate prototype.

#include "ps_core.hpp"

#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace ps;

namespace {

Config small_config() {
  Config cfg;
  cfg.width = 16;
  cfg.height = 16;
  cfg.seed = 7;
  return cfg;
}

// Matter and energy ledgers stay exact every tick with every stochastic process on.
void test_ledgers_exact() {
  Config cfg = small_config();
  cfg.p_mut = 0.01;
  cfg.p_hydro = 1e-5;
  cfg.p_erode = 1e-2;
  World w(cfg);
  assert(w.seed_program(8, 8, ancestor()));
  w.set_wall(w.site_index(3, 3), 1, 5);
  const uint64_t kTicks = 3000;
  for (uint64_t t = 0; t < kTicks; ++t) {
    w.run(1);
    assert(w.ledger_ok());
  }
  std::cout << "[ps test 1] ledgers exact for " << kTicks << " ticks; active="
            << w.active_count() << " births=" << w.stats().births
            << " hydrolyzed=" << w.stats().hydrolyzed << "\n";
}

// Same seed and configuration reproduce the same state; another seed does not.
void test_deterministic_replay() {
  Config cfg = small_config();
  cfg.p_mut = 0.01;
  const uint64_t kTicks = 2000;
  World a(cfg), b(cfg);
  a.seed_program(8, 8, ancestor());
  b.seed_program(8, 8, ancestor());
  a.run(kTicks);
  b.run(kTicks);
  assert(a.digest() == b.digest());
  Config other = cfg;
  other.seed += 1;
  World c(other);
  c.seed_program(8, 8, ancestor());
  c.run(kTicks);
  assert(a.digest() != c.digest());
  std::cout << "[ps test 2] digest=" << std::hex << a.digest() << std::dec << "\n";
}

// Diffusion conserves mass, keeps stocks non-negative, and walls slow but never seal.
int64_t leaked_after(bool walled, uint64_t ticks) {
  Config cfg = small_config();
  cfg.mass0 = 0;
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  World w(cfg);
  const int32_t center = w.site_index(8, 8);
  const int32_t kStock = 4000;
  w.set_free_mass(center, kStock);
  if (walled) {
    for (uint8_t d = 0; d < kDirs; ++d) w.set_wall(center, d, cfg.w_max);
  }
  for (uint64_t t = 0; t < ticks; ++t) {
    w.run(1);
    assert(w.ledger_ok());
  }
  return kStock - w.free_mass(center);
}

void test_diffusion_and_leaky_walls() {
  const uint64_t kTicks = 1;  // first-tick flux, before the gradient relaxes
  const int64_t open = leaked_after(false, kTicks);
  const int64_t walled = leaked_after(true, kTicks);
  assert(open > 0);
  assert(walled > 0);       // no perfect seal
  assert(4 * walled < open); // walls of total W cut flux about (W + 1)-fold
  std::cout << "[ps test 3] leaked open=" << open << " walled=" << walled << "\n";
}

// With mutation and decay off, the ancestor's first copy differs only in its counters.
void test_ancestor_faithful() {
  Config cfg = small_config();
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  World w(cfg);
  assert(w.seed_program(8, 8, ancestor()));
  const uint64_t kTicks = 1500;
  while (w.stats().births == 0 && w.tick() < kTicks) w.run(1);
  // The copy matches except the two offset counters, copied while they were counting.
  const uint64_t kCounterBytes = 2;
  assert(w.stats().births == 1);
  assert(w.stats().birth_hamming == kCounterBytes);
  assert(w.ledger_ok());
  std::cout << "[ps test 4] births=" << w.stats().births << " active=" << w.active_count()
            << "\n";
}

// Without energy inflow an activation starves once its site's energy is spent.
void test_starvation() {
  Config cfg = small_config();
  cfg.e_in = 0;
  cfg.e0 = 10;
  cfg.p_hydro = 0.0;
  World w(cfg);
  assert(w.seed_program(8, 8, ancestor()));
  w.run(100);
  assert(w.active_count() == 0);
  assert(w.stats().deaths_starve == 1);
  assert(w.ledger_ok());
  std::cout << "[ps test 5] starved after spending " << cfg.e0 << " energy\n";
}

// Changing a non-inert byte costs bond energy; if unaffordable, overwrites never happen.
uint64_t overwrites_with_bond(int32_t e_bond) {
  Config cfg = small_config();
  cfg.e_bond = e_bond;
  cfg.p_hydro = 0.0;
  World w(cfg);
  // Inactive filler: non-inert bytes that no activation executes.
  const std::vector<uint8_t> filler(cfg.site_len, 100);
  for (int32_t site : {w.site_index(8, 7), w.site_index(9, 8), w.site_index(8, 9),
                       w.site_index(7, 8)}) {
    w.set_free_mass(site, cfg.site_len);
    assert(w.place_bytes(site, filler));
  }
  assert(w.seed_program(8, 8, ancestor()));
  w.run(500);
  assert(w.ledger_ok());
  return w.stats().overwrites;
}

void test_bond_energy() {
  const Config cfg = small_config();
  const uint64_t free_bond = overwrites_with_bond(0);
  const uint64_t blocked = overwrites_with_bond(cfg.e_max + 1);
  assert(free_bond > 0);
  assert(blocked == 0);
  std::cout << "[ps test 6] overwrites bond=0: " << free_bond << ", bond>e_max: " << blocked
            << "\n";
}

// Multi-slot sites and stall_fail under mutation: ledgers stay
// exact and replay is bit-identical.
void test_multislot_ledgers_and_replay() {
  Config cfg = small_config();
  cfg.act_cap = 3;
  cfg.stall_fail = true;
  cfg.p_mut = 0.01;
  cfg.p_erode = 1e-3;
  const uint64_t kTicks = 3000;
  World a(cfg), b(cfg);
  assert(a.seed_program(8, 8, ancestor()));
  assert(a.seed_program(8, 8, ancestor()) == false); // site already active
  b.seed_program(8, 8, ancestor());
  for (uint64_t t = 0; t < kTicks; ++t) {
    a.run(1);
    assert(a.ledger_ok());
  }
  b.run(kTicks);
  assert(a.digest() == b.digest());
 std::cout << "[ps test 7] act_cap=3 ledgers exact; active=" << a.active_count()
            << " births=" << a.stats().births << "\n";
}

// The copier writes into neighbors filled with inactive code. Allow substitutes freely;
// FillOnly refuses every change; FillErase lets only erasures (the copier's INERT bytes)
// through. Ledgers stay exact in all modes.
Stats ext_write_stats(ExtWrite mode) {
  Config cfg = small_config();
  cfg.p_hydro = 0.0;
  cfg.ext_write = mode;
  World w(cfg);
  const std::vector<uint8_t> filler(cfg.site_len, 100);
  for (int32_t site : {w.site_index(8, 7), w.site_index(9, 8), w.site_index(8, 9),
                       w.site_index(7, 8)}) {
    w.set_free_mass(site, cfg.site_len);
    assert(w.place_bytes(site, filler));
  }
  assert(w.seed_program(8, 8, ancestor()));
  w.run(500);
  assert(w.ledger_ok());
  return w.stats();
}

void test_ext_write_modes() {
  const Stats allow = ext_write_stats(ExtWrite::Allow);
  const Stats fill = ext_write_stats(ExtWrite::FillOnly);
  const Stats erase = ext_write_stats(ExtWrite::FillErase);
  assert(allow.ext_blocked == 0 && allow.ext_erasures > 0);
  assert(fill.ext_blocked > 0 && fill.ext_erasures == 0);
  assert(erase.ext_blocked > 0 && erase.ext_erasures > 0);
  std::cout << "[ps test 8] ext_write blocked allow/fill/erase: " << allow.ext_blocked << '/'
            << fill.ext_blocked << '/' << erase.ext_blocked
            << " erased: " << allow.ext_erasures << '/' << fill.ext_erasures << '/'
            << erase.ext_erasures << "\n";
}

// Diagnostic p_dead: bytes of sites with no activation hydrolyze at their own rate, the
// active site keeps its code, and the matter ledger stays exact.
void test_dead_hydrolysis() {
  Config cfg = small_config();
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  cfg.p_dead = 1.0;
  World w(cfg);
  const int32_t corpse = w.site_index(2, 2);
  assert(w.place_bytes(corpse, ancestor()));
  assert(w.seed_program(8, 8, ancestor()));
  const int32_t live = w.site_index(8, 8);
  w.run(1);
  int corpse_code = 0;
  for (uint8_t b : w.site_bytes(corpse)) corpse_code += b != INERT;
  assert(corpse_code == 0);
  assert(w.site_active(live));
  assert(w.stats().hydrolyzed == static_cast<uint64_t>(
      std::count_if(ancestor().begin(), ancestor().end(), [](uint8_t b) { return b != INERT; })));
  assert(w.ledger_ok());
  std::cout << "[ps test 9] p_dead=1 cleared " << w.stats().hydrolyzed
            << " corpse bytes; live site intact\n";
}

// Births whose child matches polite() outside its volatile bytes, with p_dead = 1. A
// never-written corpse must clear in every case.
int intact_births_with_dead_quiet(int32_t quiet) {
  Config cfg = small_config();
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  cfg.p_dead = 1.0;
  cfg.dead_quiet = quiet;
  World w(cfg);
  const int32_t corpse = w.site_index(2, 2);
  assert(w.place_bytes(corpse, ancestor()));
  assert(w.seed_program(8, 8, polite()));
  int intact = 0;
  for (int t = 0; t < 2000; ++t) {
    w.run(1);
    assert(w.ledger_ok());
    for (const auto& b : w.births_this_tick()) {
      const std::vector<uint8_t> child = w.site_bytes(b.child);
      bool same = true;
      for (int k = 0; k < static_cast<int>(polite().size()); ++k) {
        const bool volatile_byte = k == 31 || k == 32 || k == 33 || k == 44;
        same = same && (volatile_byte || child[k] == polite()[k]);
      }
      intact += same;
    }
  }
  for (uint8_t b : w.site_bytes(corpse)) assert(b == INERT);
  return intact;
}

// Diagnostic dead_quiet: p_dead spares an inactive site while writes keep reaching it, so a
// copy under construction survives; without it every copy decays before ignition.
void test_dead_quiet() {
  const int off = intact_births_with_dead_quiet(0);
  const int on = intact_births_with_dead_quiet(64);
  assert(off == 0);
  assert(on > 0);
  std::cout << "[ps test 12] p_dead=1 intact births dead_quiet 0/64: " << off << "/" << on
            << "\n";
}

// Energy diffusion conserves energy, keeps the field non-negative, and walls insulate.
int64_t energy_leaked_after(bool walled, bool diffuse) {
  Config cfg = small_config();
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  cfg.e_in = 0;
  cfg.e_diffuse = diffuse;
  World w(cfg);
  const int32_t center = w.site_index(8, 8);
  const int32_t kStock = 4000;
  w.set_energy(center, kStock);
  if (walled) {
    for (uint8_t d = 0; d < kDirs; ++d) w.set_wall(center, d, cfg.w_max);
  }
  w.run(1);
  assert(w.ledger_ok());
  return kStock - w.energy_at(center);
}

void test_energy_diffusion() {
  const int64_t off = energy_leaked_after(false, false);
  const int64_t open = energy_leaked_after(false, true);
  const int64_t walled = energy_leaked_after(true, true);
  assert(off == 0);
  assert(open > 0 && walled > 0);
  assert(4 * walled < open);
  std::cout << "[ps test 10] energy leaked off=" << off << " open=" << open
            << " walled=" << walled << "\n";
}

// Bond storage: hydrolysis releases e_bond per byte at the byte's site; with every process
// on, field + bond energy stays exactly initial + inflow - dissipation, and replay holds.
void test_bond_store() {
  Config cfg = small_config();
  cfg.bond_store = true;
  cfg.e_bond = 4;
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  cfg.p_dead = 1.0;
  cfg.e_in = 0;
  World r(cfg);
  const int32_t corpse = r.site_index(2, 2);
  assert(r.place_bytes(corpse, ancestor()));
  assert(r.ledger_ok());
  const int32_t before = r.energy_at(corpse);
  r.run(1);
  const int64_t n = std::count_if(ancestor().begin(), ancestor().end(),
                                  [](uint8_t b) { return b != INERT; });
  assert(r.energy_at(corpse) == before + n * cfg.e_bond);
  assert(r.ledger_ok());

  Config all = small_config();
  all.bond_store = true;
  all.e_diffuse = true;
  all.e_bond = 4;
  all.p_mut = 0.01;
  all.p_hydro = 1e-4;
  all.p_erode = 1e-2;
  all.ext_write = ExtWrite::FillErase;
  World a(all), b(all);
  for (World* w : {&a, &b}) {
    assert(w->seed_program(8, 8, polite()));
    assert(w->seed_program(4, 4, ancestor()));
    w->set_wall(w->site_index(3, 3), 1, 5);
  }
  const uint64_t kTicks = 3000;
  int64_t max_bonds = 0;
  for (uint64_t t = 0; t < kTicks; ++t) {
    a.run(1);
    assert(a.ledger_ok());
    max_bonds = std::max(max_bonds, a.ledger().bond_energy);
  }
  b.run(kTicks);
  assert(a.digest() == b.digest());
  assert(a.stats().births > 0);
  std::cout << "[ps test 11] hydrolysis released " << n * cfg.e_bond << "; 3000 ticks exact,"
            << " births=" << a.stats().births << " max bond energy=" << max_bonds << "\n";
}

} // namespace

int main() {
  test_ledgers_exact();
  test_deterministic_replay();
  test_diffusion_and_leaky_walls();
  test_ancestor_faithful();
  test_starvation();
  test_bond_energy();
  test_multislot_ledgers_and_replay();
  test_ext_write_modes();
  test_dead_hydrolysis();
  test_energy_diffusion();
  test_bond_store();
  test_dead_quiet();
  std::cout << "all physub tests passed\n";
  return 0;
}
