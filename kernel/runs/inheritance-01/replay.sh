#!/bin/sh
# Run from the repository root. Each traversal has its own build and output directory.
set -eu
study=kernel/runs/inheritance-01
case "${1:-forward}" in
    forward) suffix=; flags='-O2 -Wall -Wextra -Werror'; set -- ;;
    reverse) suffix=-replay; flags='-O3 -Wall -Wextra -Werror'; set -- --reverse ;;
    *) echo "usage: sh $study/replay.sh [forward|reverse]" >&2; exit 2 ;;
esac
bin=kernel/build/inheritance$suffix
obs=kernel/build/vacancy$suffix
make -C kernel all test
make -C kernel/runs/vacancy-01 "BUILD=../../build/vacancy$suffix" "CXXFLAGS=$flags" \
    "../../build/vacancy$suffix/field" "../../build/vacancy$suffix/observe"
make -C "$study" "BUILD=../../build/inheritance$suffix" "CXXFLAGS=$flags" all
"$bin/reference" > "$bin/reference.tsv"
PYTHONPATH=kernel/runs/lineage-01 python3 -B "$bin/natural.py" "$bin/reference.tsv" "$obs" \
    "$bin/lifetime" "$bin/natural" "$@"
python3 -B kernel/runs/placement-01/witness.py "$bin/natural" "$obs/field" "$@"
python3 -B "$study/pedigree.py" "$bin/natural" "$obs/field" "$bin/lifetime" "$bin/pedigrees" "$@"
diff -qr "$study/natural" "$bin/natural"
for result in "$study"/pedigrees/*.tsv "$study"/pedigrees/forks-*/*.tsv; do
    cmp "$result" "$bin/${result#"$study/"}"
done
