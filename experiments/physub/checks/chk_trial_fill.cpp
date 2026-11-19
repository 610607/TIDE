// Check: census verdicts for polite with one reference-inert or tail offset filled.
#include "ps_census.hpp"
#include <iostream>
using namespace ps;
int main() {
  Config cfg;
  cfg.width = 96; cfg.height = 96; cfg.p_mut = 0.003; cfg.p_hydro = 1.95e-6;
  cfg.hydro_whole = Whole::All; cfg.mass0 = 48;
  { std::string k0(cfg.site_len, 0); } cfg.ext_write = ExtWrite::FillOnly;
  const census::Reference& ref = *census::reference_named("polite");
  std::string key(cfg.site_len, 0);
  for (size_t k = 0; k < polite().size(); ++k) key[k] = static_cast<char>(polite()[k]);
  for (int v : ref.volatile_offsets) key[v] = 0;
  { const auto r0 = census::run_trial(cfg, key, ref); std::cout << "polite strict " << r0.strict() << "\n"; }
  for (int off : {30, 34, 36, 38, 40, 46, 47, 48, 49, 50, 51, 52, 53, 60}) {
    int strict = 0, rep = 0, n = 0;
    for (int v = 1; v < 256; v += 1) {
      std::string k2 = key; k2[off] = static_cast<char>(v);
      const auto r = census::run_trial(cfg, k2, ref);
      strict += r.strict(); rep += r.replicator; n += 1;
    }
    std::cout << "offset " << off << ": strict " << strict << "/" << n << " replicator " << rep << "/" << n << "\n";
  }
}
