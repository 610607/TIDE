// Check: polite alone with one own-site direction byte (or a tail byte) filled, every
// value 1..255, census verdict reset-only and copy-born, under inert_operand zero and fail.
#include <cstdio>
#include "ps_core.hpp"
#include "ps_census.hpp"
using namespace ps;
int main() {
  Config cfg;
  cfg.ext_write = ExtWrite::FillOnly;
  cfg.mass0 = 48;
  const census::Reference& ref = *census::reference_named("polite");
  std::string key(cfg.site_len, 0);
  for (size_t k = 0; k < ref.program->size(); ++k) key[k] = static_cast<char>((*ref.program)[k]);
  for (int v : ref.volatile_offsets) key[v] = 0;
  for (InertOperand io : {InertOperand::Zero, InertOperand::Fail}) {
    Config c = cfg; c.inert_operand = io;
    for (int off : {30, 34, 36, 38, 40, 50}) {
      int reset = 0, born = 0, rep = 0;
      int bydir_born[4] = {0, 0, 0, 0};
      for (int v = 1; v <= 255; ++v) {
        std::string k = key; k[off] = static_cast<char>(v);
        const census::TrialResult r = census::run_trial(c, k, ref);
        rep += r.replicator; reset += r.reset_strict(); born += r.strict();
        bydir_born[(v - 1) % 4] += r.strict();
      }
      std::printf("%s off=%d replicator=%d reset_strict=%d strict(born)=%d by_dir_born=%d/%d/%d/%d\n",
                  io == InertOperand::Zero ? "zero" : "fail", off, rep, reset, born,
                  bydir_born[0], bydir_born[1], bydir_born[2], bydir_born[3]);
    }
  }
}
