"""Exact arithmetic audit of manual published input scenarios, not a source reader."""
from fractions import Fraction
from itertools import product
from pathlib import Path
import json

DIRECTORY = Path(__file__).resolve().parent
data = json.loads((DIRECTORY / "CANONICAL_INPUT_SCENARIOS_001.json").read_text())
rows = {row["source_tip"]: row for row in data["reference_rows"]}
assert len(rows) == len(data["reference_rows"]) == 6
assert len({row["canonical_source_identity"] for row in rows.values()}) == 6
assert len({row["organism"] for row in rows.values()}) == 6
assert data["clades"]["P5"]["fixed_intended_inventory"] == ["Paer", "Pstu", "Pflu", "Pput", "Avin"]
assert data["clades"]["PA6"]["fixed_intended_inventory"] == ["Paer", "Pstu", "Pflu", "Pput", "Avin", "ACIN"]
assert len(rows["Avin"]["unresolved_source_candidates"]) == 2
assert rows["Avin"]["source_protein_id"] is None
assert rows["Pstu"]["natural_reference"] is True
assert rows["Pstu"]["assayed_construct"].startswith("engineered isolated core")


def coverage(clade, assertion, mapping, avin_candidate):
    inventory = data["clades"][clade]["fixed_intended_inventory"]
    assert avin_candidate in rows["Avin"]["unresolved_source_candidates"]
    n = len(inventory)
    assert len(set(inventory)) == n
    assigned = {}
    for tip in inventory:
        row = rows[tip]
        variable = row["assay_to_tip_mapping_variable"]
        label = row["reported_class"] if variable and mapping[variable] else None
        if label and assertion == "h":
            label = data["entailment_map"][label]
        assigned[tip] = label
    k = sum(label == assertion for label in assigned.values())
    other = sum(label is not None and label != assertion for label in assigned.values())
    unresolved = sum(label is None for label in assigned.values())
    assert k + other + unresolved == n
    value = Fraction(0) if other else Fraction(k, n)
    return n, k, other, unresolved, value


comparisons = [("P5", "f"), ("PA6", "f"), ("PA6", "h")]
author_mapping = data["mapping_scenarios"]["author_mapped_example"]
expected = [(5, 2, 0, 3, Fraction(2, 5)), (6, 2, 1, 3, Fraction(0)), (6, 3, 0, 3, Fraction(1, 2))]
for comparison, result in zip(comparisons, expected):
    for avin in rows["Avin"]["unresolved_source_candidates"]:
        assert coverage(*comparison, author_mapping, avin) == result

scenarios = []
values = {f"{clade}/{assertion}": set() for clade, assertion in comparisons}
for a, b, c in product((0, 1), repeat=3):
    mapping = dict(a=a, b=b, c=c)
    outputs = {}
    for clade, assertion in comparisons:
        first = coverage(clade, assertion, mapping, rows["Avin"]["unresolved_source_candidates"][0])
        second = coverage(clade, assertion, mapping, rows["Avin"]["unresolved_source_candidates"][1])
        assert first == second  # identity ambiguity never manufactures a reference
        n, k, other, unresolved, value = first
        key = f"{clade}/{assertion}"
        values[key].add(value)
        outputs[key] = {"n": n, "k": k, "known_other_count": other,
                        "unresolved_count": unresolved, "C_exact": str(value)}
    assert Fraction(outputs["P5/f"]["C_exact"]) == Fraction(a + b, 5)
    assert Fraction(outputs["PA6/f"]["C_exact"]) == (Fraction(0) if c else Fraction(a + b, 6))
    assert Fraction(outputs["PA6/h"]["C_exact"]) == Fraction(a + b + c, 6)
    scenarios.append({"shared_mapping": mapping, "outputs": outputs})

assert values["P5/f"] == {Fraction(0), Fraction(1, 5), Fraction(2, 5)}
assert values["PA6/f"] == {Fraction(0), Fraction(1, 6), Fraction(1, 3)}
assert values["PA6/h"] == {Fraction(0), Fraction(1, 6), Fraction(1, 3), Fraction(1, 2)}
assert all(point is None for point in data["unconditional_canonical_points"].values())
assert data["whole_target_A104_point"] is None
assert Fraction(2, 4) != Fraction(2, 5)  # query exclusion would change the instance

result = {
    "status": "passed",
    "meaning": "manual input arithmetic audit; no primary biological validation or implemented reader",
    "author_mapping": [
        {"comparison": f"{clade}/{assertion}", "n": n, "k": k,
         "known_other_count": other, "unresolved_count": unresolved,
         "C_exact": str(value), "C_decimal": float(value)}
        for (clade, assertion), (n, k, other, unresolved, value) in zip(comparisons, expected)
    ],
    "mapping_scenarios": scenarios,
    "tested_avin_candidate_count": 2,
    "shared_mapping_scenario_count": len(scenarios),
    "joint_mapping_identity_scenario_count": len(scenarios) * 2,
    "mapping_only_envelopes": {
        key: {"possible_exact_values": [str(v) for v in sorted(vs)],
              "lower_exact": str(min(vs)), "upper_exact": str(max(vs))}
        for key, vs in values.items()
    },
    "unconditional_whole_target_point": None,
    "unverified": ["original assay-to-tip correspondences", "Avin canonical identifier",
                   "independent organismal tree", "query placement", "numerical branch paths"]
}
(DIRECTORY / "ARITHMETIC_RESULTS_001.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "author_mapping": result["author_mapping"],
                  "joint_mapping_identity_scenario_count": result["joint_mapping_identity_scenario_count"],
                  "mapping_only_envelopes": result["mapping_only_envelopes"]}, indent=2))
