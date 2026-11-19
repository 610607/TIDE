#!/usr/bin/env bash
# Compare v19 outputs (fate lines removed) with v18 (shift renamed multi), over the v19 prefix.
cd "$(dirname "$0")/../.."
for r in m195_s1 m195_s2 nomut_s1 nomut_s2; do
  a=$(mktemp); b=$(mktemp)
  grep -v '^# fate' runs/v19/$r.tsv > $a
  sed 's/ shift=/ multi=/' runs/v18/$r.tsv | head -n $(wc -l < $a) > $b
  if cmp -s $a $b; then echo "$r identical over $(wc -l < $a) lines"; else echo "$r DIFFERS"; diff $a $b | head -5; fi
  rm -f $a $b
done
