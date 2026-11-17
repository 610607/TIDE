// Mechanism checks for the physical-substrate prototype.

#include "ps_census.hpp"
#include "ps_core.hpp"

#include <algorithm>
#include <cassert>
#include <cmath>
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

int non_inert(const std::vector<uint8_t>& bytes) {
  return static_cast<int>(std::count_if(bytes.begin(), bytes.end(),
                                        [](uint8_t b) { return b != INERT; }));
}

// Form M: a program decays in one event, all its bytes return to the site's free monomers,
// and the activation ends; with a small rate the ledger stays exact and replay holds.
void test_whole_decay() {
  Config cfg = small_config();
  cfg.hydro_whole = Whole::All;
  cfg.p_hydro = 1.0;
  cfg.p_erode = 0.0;
  World w(cfg);
  const int32_t site = w.site_index(8, 8);
  assert(w.seed_program(8, 8, polite()));
  w.run(1);
  assert(non_inert(w.site_bytes(site)) == 0);
  assert(!w.site_active(site));
  assert(w.free_mass(site) >= cfg.mass0);  // the program's monomers are back
  assert(w.stats().whole_decays == 1 && w.stats().whole_decays_active == 1);
  assert(w.stats().hydrolyzed == static_cast<uint64_t>(non_inert(polite())));
  assert(w.ledger_ok());

  Config slow = small_config();
  slow.hydro_whole = Whole::All;
  slow.p_hydro = 2e-5;
  slow.p_mut = 0.01;
  World a(slow), b(slow);
  for (World* x : {&a, &b}) assert(x->seed_program(8, 8, polite()));
  const uint64_t kTicks = 4000;
  for (uint64_t t = 0; t < kTicks; ++t) {
    a.run(1);
    assert(a.ledger_ok());
  }
  b.run(kTicks);
  assert(a.digest() == b.digest());
  assert(a.stats().whole_decays > 0 && a.stats().births > 0);
  std::cout << "[ps test 13] whole decay cleared " << w.stats().hydrolyzed
            << " bytes in one event; 4000 ticks exact, decays=" << a.stats().whole_decays
            << " births=" << a.stats().births << "\n";
}

// Whole decay per class: with hydro_whole=dead only inactive code clears in one event and
// the live site keeps per-byte decay; with hydro_whole=live the reverse.
void test_whole_decay_split() {
  for (Whole mode : {Whole::Dead, Whole::Live}) {
    Config cfg = small_config();
    cfg.hydro_whole = mode;
    cfg.p_erode = 0.0;
    cfg.p_hydro = mode == Whole::Live ? 1.0 : 0.0;  // live sites
    cfg.p_dead = mode == Whole::Live ? 0.0 : 1.0;   // the others
    World w(cfg);
    const int32_t corpse = w.site_index(2, 2);
    const int32_t live = w.site_index(8, 8);
    assert(w.place_bytes(corpse, ancestor()));
    assert(w.seed_program(8, 8, polite()));
    w.run(1);
    const bool corpse_cleared = non_inert(w.site_bytes(corpse)) == 0;
    const bool live_cleared = non_inert(w.site_bytes(live)) == 0;
    assert(w.stats().whole_decays == 1);
    assert(corpse_cleared == (mode == Whole::Dead));
    assert(live_cleared == (mode == Whole::Live));
    assert(w.site_active(live) == (mode == Whole::Dead));
    assert(w.stats().whole_decays_active == (mode == Whole::Live ? 1u : 0u));
    assert(w.ledger_ok());
  }
  // Per-byte decay still acts on the other class: p_hydro = 1 per byte empties the live site
  // byte by byte while hydro_whole=dead leaves the corpse to whole decay at p_dead = 0.
  Config cfg = small_config();
  cfg.hydro_whole = Whole::Dead;
  cfg.p_erode = 0.0;
  cfg.p_hydro = 1.0;
  cfg.p_dead = 0.0;
  World w(cfg);
  const int32_t corpse = w.site_index(2, 2);
  assert(w.place_bytes(corpse, ancestor()));
  assert(w.seed_program(8, 8, polite()));
  w.run(1);
  assert(non_inert(w.site_bytes(w.site_index(8, 8))) == 0);
  assert(non_inert(w.site_bytes(corpse)) == non_inert(ancestor()));
  assert(w.stats().whole_decays == 0 && w.ledger_ok());
  std::cout << "[ps test 15] whole decay per class: dead clears the corpse only, live clears"
            << " the live site only\n";
}

// Per-op whole decay (decay_table): the documented tables, the class-mean rate, ratio 1
// equal to uniform form M bit for bit, and fast-class programs clearing faster.
void test_decay_table() {
  const char* kExpected[] = {"", "mov dec rnd unwall", "jmp ignite wall unwall",
                             "dec jmp rnd unwall", "mov inc jmp wall"};
  const char* kNames[kOps] = {"mov", "inc", "dec", "jz", "jmp", "rnd", "ignite", "wall", "unwall"};
  for (int t = 0; t <= 4; ++t) {
    const auto fast = decay_fast_classes(t);
    std::string got;
    for (int k = 0; k < kOps; ++k) {
      if (!fast[k]) continue;
      if (!got.empty()) got += ' ';
      got += kNames[k];
    }
    assert(got == kExpected[t]);
  }
  double slow = 0.0, fast = 0.0;
  decay_rates(1.95e-6, 30.0, slow, fast);
  assert(std::abs(slow - 1.404e-7) < 1e-12 && std::abs(fast - 4.212e-6) < 1e-12);
  const double classes = kOps;
  assert(std::abs((kDecayFast * fast + (classes - kDecayFast) * slow) / classes - 1.95e-6) < 1e-15);
  decay_rates(1.95e-6, 1.0, slow, fast);
  assert(slow == 1.95e-6 && fast == 1.95e-6);

  // Ratio 1 is uniform form M, bit for bit, with mutation and whole decays happening.
  Config base = small_config();
  base.hydro_whole = Whole::All;
  base.p_hydro = 2e-5;
  base.p_mut = 0.01;
  Config one = base;
  one.decay_table = 1;
  one.decay_ratio = 1.0;
  Config thirty = base;
  thirty.decay_table = 1;
  World u(base), a(one), b(thirty);
  for (World* x : {&u, &a, &b}) assert(x->seed_program(8, 8, polite()));
  const uint64_t kTicks = 4000;
  for (uint64_t t = 0; t < kTicks; ++t) {
    b.run(1);
    assert(b.ledger_ok());
  }
  u.run(kTicks);
  a.run(kTicks);
  assert(u.digest() == a.digest() && u.stats().whole_decays > 0);
  assert(b.digest() != u.digest());

  // Inactive programs of one class each: 32 fast-class bytes or 32 slow-class bytes.
  Config cfg = small_config();
  cfg.hydro_whole = Whole::All;
  cfg.p_hydro = 1e-3;  // slow 7.2e-5, fast 2.16e-3 per byte
  cfg.p_erode = 0.0;
  cfg.decay_table = 1;
  World w(cfg);
  const auto fc = decay_fast_classes(1);
  uint8_t fast_v = 0, slow_v = 0;
  for (int v = 1; v <= 9; ++v) {
    if (fc[op_class(static_cast<uint8_t>(v))] && !fast_v) fast_v = static_cast<uint8_t>(v);
    if (!fc[op_class(static_cast<uint8_t>(v))] && !slow_v) slow_v = static_cast<uint8_t>(v);
  }
  const int32_t sites = cfg.width * cfg.height;
  for (int32_t s = 0; s < sites; ++s) {
    w.set_free_mass(s, 64);
    assert(w.place_bytes(s, std::vector<uint8_t>(32, s % 2 ? slow_v : fast_v)));
  }
  w.run(10);
  int cleared[2] = {0, 0};  // [0] fast, [1] slow
  for (int32_t s = 0; s < sites; ++s) cleared[s % 2] += non_inert(w.site_bytes(s)) == 0;
  // Expected after 10 ticks: fast about 128 x 0.5 = 64, slow about 128 x 0.023 = 3.
  assert(cleared[0] > 30 && cleared[0] > 4 * cleared[1]);
  assert(w.ledger_ok());
  std::cout << "[ps test 16] decay tables match; ratio 1 equals uniform M over " << kTicks
            << " ticks (decays=" << u.stats().whole_decays << "); cleared fast/slow "
            << cleared[0] << '/' << cleared[1] << " of 128 each\n";
}

// Every activation points at a non-inert byte of its own site's code.
bool activations_on_code(const World& w) {
  const int32_t n = w.config().width * w.config().height;
  for (int32_t s = 0; s < n; ++s) {
    const int ip = w.first_ip(s);
    if (ip >= 0 && w.bytes_at(s)[ip] == INERT) return false;
  }
  return true;
}

// Block rotation moves code and activation together, conserves matter, replays exactly,
// and a walled block stays.
void test_block_rotation() {
  Config cfg = small_config();
  cfg.p_rot = 1.0;
  cfg.p_hydro = 0.0;
  cfg.p_erode = 0.0;
  World w(cfg);
  assert(w.seed_program(8, 8, polite()));
  const int32_t from = w.site_index(8, 8);
  w.run(1);
  assert(w.stats().rotations == static_cast<uint64_t>((cfg.width / 2) * (cfg.height / 2)));
  assert(w.moves_this_tick().size() == 4 * w.stats().rotations);
  assert(!w.site_active(from) && non_inert(w.site_bytes(from)) == 0);
  int32_t to = -1;
  for (int32_t s : {w.site_index(9, 8), w.site_index(8, 9)}) if (w.site_active(s)) to = s;
  assert(to >= 0);
  assert(non_inert(w.site_bytes(to)) == non_inert(polite()));
  assert(w.ledger_ok());

  World walled(cfg);
  assert(walled.seed_program(8, 8, polite()));
  const int32_t a = walled.site_index(8, 8), b = walled.site_index(9, 8);
  walled.set_wall(a, 1, cfg.w_max);   // a | b
  walled.set_wall(b, 2, cfg.w_max);   // b over c
  walled.set_wall(walled.site_index(8, 9), 1, cfg.w_max);  // d | c
  walled.set_wall(a, 2, cfg.w_max);   // a over d
  walled.run(1);
  assert(walled.stats().rot_walled == 1 && walled.site_active(a));
  assert(walled.ledger_ok());

  Config mix = small_config();
  mix.p_rot = 1e-3;
  mix.p_mut = 0.01;
  mix.ext_write = ExtWrite::FillOnly;
  World x(mix), y(mix);
  for (World* v : {&x, &y}) assert(v->seed_program(8, 8, polite()));
  const uint64_t kTicks = 4000;
  for (uint64_t t = 0; t < kTicks; ++t) {
    x.run(1);
    assert(x.ledger_ok());
    assert(activations_on_code(x));
  }
  y.run(kTicks);
  assert(x.digest() == y.digest());
  assert(x.stats().births > 0 && x.stats().copies_cut > 0);
  std::cout << "[ps test 14] rotation moved code with activation; walled block stayed;"
            << " 4000 ticks exact, rotations=" << x.stats().rotations
            << " copies started/cut/born/born_cut=" << x.stats().copies_started << '/'
            << x.stats().copies_cut << '/' << x.stats().copies_born << '/'
            << x.stats().copies_born_cut << "\n";
}

// Census trial and copy-difference classes (apps/ps_census.hpp): polite is a strict
// replicator; a knocked-out IGNITE or a source pointer redirected to a neighbor is not; trials
// are deterministic; a clean copy is exact and a refused fill-mode write leaves residue.
void test_census_trial() {
  Config cfg;
  cfg.mass0 = 48;
  cfg.ext_write = ExtWrite::FillOnly;
  const census::Reference& ref = *census::reference_named("polite");
  std::string key(cfg.site_len, 0);
  for (size_t k = 0; k < polite().size(); ++k) key[k] = static_cast<char>(polite()[k]);
  for (int v : ref.volatile_offsets) key[v] = 0;
  const census::TrialResult a = census::run_trial(cfg, key, ref);
  const census::TrialResult b = census::run_trial(cfg, key, ref);
  assert(a.replicator && a.strict() && a.depth >= 2 && a.founder_copies >= 2);
  assert(b.replicator == a.replicator && b.depth == a.depth && b.op_mask == a.op_mask &&
         b.founder_copies == a.founder_copies && b.founder_exact == a.founder_exact);
  std::string ko = key;
  ko[26] = 0;  // IGNITE opcode
  assert(!census::run_trial(cfg, ko, ref).replicator);
  std::string redirected = key;
  redirected[30] = static_cast<char>(192);  // source pointer: a neighbor instead of own site
  assert(!census::run_trial(cfg, redirected, ref).replicator);
  // Alone, a fill of another own-site pointer byte or of the tail leaves a strict replicator
  // (the neighbors it names are empty).
  for (int off : {34, 36, 38, 40, 50}) {
    std::string filled_key = key;
    filled_key[off] = static_cast<char>(192);
    assert(census::run_trial(cfg, filled_key, ref).strict());
  }
  assert(!census::ref_inert_filled(polite().data(), ref));
  std::vector<uint8_t> filled = polite();
  filled[36] = 192;
  assert(census::ref_inert_filled(filled.data(), ref));

  // First copy of a lone founder: exact in an empty world; residue when every neighbor holds
  // a non-inert byte at an offset where polite is inert (fill refuses the inert write).
  for (const bool dirty : {false, true}) {
    Config c = cfg;
    c.width = 9;
    c.height = 9;
    c.p_hydro = 0.0;
    c.p_erode = 0.0;
    World w(c);
    assert(w.seed_program(4, 4, polite()));
    if (dirty) {
      for (auto [x, y] : {std::pair{3, 4}, {5, 4}, {4, 3}, {4, 5}}) {
        std::vector<uint8_t> junk(c.site_len, INERT);
        junk[50] = 7;
        assert(w.seed_program(x, y, junk));
      }
    }
    const int32_t center = w.site_index(4, 4);
    int cls = -1;
    for (int t = 0; t < 2000 && cls < 0; ++t) {
      w.run(1);
      for (const auto& birth : w.births_this_tick()) {
        if (birth.parent == center && census::classify(birth) == census::kCopy) {
          const census::Diff d = census::diff_sources(w, birth, ref);
          cls = d.cls;
          assert(!dirty || d.n[census::kSrcResidue] == 1);
          // Writer records: in an empty world every non-inert byte of the child was written
          // by the founder in an earlier tick; untouched bytes have no writer.
          for (int k = 0; !dirty && k < c.site_len; ++k) {
            const int32_t wr = w.byte_writer(birth.child, k);
            assert(wr == center || wr == -1);
            assert(wr == -1 || w.byte_written_at(birth.child, k) < w.tick());
            assert(w.bytes_at(birth.child)[k] == INERT || wr == center);
          }
        }
      }
    }
    assert(cls == (dirty ? census::kClsEnv : census::kClsExact));
  }
  std::cout << "[ps test 17] census trial: polite strict, depth " << a.depth << ", founder copies "
            << a.founder_exact << '/' << a.founder_copies
            << "; knockout and redirected source fail, other fills stay strict; first copy exact, residue is env;"
            << " writers recorded\n";
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
  test_whole_decay();
  test_block_rotation();
  test_whole_decay_split();
  test_decay_table();
  test_census_trial();
  std::cout << "all physub tests passed\n";
  return 0;
}
