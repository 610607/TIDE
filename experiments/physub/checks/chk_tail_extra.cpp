// Check: census status of polite with k tail bytes filled, trial mass0 as in ps_probe.
#include "ps_census.hpp"
#include <cstdio>
#include <cstdlib>
using namespace ps;
int main() {
  Config c;
  c.mass0 = 48;
  c.ext_write = ExtWrite::FillOnly;
  c.inert_operand = getenv("ZERO") ? InertOperand::Zero : InertOperand::Fail;
  const auto* ref = census::reference_named("polite");
  const auto& p = polite();
  std::string base(c.site_len, 0);
  for (size_t i = 0; i < p.size(); ++i) base[i] = (char)p[i];
  for (int x : ref->volatile_offsets) base[x] = 0;
  for (int k = 0; k <= 14; ++k) {
    std::string key = base;
    for (int j = 0; j < k; ++j) key[46 + j] = (char)(7 + 9 * j);
    auto r = census::run_trial(c, key, *ref);
    printf("tail fills %d (bytes after volatile reset %d): strict=%d rep=%d op_mask=%llx copies=%d\n",
           k, 40 + k, r.strict(), r.replicator, (unsigned long long)r.op_mask, r.founder_copies);
  }
  // single fills of each non-volatile INERT offset, all values
  for (int k = 0; k < c.site_len; ++k) {
    if (base[k] != 0 || ref->is_volatile(k)) continue;
    int st = 0, lo = 0, no = 0;
    for (int v = 1; v < 256; ++v) {
      std::string key = base; key[k] = (char)v;
      auto r = census::run_trial(c, key, *ref);
      if (r.strict()) st++; else if (r.replicator) lo++; else no++;
    }
    printf("offset %d: strict %d loose %d nonrep %d\n", k, st, lo, no);
  }
}
