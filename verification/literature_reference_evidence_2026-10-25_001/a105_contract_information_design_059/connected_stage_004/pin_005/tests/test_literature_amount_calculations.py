"""Explicit synthetic numerical inputs; no paper parsing or scientific run."""
from copy import deepcopy
from fractions import Fraction
import math

import pytest

from gene_annotation_episode.literature_amount_calculations import COMPONENTS, populate_amount_components
from gene_annotation_episode.literature_amount_inputs import validate_amount_calculation_inputs
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def quantity(value, role, key, *, unit="mg/ml", kind="estimated", approximate=False):
    return {"value": value, "unit": unit, "status": "observed", "bound": "none",
        "approximate": approximate,
        "qualification": "source_qualified_approximate" if approximate else "reported_point",
        "amount_role": role, "amount_kind": kind, "basis_status": "supported",
        "measurement_key": key, "physical_observation_key": None, "origin": "synthetic", "unavailable_reason": None}


def stock(n=5, d=7):
    return {"quantities": {
        "numerator": quantity(n, "target_mass_estimate", "target-estimate", approximate=True),
        "denominator": quantity(d, "total_protein_mass_estimate", "total-estimate")},
        "comparison_kind": "stock_target_mass_estimate_over_total_mass_estimate",
        "pair_relationship": "supported", "stock_relationship": "same",
        "covariance": None, "covariance_origin": None, "variance_status": "unknown"}


def arms(n=8.4, d=8.8):
    args = stock()
    args.update(comparison_kind="between_arm_nominal_molar_amount", stock_relationship="not_applicable")
    args["quantities"] = {role: quantity(value, "nominal_molecule_amount", role,
        unit="uM", kind="nominal") for role, value in (("numerator", n), ("denominator", d))}
    return args


def covariance(args, matrix=((.25, .1), (.1, .49)), status="estimated"):
    args.update(covariance=[list(row) for row in matrix], covariance_origin="synthetic", variance_status=status)
    return args


def test_stock_estimate_arithmetic_and_factor_alias_without_rate_application():
    args = stock()
    before = deepcopy(args)
    sheet = populate_amount_components(args)
    cells = sheet["cells"]
    assert tuple(cells) == COMPONENTS
    assert cells["numerator_amount"]["value"] == 5
    assert cells["denominator_amount"]["value"] == 7
    assert cells["amount_difference"]["value"] == -2
    assert cells["amount_difference"]["unit"] == "mg/ml"
    assert cells["amount_ratio"]["value"] == 5 / 7
    assert cells["reciprocal_amount_ratio"]["value"] == 1.4
    assert cells["conditional_mass_denominator_factor"]["value"] == 1.4
    assert cells["conditional_mass_denominator_factor"]["approximate"]
    assert sheet["mass_factor_alias_of"] == "reciprocal_amount_ratio"
    assert sheet["mass_factor_applied_to_rate"] is False
    assert sheet["annotation_credit"] is sheet["independent_preparation_count"] is None
    assert "target_and_total_protein_are_different_measurands" in sheet["interpretation_limits"]
    assert args == before
    sheet["inputs"]["quantities"]["numerator"]["value"] = 100
    assert args == before


def test_nominal_arm_comparability_is_not_mass_factor_or_activity_correction():
    sheet = populate_amount_components(arms())
    cells = sheet["cells"]
    assert cells["amount_difference"]["value"] == pytest.approx(-.4)
    assert cells["amount_difference"]["unit"] == "uM"
    assert cells["amount_ratio"]["value"] == pytest.approx(8.4 / 8.8)
    assert cells["reciprocal_amount_ratio"]["value"] == pytest.approx(8.8 / 8.4)
    assert cells["conditional_mass_denominator_factor"]["value"] is None
    assert cells["conditional_mass_denominator_factor"]["unavailable_reason"] == "mass_factor_not_applicable"
    assert not cells["amount_ratio"]["approximate"]
    assert "nominal_amount_ratio_is_not_amount_response_correction" in sheet["interpretation_limits"]


def test_estimate_ratio_above_one_is_retained_without_purity_clamp():
    cells = populate_amount_components(stock(8, 7))["cells"]
    assert cells["amount_ratio"]["value"] == 8 / 7 > 1
    assert cells["conditional_mass_denominator_factor"]["value"] == 7 / 8


@pytest.mark.parametrize("n,d", [(-5, 7), (5, -7), (-5, -7), (0, 7), (5, 0)])
def test_nonpositive_noisy_estimates_survive_but_physical_mass_factor_does_not(n, d):
    cells = populate_amount_components(stock(n, d))["cells"]
    assert cells["numerator_amount"]["value"] == n
    assert cells["denominator_amount"]["value"] == d
    assert cells["amount_difference"]["value"] == n - d
    assert cells["conditional_mass_denominator_factor"]["value"] is None
    if n:
        assert cells["reciprocal_amount_ratio"]["value"] == d / n
    else:
        assert cells["reciprocal_amount_ratio"]["unavailable_reason"] == "zero_numerator_amount"
    if d:
        assert cells["amount_ratio"]["value"] == n / d
    else:
        assert cells["amount_ratio"]["unavailable_reason"] == "zero_denominator_amount"


@pytest.mark.parametrize("field,value,reason", [
    ("pair_relationship", "unknown", "pair_relationship_unknown"),
    ("pair_relationship", "conflicting", "pair_relationship_conflicting"),
    ("comparison_kind", "unknown", "comparison_kind_unknown"),
    ("comparison_kind", "conflicting", "comparison_kind_conflicting"),
    ("stock_relationship", "different", "different_stocks"),
    ("stock_relationship", "unknown", "stock_relationship_unknown"),
    ("stock_relationship", "conflicting", "stock_relationship_conflicting"),
])
def test_unavailable_relationship_preserves_individual_values(field, value, reason):
    args = stock()
    args[field] = value
    cells = populate_amount_components(args)["cells"]
    assert cells["numerator_amount"]["value"] == 5
    assert cells["denominator_amount"]["value"] == 7
    assert cells["amount_ratio"]["value"] is None
    assert cells["amount_ratio"]["unavailable_reason"] == reason


@pytest.mark.parametrize("field,value,reason", [
    ("basis_status", "unknown", "amount_basis_unknown"),
    ("basis_status", "conflicting", "amount_basis_conflicting"),
    ("amount_role", "total_protein_mass_estimate", "amount_role_mismatch"),
    ("amount_kind", "nominal", "amount_kind_unresolved"),
    ("unit", "uM", "incompatible_amount_dimensions"),
    ("qualification", "unknown", "amount_qualification_unknown"),
    ("qualification", "conflicting", "amount_qualification_conflicting"),
])
def test_quantity_meanings_and_dimensions_control_pairing_not_individual_record(field, value, reason):
    args = stock()
    args["quantities"]["numerator"][field] = value
    cells = populate_amount_components(args)["cells"]
    assert cells["numerator_amount"]["value"] == 5
    assert cells["amount_ratio"]["value"] is None
    assert cells["amount_ratio"]["unavailable_reason"] == reason


def test_missing_other_arm_does_not_erase_reported_operand():
    args = stock()
    args["quantities"]["denominator"] = None
    cells = populate_amount_components(args)["cells"]
    assert cells["numerator_amount"]["value"] == 5
    assert cells["denominator_amount"]["value"] is None
    assert cells["amount_ratio"]["unavailable_reason"] == "source_measurement_unavailable"


@pytest.mark.parametrize("bound", ["lt", "le", "gt", "ge"])
def test_censored_threshold_remains_visible_but_never_a_point_ratio(bound):
    args = stock()
    args["quantities"]["numerator"].update(status="censored", bound=bound)
    cells = populate_amount_components(args)["cells"]
    assert cells["numerator_amount"]["value"] is None
    assert cells["numerator_amount"]["threshold"] == 5
    assert cells["numerator_amount"]["bound"] == bound
    assert cells["amount_ratio"]["value"] is None
    assert cells["amount_ratio"]["unavailable_reason"] == "censored_measurement"


def test_reported_point_selection_cannot_erase_lexical_approximation_flag():
    args = stock()
    args["quantities"]["numerator"]["qualification"] = "reported_point"
    cells = populate_amount_components(args)["cells"]
    assert cells["amount_ratio"]["value"] == 5 / 7
    assert cells["amount_ratio"]["approximate"]


def test_approximation_does_not_supply_uncertainty_or_covariance():
    sheet = populate_amount_components(stock())
    for key in COMPONENTS[6:]:
        assert sheet["cells"][key]["value"] is None
        assert sheet["cells"][key]["unavailable_reason"] == "amount_covariance_unreported"
    assert sheet["variance_status"] == "unknown"


@pytest.mark.parametrize("status", ["known", "estimated"])
def test_actual_nonzero_correlated_covariance_with_signed_cross_terms(status):
    sheet = populate_amount_components(covariance(stock(), status=status))
    cells = sheet["cells"]
    ratio_variance = float(Fraction(1, 7)**2 * Fraction(1, 4)
        + Fraction(-5, 49)**2 * Fraction(49, 100)
        + 2 * Fraction(1, 7) * Fraction(-5, 49) * Fraction(1, 10))
    assert cells["amount_difference_variance"]["value"] == pytest.approx(.54)
    assert cells["amount_difference_standard_uncertainty"]["value"] == pytest.approx(math.sqrt(.54))
    assert cells["amount_ratio_variance"]["value"] == pytest.approx(ratio_variance)
    assert cells["amount_ratio_standard_uncertainty"]["value"] == pytest.approx(math.sqrt(ratio_variance))
    assert cells["reciprocal_amount_ratio_variance"]["value"] == pytest.approx(.028)
    assert cells["reciprocal_amount_ratio_standard_uncertainty"]["value"] == pytest.approx(math.sqrt(.028))
    assert sheet["variance_status"] == status
    assert sheet["covariance_origin"] == "synthetic"
    assert "first_order_covariance_propagation" in cells["amount_ratio_variance"]["conditional_on"]
    assert "linear_covariance_propagation" in cells["amount_difference_variance"]["conditional_on"]
    independent = populate_amount_components(covariance(stock(), ((.25, 0), (0, .49))))
    assert independent["cells"]["amount_ratio_variance"]["value"] > cells["amount_ratio_variance"]["value"]


def test_noisy_negative_correlation_is_not_replaced_by_absolute_or_zero_cross_term():
    positive = populate_amount_components(covariance(stock()))
    negative = populate_amount_components(covariance(stock(), ((.25, -.1), (-.1, .49))))
    assert negative["cells"]["amount_ratio_variance"]["value"] > positive["cells"]["amount_ratio_variance"]["value"]
    assert negative["cells"]["amount_difference_variance"]["value"] == pytest.approx(.94)


@pytest.mark.parametrize("fixture,unit", [(stock, "mg/ml"), (arms, "uM")])
def test_variance_units_square_the_entire_quantity_unit(fixture, unit):
    cells = populate_amount_components(covariance(fixture()))["cells"]
    assert cells["amount_difference_variance"]["unit"] == f"({unit})^2"
    assert cells["amount_difference_standard_uncertainty"]["unit"] == unit
    assert cells["amount_ratio_variance"]["unit"] == "dimensionless"


@pytest.mark.parametrize("field", ["measurement_key", "physical_observation_key"])
def test_shared_observation_does_not_supply_a_new_comparison_or_independent_precision(field):
    args = stock(5, 5)
    for row in args["quantities"].values():
        row[field] = "one-physical-measurement"
    covariance(args, ((.25, .1), (.1, .49)))
    with pytest.raises(ExperimentalContractError, match="shared_measurement_covariance_mismatch"):
        populate_amount_components(args)
    covariance(args, ((.25, .25), (.25, .25)))
    cells = populate_amount_components(args)["cells"]
    assert cells["numerator_amount"]["value"] == cells["denominator_amount"]["value"] == 5
    assert cells["amount_ratio"]["unavailable_reason"] == "reused_source_observation"
    assert cells["amount_ratio_variance"]["value"] is None


def test_equal_values_at_distinct_locations_are_not_treated_as_same_observation():
    cells = populate_amount_components(stock(5, 5))["cells"]
    assert cells["amount_ratio"]["value"] == 1
    assert cells["amount_ratio_variance"]["value"] is None


@pytest.mark.parametrize("matrix,error", [
    ([[1]], "two_by_two_covariance_required"),
    ([[1, 0], [.1, 1]], "symmetric_covariance_required"),
    ([[1, 2], [2, 1]], "positive_semidefinite_covariance_required"),
    ([[-1, 0], [0, 1]], "positive_semidefinite_covariance_required"),
    ([[True, 0], [0, 1]], "finite_number_required"),
    ([[math.inf, 0], [0, 1]], "finite_number_required"),
])
def test_covariance_is_not_repaired(matrix, error):
    with pytest.raises(ExperimentalContractError, match=error):
        populate_amount_components(covariance(stock(), matrix))


@pytest.mark.parametrize("mutation,error", [
    (lambda x: x.update(extra=1), "closed_fields_required"),
    (lambda x: x["quantities"]["numerator"].update(value=True), "finite_number_required"),
    (lambda x: x["quantities"]["numerator"].update(value=math.nan), "finite_number_required"),
    (lambda x: x["quantities"]["numerator"].update(measurement_key=None), "measurement_owner_key_required"),
    (lambda x: x["quantities"]["numerator"].update(approximate=False), "source_approximation_not_retained"),
    (lambda x: x.update(variance_status="known"), "covariance_status_without_matrix"),
])
def test_closed_numerical_input_relationships(mutation, error):
    args = stock()
    mutation(args)
    with pytest.raises(ExperimentalContractError, match=error):
        validate_amount_calculation_inputs(args)


def test_extreme_arithmetic_preserves_finite_inputs_without_nonfinite_cells():
    cells = populate_amount_components(stock(1e308, -1e308))["cells"]
    assert cells["numerator_amount"]["value"] == 1e308
    assert cells["amount_difference"]["value"] is None
    assert cells["amount_difference"]["unavailable_reason"] == "numerical_model_range"
    assert cells["amount_difference_variance"]["value"] is None
    assert all(row["value"] is None or math.isfinite(row["value"]) for row in cells.values())
