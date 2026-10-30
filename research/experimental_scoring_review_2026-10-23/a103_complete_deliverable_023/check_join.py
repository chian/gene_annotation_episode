"""Bounded independent A103 research arithmetic; not a production reader/scorer.

Reads retained synthetic inputs and the parent's inherited native-score receipt.
Writes only a new receipt beside this file, refusing to replace an existing one.
No source/network/model/native-job work is performed.
"""
import json
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def g(p, b):
    assert 0 <= p <= 1 and 0 <= b <= 1
    if p == b:
        return F(0)
    return (p - b) / (1 - b) if p > b else (p - b) / b


def contribution(strata):
    # Each tuple is (foreground positive, foreground total,
    #                background positive, background total).
    for k, n, k0, n0 in strata:
        assert 0 <= k <= n and 0 <= k0 <= n0
    n_total = sum(r[1] for r in strata)
    n0_total = sum(r[3] for r in strata)
    if not n_total or not n0_total:
        return {"C": None, "E": None, "t": None,
                "reason": "empty_population"}
    c = F(0)
    t = F(0)
    for k, n, k0, n0 in strata:
        m = min(F(n, n_total), F(n0, n0_total))
        c += m
        if not m:
            continue
        t += m * g(F(k, n), F(k0, n0))
    return {"C": c, "E": t/c if c else None, "t": t,
            "reason": None if c else "no_common_strata"}


def aggregate(ts, ws):
    if not ts:
        return None
    assert len(ts) == len(ws) and sum(ws) == 1 and all(w >= 0 for w in ws)
    # Explicit zero-weight skip preserves unknown t instead of multiplying None.
    used = [(t, w) for t, w in zip(ts, ws) if w]
    assert all(t is not None and abs(t) <= 1 for t, _ in used)
    s = sum((w * max(t, 0) for t, w in used), F(0))
    o = sum((w * max(-t, 0) for t, w in used), F(0))
    return {"S": s, "O": o, "coordinate": s * (1-o)}


rows = json.loads((BASE / "a103_numerical_sheet_011/synthetic_observation_rows.json").read_text())
selected = [r for r in rows if not r["duplicate_of"] and r["selected_representative"]]
check("30 retained synthetic rows select 28 unique representatives", len(rows) == 30 and len(selected) == 28)
check("selected source-event identities are unique", len({r["source_event_ref"] for r in selected}) == 28)
check("selected dependence blocks are unique", len({r["dependence_block_ref"] for r in selected}) == 28)
counts = defaultdict(lambda: [0, 0])
geometry_ok = True
for r in selected:
    gap = r["anchor_start"] - r["subject_end"] - 1
    endpoint = int(r["same_contig"] and r["subject_strand"] == r["anchor_strand"]
                   and r["intervening_gene_count"] == 0 and gap <= 300)
    geometry_ok &= gap == r["gap_bp"] and endpoint == r["endpoint_value"]
    cell = counts[(r["question_ref"], r["stratum_ref"], r["side"])]
    cell[0] += endpoint
    cell[1] += 1
check("all selected spatial endpoints reconstruct from coordinates", geometry_ok)

fixture = json.loads((BASE / "a103_numerical_sheet_011/synthetic_count_inputs.json").read_text())
questions = []
for q in fixture["questions"]:
    ss = []
    for s in q["strata"]:
        actual = tuple(counts[(q["id"], s["s"], "foreground")]
                       + counts[(q["id"], s["s"], "background")])
        expected = (s["k"], s["n"], s["k0"], s["n0"])
        assert actual == expected
        ss.append(actual)
    questions.append(contribution(ss))
check("six foreground/background strata reproduce retained count inputs", len(questions) == 3)
ts = [q["t"] for q in questions]
weights = [F(1, 3)] * 3
check("complete question contributions reproduce", ts == [F(7,12), F(1,2), F(-1,2)])
check("Q2 separates comparability and association contrast", questions[1]["C"] == F(3,4) and questions[1]["E"] == F(2,3))
total = aggregate(ts, weights)
check("complete synthetic compilation is 65/216", total == {"S":F(13,36),"O":F(1,6),"coordinate":F(65,216)})
check("observed opposition decrease is 13/216", aggregate([ts[0],ts[1],F(0)],weights)["coordinate"] - total["coordinate"] == F(13,216))
missing_bounds = [aggregate([ts[0], x, ts[2]], weights)["coordinate"] for x in (F(-1), F(1))]
check("missing Q2 bounds reproduce", missing_bounds == [F(7,72), F(95,216)])
check("finite unresolved-member contrast bounds reproduce", [g(F(1,2),F(1,4)),g(F(3,4),F(1,4))] == [F(1,3),F(2,3)])
check("all four contrast corners defined", [g(F(p),F(b)) for p,b in ((0,0),(1,1),(1,0),(0,1))] == [0,0,1,-1])
disjoint = contribution([(1,1,0,0),(0,0,1,1)])
check("zero common mass skips unestimable contrast", disjoint == {"C":F(0),"E":None,"t":F(0),"reason":"no_common_strata"})
check("empty background remains unknown", contribution([(1,1,0,0)])["t"] is None)
partial = contribution([(1,2,0,2),(1,2,0,0)])
check("partial overlap skips only its zero-common-mass stratum", partial == {"C":F(1,2),"E":F(1,2),"t":F(1,4),"reason":None})
check("empty extra stratum changes no identified comparison", contribution([(2,3,0,3),(2,3,1,3),(0,0,0,0)]) == questions[0])
check("no questions stays no evidence", aggregate([],[]) is None)
parent_receipt = json.loads((BASE / "a103_sheet_construction_001/a103_parent_arithmetic_002.json").read_text())
native = F(parent_receipt["native_score"]["fraction"])
check("inherited native neighborhood value is .956", native == F(956,1000) and native != F(959,1000))
check("native one-question compilation preserves its value", aggregate([native],[F(1)])["coordinate"] == native)
check("unknown zero-weight question contributes no arithmetic", aggregate([native,None],[F(1),F(0)])["coordinate"] == native)
check("BioY redundancy and RibK selected-list ratios", F(150,127) == F(1)+F(23,127) and F(9,9) == 1)


def encode(value):
    if isinstance(value,F):
        return {"fraction":str(value),"decimal":float(value)}
    if isinstance(value,dict):
        return {k:encode(v) for k,v in value.items()}
    if isinstance(value,list):
        return [encode(v) for v in value]
    return value


receipt = {
    "kind":"bounded_independent_research_join_check_not_reader_implementation",
    "checks_passed":len(checks), "checks":checks,
    "synthetic_question_cells":questions,
    "synthetic_aggregate":total,
    "missing_Q2_coordinate_bounds":missing_bounds,
    "disjoint_positive_sized_populations":disjoint,
    "partial_overlap":partial,
    "native_score_inherited_from_parent_receipt":native,
    "native_pair_or_source_not_requeried":True,
    "primary_papers_or_packets_newly_inspected":0,
    "inherited_check_runs_not_rerun_or_summed":[44,19],
}
with (HERE / "arithmetic_receipt.json").open("x") as out:
    json.dump(encode(receipt),out,indent=2)
    out.write("\n")
print(json.dumps({"checks_passed":len(checks),"coordinate":str(total["coordinate"]),
                  "native_coordinate":str(native),"receipt":"arithmetic_receipt.json"}))
