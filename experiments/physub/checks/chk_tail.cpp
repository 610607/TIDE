// Check: census status of polite with one INERT offset filled (fail mode, v20 physics).
#include "ps_census.hpp"
#include <cstdio>
#include <cstdlib>
using namespace ps;
int main() {
  Config c;
  c.width = 96; c.height = 96;
  c.ext_write = ExtWrite::FillOnly;
  if (getenv("MASS0")) c.mass0 = atoi(getenv("MASS0"));
  c.inert_operand = InertOperand::Fail;
  const auto* ref = census::reference_named("polite");
  const auto& p = polite();
  std::string base(c.site_len, 0);
  for (size_t i = 0; i < p.size(); ++i) base[i] = (char)p[i];
  for (int x : ref->volatile_offsets) base[x] = 0;
  { auto r0 = census::run_trial(c, base, *ref); printf("base strict=%d rep=%d copies=%d\n", r0.strict(), r0.replicator, r0.founder_copies); }
  for (int k = 0; k < c.site_len; ++k) {
    if (base[k] != 0 || ref->is_volatile(k)) continue;
    int rep = 0, loose = 0, other = 0;
    for (int v = 1; v < 256; v += 1) {
      std::string key = base;
      key[k] = (char)v;
      auto r = census::run_trial(c, key, *ref);
      if (r.strict()) rep++; else if (r.replicator) loose++; else other++;
    }
    printf("offset %d: strict %d loose %d nonrep %d\n", k, rep, loose, other);
  }
}
