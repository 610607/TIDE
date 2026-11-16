#!/usr/bin/env bash
# Run a job list in parallel. Each non-comment line: <name> <tool> key=value...
# where <tool> is ps_probe or ps_run. Output goes to <out_dir>/<name>.tsv (stderr .err).
# Usage: scripts/run_jobs.sh <jobs file> <out dir> [parallel jobs] [bin dir]
set -euo pipefail

jobs_file=${1:?jobs file}
out_dir=${2:?output directory}
parallel=${3:-8}
bin_dir=${4:-build}

for tool in ps_probe ps_run; do
  [[ -x "$bin_dir/$tool" ]] || { echo "missing $bin_dir/$tool; build first (see README.md)" >&2; exit 1; }
done
mkdir -p "$out_dir"
export PHYSUB_BIN="$bin_dir" PHYSUB_OUT="$out_dir"
grep -Ev '^[[:space:]]*(#|$)' "$jobs_file" |
  xargs -P "$parallel" -L 1 sh -c \
    'name=$0; tool=$1; shift; "$PHYSUB_BIN/$tool" "$@" > "$PHYSUB_OUT/$name.tsv" 2> "$PHYSUB_OUT/$name.err" || echo "failed: $name" >&2'
