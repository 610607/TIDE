// Isolated copy fidelity and mutant scans of genotypes listed by ps_probe ("# fidtop" lines,
// read from stdin). Observation only. For each genotype key:
//   first copies: `first` worlds of 9x9 (seeds 1..first), the program alone with the run's
//     physics and copy error p_mut but no hydrolysis, erosion, p_dead or rotation. The
//     founder's first copy birth is classified (census::diff_sources) and its child gets a
//     census verdict. The target site is empty and no other site is active, so differences
//     can come only from the program's own copying under copy error: the share of strict
//     replicator children is the genotype's intrinsic copy fidelity.
//   knockouts: every non-inert, non-volatile byte set to INERT, as ps_knockout does, with the
//     census verdict instead of ps_knockout's functional count.
//   substitutions: `subs` values per such byte, drawn as copy errors are (1 + h % 255).
//   census_topup: as ps_probe's; it applies to the census verdicts and to the founder of the
//     first copies (a key past mass0 bytes is seeded only when topped up).
//   census_born: as ps_probe's; it applies to the census verdicts only. The first copies
//     start from reset volatile offsets either way.
//   pred: the strict share expected from text substitutions alone, to first order:
//     (1-u)^m + u (1-u)^(m-1) sum_k s_k, with m non-inert non-volatile bytes and s_k the share
//     of substitutions at k that leave a strict replicator. Copy errors in the program's own
//     bookkeeping moves (counter set-up, probe) are not in pred but are in the first copies.
// Usage: ps_scan [anc=polite|copier] [first=200] [subs=4] [label=NAME] [p_mut=0.003]
//                [mass0=48] [ext_write=fill] [ext_active=allow|refuse] [census_topup=1|0]
//                [census_born=1|0] < probe.tsv

#include "ps_census.hpp"
#include "ps_core.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <map>
#include <sstream>
#include <string>

using namespace ps;
using namespace ps::census;

namespace {

uint64_t splitmix(uint64_t z) {
  z += 0x9e3779b97f4a7c15ULL;
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
  return z ^ (z >> 31);
}

std::string unhex(const std::string& h) {
  std::string out;
  for (size_t i = 0; i + 1 < h.size(); i += 2) {
    out += static_cast<char>(std::stoi(h.substr(i, 2), nullptr, 16));
  }
  return out;
}

std::string field(const std::string& line, const std::string& name) {
  const std::string tag = " " + name + "=";
  const auto at = line.find(tag);
  if (at == std::string::npos) return "";
  const auto from = at + tag.size();
  return line.substr(from, line.find(' ', from) - from);
}

struct First {
  bool born = false;
  int cls = kClsExact;
  std::string child;
};

First first_copy(const Config& run_cfg, const std::string& key, const Reference& ref,
                 uint64_t seed, bool top_up) {
  Config c = run_cfg;
  c.width = kTrialSize;
  c.height = kTrialSize;
  c.p_hydro = 0.0;
  c.p_erode = 0.0;
  c.p_dead = 0.0;
  c.dead_quiet = 0;
  c.p_rot = 0.0;
  c.seed = seed;
  World t(c);
  const int32_t center = t.site_index(kTrialSize / 2, kTrialSize / 2);
  First f;
  if (!seed_founder(t, key, ref, top_up)) return f;
  for (uint64_t k = 0; k < kTrialTicks && t.active_count() > 0; ++k) {
    t.run(1);
    for (const auto& b : t.births_this_tick()) {
      if (b.parent != center || classify(b) != kCopy) continue;
      f.born = true;
      f.cls = diff_sources(t, b, ref).cls;
      f.child = masked(t, b.child, ref);
      return f;
    }
  }
  return f;
}

} // namespace

int main(int argc, char** argv) {
  Config cfg;
  cfg.mass0 = 48;  // ps_probe's default
  cfg.p_mut = 0.003;
  cfg.ext_write = ExtWrite::FillOnly;
  int first = 200, subs = 4;
  bool top_up = true, born = true;
  std::string label = "-";
  const Reference* ref = reference_named("polite");
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    const auto eq = a.find('=');
    const std::string k = a.substr(0, eq), v = eq == std::string::npos ? "" : a.substr(eq + 1);
    if (k == "anc") ref = reference_named(v);
    else if (k == "first") first = std::atoi(v.c_str());
    else if (k == "subs") subs = std::atoi(v.c_str());
    else if (k == "label") label = v;
    else if (k == "p_mut") cfg.p_mut = std::atof(v.c_str());
    else if (k == "mass0") cfg.mass0 = std::atoi(v.c_str());
    else if (k == "ext_write" && parse_ext_write(v, cfg.ext_write)) {}
    else if (k == "ext_active" && parse_ext_active(v, cfg.ext_active)) {}
    else if (k == "census_topup") top_up = v == "1";
    else if (k == "census_born") born = v == "1";
    else {
      std::cerr << "bad argument: " << a << '\n';
      return 1;
    }
    if (!ref) {
      std::cerr << "bad anc: " << v << '\n';
      return 1;
    }
  }
  std::map<std::string, TrialResult> cache;
  auto verdict = [&](const std::string& key) -> const TrialResult& {
    auto it = cache.find(key);
    if (it == cache.end()) it = cache.emplace(key, run_trial(cfg, key, *ref, top_up, born)).first;
    return it->second;
  };
  std::cout << "label\ttick\trank\tstatus\trun_births\trun_child_strict%\tlen\tm"
               "\tfirst_n\tfirst_strict%\tfirst_exact%\tfirst_point%\tfirst_gap%\tfirst_multi%"
               "\tko_n\tko_nonstrict\tsub_n\tsub_nonstrict\tsub_sensitive_len\tpred%\n";
  std::string line;
  const double u = cfg.p_mut;
  while (std::getline(std::cin, line)) {
    if (line.rfind("# fidtop ", 0) != 0) continue;
    const std::string key = unhex(field(line, "hex"));
    if (static_cast<int>(key.size()) != cfg.site_len) continue;
    int born = 0, strict = 0, cls[kDiffClasses] = {};
    for (int s = 1; s <= first; ++s) {
      const First f = first_copy(cfg, key, *ref, static_cast<uint64_t>(s), top_up);
      if (!f.born) continue;
      born += 1;
      cls[f.cls] += 1;
      strict += verdict(f.child).strict();
    }
    int m = 0, ko_n = 0, ko_bad = 0, sub_n = 0, sub_bad = 0;
    double sum_s = 0.0;
    for (int k = 0; k < cfg.site_len; ++k) {
      if (ref->is_volatile(k) || key[k] == 0) continue;
      m += 1;
      std::string ko = key;
      ko[k] = 0;
      ko_n += 1;
      ko_bad += !verdict(ko).strict();
      int ok = 0;
      for (int j = 0; j < subs; ++j) {
        std::string sub = key;
        const uint64_t h = splitmix(static_cast<uint64_t>(k) * 1000003ULL + static_cast<uint64_t>(j));
        sub[k] = static_cast<char>(1 + h % 255);
        const bool good = verdict(sub).strict();
        ok += good;
        sub_n += 1;
        sub_bad += !good;
      }
      sum_s += subs > 0 ? static_cast<double>(ok) / subs : 0.0;
    }
    const double pred = std::pow(1.0 - u, m) + u * std::pow(1.0 - u, m - 1) * sum_s;
    auto pct = [](int a, int b) { return b ? 100.0 * a / b : 0.0; };
    std::cout << label << '\t' << field(line, "tick") << '\t' << field(line, "rank") << '\t'
              << field(line, "status") << '\t' << field(line, "births") << '\t'
              << field(line, "child_strict%") << '\t' << field(line, "len") << '\t' << m << '\t'
              << born << '\t' << pct(strict, born) << '\t' << pct(cls[kClsExact], born) << '\t'
              << pct(cls[kClsPoint], born) << '\t' << pct(cls[kClsGap], born) << '\t'
              << pct(cls[kClsMulti], born) << '\t' << ko_n << '\t' << ko_bad << '\t' << sub_n
              << '\t' << sub_bad << '\t' << (m - sum_s) << '\t' << 100.0 * pred << std::endl;
  }
  return 0;
}
