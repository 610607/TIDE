"""Audit the confirmed field pedigree from the complete fetch/8 event stream."""
import csv
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(trace_path, output_path):
    with trace_path.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    births = {(int(r["target"]), int(r["tick"])): r for r in rows if r["effect"] == "birth"}

    def actor(r):
        return (int(r["actor"]), int(r["born"]))

    chain = [(58, 123)]
    while chain[-1] in births:
        chain.append(actor(births[chain[-1]]))
    chain.reverse()
    require(chain == [(36, 0), (35, 52), (34, 78), (42, 93), (50, 108), (58, 123)],
            "field parentage differs")
    for child in chain[1:]:
        expected = b"R.CLD" if child == (35, 52) else b"R.CJD"
        require(bytes.fromhex(births[child]["product_hex"]) == expected, "unexpected product bytes")

    witness = []
    mutation = []
    transmissions = {(42, 93): (50, 108), (50, 108): (58, 123)}
    for r in rows:
        cpu = actor(r)
        site, tick = int(r["target"]), int(r["tick"])
        ancestry = r["effect"] == "birth" and (site, tick) in chain
        origin_copy = cpu == (35, 52) and site == 34 and tick <= 78 and r["effect"] == "copy"
        generation = cpu in transmissions and tick <= transmissions[cpu][1]
        if ancestry or origin_copy or generation:
            witness.append(r)
        if origin_copy and r["input"] != r["output"]:
            mutation.append((tick, int(r["write_offset"]), int(r["input"]), int(r["output"])))
    require(mutation == [(74, 3, ord("L"), ord("J"))], "unexpected mutation history")
    for cpu, child in transmissions.items():
        copies = [r for r in witness if actor(r) == cpu and r["effect"] == "copy"]
        require([int(r["read_site"]) for r in copies] == [cpu[0]] * 5 and
                [int(r["target"]) for r in copies] == [child[0]] * 5 and
                [int(r["write_offset"]) for r in copies] == list(range(5)) and
                bytes(int(r["output"]) for r in copies) == b"R.CJD", "copy provenance differs")
        require([int(r["fetch_site"]) for r in copies] == [cpu[0]] + [cpu[0] + 1] * 4,
                "instruction provenance differs")

    founder = (34, 78)
    depth, alive = {}, set()
    last_death = 0
    for r in rows:
        cpu = actor(r)
        child = (int(r["target"]), int(r["tick"]))
        if r["effect"] == "birth" and (child == founder or cpu in depth):
            if bytes.fromhex(r["product_hex"]) == b"R.CJD":
                depth[child] = depth.get(cpu, 0) + 1
                alive.add(child)
        if r["effect"] == "death" and cpu in alive:
            last_death = int(r["tick"])
            alive.remove(cpu)
    stats = (len(depth), max(depth.values()), max(t for _, t in depth), last_death, len(alive))
    require(stats == (6, 4, 177, 258, 0), "clonal persistence differs")
    with output_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(witness)
    print("Field pedigree and copy sources verified. Six clonal births, last death at tick 258.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: audit_case.py FULL_TRACE.tsv CASE_TRACE.tsv")
    audit(Path(sys.argv[1]), Path(sys.argv[2]))
