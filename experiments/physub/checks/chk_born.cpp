// Check: single-byte variants of polite at the counter-reset
// instructions (offsets 0-5), the K pointer and its target (34, 35, 42) and the so/do pointer
// directions (36, 38). For each: the census verdict (volatile offsets reset: so = do = 192) and
// the same trial started from the counters a copy-born child carries (31 = 223, 33 = 225).
#include "ps_census.hpp"
#include <cstdio>
#include <vector>
using namespace ps;
static bool strict_from(const Config& rc, std::vector<uint8_t> prog, const std::string& key,
                        const census::Reference& ref) {
  Config c = rc;
  c.width = 9; c.height = 9; c.p_mut = 0; c.p_hydro = 0; c.p_erode = 0; c.p_dead = 0;
  c.dead_quiet = 0; c.p_rot = 0; c.seed = 1;
  World t(c);
  const int32_t ctr = t.site_index(4, 4);
  int need = 0;
  for (uint8_t b : prog) need += b != INERT;
  if (need > t.free_mass(ctr)) t.set_free_mass(ctr, need);
  if (!t.seed_program(4, 4, prog)) return false;
  int copies = 0, exact = 0;
  for (int k = 0; k < 2000 && t.active_count() > 0; ++k) {
    t.run(1);
    for (const auto& b : t.births_this_tick()) {
      if (census::classify(b) != census::kCopy || b.parent != ctr) continue;
      copies += 1;
      exact += census::masked(t, b.child, ref) == key;
    }
  }
  int carriers = 0;
  for (int32_t s = 0; s < 81; ++s) carriers += t.site_active(s) && census::masked(t, s, ref) == key;
  return carriers >= 2 && copies > 0 && exact == copies;
}
int main() {
  const census::Reference& ref = *census::reference_named("polite");
  for (int io = 0; io < 2; ++io) {
    Config rc;
    rc.mass0 = 48; rc.hydro_whole = Whole::All; rc.ext_write = ExtWrite::FillOnly;
    rc.inert_operand = io ? InertOperand::Fail : InertOperand::Zero;
    printf("inert_operand=%s\n", io ? "fail" : "zero");
    for (int k : {0, 1, 2, 3, 4, 5, 34, 35, 36, 38, 42}) {
      int n = 0, cs = 0, bs = 0, cs_not_bs = 0;
      for (int v = 1; v < 256; ++v) {
        std::vector<uint8_t> p = polite();
        p.resize(64, INERT);
        if (p[k] == v) continue;
        p[k] = static_cast<uint8_t>(v);
        std::string key(p.begin(), p.end());
        for (int x : ref.volatile_offsets) key[x] = 0;
        const bool c = census::run_trial(rc, key, ref).strict();
        std::vector<uint8_t> born = census::trial_program(key, ref);
        born[31] = 223; born[32] = 1; born[33] = 225; born[44] = INERT;
        const bool b = strict_from(rc, born, key, ref);
        n += 1; cs += c; bs += b; cs_not_bs += c && !b;
      }
      printf("  offset %2d: variants=%d census_strict=%d strict_from_born_counters=%d census_strict_but_not_born=%d\n",
             k, n, cs, bs, cs_not_bs);
    }
  }
}
