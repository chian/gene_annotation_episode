"""Research-only arithmetic checks; no scientific tool or production scorer."""

import json
from fractions import Fraction
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    first = json.loads((BASE / "checked_arithmetic_001.json").read_text())
    assert Fraction(first["reported_identity_pct"], 100) == Fraction(17, 50)
    assert first["rna_matching_sites"] == 4 * 2 + 2 == 10
    assert first["rna_compared_sites"] == 10
    assert first["rna_selected_site_fraction"] == 1
    assert first["rna_displayed_window_fraction"] == 1
    assert first["modeled_loop_length"] == 238 - 224 + 1 == 15
    assert first["protein_coverage_adjusted_identity"] is None
    assert first["overall_a101_score"] is None

    q_length, r_length = 298, 468
    upper = Fraction(min(q_length, r_length), r_length)
    unpaired = Fraction(r_length - min(q_length, r_length), r_length)
    assert upper == Fraction(149, 234)
    assert unpaired == Fraction(85, 234)
    assert upper + unpaired == 1
    assert upper * r_length == q_length
    assert r_length - q_length == 170
    # Algebra verified across every permissible paired count; these are
    # mathematical checks, not invented observed alignments.
    for paired in range(q_length + 1):
        assert Fraction(paired, r_length) == Fraction(paired, q_length) * upper
    second = {
        "source_doi": "10.1016/j.jmb.2004.01.027",
        "source_scope": "primary_abstract_only",
        "query_length_aa": q_length,
        "reference_length_aa": r_length,
        "reported_identity_pct": 34,
        "identity_denominator": None,
        "length_difference_aa": r_length - q_length,
        "length_ratio_exact": str(upper),
        "length_ratio": float(upper),
        "maximum_paired_reference_fraction": float(upper),
        "minimum_unpaired_reference_fraction": float(unpaired),
        "minimum_unpaired_reference_count": 170,
        "paired_reference_coverage_bounds": [0.0, float(upper)],
        "actual_paired_reference_coverage": None,
        "actual_paired_query_coverage": None,
        "raw_score": None,
        "bit_score": None,
        "e_value": None,
        "overall_a101_score": None,
        "bounds_assumption": "one-to-one nongap residue pairing; no reused query residues",
        "alignment_computed": False,
        "checks_passed": True,
    }
    dest = BASE / "checked_arithmetic_002.json"
    if dest.exists():
        assert json.loads(dest.read_text()) == second
    else:
        dest.write_text(json.dumps(second, indent=2) + "\n")
    print("Both paper packets: arithmetic and missing-value checks passed.")


if __name__ == "__main__":
    main()
