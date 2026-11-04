"""Synthetic optical contrasts only; no published assay measurements."""
from copy import deepcopy
import json
import math

import numpy as np
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_optical_calculations import (
    OPERANDS_VERSION, PRIMITIVE_ORDER, VERSION, calculate_nadh_optical_rate,
)


def example():
    covariance = np.diag([1e-8, 1e-8, .01, .0001])
    covariance[0, 1] = covariance[1, 0] = 5e-9
    return {"version": OPERANDS_VERSION, "sample_slope": -.012, "blank_slope": -.002,
            "epsilon": 5., "path_length": 1., "covariance": covariance.tolist(),
            "covariance_status": "known", "relation": "applicable_extinction_relation",
            "blank_role": "matched_no_reaction_background", "same_endpoint": "same",
            "matched_window": "same", "rate_window": "source_supported_rate_interval",
            "primitive_observation_refs": ["synthetic-sample", "synthetic-blank",
                                           "synthetic-epsilon", "synthetic-path"]}


def test_matched_background_is_subtracted_once_and_optical_operands_are_not_recovery():
    result = calculate_nadh_optical_rate(example())
    assert result["net_depletion_rate"]["value"] == pytest.approx(2.)
    # Independently: slope variance .0008 minus shared error .0004,
    # extinction contribution (.4)^2*.01=.0016, path contribution 2^2*.0001=.0004.
    assert result["net_depletion_variance"]["value"] == pytest.approx(.0008 - .0004 + .0016 + .0004)
    assert result["net_depletion_variance"]["value"] == pytest.approx(.0024)
    changed = example()
    changed["path_length"] = .5
    assert calculate_nadh_optical_rate(changed)["net_depletion_rate"]["value"] == pytest.approx(4.)


def test_output_is_closed_and_contains_only_derived_endpoint_cells_and_detached_inputs():
    operands = example()
    result = calculate_nadh_optical_rate(operands)
    assert set(result) == {"version", "endpoint", "net_depletion_rate", "net_depletion_variance",
                           "primitive_observation_refs", "input_snapshot"}
    assert result["version"] == VERSION
    assert result["endpoint"] == "NADH_depletion"
    for name, unit in (("net_depletion_rate", "uM/min"), ("net_depletion_variance", "(uM/min)^2")):
        cell = result[name]
        assert set(cell) == {"value", "unit", "status", "formula", "origin",
                             "unavailable_reason", "conditional_on"}
        assert cell["unit"] == unit
        assert cell["origin"] == "derived"
        assert cell["status"] == "populated"
        assert cell["unavailable_reason"] is None
        assert "blank_role=matched_no_reaction_background" in cell["conditional_on"]
    assert "first_order_covariance_propagation" in result["net_depletion_variance"]["conditional_on"]
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_jacobian_variance_matches_independent_finite_difference_of_optical_conversion():
    operands = example()
    # Nonzero correlations with both denominator operands exercise signed terms.
    factor = np.array([[.0001, 0, 0, 0], [.00005, .0001, 0, 0],
                       [.02, -.03, .08, 0], [.002, .001, -.001, .009]])
    covariance = factor @ factor.T
    operands["covariance"] = covariance.tolist()
    x = np.array([operands[name] for name in PRIMITIVE_ORDER])

    def optical(z):
        return -1000 * (z[0] - z[1]) / (z[2] * z[3])

    steps = [1e-6, 1e-6, 1e-4, 1e-5]
    jacobian = []
    for index, h in enumerate(steps):
        delta = np.zeros(4)
        delta[index] = h
        jacobian.append((optical(x + delta) - optical(x - delta)) / (2 * h))
    expected = np.array(jacobian) @ covariance @ np.array(jacobian)
    assert calculate_nadh_optical_rate(operands)["net_depletion_variance"]["value"] == pytest.approx(expected)


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
def test_each_missing_primitive_preserves_uncertainty_without_imputing_rate(name):
    operands = example()
    operands[name] = None
    result = calculate_nadh_optical_rate(operands)
    assert result["input_snapshot"] == operands
    for field in ("net_depletion_rate", "net_depletion_variance"):
        assert result[field]["status"] == "unavailable"
        assert result[field]["value"] is None
        assert result[field]["unavailable_reason"] == "missing_" + name


@pytest.mark.parametrize("field,value,reason", [
    ("relation", "unknown", "optical_relation_unknown"),
    ("relation", "conflicting", "optical_relation_conflicting"),
    ("relation", "not_applicable", "optical_relation_not_applicable"),
    ("blank_role", "unknown", "blank_role_unresolved"),
    ("blank_role", "conflicting", "blank_role_unresolved"),
    ("blank_role", "condition_reference", "blank_role_not_background"),
    ("blank_role", "component_omission", "blank_role_not_background"),
    ("same_endpoint", "different", "endpoint_mismatch_or_unknown"),
    ("same_endpoint", "unknown", "endpoint_mismatch_or_unknown"),
    ("matched_window", "different", "window_mismatch_or_unknown"),
    ("matched_window", "unknown", "window_mismatch_or_unknown"),
    ("rate_window", "static_only", "rate_interval_unestablished"),
    ("rate_window", "interval_mean_only", "rate_interval_unestablished"),
    ("rate_window", "unknown", "rate_interval_unestablished"),
])
def test_units_and_values_do_not_establish_the_required_scientific_relationship(field, value, reason):
    operands = example()
    operands[field] = value
    result = calculate_nadh_optical_rate(operands)
    for name in ("net_depletion_rate", "net_depletion_variance"):
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == reason
        assert f"{field}={value}" in result[name]["conditional_on"]


@pytest.mark.parametrize("matrix,status,reason", [
    (False, "known", "covariance_unreported"),
    (False, "unknown", "covariance_unreported"),
    (True, "unknown", "covariance_status_unknown"),
])
def test_unavailable_covariance_does_not_erase_rate_or_manufacture_independence(matrix, status, reason):
    operands = example()
    if not matrix:
        operands["covariance"] = None
    operands["covariance_status"] = status
    operands["primitive_observation_refs"] = [None] * 4
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == pytest.approx(2.)
    assert result["net_depletion_variance"]["value"] is None
    assert result["net_depletion_variance"]["unavailable_reason"] == reason
    assert result["input_snapshot"] == operands


def test_estimated_covariance_stays_explicitly_estimated_after_propagation():
    operands = example()
    operands["covariance_status"] = "estimated"
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_variance"]["value"] == pytest.approx(.0024)
    assert "covariance_status=estimated" in result["net_depletion_variance"]["conditional_on"]
    assert result["input_snapshot"]["covariance_status"] == "estimated"


@pytest.mark.parametrize("sample,expected", [(-.002, 0.), (.003, -1.)])
def test_exact_zero_and_negative_noisy_estimates_remain_measured_signed_values(sample, expected):
    operands = example()
    operands["sample_slope"] = sample
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == pytest.approx(expected)
    assert result["net_depletion_rate"]["status"] == "populated"
    assert result["net_depletion_variance"]["value"] > 0


def test_known_reused_slope_observation_cancels_rate_and_shared_uncertainty():
    operands = example()
    operands["blank_slope"] = operands["sample_slope"]
    operands["primitive_observation_refs"][1] = operands["primitive_observation_refs"][0]
    operands["covariance"][0][1] = operands["covariance"][1][0] = 1e-8
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == 0.
    assert result["net_depletion_variance"]["value"] == 0.


@pytest.mark.parametrize("unknown_refs", [False, True])
def test_equal_slope_values_do_not_establish_reused_identity(unknown_refs):
    operands = example()
    operands["blank_slope"] = operands["sample_slope"]
    if unknown_refs:
        operands["primitive_observation_refs"] = [None] * 4
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == 0.
    assert result["net_depletion_variance"]["value"] == pytest.approx(.0004)


@pytest.mark.parametrize("contradiction,code", [
    ("value", "reused_identity_value_mismatch"),
    ("covariance", "reused_identity_covariance_mismatch"),
    ("dimension", "reused_identity_dimension_mismatch"),
])
def test_known_identity_cannot_have_contradictory_values_dimensions_or_covariance(contradiction, code):
    operands = example()
    if contradiction == "dimension":
        operands["primitive_observation_refs"][2] = operands["primitive_observation_refs"][0]
    else:
        operands["primitive_observation_refs"][1] = operands["primitive_observation_refs"][0]
        if contradiction == "covariance":
            operands["blank_slope"] = operands["sample_slope"]
    with pytest.raises(ExperimentalContractError, match=code):
        calculate_nadh_optical_rate(operands)


def test_indefinite_covariance_rejected_even_when_rate_direction_variance_is_positive():
    operands = example()
    operands["blank_slope"] = operands["sample_slope"]
    covariance = np.eye(4)
    covariance[2, 3] = covariance[3, 2] = 2.
    operands["covariance"] = covariance.tolist()
    # At zero rate, J has zero denominator derivatives; JΣJᵀ is positive.
    assert np.array([-200., 200., 0., 0.]) @ covariance @ np.array([-200., 200., 0., 0.]) > 0
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        calculate_nadh_optical_rate(operands)


def test_asymmetric_supplied_integers_do_not_become_symmetric_through_float_rounding():
    operands = example()
    covariance = [[0] * 4 for _ in range(4)]
    for i in range(4):
        covariance[i][i] = 2**54
    covariance[0][1], covariance[1][0] = 2**53, 2**53 + 1
    assert float(covariance[0][1]) == float(covariance[1][0])
    operands["covariance"] = covariance
    with pytest.raises(ExperimentalContractError, match="symmetric_covariance_required"):
        calculate_nadh_optical_rate(operands)


def test_tolerated_eigensolver_residue_does_not_authorize_clipping_negative_variance():
    operands = example()
    operands["blank_slope"] = operands["sample_slope"]
    covariance = np.zeros((4, 4))
    covariance[:2, :2] = [[1., 1. + 1e-15], [1. + 1e-15, 1.]]
    operands["covariance"] = covariance.tolist()
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == 0.
    assert result["net_depletion_variance"]["value"] is None
    assert result["net_depletion_variance"]["unavailable_reason"] == "invalid_propagated_variance"
    assert result["input_snapshot"]["covariance"] == covariance.tolist()


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf"), "1", 10**1000])
def test_invalid_numeric_primitives_raise_repairable_contract_errors(name, value):
    operands = example()
    operands[name] = value
    with pytest.raises(ExperimentalContractError) as caught:
        calculate_nadh_optical_rate(operands)
    assert (caught.value.code, caught.value.field) == ("finite_number_required", name)


@pytest.mark.parametrize("name", ["epsilon", "path_length"])
@pytest.mark.parametrize("value", [0., -1.])
def test_nonpositive_optical_denominators_rejected(name, value):
    operands = example()
    operands[name] = value
    with pytest.raises(ExperimentalContractError, match="positive_optical_operand_required"):
        calculate_nadh_optical_rate(operands)


@pytest.mark.parametrize("mutation,code", [
    (lambda x: x.update(extra=1), "closed_fields_required"),
    (lambda x: x.pop("blank_slope"), "closed_fields_required"),
    (lambda x: x.update(version="v0"), "unsupported_operands_version"),
    (lambda x: x.update(covariance=[[1]]), "four_by_four_covariance_required"),
    (lambda x: x["covariance"][0].__setitem__(1, 0.), "symmetric_covariance_required"),
    (lambda x: x["covariance"][0].__setitem__(0, -.1), "positive_semidefinite_covariance_required"),
    (lambda x: x["covariance"][0].__setitem__(0, True), "finite_number_required"),
    (lambda x: x["covariance"][0].__setitem__(0, math.nan), "finite_number_required"),
    (lambda x: x.update(primitive_observation_refs=[None]), "four_primitive_observation_refs_required"),
    (lambda x: x["primitive_observation_refs"].__setitem__(0, " "), "nonempty_observation_ref_required"),
    (lambda x: x["primitive_observation_refs"].__setitem__(0, True), "nonempty_observation_ref_required"),
])
def test_closed_contract_and_malformed_covariance_are_not_missing_science(mutation, code):
    operands = example()
    mutation(operands)
    with pytest.raises(ExperimentalContractError, match=code):
        calculate_nadh_optical_rate(operands)


@pytest.mark.parametrize("name", ["covariance_status", "relation", "blank_role", "same_endpoint",
                                   "matched_window", "rate_window"])
@pytest.mark.parametrize("value", ["unsupported", None, True, []])
def test_interpretation_vocabulary_is_closed(name, value):
    operands = example()
    operands[name] = value
    with pytest.raises(ExperimentalContractError, match="unsupported_" + name):
        calculate_nadh_optical_rate(operands)


@pytest.mark.parametrize("changes", [
    {"sample_slope": 1e308, "blank_slope": 0., "epsilon": 1e-300},
    {"sample_slope": -5e-324, "blank_slope": 0., "epsilon": 1e308, "path_length": 1e308},
])
def test_unrepresentable_nonzero_rates_are_not_inf_or_fabricated_zero(changes):
    operands = example()
    operands.update(changes)
    result = calculate_nadh_optical_rate(operands)
    for name in ("net_depletion_rate", "net_depletion_variance"):
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == "numerical_model_range"
    assert result["input_snapshot"] == operands


@pytest.mark.parametrize("epsilon,variance", [(1e-150, 1e308), (1e100, 5e-324)])
def test_unrepresentable_variance_preserves_finite_signed_rate(epsilon, variance):
    operands = example()
    operands.update(sample_slope=-1e-100, blank_slope=0., epsilon=epsilon)
    covariance = np.zeros((4, 4))
    covariance[0, 0] = variance
    operands["covariance"] = covariance.tolist()
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["status"] == "populated"
    assert result["net_depletion_variance"]["value"] is None
    assert result["net_depletion_variance"]["unavailable_reason"] == "numerical_model_range"


def test_representable_final_rate_survives_intermediate_float_overflow():
    operands = example()
    operands.update(sample_slope=-1e308, blank_slope=1e308, epsilon=1e308,
                    path_length=1000., covariance=np.zeros((4, 4)).tolist())
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["value"] == pytest.approx(2.)
    assert result["net_depletion_variance"]["value"] == 0.


def test_snapshot_and_reference_lists_do_not_alias_in_either_direction():
    operands = example()
    original = deepcopy(operands)
    result = calculate_nadh_optical_rate(operands)
    assert operands == original
    operands["covariance"][0][0] = 100.
    operands["primitive_observation_refs"][0] = "changed-caller"
    assert result["input_snapshot"] == original
    result["primitive_observation_refs"][1] = "changed-result"
    assert result["input_snapshot"]["primitive_observation_refs"] == original["primitive_observation_refs"]
    result["input_snapshot"]["covariance"][1][1] = 200.
    assert operands["covariance"][1][1] == original["covariance"][1][1]


def test_reason_precedence_keeps_the_same_repair_target_for_multiple_missing_conditions():
    operands = example()
    operands.update(sample_slope=None, blank_slope=None, relation="unknown", blank_role="unknown",
                    covariance=None, covariance_status="unknown")
    result = calculate_nadh_optical_rate(operands)
    assert result["net_depletion_rate"]["unavailable_reason"] == "missing_sample_slope"
    assert result["net_depletion_variance"]["unavailable_reason"] == "missing_sample_slope"
    operands.update(sample_slope=-.012, blank_slope=-.002)
    assert calculate_nadh_optical_rate(operands)["net_depletion_variance"]["unavailable_reason"] == "optical_relation_unknown"
