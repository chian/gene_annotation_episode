"""Research arithmetic only; synthetic fixtures and retained reported counts.

No native program, parser, scientific run, model, or production module is used.
This file does not implement the sheet's populating readers.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCALES = {"BLAST": 0.025, "HMMER": 0.020}
TARGET = set(range(1, 101))


def saturation(bits, scale):
    return -math.expm1(-scale * max(bits, 0.0))


def weight(row, scale_factor=1.0, identity_weight=0.5):
    value = saturation(row["bits"], SCALES[row["tool"]] * scale_factor)
    value *= row["paired_reference_count"] / row["reference_denominator"]
    if row["tool"] == "BLAST":
        identity = row["identical_columns"] / row["alignment_columns"]
        value *= 1 - identity_weight + identity_weight * identity
    return value


def maxima(rows, tool, function, scale_factor=1.0, identity_weight=0.5):
    matching = [r for r in rows if r["tool"] == tool and r["function"] == function]
    return {
        p: max([0.0] + [
            weight(r, scale_factor, identity_weight)
            for r in matching if r["q_from"] <= p <= r["q_to"]
        ])
        for p in TARGET
    }


def calculate(rows, tools=("BLAST", "HMMER"), regions=None,
              scale_factor=1.0, identity_weight=0.5):
    regions = regions or [TARGET]
    own = {t: maxima(rows, t, "F", scale_factor, identity_weight) for t in tools}
    alt = {t: maxima(rows, t, "G", scale_factor, identity_weight) for t in tools}
    blocks = []
    for region in regions:
        assert region and region <= TARGET
        channels = {}
        for t in tools:
            h = sum(own[t][p] for p in sorted(region)) / len(region)
            x = sum(own[t][p] * alt[t][p] for p in sorted(region)) / len(region)
            channels[t] = {"H": h, "X": x, "C": h-x}
        h = sum(c["H"] for c in channels.values()) / len(tools)
        x = sum(c["X"] for c in channels.values()) / len(tools)
        blocks.append({"region_length": len(region), "channels": channels,
                       "H": h, "X": x, "C": h-x})
    native = math.prod(b["C"] for b in blocks) ** (1 / len(blocks))
    h_all = math.prod(b["H"] for b in blocks) ** (1 / len(blocks))
    return {"regions": blocks, "H_F": h_all, "C_native": native,
            "A_F": 0.8, "V_F": 1.0, "feature_qualified": native * 0.8}


rows = [
    dict(id="B_F1", tool="BLAST", function="F", group="F_A",
         bits=80., q_from=1, q_to=60, paired_reference_count=60,
         reference_denominator=60, identical_columns=48, alignment_columns=60),
    dict(id="B_F2", tool="BLAST", function="F", group="F_B",
         bits=60., q_from=41, q_to=100, paired_reference_count=60,
         reference_denominator=60, identical_columns=42, alignment_columns=60),
    dict(id="B_G1", tool="BLAST", function="G", group="G_A",
         bits=65., q_from=1, q_to=60, paired_reference_count=60,
         reference_denominator=60, identical_columns=45, alignment_columns=60),
    dict(id="H_F1", tool="HMMER", function="F", group="F_A",
         bits=50., q_from=1, q_to=50, paired_reference_count=50,
         reference_denominator=60, full_sequence_bits=52.),
    dict(id="H_F2", tool="HMMER", function="F", group="F_B",
         bits=70., q_from=51, q_to=100, paired_reference_count=50,
         reference_denominator=50, full_sequence_bits=72.),
    dict(id="H_F1_related_profile", tool="HMMER", function="F", group="F_A",
         bits=45., q_from=1, q_to=50, paired_reference_count=50,
         reference_denominator=60, full_sequence_bits=47.),
    dict(id="H_G1", tool="HMMER", function="G", group="G_A",
         bits=60., q_from=1, q_to=50, paired_reference_count=50,
         reference_denominator=50, full_sequence_bits=62.),
]

# All native-shaped values are stipulated, not observed search outputs.
omega = 90 * 1_000_000
for row in rows:
    if row["tool"] == "BLAST":
        row["synthetic_effective_search_space"] = omega
        row["synthetic_E"] = omega * 2.0 ** (-row["bits"])
    else:
        row.update(synthetic_tau_bits=5.0, synthetic_lambda_H=math.log(2),
                   synthetic_Z=20000, synthetic_domZ=8)
        tail = 2.0 ** (-(row["bits"] - 5))
        row["synthetic_iE"] = 20000 * tail
        row["synthetic_cE"] = 8 * tail
        row["synthetic_sequence_E"] = 20000 * 2.0 ** (-(row["full_sequence_bits"]-5))
        assert math.isclose(row["synthetic_iE"]/row["synthetic_cE"], 2500,
                            rel_tol=1e-14, abs_tol=0.0)

base = calculate(rows)
w = {r["id"]: weight(r) for r in rows}

# A separately written closed-form derivation checks the position integration.
h_b = 0.6*w["B_F1"] + 0.4*w["B_F2"]
x_b = 0.6*w["B_F1"]*w["B_G1"]
h_h = 0.5*w["H_F1"] + 0.5*w["H_F2"]
x_h = 0.5*w["H_F1"]*w["H_G1"]
expected = (h_b-x_b + h_h-x_h)/2
assert math.isclose(base["C_native"], expected, rel_tol=1e-14, abs_tol=0)
assert w["B_F1"] > w["B_F2"]
assert w["H_F1"] > w["H_F1_related_profile"]
assert 0 <= base["feature_qualified"] <= base["C_native"] <= base["H_F"] <= 1
checks = ["closed-form versus per-position complete calculation"]

# Redelivery, a weaker overlapping profile, and reference duplication.
assert calculate(rows + [deepcopy(rows[0])]) == base
assert calculate([r for r in rows if r["id"] != "H_F1_related_profile"]) == base
checks += ["duplicate invariance", "weaker overlapping profile adds no vote"]

# Unit conversion preserves the index, provided inverse-unit scales transform.
for r in rows:
    x = saturation(r["bits"], SCALES[r["tool"]])
    y = saturation(r["bits"]*math.log(2), SCALES[r["tool"]]/math.log(2))
    assert math.isclose(x, y, rel_tol=1e-14, abs_tol=0)
checks += ["bits/nats operand-and-coefficient conversion"]

# Increasing one native own score cannot reverse its direction at high scores.
direction_count = 0
for idx, row in enumerate(rows):
    for bits in (0., 20., 80., 325., 400., 1000.):
        low = deepcopy(rows)
        high = deepcopy(rows)
        low[idx]["bits"] = bits
        high[idx]["bits"] = bits + 1
        l = calculate(low)["C_native"]
        h = calculate(high)["C_native"]
        if row["function"] == "F":
            assert h >= l-1e-14
        else:
            assert h <= l+1e-14
        direction_count += 1
checks += [f"own/alternative score directions at {direction_count} settings"]

# The full sequence fields are preserved but do not enter domain calculation.
altered_full = deepcopy(rows)
for r in altered_full:
    if r["tool"] == "HMMER":
        r["full_sequence_bits"] += 1000
assert calculate(altered_full) == base
# A displayed E=0 with a finite bit score never produces infinite evidence.
zero_e = deepcopy(rows)
zero_e[0]["synthetic_E"] = 0.0
assert calculate(zero_e) == base
checks += ["full-sequence/domain separation", "displayed-zero E leaves finite bit channel"]

# Two actual required regions are a different declared scope, not print blocks.
two_regions = [set(range(1, 51)), set(range(51, 101))]
two = calculate(rows, regions=two_regions)
assert math.isclose(two["C_native"],
                    math.sqrt(two["regions"][0]["C"]*two["regions"][1]["C"]),
                    rel_tol=1e-14)
assert two["C_native"] <= base["C_native"] + 1e-14
checks += ["required-region geometric mean"]

# Missing one site of the first five-site panel: k=3, m=4, N=5.
panel_lower, panel_upper = 3/5, 4/5
factor_lower, factor_upper = (panel_lower+1)/2, (panel_upper+1)/2
missing_site = {
    "point": None, "panel_bounds": [panel_lower, panel_upper],
    "A_bounds": [factor_lower, factor_upper],
    "qualified_bounds": [base["C_native"]*factor_lower, base["C_native"]*factor_upper],
}
assert math.isclose(missing_site["qualified_bounds"][0], base["feature_qualified"])
assert missing_site["qualified_bounds"][1] > missing_site["qualified_bounds"][0]
checks += ["missing-site interval without point imputation"]

# Unknown identity of B_F1 with other exact inputs: extreme endpoints suffice.
lo, hi = deepcopy(rows), deepcopy(rows)
lo[0]["identical_columns"], hi[0]["identical_columns"] = 0, 60
missing_identity = [calculate(lo)["feature_qualified"], calculate(hi)["feature_qualified"]]
assert missing_identity[0] <= base["feature_qualified"] <= missing_identity[1]
checks += ["missing identity conservative bounds"]

no_alt = calculate([r for r in rows if r["function"] == "F"])
assert math.isclose(no_alt["C_native"], base["H_F"], rel_tol=1e-14)
assert base["C_native"] < no_alt["C_native"]
checks += ["observed opposing hits lower the conditional index"]

# Retained published counts; these are not synthetic measurements.
source_cells = {
    "CodA": {"named_site_exact_identity": 0/1, "named_site_assessed": 1/1,
             "A105_rounded_ratio_excluded_from_A101": 6.7/1.5,
             "native_bits": None},
    "QueF_like": {"reported_domain_identity_range": [16/100, 22/100],
                  "pocket_fraction": 4/4, "query_pattern_count": 0,
                  "source_family_pattern_fraction": 0/8,
                  "proposed_two_panel_average": ((4/4)+(0/1))/2,
                  "native_bits": None},
    "TriA_AtzA": {"identical": 475-9, "pair_identity": (475-9)/475,
                  "query_coverage": 475/475, "reference_coverage": 475/475,
                  "conditional_DNA_identity": (1425-9)/1425,
                  "native_bits": None},
}
assert source_cells["TriA_AtzA"]["identical"] == 466
assert math.isclose(source_cells["TriA_AtzA"]["pair_identity"],
                    0.9810526315789474, rel_tol=1e-14)
assert source_cells["QueF_like"]["proposed_two_panel_average"] == 0.5
assert all(v["native_bits"] is None for v in source_cells.values())
checks += ["retained source counts and absent native scores preserved"]

receipt = {
    "status": "passed_research_arithmetic_only",
    "proposal": "015_not_adopted_or_calibrated",
    "synthetic_native_rows": rows,
    "comparison_weights": w,
    "complete_example_one_region": base,
    "two_required_regions_variant": two,
    "BLAST_only_variant": calculate(rows, tools=("BLAST",)),
    "HMMER_only_variant": calculate(rows, tools=("HMMER",)),
    "no_observed_competitor_variant": no_alt,
    "unsearched_alternatives_sensitivity": [0, base["feature_qualified"]],
    "missing_site": missing_site,
    "missing_BLAST_identity_qualified_bounds": missing_identity,
    "source_populated_components": source_cells,
    "scale_sensitivity": {
        str(s): calculate(rows, scale_factor=s)["feature_qualified"]
        for s in (0.5, 1., 2.)
    },
    "identity_mixture_sensitivity": {
        str(s): calculate(rows, identity_weight=s)["feature_qualified"]
        for s in (0., 0.5, 1.)
    },
    "checks": checks,
    "native_programs_or_production_readers_executed": False,
}
out = HERE / "arithmetic_receipt_001.json"
payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
if out.exists():
    assert out.read_text() == payload, "Preserve prior receipt; issue an additive revision"
else:
    out.write_text(payload)
print(json.dumps({
    "status": receipt["status"], "weights": w,
    "complete_example": base, "two_regions": two,
    "missing_site": missing_site, "missing_identity": missing_identity,
    "scale_sensitivity": receipt["scale_sensitivity"],
    "identity_sensitivity": receipt["identity_mixture_sensitivity"],
    "checks": len(checks), "receipt": str(out),
}, indent=2))
