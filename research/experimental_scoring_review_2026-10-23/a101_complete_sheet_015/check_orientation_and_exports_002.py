"""Additive research check and separated review exports; no native reader."""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent
prior = json.loads((HERE / "arithmetic_receipt_001.json").read_text())


def write_new(name, value):
    path = HERE / name
    text = json.dumps(value, sort_keys=True, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == text, "Preserve existing receipt; add a new revision"
    else:
        path.write_text(text)


# A single query-derived profile comparison: source statistics are native-shaped
# synthetic operands. Biological target length and reference denominator differ.
target_length = 100
reference_length = 200
paired = 60
bits = 50
f = -math.expm1(-0.020*bits)
reference_fraction = paired/reference_length
w = f*reference_fraction
target_fraction = paired/target_length
correct = target_fraction*w
incorrect_if_query_denominator_used_twice = target_fraction*f*(paired/target_length)
assert math.isclose(correct, 0.11378170058914037, rel_tol=1e-14)
assert math.isclose(incorrect_if_query_denominator_used_twice, 2*correct,
                    rel_tol=1e-14)

# Rounding/bound propagation cannot manufacture a finite point from an interval.
low, high = 49.95, 50.05
native_interval = [
    target_fraction*(-math.expm1(-0.020*b))*reference_fraction for b in (low, high)
]
assert native_interval[0] < correct < native_interval[1]
orientation = {
    "status": "passed_synthetic_arithmetic_only",
    "all_native_and_map_inputs_are_synthetic": True,
    "target_length_aa": target_length,
    "characterized_reference_length_aa": reference_length,
    "paired_count": paired,
    "native_domain_bits": bits,
    "f": f, "reference_fraction": reference_fraction,
    "target_fraction": target_fraction, "w": w, "C": correct,
    "incorrect_query_denominator_result": incorrect_if_query_denominator_used_twice,
    "stipulated_rounding_bounds_bits": [low, high],
    "C_rounding_bounds": native_interval,
    "checks": ["biological reference denominator after native-role normalization",
               "stipulated rounding interval enclosure"],
    "native_parser_or_program_executed": False,
}
write_new("orientation_arithmetic_002.json", orientation)

# The first receipt is preserved unchanged. These current exports separate
# paper-specific arithmetic for review with one authority reset per packet.
entries = [
    ("CodA", "10.1021/bi200680y", "source_arithmetic_001_coda.json"),
    ("QueF_like", "10.1021/cb200361w", "source_arithmetic_002_quefl.json"),
    ("TriA_AtzA", "10.1128/JB.183.8.2405-2410.2001", "source_arithmetic_003_tria.json"),
]
for key, doi, name in entries:
    values = prior["source_populated_components"][key].copy()
    if key == "TriA_AtzA":
        values["proposed_pair_identity_factor"] = 0.5+0.5*values["pair_identity"]
        assert math.isclose(values["proposed_pair_identity_factor"],
                            0.9905263157894737, rel_tol=1e-14)
    write_new(name, {
        "DOI": doi, "inspected_extent": "complete retained parent conversion only",
        "origin": "reported counts and derived arithmetic, with explicitly proposed transforms",
        "values": values, "native_score_measurement_supplied": False,
        "research_arithmetic_check": "passed",
    })
current = {k: v for k, v in prior.items() if k != "source_populated_components"}
current["additive_export_note"] = (
    "Same arithmetic as receipt001; paper-specific components exported separately."
)
current["source_component_receipts"] = [name for _, _, name in entries]
current["orientation_receipt"] = "orientation_arithmetic_002.json"
write_new("CURRENT_SYNTHETIC_ARITHMETIC_002.json", current)
print(json.dumps({
    "orientation": orientation,
    "separated_exports": current["source_component_receipts"],
    "current_synthetic_receipt": "CURRENT_SYNTHETIC_ARITHMETIC_002.json",
}, indent=2))
