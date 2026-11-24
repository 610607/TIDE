"""Export the second-half strict-site ledger from the eight completed v31 probe outputs."""
import csv
import sys
from pathlib import Path

import v19
from v31_mass import END, INTERVAL, load


def late_windows(path):
    census, final = load(path)
    events = v19.load(path)
    ticks = list(range(INTERVAL, END + 1, INTERVAL))
    if int(final["tick"]) != END or sorted(census) != ticks or sorted(events) != ticks:
        raise ValueError(f"{path}: incomplete v31 record")
    previous = 1  # one strict polite founder
    for tick in ticks:
        e = events[tick]
        f = e["fate"]
        copies, reignitions, self_ignitions = e["born"]["rep"]
        decay, wick = e["end"]["rep"]
        gains, losses = int(f["in_in_place"]), int(f["out_in_place"])
        found = e["found"][0]
        activation_net = copies + reignitions + self_ignitions - decay - wick
        inplace_net = gains - losses
        closing = int(census[tick]["census"]["strict"])
        if (int(f["rep_prev"]) != previous or previous + activation_net + inplace_net != closing
                or int(f["balance"]) != closing or closing != int(f["rep_now"])
                or sum(e["change"]["rep"][1:]) != losses
                or found + sum(e["change"][s][0] for s in v19.ST[1:]) != gains
                or sum(int(e["out"][s]) for s in v19.WR) != losses
                or any(int(f[k]) for k in ("census_mismatch", "untracked", "stale", "replaced", "starved"))):
            raise ValueError(f"{path}: strict-site ledger or observer check failed at {tick}")
        if tick > END // 2:
            yield dict(start=tick - INTERVAL, end=tick, opening=previous, closing=closing,
                       strict_copies=copies, strict_reignitions=reignitions, strict_self=self_ignitions,
                       whole_decay=decay, wick=wick, inplace_gains=gains, found_within_gains=found,
                       inplace_losses=losses, self_written_losses=int(e["out"]["self"]),
                       activation_net=activation_net, inplace_net=inplace_net, net=closing - previous)
        previous = closing


def main():
    run_dir = Path(sys.argv[1])
    rows = []
    for rule in ("zero", "fail"):
        for seed in (1, 2):
            for mass in (48, 64):
                path = run_dir / f"{rule}_s{seed}_m{mass}.tsv"
                rows.extend(dict(rule=rule, seed=seed, mass=mass, **window)
                            for window in late_windows(path))
    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
