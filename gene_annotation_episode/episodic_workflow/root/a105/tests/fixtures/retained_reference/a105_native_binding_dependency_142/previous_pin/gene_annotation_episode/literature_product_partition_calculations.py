"""Basic arithmetic on reported fractions; no confidence or annotation credit."""
from fractions import Fraction
import math
from .literature_product_partition_inputs import validate_product_partition_extraction

VERSION = "a105_product_partition_components_v1"
COMPONENTS = ("partition_a_fraction", "partition_b_fraction", "selected_fraction_sum",
              "selected_closure_deviation", "partition_a_over_b")
REASONS = ("source_measurement_unavailable", "source_fraction_unit_unreported",
    "unsupported_source_fraction_unit", "censored_measurement", "basis_unknown", "basis_conflicting",
    "incompatible_fraction_bases", "same_preparation_unknown", "same_preparation_conflicting",
    "same_endpoint_unknown", "same_endpoint_conflicting", "shared_denominator_unknown",
    "shared_denominator_conflicting", "reused_source_observation", "zero_denominator_fraction",
    "numerical_model_range", "qualification_unknown", "qualification_conflicting")
CONDITIONS = ("source_reported_fraction_scale", "same_selected_preparation_and_endpoint",
              "shared_selected_denominator", "dependent_transforms_not_independent_evidence")


def component_roles(component):
    return ("a",) if component == "partition_a_fraction" else ("b",) if component == "partition_b_fraction" else ("a", "b")


def populate_product_partition_components(extraction):
    validate_product_partition_extraction(extraction)
    rows = extraction["quantities"]
    def reason(row):
        return "source_measurement_unavailable" if row is None else row["unavailable_reason"] or (
            "censored_measurement" if row["status"] == "censored" else None)
    reasons = {role: reason(rows[role]) for role in ("a", "b")}
    paired = next((v for v in reasons.values() if v), None)
    if paired is None:
        for role in ("a", "b"):
            if rows[role]["qualification"] in ("unknown", "conflicting"):
                paired = "qualification_" + rows[role]["qualification"]; break
    if paired is None:
        for name, relationship in extraction["selection"]["relationships"].items():
            if relationship["value"] != "supported":
                paired = name + "_" + relationship["value"]; break
    if paired is None:
        for role in ("a", "b"):
            if rows[role]["basis"] in ("unknown", "conflicting"):
                paired = "basis_" + rows[role]["basis"]; break
    if paired is None and rows["a"]["basis"] != rows["b"]["basis"]:
        paired = "incompatible_fraction_bases"
    if paired is None and rows["a"]["measurement_key"] == rows["b"]["measurement_key"]:
        paired = "reused_source_observation"
    # A physical species-contribution witness can identify repeated
    # representations; it is not a replicate count or a spectrum count.
    if paired is None:
        a, b = (extraction["selection"]["quantities"][r]["meanings"]["measurement_identity"] for r in ("a", "b"))
        if a is not None and b is not None and all(a[k] == b[k] for k in ("source_ref", "artifact_ref", "start", "end")):
            paired = "reused_source_observation"
    values = {role: Fraction(row["exact_fraction"]) if row and row["exact_fraction"] is not None else None for role, row in rows.items()}
    cells = {}
    def cell(component, value, unavailable, formula):
        roles = component_roles(component)
        selected = [rows[role] for role in roles]
        if value is not None:
            try:
                converted = float(value)
                if not math.isfinite(converted) or converted == 0 and value != 0:
                    value, unavailable = None, "numerical_model_range"
                else:
                    value = converted
            except (ValueError, OverflowError):
                value, unavailable = None, "numerical_model_range"
        return {"value": value, "unit": "dimensionless" if component == "partition_a_over_b" else "fraction",
            "status": "populated" if value is not None else "unavailable", "unavailable_reason": unavailable,
            "formula": formula, "origin": selected[0]["origin"] if len(roles) == 1 and selected[0] else "derived",
            "approximate": any(row and row["approximate"] for row in selected),
            "threshold": selected[0]["value"] if len(roles) == 1 and selected[0] and selected[0]["status"] == "censored" else None,
            "bound": selected[0]["bound"] if len(roles) == 1 and selected[0] else "none",
            "outside_reported_fraction_range": any(row and row["value"] is not None and not 0 <= row["value"] <= 1 for row in selected),
            "conditional_on": [CONDITIONS[0]] if len(roles) == 1 else list(CONDITIONS)}
    for role in ("a", "b"):
        name = "partition_" + role + "_fraction"
        cells[name] = cell(name, values[role] if reasons[role] is None else None, reasons[role], "reported_fraction_unit_conversion")
    total = values["a"] + values["b"] if paired is None else None
    cells["selected_fraction_sum"] = cell("selected_fraction_sum", total, paired, "a+b")
    cells["selected_closure_deviation"] = cell("selected_closure_deviation", total - 1 if total is not None else None, paired, "(a+b)-1")
    ratio_reason = paired or ("zero_denominator_fraction" if values["b"] == 0 else None)
    cells["partition_a_over_b"] = cell("partition_a_over_b", values["a"] / values["b"] if ratio_reason is None else None, ratio_reason, "a/b")
    return {"version": VERSION, "axis": "A105", "evaluation_scope": "reported_selected_product_partition",
        "cells": cells, "uncertainty_calculation": "not_implemented",
        "interpretation_limits": ["selected_closure_is_not_independent_mass_balance",
            "partition_is_not_rate_specificity_or_molecular_attribution", "no_independence_or_variance_assumption"]}
