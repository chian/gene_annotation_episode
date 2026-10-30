"""Research-only source parsing and conditional arithmetic, no runtime wiring.

No preparation-resolved measurements are reconstructed from summary data.
The paper's central estimates are not silently declared arithmetic means.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast


def main():
    original = (HERE / "sources/elife-06181-v2.pdf").read_bytes()
    literal = (HERE / "sources/elife-06181-v2.txt").read_bytes()
    text = literal.decode()
    source_ref = "@elife2015AP"
    anchors = {}

    def witness(quote, *, after=None):
        start_character = text.index(quote, text.index(after) if after else 0)
        start = len(text[:start_character].encode())
        result = {"source_ref": source_ref, "representation": "text", "start": start,
                  "end": start + len(quote.encode()), "quote": quote}
        assert literal[result["start"]:result["end"]].decode() == quote
        return result

    def numeric(w, token):
        i = w["quote"].index(token)
        return {"witness": w, "number_start": i, "number_end": i + len(token)}

    def meaning(value, *quotes):
        return {"value": value, "witnesses": [witness(q) for q in quotes]}

    # Each exact line is retained; selection uses existing source-span reader.
    row_text = next(line for line in text.splitlines() if line.strip().startswith("D101A/E322Y#"))
    marker_text = "#The mutant was expressed in two independent enzyme preparations and standard deviations are from activity"
    row = witness(row_text)
    footnote = witness(marker_text)
    unit = witness("M−1s−1", after="Table 1. Kinetic constants")
    anchors.update(row=row, independent_preparation_footnote=footnote, unit_header=unit)
    measured = {
        "parameter_kind": meaning("catalytic_efficiency", "kcat/KM (M−1s−1)"),
        "subject": {"organism": witness("E. coli"), "genotype": None,
                    "molecule": witness("AP mutant", after="Table 1. Kinetic constants"),
                    "construct": witness("D101A/E322Y#", after="Table 1. Kinetic constants")},
        "context": {"substrate": witness("pNPP"), "preparation": footnote,
                    "experiment": witness("Table 1. Kinetic constants for WT and mutant AP*,†"),
                    "experimental_system": None, "conditions": None,
                    "endpoint": witness("400 nm"), "normalization": unit},
        "measurement_identity": None,
        "measurement": {"number": numeric(row, "3.1"), "unit": unit},
        "qualification": {"value": "reported_point", "witnesses": [row]},
        "uncertainty": {
            "statistic": {"value": "sd", "witnesses": [footnote]},
            "magnitude": numeric(row, "0.1"), "interval": None,
            "unit": None,
            "unit_relationship": {"value": "same_as_parameter", "witnesses": [row, unit]},
            "confidence_level": None,
            "count": numeric(footnote, "two"),
            "repetition_basis": {"value": "biological_preparations", "witnesses": [footnote]},
            # The publication explicitly owns the preparation-level SD, but does
            # not expose its complete fitting/averaging hierarchy.
            "estimate_basis": {"value": "unknown", "witnesses": []},
        },
    }
    selection = {
        "version": "a105_kinetic_source_selection_v1", "source_ref": source_ref,
        "source_kind": "primary_source", "numerator": measured, "denominator": None,
        "comparison": {key: {"value": "unknown", "witnesses": []} for key in (
            "subject_relationship", "parameter_definition_relationship", "substrate_arrangement",
            "comparison_scope", "nonintended_conditions_relationship")},
    }

    def read_source(ref, representation):
        assert ref == source_ref
        content = original if representation == "original" else literal
        return {"artifact_ref": "sha256_" + hashlib.sha256(content).hexdigest(), "content": content}

    extraction = read_kinetic_inputs(selection, read_source=read_source)
    operand = extraction["calculation_inputs"]["numerator"]
    sheet = populate_kinetic_contrast(extraction["calculation_inputs"])
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    check("source_value_and_unit_conversion", math.isclose(operand["value"], 3.1 * 60 / 1e6))
    check("source_sd_and_unit_conversion", math.isclose(operand["uncertainty"]["magnitude"], 0.1 * 60 / 1e6))
    check("literal_english_two_count", operand["uncertainty"]["count"] == 2)
    check("source_established_preparations", operand["uncertainty"]["repetition_basis"] == "biological_preparations")
    check("no_raw_measurement_id_fabricated", operand["physical_measurement_id"] is None)
    check("no_model_fabricated", sheet["model"] is None)
    check("no_assay_confidence_score_created", sheet["cells"]["source_profile_log_ratio"]["value"] is None)
    check("available_single_parameter_preserved", sheet["cells"]["numerator_parameter"]["value"] == operand["value"])

    # Native-unit numbers below are a checked reversal of the reader's exact
    # supported factor, not freshly entered scientific operands.
    x = operand["value"] / (60 / 1e6)
    s = operand["uncertainty"]["magnitude"] / (60 / 1e6)
    n = operand["uncertainty"]["count"]
    se = s / math.sqrt(n)
    t95_df1 = 1 / math.tan(math.pi * 0.025)
    halfwidth = t95_df1 * se
    native_unit = "M^-1 s^-1"
    conditional = {
        "source_estimate": x, "reported_between_preparation_sd": s,
        "source_established_preparation_count": n,
        "relative_reported_sd": s / abs(x),
        "estimated_variance_of_equal_weight_preparation_mean": s * s / n,
        "estimated_se_of_equal_weight_preparation_mean": se,
        "relative_mean_se_if_reported_estimate_is_mean": se / abs(x),
        "t95_df1": t95_df1,
        "conditional_95_percent_halfwidth": halfwidth,
        "conditional_95_percent_mean_interval": [x - halfwidth, x + halfwidth],
        "unit": native_unit,
        "conditions_for_se": ["independent common-mean finite-variance preparation estimates",
                              "reported SD uses preparation estimates and n-1 denominator"],
        "additional_conditions_for_interval": ["normally distributed preparation estimates",
                                               "reported central estimate is their arithmetic mean",
                                               "rounded summaries treated as nominal operands"],
        "source_claim_of_normality": False,
        "source_explicit_arithmetic_mean_label": False,
        "raw_preparation_values": None,
        "cross_construct_covariance": None,
        "assay_error_probability": None,
        "annotation_credit": None,
    }
    check("se_combines_sd_and_count_without_more_observations", math.isclose(se, 0.07071067811865475))
    check("normal_interval_uses_df_one_not_z", math.isclose(t95_df1, 12.7062047361747))
    check("conditional_interval_retains_native_units", math.isclose(halfwidth, 0.89846435320937))
    check("precision_normalization_is_unit_invariant", math.isclose(
        se / abs(x), operand["uncertainty"]["magnitude"] / math.sqrt(n) / abs(operand["value"])))

    # Second row is read literally for the matched K328 substitution contrast.
    # Its SD is NOT promoted to a between-preparation SD.
    yrow_text = next(line for line in text.splitlines() if line.strip().startswith("D101A/E322Y/K328A "))
    yw = witness(yrow_text)
    import re
    match = re.search(r"D101A/E322Y/K328A\s+([0-9.]+) \(([0-9.]+)\)", yrow_text)
    assert match
    y, ys = map(float, match.groups())
    contrast = {"reference_row": row, "test_row": yw,
        "reference_source_estimate": x, "test_source_estimate": y,
        "test_reported_sd": ys, "test_source_established_independent_preparation_count": None,
        "difference_reference_minus_test": x-y, "test_over_reference": y/x,
        "fractional_decrease": 1-y/x, "reference_over_test": x/y,
        "unit": native_unit, "difference_between_preparation_se": None,
        "unavailable_reason": "test_independent_preparation_count_and_cross_construct_dependence_not_established",
        "variance_formula": "Var(Xbar-Ybar)=Var(Xbar)+Var(Ybar)-2*Cov(Xbar,Ybar)",
        "scientific_scope": "adding K328A to D101A/E322Y; reported-protocol contrast only",
        "annotation_credit": None}
    check("matched_substitution_contrast_uses_actual_rows", math.isclose(x-y, 2.0))
    check("retained_and_decreased_fractions_sum_to_one", math.isclose(y/x + (1-y/x), 1))
    check("missing_test_physical_n_stays_unknown", contrast["test_source_established_independent_preparation_count"] is None)
    check("missing_covariance_does_not_become_zero", contrast["difference_between_preparation_se"] is None)

    outputs = {"source_selection.json": selection, "existing_reader_output.json": extraction,
               "existing_kinetic_sheet_output.json": sheet,
               "conditional_precision_cells.json": conditional,
               "matched_substitution_components.json": contrast,
               "exact_source_anchors.json": anchors,
               "arithmetic_receipt.json": {"passed": len(checks), "checks": checks,
                   "scope": "research arithmetic and existing pure source reader; no biological suite or episode execution"}}
    for name, value in outputs.items():
        (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"passed": len(checks), "files_written": list(outputs)}, indent=2))


if __name__ == "__main__":
    main()
