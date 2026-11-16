"""Refresh the small plotted-data snapshot from ignored local round-3 logs."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def extract_run(path):
    raw = path.read_bytes()
    lines = raw.decode().splitlines()
    config = dict(re.findall(r"(\w+)=([^ ]+)", lines[0]))
    rows = [line.split() for line in lines if line.strip() and not line.startswith("#")]
    final = rows[-1]
    totals_line = next(line for line in lines if line.startswith("# totals"))
    totals = dict(re.findall(r"(\w+)=([\d.]+)", totals_line))
    assert config["mut"] == "0.003" and config["spawn"] == "written"
    assert config["reaper"] == "local" and config["max_age"] == "200"
    assert config["guard"] == "none" and config["site_cap"] == "1"
    assert [int(row[0]) for row in rows] == list(range(2000, 20001, 2000))
    return {
        "source": f"prototype/experiments/coreworld/runs/e3/{path.name}",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "seed": int(config["seed"]), "write": config["write"],
        "fidelity_pct": float(final[4]), "interval_spawns": int(final[3]),
        "final_cpus": int(final[1]), "final_genotypes": int(final[8]),
        "cumulative_reaped": int(totals["reaped"]),
        "cumulative_reaped_age": int(totals["reaped_age"]),
        "age_death_pct": 100 * int(totals["reaped_age"]) / int(totals["reaped"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.runs.glob("E_write_*_m0.003_s*.txt"))
    assert len(paths) == 10, "Expected five seeds in each of two conditions"
    data = {
        "status": "Reanalysis of archived outputs; no simulations executed by this script",
        "configuration": "48x48 torus, 32 bytes/site, four instructions/CPU/round; spawn=written, reaper=local, site_cap=1, max_age=200, guard=none, mutation=0.003",
        "fidelity_definition": "Exact target bytes equal executing CPU's current site at spawn; rounded to two decimal places by original runner; not functional replication fidelity",
        "interval": "Final reported interval, rounds 18000 to 20000",
        "death_window": "Cumulative over all 20000 rounds",
        "runs": [extract_run(path) for path in paths],
    }
    Path(__file__).with_name("probe-data.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Extracted", len(paths), "archived runs")


if __name__ == "__main__":
    main()
