// Check: census trial verdicts for polite and copier keys (volatile offsets reset), for
// polite with offset 30, 34, 36, 38 or 40 filled (192), and with offset 26 knocked out.
#include "ps_census.hpp"
#include <iostream>
using namespace ps; using namespace ps::census;
int main() {
  Config c; c.mass0 = 48; c.ext_write = ExtWrite::FillOnly;
  for (const char* name : {"polite", "copier"}) {
    const Reference& r = *reference_named(name);
    std::string key(c.site_len, 0);
    for (size_t k = 0; k < r.program->size(); ++k) key[k] = (*r.program)[k];
    for (int v : r.volatile_offsets) key[v] = 0;
    auto t = run_trial(c, key, r);
    std::cout << name << " rep=" << t.replicator << " strict=" << t.strict() << " depth=" << t.depth << " fc=" << t.founder_exact << "/" << t.founder_copies << "\n";
    if (std::string(name) == "polite") {
      for (int k : {30, 34, 36, 38, 40}) {
        std::string m = key; m[k] = (char)192;
        auto u = run_trial(c, m, r);
        std::cout << "  fill " << k << " rep=" << u.replicator << " strict=" << u.strict() << " depth=" << u.depth << " fc=" << u.founder_exact << "/" << u.founder_copies << "\n";
      }
      std::string m = key; m[26] = 0;
      auto u = run_trial(c, m, r);
      std::cout << "  ko26 rep=" << u.replicator << " strict=" << u.strict() << " depth=" << u.depth << " fc=" << u.founder_exact << "/" << u.founder_copies << "\n";
    }
  }
}
