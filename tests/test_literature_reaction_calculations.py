"""Synthetic arithmetic/design checks; no new primary-source measurements."""
from copy import deepcopy
from fractions import Fraction
import json
import math

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_reaction_calculations import (
    COMPONENTS, FORMULAS, REASONS, CONDITIONAL_CODES,
    populate_reaction_constraints,
)


def ratio(values=(0.7, 0.9), claim=1, predictions=(0.5,)):
    return {"mode": "independent_units", "ratio_kind": "formed_per_consumed",
        "unit": "mol_per_mol", "origin": "synthetic",
        "observations": [{"measurement_key": f"prep-{index}", "value": value} for index, value in enumerate(values)],
        "mean": None, "sample_sd": None, "independent_n": None,
        "claim": claim, "alternatives": [{"key": f"model-{index}", "prediction": value} for index, value in enumerate(predictions)]}


def summary(mean=1, sd=None, n=None, predictions=(0.5,)):
    result = ratio(predictions=predictions)
    result.update(mode="source_summary", observations=[], mean=mean, sample_sd=sd, independent_n=n)
    return result


def budget(values=(12, 6), coefficients=None, demand=10, complete=True):
    coefficients = coefficients or [1] * len(values)
    return {"basis": "usable_batch", "unit": "umol", "origin": "synthetic",
        "resources_complete": complete,
        "resources": [{"resource_key": f"resource-{index}", "value": value,
                       "lower": value, "upper": value, "coefficient": coefficient}
                      for index, (value, coefficient) in enumerate(zip(values, coefficients))], "demand": demand}


def calculate(r=None, b=None):
    return populate_reaction_constraints({"ratio": r, "budget": b})


def cell(result, key):
    return result["cells"][key]["value"]


def test_checked_synthetic_equations_and_all_component_order():
    result = calculate(ratio(), budget())
    assert tuple(result["cells"]) == COMPONENTS
    assert set(result) == {"version", "inputs", "cells", "comparisons", "ratio_details", "budget_details"}
    assert cell(result, "ratio_mean") == pytest.approx(0.8)
    assert cell(result, "claim_nominal_squared_error") == pytest.approx(0.04)
    assert cell(result, "claim_mean_squared_error") == pytest.approx(0.05)
    assert result["comparisons"][0]["mean_squared_error"]["value"] == pytest.approx(0.1)
    assert cell(result, "reaction_comparison") == pytest.approx(1 / 3)
    assert result["ratio_details"]["independent_n"] == 2
    assert result["ratio_details"]["derived_sample_sd"]["value"] == pytest.approx(math.sqrt(0.02))
    assert cell(result, "resource_capacity") == 6
    assert cell(result, "resource_coverage") == 0.6
    assert cell(result, "resource_comparison") == 0.2
    assert result["budget_details"]["limiting_resource_keys"] == ["resource-1"]


def test_summary_identity_matches_complete_independent_data():
    raw = calculate(ratio((1, 2, 3), claim=3, predictions=(0, 1)))
    smry = summary(mean=2, sd=1, n=3, predictions=(0, 1))
    smry["claim"] = 3
    summarized = calculate(smry)
    for key in ("ratio_mean", "claim_nominal_squared_error", "claim_mean_squared_error", "reaction_comparison"):
        assert cell(raw, key) == cell(summarized, key)
    assert summarized["ratio_details"]["reported_sample_sd"] == 1
    assert "summary_sample_SD_and_exact_n" in summarized["cells"]["claim_mean_squared_error"]["conditional_on"]


@pytest.mark.parametrize("sd,n", [(None, None), (0.2, None), (None, 3)])
def test_missing_sampling_moments_preserve_nominal_not_one_exact_observation(sd, n):
    result = calculate(summary(mean=1, sd=sd, n=n))
    assert cell(result, "ratio_mean") == 1
    assert cell(result, "claim_nominal_squared_error") == 0
    assert cell(result, "claim_mean_squared_error") is None
    assert cell(result, "reaction_comparison") is None
    assert cell(result, "reaction_comparison_lower") == -1
    assert cell(result, "reaction_comparison_upper") == 1
    assert result["ratio_details"]["independent_n"] == n
    assert result["cells"]["claim_mean_squared_error"]["unavailable_reason"] == "sampling_moments_unreported"


def test_explicit_single_unit_summary_differs_from_unknown_n():
    result = calculate(summary(mean=1, n=1))
    assert cell(result, "claim_mean_squared_error") == 0
    assert cell(result, "reaction_comparison") == 1
    assert "explicit_single_unit_summary" in result["cells"]["claim_mean_squared_error"]["conditional_on"]


def test_equal_wrong_predictions_and_double_zero_are_zero_contrast():
    for values in ((1, 1), (0, 2)):
        result = calculate(ratio(values, claim=1, predictions=(1,)))
        assert cell(result, "reaction_comparison") == 0
    assert cell(calculate(ratio((0, 2), claim=1, predictions=(1,))), "claim_mean_squared_error") == 1


def test_conflicting_units_increase_errors_and_can_cancel_relative_support():
    result = calculate(ratio((0, 1), claim=1, predictions=(0,)))
    assert cell(result, "claim_mean_squared_error") == 0.5
    assert result["comparisons"][0]["mean_squared_error"]["value"] == 0.5
    assert cell(result, "reaction_comparison") == 0


def test_signed_scalar_values_are_not_clamped():
    result = calculate(ratio((-1, -3), claim=-2, predictions=(0,)))
    assert cell(result, "ratio_mean") == -2
    assert cell(result, "claim_mean_squared_error") == 1
    assert cell(result, "reaction_comparison") == pytest.approx(2 / 3)
    assert [row["value"] for row in result["ratio_details"]["residuals_by_model"][0]["residuals"]] == [1, -1]


def test_named_alternative_minimum_keeps_all_absolute_errors():
    result = calculate(ratio((0.7, 0.9), predictions=(0.5, 0.8, -2)))
    assert len(result["comparisons"]) == 3
    assert cell(result, "reaction_comparison") == pytest.approx(-2 / 3)
    assert result["comparisons"][2]["mean_squared_error"]["value"] > 7
    assert cell(result, "reaction_comparison_lower") <= cell(result, "reaction_comparison")
    assert cell(result, "reaction_comparison_upper") >= cell(result, "reaction_comparison")


def test_missing_alternative_not_dropped_but_known_minimum_bounds_narrow():
    result = calculate(ratio((0.7, 0.9), predictions=(0.5, None)))
    assert cell(result, "reaction_comparison") is None
    assert cell(result, "reaction_comparison_lower") == -1
    assert cell(result, "reaction_comparison_upper") == pytest.approx(1 / 3)
    assert len(result["comparisons"]) == 2


def test_no_alternatives_is_unknown_not_default_positive():
    result = calculate(ratio(predictions=()))
    assert cell(result, "claim_mean_squared_error") is not None
    assert cell(result, "reaction_comparison") is None
    assert result["cells"]["reaction_comparison"]["unavailable_reason"] == "alternatives_unreported"


def test_missing_claim_and_missing_mean_keep_partial_source_data():
    result = calculate(ratio(claim=None))
    assert cell(result, "ratio_mean") == pytest.approx(0.8)
    assert cell(result, "claim_mean_squared_error") is None
    assert result["comparisons"][0]["mean_squared_error"]["value"] is not None
    result = calculate(summary(mean=None, sd=1, n=3))
    assert cell(result, "ratio_mean") is None
    assert cell(result, "claim_mean_squared_error") is None
    assert result["cells"]["claim_mean_squared_error"]["unavailable_reason"] == "mean_unreported"


def test_alternative_named_claim_has_distinct_model_role():
    r = ratio()
    r["alternatives"][0]["key"] = "claim"
    result = calculate(r)
    assert [row["model_role"] for row in result["ratio_details"]["residuals_by_model"]] == ["claim", "alternative"]


def test_missing_complete_inventory_is_not_assumed_sufficient():
    b = budget(complete=False)
    result = calculate(b=b)
    assert cell(result, "resource_capacity") is None
    assert cell(result, "resource_capacity_lower") == 0
    assert cell(result, "resource_capacity_upper") == 6
    assert cell(result, "resource_coverage") is None
    assert cell(result, "resource_coverage_lower") == 0
    assert cell(result, "resource_coverage_upper") >= 0.6
    assert cell(result, "resource_comparison_upper") >= 0.2
    assert all(key in {"resource-0", "resource-1"} for key in result["budget_details"]["lower_limiting_resource_keys"])


def test_missing_resource_values_use_only_explicit_bounds():
    b = budget(values=(None, 6))
    b["resources"][0].update(lower=2, upper=20)
    result = calculate(b=b)
    assert cell(result, "resource_capacity") is None
    assert cell(result, "resource_capacity_lower") == 2
    assert cell(result, "resource_capacity_upper") == 6
    b["resources"][0].update(lower=None, upper=None)
    result = calculate(b=b)
    assert cell(result, "resource_capacity_lower") == 0
    assert cell(result, "resource_capacity_upper") == 6


def test_known_nominal_values_without_domain_bounds_are_not_exact_bounds():
    b = budget()
    for row in b["resources"]:
        row.update(lower=None, upper=None)
    result = calculate(b=b)
    assert cell(result, "resource_capacity") == 6
    assert cell(result, "resource_capacity_lower") == 0
    assert cell(result, "resource_capacity_upper") is None
    assert result["cells"]["resource_capacity_upper"]["unavailable_reason"] == "capacity_upper_unbounded"
    assert cell(result, "resource_coverage_lower") == 0
    assert cell(result, "resource_coverage_upper") == 1


@pytest.mark.parametrize("complete", [True, False])
def test_explicit_zero_cap_determines_zero_with_unknown_other_resource(complete):
    b = budget(values=(None, None), complete=complete)
    b["resources"][1].update(lower=0, upper=0)
    result = calculate(b=b)
    for key in ("resource_capacity", "resource_capacity_lower", "resource_capacity_upper", "resource_coverage", "resource_coverage_lower", "resource_coverage_upper"):
        assert cell(result, key) == 0
    assert cell(result, "resource_comparison") == -1


def test_unknown_demand_remains_unknown_and_keeps_physical_domain():
    result = calculate(b=budget(demand=None))
    assert cell(result, "resource_capacity") == 6
    assert cell(result, "resource_coverage") is None
    assert cell(result, "resource_coverage_lower") == 0
    assert cell(result, "resource_coverage_upper") == 1
    assert cell(result, "resource_comparison_lower") == -1
    assert cell(result, "resource_comparison_upper") == 1


def test_coefficients_and_capacity_ties_and_no_surplus_bonus():
    result = calculate(b=budget(values=(12, 6), coefficients=(2, 1), demand=3))
    assert cell(result, "resource_capacity") == 6
    assert result["budget_details"]["limiting_resource_keys"] == ["resource-0", "resource-1"]
    assert cell(result, "resource_coverage") == 1
    assert cell(result, "resource_comparison") == 1


@pytest.mark.parametrize("basis,unit", [("supplied_reagent_batch", "uM"), ("usable_rate", "uM_per_min"), ("usable_rate", "umol_per_min")])
def test_distinct_valid_resource_bases_and_supplied_reagents_qualification(basis, unit):
    b = budget()
    b.update(basis=basis, unit=unit)
    result = calculate(b=b)
    assert result["cells"]["resource_capacity"]["unit"] == unit
    assert result["budget_details"]["basis"] == basis
    condition = "supplied_reagents_only" if basis == "supplied_reagent_batch" else "usable_resources_as_declared"
    assert condition in result["cells"]["resource_capacity"]["conditional_on"]


def test_all_missing_has_no_fabricated_values_or_dimensions_and_is_json_serializable():
    result = calculate()
    for key in ("ratio_mean", "claim_nominal_squared_error", "claim_mean_squared_error", "reaction_comparison", "resource_capacity", "resource_coverage", "resource_comparison"):
        assert cell(result, key) is None
    assert result["cells"]["ratio_mean"]["unit"] == "unreported"
    assert result["cells"]["resource_capacity"]["unit"] == "unreported"
    assert cell(result, "reaction_comparison_lower") == -1
    assert cell(result, "resource_capacity_lower") == 0
    json.dumps(result, allow_nan=False)


def test_inputs_are_never_mutated_or_retained_as_mutable_aliases():
    inputs = {"ratio": ratio(), "budget": budget()}
    saved = deepcopy(inputs)
    result = populate_reaction_constraints(inputs)
    assert inputs == saved
    inputs["ratio"]["observations"][0]["value"] = 100
    assert result["inputs"] == saved
    result["inputs"]["budget"]["resources"][0]["value"] = 200
    assert inputs["budget"] == saved["budget"]


def test_constants_cover_every_primary_cell_reason_and_condition():
    for result in (calculate(), calculate(summary()), calculate(ratio(), budget()), calculate(b=budget(complete=False))):
        for component, row in result["cells"].items():
            assert set(row) == {"value", "unit", "status", "formula", "origin", "unavailable_reason", "conditional_on"}
            assert row["formula"] == FORMULAS[component]
            assert row["unavailable_reason"] is None or row["unavailable_reason"] in REASONS
            assert set(row["conditional_on"]) <= set(CONDITIONAL_CODES)


@pytest.mark.parametrize("scale", [1e308, 1e-300])
def test_extreme_squared_errors_do_not_erase_representable_relative_contrast(scale):
    result = calculate(ratio((scale, scale), claim=0, predictions=(-scale,)))
    assert cell(result, "claim_mean_squared_error") is None
    assert result["cells"]["claim_mean_squared_error"]["unavailable_reason"] == "numerical_model_range"
    assert cell(result, "reaction_comparison") == pytest.approx(0.6)


def test_mean_and_SD_scaled_before_float_conversion():
    result = calculate(ratio((1e308, -1e308), claim=0, predictions=(1e308,)))
    assert cell(result, "ratio_mean") == 0
    assert result["ratio_details"]["derived_sample_sd"]["value"] == pytest.approx(math.sqrt(2) * 1e308)
    assert cell(result, "reaction_comparison") == pytest.approx(1 / 3)


def test_extreme_budget_capacity_range_does_not_erase_bounded_coverage():
    result = calculate(b=budget(values=(1e308,), coefficients=(1e-308,), demand=1))
    assert cell(result, "resource_capacity") is None
    assert cell(result, "resource_coverage") == 1
    assert cell(result, "resource_coverage_lower") == 1
    assert cell(result, "resource_coverage_upper") == 1
    result = calculate(b=budget(values=(1e-308,), coefficients=(1e308,), demand=1e-308))
    assert cell(result, "resource_capacity") is None
    assert cell(result, "resource_coverage") == pytest.approx(1e-308, rel=1e-12, abs=0)


def test_exact_bounds_round_outward_for_nonrepresentable_fraction():
    b = budget(values=(1,), coefficients=(3,), demand=2)
    result = calculate(b=b)
    for key, exact in (("resource_capacity", Fraction(1, 3)), ("resource_coverage", Fraction(1, 6)), ("resource_comparison", Fraction(-2, 3))):
        assert Fraction(cell(result, key + "_lower")) <= exact
        assert Fraction(cell(result, key + "_upper")) >= exact


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, "1", {}, [], 10**1000])
def test_invalid_ratio_numeric_inputs(value):
    r = ratio()
    r["observations"][0]["value"] = value
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        calculate(r)


@pytest.mark.parametrize("mutate,code", [
    (lambda r: r.update(extra=1), "closed_fields_required"),
    (lambda r: r.update(mode="raw"), "unsupported_mode"),
    (lambda r: r.update(origin="invented"), "unsupported_origin"),
    (lambda r: r.update(unit="signal_per_signal"), "ratio_kind_unit_mismatch"),
    (lambda r: r.update(observations=[]), "independent_observations_required"),
    (lambda r: r.update(mean=1), "independent_summary_fields_must_be_null"),
    (lambda r: r["observations"][1].update(measurement_key="prep-0"), "duplicate_measurement_key"),
    (lambda r: r["observations"][0].update(measurement_key=" "), "nonempty_identity_required"),
    (lambda r: r["alternatives"].append(deepcopy(r["alternatives"][0])), "duplicate_alternative_key"),
    (lambda r: r["alternatives"][0].update(prediction=True), "finite_number_required"),
])
def test_invalid_ratio_design_relationships(mutate, code):
    r = ratio()
    mutate(r)
    with pytest.raises(ExperimentalContractError, match=code):
        calculate(r)


@pytest.mark.parametrize("n", [0, -1, 1.0, True, "3"])
def test_summary_requires_exact_positive_integer_n(n):
    with pytest.raises(ExperimentalContractError, match="positive_integer_required"):
        calculate(summary(n=n))


def test_summary_cannot_smuggle_replicates_or_single_unit_sample_SD():
    r = summary(sd=0, n=1)
    with pytest.raises(ExperimentalContractError, match="single_unit_has_no_sample_sd"):
        calculate(r)
    r = summary()
    r["observations"] = [{"measurement_key": "rep", "value": 1}]
    with pytest.raises(ExperimentalContractError, match="summary_observations_must_be_empty"):
        calculate(r)


@pytest.mark.parametrize("mutate,code", [
    (lambda b: b.update(resources=[]), "resources_required"),
    (lambda b: b.update(resources_complete=1), "boolean_required"),
    (lambda b: b.update(demand=0), "positive_value_required"),
    (lambda b: b.update(demand=-1), "positive_value_required"),
    (lambda b: b.update(demand=float("nan")), "finite_number_required"),
    (lambda b: b.update(unit="umol_per_min"), "budget_basis_unit_mismatch"),
    (lambda b: b.update(basis="usable_rate"), "budget_basis_unit_mismatch"),
    (lambda b: b["resources"][0].update(value=-1), "nonnegative_value_required"),
    (lambda b: b["resources"][0].update(coefficient=0), "positive_value_required"),
    (lambda b: b["resources"][0].update(lower=15), "ordered_resource_bounds_required"),
    (lambda b: b["resources"][0].update(value=13), "nominal_outside_resource_bounds"),
    (lambda b: b["resources"][1].update(resource_key="resource-0"), "duplicate_resource_key"),
    (lambda b: b["resources"][0].update(extra=1), "closed_fields_required"),
])
def test_invalid_resource_design_relationships(mutate, code):
    b = budget()
    mutate(b)
    with pytest.raises(ExperimentalContractError, match=code):
        calculate(b=b)
