#!/usr/bin/env bash
# Regenerate the analysis outputs of the census recomputes (v23, v27) and the v26 comparison
# from tracked runs. The per-version scripts expect each version's run names (m195_s1, ...),
# so the recompute runs are linked under those names in OUT/view first.
#
# Usage (from experiments/physub): scripts/analysis/regen.sh v23|v27|v26 OUT
#   v23: v17-v22 tables from runs/v23 (topped-up census); v24 and v25 are separate versions.
#   v27: v18-v25 tables from runs/v27 (copy-born census).
#   v26: erase (runs/v26) against fill (the v27 m195 runs of the same names).
# v23 and v27 also run build/ps_scan on the strict genotypes of the fidelity runs; the v23
# scans were made at b4b4ea1 (census_born did not exist yet; here census_born=0), the v27
# scans at 34839f4. Every script writes OUT/<name>.txt; errors go to the same file.
set -u
mode=${1:?v23|v27|v26}
O=${2:?output dir}
cd "$(dirname "$0")/../.."
R=$PWD/runs
A=$PWD/scripts/analysis
B=$PWD/build
mkdir -p "$O"
O=$(cd "$O" && pwd)
V=$O/view
rm -rf "$V"
l() { ln -s "$1" "$2"; }

if [ "$mode" = v26 ]; then
  mkdir -p "$V"/erase "$V"/fill "$V"/z/erase "$V"/z/fill
  for x in zero fail; do for s in 1 2; do
    l "$R/v26/${x}_s$s.tsv" "$V/erase/${x}_s$s.tsv"
    l "$R/v27/${x}_m195_s$s.tsv" "$V/fill/${x}_s$s.tsv"
  done; done
  for v in erase fill; do for s in 1 2; do l "$V/$v/zero_s$s.tsv" "$V/z/$v/zero_s$s.tsv"; done; done
  cd "$A"
  python3 v26_cmp.py "$V/erase" "$V/fill" > "$O/v26_cmp.txt" 2>&1
  python3 v25_md.py "$V/z/erase" > "$O/v25_md_erase.txt" 2>&1
  python3 v25_md.py "$V/z/fill" > "$O/v25_md_fill.txt" 2>&1
  echo "regen-$mode-done"
  exit 0
fi

case $mode in
  v23) N=$R/v23; scanopt=census_born=0 ;;
  v27) N=$R/v27; scanopt=census_born=1 ;;
  *) echo "unknown mode $mode" >&2; exit 2 ;;
esac
mkdir -p "$V"/{v17,v18,v19,v20,v21,v21z2,v22,v24,v25}
l "$N/zero_m195_s1.tsv" "$V/v17/m195_s1.tsv"; l "$N/zero_m195_s2.tsv" "$V/v17/m195_s2.tsv"
if [ "$mode" = v23 ]; then
  for t in 1 2 3 4; do for s in 1 2; do l "$N/t${t}_s$s.tsv" "$V/v17/t${t}_s$s.tsv"; done; done
fi
l "$N/zero_m195_s1.tsv" "$V/v18/m195_s1.tsv"; l "$N/zero_m195_s2.tsv" "$V/v18/m195_s2.tsv"
l "$N/t2_s1.tsv" "$V/v18/t2_s1.tsv"; l "$N/t3_s1.tsv" "$V/v18/t3_s1.tsv"
l "$N/anc_s1.tsv" "$V/v18/anc_s1.tsv"; l "$N/anc_s2.tsv" "$V/v18/anc_s2.tsv"
l "$N/zero_nomut_s1.tsv" "$V/v18/nomut_s1.tsv"; l "$N/zero_nomut_s2.tsv" "$V/v18/nomut_s2.tsv"
for s in 1 2 3 4 5 6; do l "$R/v18/anc_run_s$s.tsv" "$V/v18/anc_run_s$s.tsv"; done
l "$N/zero_m195_s1.tsv" "$V/v19/m195_s1.tsv"; l "$N/zero_m195_s2.tsv" "$V/v19/m195_s2.tsv"
l "$N/zero_nomut_s1.tsv" "$V/v19/nomut_s1.tsv"; l "$N/zero_nomut_s2.tsv" "$V/v19/nomut_s2.tsv"
l "$N/fail_m195_s1.tsv" "$V/v20/m195_s1.tsv"; l "$N/fail_m195_s2.tsv" "$V/v20/m195_s2.tsv"
l "$N/fail_nomut_s1.tsv" "$V/v20/nomut_s1.tsv"; l "$N/fail_nomut_s2.tsv" "$V/v20/nomut_s2.tsv"
l "$N/fail_m195_s1.tsv" "$V/v21/m195_s1.tsv"; l "$N/fail_m195_s2.tsv" "$V/v21/m195_s2.tsv"
l "$N/fail_nomut_s1.tsv" "$V/v21/nomut_s1.tsv"; l "$N/zero_m195_s1.tsv" "$V/v21/zero_s1.tsv"
l "$N/zero_m195_s2.tsv" "$V/v21z2/zero_s1.tsv"
l "$N/fail_m195_s1.tsv" "$V/v22/m195_s1.tsv"; l "$N/fail_m195_s2.tsv" "$V/v22/m195_s2.tsv"
l "$N/zero_m195_s1.tsv" "$V/v22/zero_s1.tsv"; l "$N/zero_m195_s2.tsv" "$V/v22/zero_s2.tsv"
if [ "$mode" = v23 ]; then
  for r in zero_s1 zero_s2 fail_s1 fail_s2; do l "$R/v24/$r.tsv" "$V/v24/$r.tsv"; done
  for r in zero_s1 zero_s2 fail_s1 fail_s2 zero_nomut_s1 fail_nomut_s1; do
    l "$R/v25/$r.tsv" "$V/v25/$r.tsv"
  done
else
  for x in zero fail; do for s in 1 2; do
    l "$N/${x}_m195_s$s.tsv" "$V/v24/${x}_s$s.tsv"; l "$N/${x}_m195_s$s.tsv" "$V/v25/${x}_s$s.tsv"
  done; done
  l "$N/zero_nomut_s1.tsv" "$V/v25/zero_nomut_s1.tsv"; l "$N/fail_nomut_s1.tsv" "$V/v25/fail_nomut_s1.tsv"
fi

# Isolated scans of the top strict genotypes (v18 T3 and the ancestor control).
SCANP=$O/scan_polite.tsv; SCANC=$O/scan_copier.tsv
for r in zero_m195_s1 zero_m195_s2 t2_s1 t3_s1; do
  lab=${r/zero_/}
  "$B/ps_scan" label="$lab" first=400 subs=4 $scanopt < "$N/$r.tsv" > "$O/scan_$lab.tsv" &
done
( "$B/ps_scan" anc=copier label=anc_s1 first=400 subs=4 $scanopt < "$N/anc_s1.tsv"
  "$B/ps_scan" anc=copier label=anc_s2 first=400 subs=4 $scanopt < "$N/anc_s2.tsv" | tail -n +2
) > "$SCANC" 2> "$O/scan_copier.err" &
wait
(cat "$O/scan_m195_s1.tsv"; for x in m195_s2 t2_s1 t3_s1; do tail -n +2 "$O/scan_$x.tsv"; done) > "$SCANP"

cd "$A"
if [ "$mode" = v23 ]; then
  python3 v17_md.py "$V/v17" > "$O/v17_md.txt" 2>&1
  python3 v17_m195.py "$V/v17" > "$O/v17_m195.txt" 2>&1
  python3 v17_extra.py "$V/v17" > "$O/v17_extra.txt" 2>&1
fi
python3 v18.py "$V/v18" "$SCANP" > "$O/v18.txt" 2>&1
python3 v18.py "$V/v18" len > "$O/v18_len.txt" 2>&1
python3 v18_md.py "$V/v18" > "$O/v18_md.txt" 2>&1
python3 v18_extra.py "$V/v18" > "$O/v18_extra.txt" 2>&1
python3 v18_bal.py "$V/v18" m195_s1 m195_s2 t2_s1 t3_s1 > "$O/v18_bal.txt" 2>&1
python3 v18_t3.py "$SCANP" 37,38-39,40-42,43-45 > "$O/v18_t3.txt" 2>&1
python3 v18.py "$V/v18" "$SCANC" > "$O/v18_anc.txt" 2>&1
python3 v19.py "$V/v19" > "$O/v19.txt" 2>&1
python3 v19_md.py "$V/v19" > "$O/v19_md.txt" 2>&1
python3 v19_rates.py "$O/v19.txt" > "$O/v19_rates.txt" 2>&1
python3 selfoff.py "$V"/v19/{m195_s1,m195_s2,nomut_s1,nomut_s2}.tsv > "$O/v19_selfoff.txt" 2>&1
python3 v20.py "$V/v19" "$V/v20" > "$O/v20.txt" 2>&1
python3 v20_md.py "$V/v19" "$V/v20" > "$O/v20_md.txt" 2>&1
python3 v21.py "$V/v21" > "$O/v21.txt" 2>&1
python3 v21.py "$V/v21z2" > "$O/v21_zero_s2.txt" 2>&1
python3 v21_table2.py "$V"/v21/{m195_s1,m195_s2,zero_s1,nomut_s1}.tsv "$V/v22/zero_s2.tsv" \
  > "$O/v21_table2.txt" 2>&1
python3 v22.py "$V/v22" > "$O/v22.txt" 2>&1
python3 v22_md2.py "$V/v22" > "$O/v22_md2.txt" 2>&1
python3 v24_md.py "$V/v24" > "$O/v24_md.txt" 2>&1
python3 v24_extra.py "$V/v24" > "$O/v24_extra.txt" 2>&1
python3 v24_matter.py "$V/v24" > "$O/v24_matter.txt" 2>&1
python3 v24_routes.py "$V"/v24/*.tsv > "$O/v24_routes.txt" 2>&1
python3 v24_decomp.py "$V"/v24/*.tsv > "$O/v24_decomp.txt" 2>&1
python3 v25_md.py "$V/v25" > "$O/v25_md.txt" 2>&1
python3 v25_an.py "$V/v25" > "$O/v25_an.txt" 2>&1
echo "regen-$mode-done"
