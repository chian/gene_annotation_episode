"""Research-only exact arithmetic and source/reading custody verification.

Creates exclusive output files in this packet. It does not register a reader,
modify production or execute any model-backed investigation.
"""
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import time

from PIL import Image

from gene_annotation_episode.literature_compiled_assay_inputs import _point_reason


OUT = Path(__file__).resolve().parent


def write(name, data):
    with (OUT / name).open("x") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator),
            "decimal": float(value)}


def main():
    data = (OUT / "originals/primary_text.txt").read_bytes()
    source_hash = hashlib.sha256(data).hexdigest()
    selections = [
        ("alternative_control_bound", "<2 nmol/min in the 0.75-mL assay"),
        ("alternative_control_regime", "<1 mM"),
        ("source_tail_correction", "correct for by extrapolation"),
        ("corrected_MTZ_ratio", "∼0.6 mol MTZ"),
        ("low_concentration_regime", "<25 μM"),
        ("high_concentration_regime", ">75 μM"),
        ("electron_account_range", "between 2 and 2.4 mol of H2"),
        ("figure4_inputs", "90 nmol MTZ and 72 nmol CoM-S-S-CoB"),
        ("MTZ_extinction", "9,300 M−1·cm−1"),
        ("source_hydrogen_pressure", "H2 at a pressure of 1.2 bar"),
        ("native_strain", "M. marburgensis (DSM 2133)"),
        ("source_continuing_MTZ", "MTZ reduction continued slowly"),
    ]
    witnesses = []
    for name, phrase in selections:
        token = phrase.encode()
        assert data.count(token) == 1, (name, data.count(token))
        start = data.index(token)
        witnesses.append({"id": name, "artifact": "originals/primary_text.txt",
                          "artifact_sha256": source_hash, "start": start,
                          "end": start + len(token), "literal": phrase,
                          "line": data[:start].count(b"\n") + 1,
                          "original_source": "originals/primary.html",
                          "text_derivation": "TEXT_DERIVATION_001.json"})
    write("SOURCE_WITNESSES_001.json", {"publication": "10.1073/pnas.1016761108",
                                         "witnesses": witnesses})

    original = OUT / "originals/figure4.jpg"
    image = Image.open(original).convert("L")
    assert image.size == (479, 262)
    assert image.getpixel((65, 39)) < 100
    assert any(image.getpixel((75, y)) < 200 for y in range(168, 173))
    assert image.getpixel((190, 181)) < 100
    low, intercept, late = 39, 170, 181
    fast = Fraction(intercept - low)
    total = Fraction(late - low)
    tail = Fraction(late - intercept)
    assert total == fast + tail
    fraction = fast / total
    corners = [Fraction(b - a, c - a)
               for a, b, c in itertools.product((38, 40), (168, 172), (180, 183))]
    assert min(corners) == Fraction(128, 143)
    assert max(corners) == Fraction(134, 142)
    reading = {"source": "originals/figure4.jpg",
               "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
               "coordinate_system": "original 479x262 raster, x rightwards, y downwards",
               "origin": "graph_derived_manual_reading",
               "selected_readings": {
                   "initial_ordinate": {"x": 65, "y": low, "y_enclosure": [38, 40]},
                   "displayed_tail_intercept_at_addition": {"x": 75, "y": intercept,
                                                           "y_enclosure": [168, 172]},
                   "late_trace": {"x": 190, "y": late, "y_enclosure": [180, 183]}},
               "coordinate_counts_are_not_experiments": True,
               "fast_pixel_amplitude": rational(fast), "total_pixel_amplitude": rational(total),
               "additional_pixel_amplitude": rational(tail),
               "retained_fraction": rational(fraction),
               "additional_fraction": rational(1 - fraction),
               "reading_enclosure_lower": rational(min(corners)),
               "reading_enclosure_upper": rational(max(corners)),
               "enclosure_kind": "manual_raster_reading_enclosure_not_statistical_CI",
               "ordinate_scale_cancels": True,
               "physical_covariance": None, "published_slope_uncertainty": None,
               "conditional_on": ["affine_ordinate", "displayed_late_baseline_interpretation",
                                  "late_component_extrapolates_to_addition",
                                  "fast_component_effectively_completed_at_selected_late_point"]}
    write("FIGURE_READING_COMPONENTS_001.json", reading)

    values = {
        "control_rate_threshold_per_volume": Fraction(2) / Fraction("0.75"),
        "reported_corrected_stoichiometry": Fraction("0.6"),
        "relative_excess_vs_named_half_reporter_model": Fraction("0.6") / Fraction("0.5") - 1,
        "electron_account_H2_at_reported_ratio": 1 + 2 * Fraction("0.6"),
        "electron_account_low_condition": 1 + 2 * Fraction("0.5"),
        "electron_account_high_condition": 1 + 2 * Fraction("0.7"),
        "graph_retained_fraction": fraction,
        "graph_additional_fraction": 1 - fraction,
        "graph_enclosure_lower": min(corners),
        "graph_enclosure_upper": max(corners),
    }
    assert values["control_rate_threshold_per_volume"] == Fraction(8, 3)
    assert values["electron_account_H2_at_reported_ratio"] == Fraction(11, 5)
    assert values["relative_excess_vs_named_half_reporter_model"] == Fraction(1, 5)
    write("ARITHMETIC_001.json", {"values": {k: rational(v) for k, v in values.items()},
                                   "not_physical_exactness": "Exact arithmetic on qualified source/reading numbers; scientific approximation retained separately."})

    assert _point_reason({"value": None, "status": "bounded", "bound": "lt",
                          "approximate": False}) == "bounded_operand_compilation_unimplemented"
    assert _point_reason({"value": float(fraction), "status": "point", "bound": "none",
                          "approximate": True}) == "approximate_operand_requires_unimplemented_compilation"
    write("FILLED_COMPONENT_PROPOSAL_001.json", {
        "status": "research_proposal_not_production_schema", "axis": "A105",
        "assayed_subject": "native MvhADG/HdrABC complex from M. marburgensis DSM2133",
        "arrangement": "coexistence of subunits, partners and chemical contributors",
        "endpoint_correction": reading,
        "native_alternative_control": {"threshold": float(Fraction(8, 3)), "relation": "lt",
            "unit": "uM/min", "original": "<2nmol/min in0.75mL", "source_regime": "homodisulfides<1mM",
            "specific_endpoint_relationship_to_Fig4": "unknown",
            "additional_additive_contribution_relationship_to_Fig4": "unknown"},
        "source_corrected_stoichiometry": {"value": 0.6, "approximate": True,
            "unit": "mol MTZ/mol CoM-S-S-CoB added", "correction_stage": "already_applied",
            "uncertainty": None},
        "isolated_initial_rate": None, "isolated_initial_rate_reason": "matched_same_scale_q_and_g_not_established",
        "physical_effect_variance": None, "annotation_credit": None,
        "new_graders": 0, "new_selected_operations": 0})

    write("PACKET_CHECK_001.json", {"status": "passed", "observed_unix": time.time(),
        "source_spans_checked": len(witnesses), "exact_arithmetic_results": len(values),
        "reading_enclosure_corners": len(corners), "original_image_reading_support_checks": 3,
        "actual_existing_compiler_guard_checks": 2,
        "scope": "research source custody, graph-reading arithmetic and two existing eligibility guards",
        "not_established": ["independent physical replicates", "experimental covariance",
            "unconditional molecular effect isolation", "selected episode execution or typed delivery",
            "new implemented grader", "complete A105 scoring"]})
    print(json.dumps({"status": "passed", "source_spans": len(witnesses),
                      "arithmetic_results": len(values), "new_graders": 0}))


if __name__ == "__main__":
    main()
