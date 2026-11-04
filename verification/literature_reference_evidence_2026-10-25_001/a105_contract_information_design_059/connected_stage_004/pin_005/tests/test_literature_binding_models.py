"""Synthetic binding measurement fixtures; no experimental source acquisition."""
from copy import deepcopy
from hashlib import sha256
import json
import math

import numpy as np
import pytest
from scipy.optimize import minimize
from scipy.stats import norm

from gene_annotation_episode.literature_binding_calculations import populate_binding_contrast
from gene_annotation_episode.literature_binding_models import (
    COMPONENTS, CONDITIONAL_CODES, FORMULAS, REASONS,
    binding_model_operand_keys, populate_binding_model,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def row(value=10, *, index=0, relation="eq", ligand="reference"):
    return {
        "value": value, "relation": relation, "reported_spread": None,
        "origin": "synthetic", "subject": "synthetic protein", "state": "synthetic state",
        "experiment": "synthetic assay", "ligand": ligand,
        "source": {"source_ref": "synthetic source", "artifact_ref": "synthetic artifact",
                   "representation": "synthetic_fixture", "table_id": "synthetic table",
                   "row_index": index, "locator": {"row_index": index, "column": "parameter"},
                   "expression": "synthetic measurement"},
    }


def sheet(reference=10, test=20, *, reference_relation="eq", test_relation="eq"):
    return from_rows([row(reference, relation=reference_relation)],
                     [row(test, index=1, relation=test_relation, ligand="test")])


def from_rows(reference_rows, test_rows):
    return populate_binding_contrast({
        "version": "binding_parameter_extraction_v1", "parameter_kind": "ic50", "unit": "nM",
        "uncertainty_basis": "fit_to_averaged_curve", "minimum_experiment_count": 3,
        "reference_rows": reference_rows, "test_rows": test_rows,
    })


def model(binding_sheet, covariance=None, **updates):
    keys = binding_model_operand_keys(binding_sheet)
    result = {
        "version": "known_normal_log_binding_v1", "parameter_kind": binding_sheet["parameter_kind"],
        "measurement_order": ["reference", "test"],
        "measurement_keys": [keys["reference"], keys["test"]],
        "log_covariance": [[.04, .01], [.01, .09]] if covariance is None else covariance,
        "variance_status": "known", "censoring_model": "threshold_of_log_estimate",
        "log_basis": "natural_log_nM", "origin": "synthetic",
    }
    result.update(updates)
    return result


def value(result, name):
    return result["cells"][name]["value"]


def test_printed_joint_point_example_and_detachment_closed_outputs():
    source = sheet()
    error_model = model(source)
    before = deepcopy((source, error_model))
    result = populate_binding_model(source, error_model)
    assert result["version"] == "binding_model_sheet_v1"
    assert result["contrast_meaning"] == "test_parameter_exceeds_reference"
    assert value(result, "log_parameter_contrast") == pytest.approx(.6931471805599453)
    assert value(result, "log_contrast_noise_variance") == pytest.approx(.11)
    assert value(result, "log_contrast_noise_sd") == pytest.approx(.33166247903554)
    assert value(result, "source_profile_log_ratio") == pytest.approx(2.1838773359918244)
    assert value(result, "source_signed_index") == pytest.approx(.7975846370428177)
    assert result["annotation_credit"] is result["independent_preparation_count"] is None
    assert result["minimum_experiment_count"] == 3
    assert result["source_uncertainty_basis"] == "fit_to_averaged_curve"
    assert set(result["cells"]) == set(COMPONENTS)
    for name, cell in result["cells"].items():
        assert set(cell) == {"value", "relation", "unit", "status", "formula", "origin",
                             "unavailable_reason", "bound_kind", "confidence_bound",
                             "parameter_identification_bound", "conditional_on"}
        assert cell["formula"] == FORMULAS[name]
        assert cell["unavailable_reason"] is None or cell["unavailable_reason"] in REASONS
        assert set(cell["conditional_on"]) <= set(CONDITIONAL_CODES)
        assert cell["confidence_bound"] is cell["parameter_identification_bound"] is None
    assert (source, error_model) == before
    result["model"]["log_covariance"][0][0] = 99
    assert (source, error_model) == before
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("a,b", [(10, 20), (20, 10), (10, 10), (2, 3)])
@pytest.mark.parametrize("covariance", [
    [[.04, .01], [.01, .09]], [[1, -.3], [-.3, 2]], [[.2, 0], [0, .2]],
])
def test_two_point_profile_matches_independent_constrained_normal_fit(a, b, covariance):
    source = sheet(a, b)
    result = populate_binding_model(source, model(source, covariance))
    y = np.log([a, b])
    precision = np.linalg.inv(covariance)
    def loss(mu):
        residual = y - mu
        return .5 * residual @ precision @ residual
    boundary = minimize(loss, [np.mean(y)] * 2,
        constraints={"type": "eq", "fun": lambda x: x[1] - x[0]},
        method="SLSQP", options={"ftol": 1e-13, "maxiter": 300})
    assert boundary.success, boundary.message
    expected = math.copysign(boundary.fun, b - a) if a != b else 0
    assert value(result, "source_profile_log_ratio") == pytest.approx(expected, abs=1e-11)
    if a == b:
        assert value(result, "source_profile_log_ratio") == value(result, "source_signed_index") == 0
    assert result["diagnostics"]["boundary_log_likelihood"] is None


@pytest.mark.parametrize("censored_index", [0, 1])
@pytest.mark.parametrize("relation", ["gt", "ge", "lt", "le"])
@pytest.mark.parametrize("correlation", [-.75, 0, .75])
def test_one_censor_matches_independent_two_mean_likelihood_optimization(censored_index, relation, correlation):
    covariance = np.array([[.3, correlation * math.sqrt(.3 * .7)],
                           [correlation * math.sqrt(.3 * .7), .7]])
    kwargs = {"reference_relation" if censored_index == 0 else "test_relation": relation}
    source = sheet(10, 14, **kwargs)
    result = populate_binding_model(source, model(source, covariance.tolist()))
    y = np.log([10, 14])
    d, c = 1 - censored_index, censored_index
    vd, vc, cross = covariance[d, d], covariance[c, c], covariance[d, c]
    sc = math.sqrt(vc - cross * cross / vd)
    right = relation in ("gt", "ge")
    direction = (1 if right else -1) * (1 if c == 1 else -1)
    def loss(mu):
        conditional_mean = mu[c] + cross / vd * (y[d] - mu[d])
        threshold = (y[c] - conditional_mean) / sc
        log_event = norm.logsf(threshold) if right else norm.logcdf(threshold)
        return .5 * (y[d] - mu[d]) ** 2 / vd - log_event
    # Optimize both actual means in the disfavored half-plane. This verifies
    # the equality reduction against a distinct parameterization/optimizer.
    fit = minimize(loss, [y.mean(), y.mean()], method="SLSQP",
        constraints={"type": "ineq", "fun": lambda mu: -direction * (mu[1] - mu[0])},
        options={"ftol": 1e-12, "maxiter": 500})
    assert fit.success, fit.message
    assert value(result, "source_profile_log_ratio") == pytest.approx(direction * fit.fun, rel=2e-9, abs=1e-10)
    assert fit.x[0] == pytest.approx(fit.x[1], abs=1e-6)
    assert result["cells"]["source_profile_log_ratio"]["status"] == "populated"
    assert result["cells"]["source_profile_log_ratio"]["relation"] == "eq"
    assert result["cells"]["source_profile_log_ratio"]["bound_kind"] is None
    assert result["cells"]["log_parameter_contrast"]["status"] == "reported_limit"
    assert result["diagnostics"]["boundary_log_likelihood"] == pytest.approx(-fit.fun, rel=2e-9)


@pytest.mark.parametrize("relation,inverse", [("gt", "lt"), ("ge", "le"), ("lt", "gt"), ("le", "ge")])
def test_swap_and_log_reflection_symmetry_for_censoring(relation, inverse):
    covariance = [[.4, .12], [.12, .8]]
    original = sheet(10, 14, test_relation=relation)
    swapped = sheet(14, 10, reference_relation=relation)
    reflected = sheet(1 / 10, 1 / 14, test_relation=inverse)
    initial = populate_binding_model(original, model(original, covariance))
    swapped_result = populate_binding_model(swapped, model(swapped, [[.8, .12], [.12, .4]]))
    reflected_result = populate_binding_model(reflected, model(reflected, covariance))
    for name in ("source_profile_log_ratio", "source_signed_index"):
        assert value(swapped_result, name) == pytest.approx(-value(initial, name))
        assert value(reflected_result, name) == pytest.approx(-value(initial, name))


def test_equal_censored_threshold_is_not_a_point_or_exact_zero():
    detected = sheet(10, 10)
    censored = sheet(10, 10, test_relation="gt")
    point_result = populate_binding_model(detected, model(detected))
    limit_result = populate_binding_model(censored, model(censored))
    assert value(point_result, "source_profile_log_ratio") == 0
    assert value(limit_result, "source_profile_log_ratio") > 0
    assert value(limit_result, "source_signed_index") > 0
    strict = sheet(10, 10, test_relation="ge")
    assert value(populate_binding_model(strict, model(strict)), "source_profile_log_ratio") == value(limit_result, "source_profile_log_ratio")
    assert limit_result["cells"]["log_parameter_contrast"]["relation"] == "gt"


def test_covariance_is_used_once_and_counts_and_fit_spreads_are_not_weights():
    source = sheet()
    independent = populate_binding_model(source, model(source, [[.04, 0], [0, .09]]))
    correlated = populate_binding_model(source, model(source))
    assert value(correlated, "log_contrast_noise_variance") < value(independent, "log_contrast_noise_variance")
    assert value(correlated, "source_profile_log_ratio") > value(independent, "source_profile_log_ratio")
    extraction = {key: deepcopy(source[key]) for key in ("parameter_kind", "unit", "uncertainty_basis", "minimum_experiment_count", "reference_rows", "test_rows")}
    extraction["version"] = "binding_parameter_extraction_v1"
    extraction["minimum_experiment_count"] = 100
    for arm in ("reference_rows", "test_rows"):
        extraction[arm][0]["reported_spread"] = 300
    changed = populate_binding_contrast(extraction)
    assert populate_binding_model(changed, model(changed))["cells"] == correlated["cells"]


def test_missing_model_preserves_native_contrast_and_does_not_change_old_sheet():
    source = sheet(test_relation="gt")
    before = deepcopy(source)
    result = populate_binding_model(source)
    assert value(result, "log_parameter_contrast") == pytest.approx(math.log(2))
    assert result["cells"]["log_parameter_contrast"]["relation"] == "gt"
    for name in COMPONENTS[1:]:
        assert result["cells"][name]["unavailable_reason"] == "binding_sampling_model_unreported"
    assert source == before
    assert source["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "binding_observation_model_unimplemented"


@pytest.mark.parametrize("status", ["estimated", "unknown"])
def test_covariance_status_does_not_inflate_known_normal_information(status):
    source = sheet()
    result = populate_binding_model(source, model(source, variance_status=status))
    for name in COMPONENTS[3:]:
        assert value(result, name) is None
        assert result["cells"][name]["unavailable_reason"] == ("known_log_covariance_required" if status == "estimated" else "covariance_status_unknown")
    if status == "estimated":
        assert value(result, "log_contrast_noise_variance") == pytest.approx(.11)
        assert result["cells"]["log_contrast_noise_variance"]["conditional_on"] == ["supplied_log_covariance"]
    else:
        assert value(result, "log_contrast_noise_variance") is None
    assert value(result, "log_parameter_contrast") is not None


@pytest.mark.parametrize("mechanism", ["none", "unknown"])
def test_reporting_limit_without_event_mechanism_is_unavailable(mechanism):
    source = sheet(test_relation="gt")
    result = populate_binding_model(source, model(source, censoring_model=mechanism))
    assert value(result, "log_contrast_noise_sd") > 0
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "binding_censoring_mechanism_unreported"
    assert value(result, "log_parameter_contrast") is not None


@pytest.mark.parametrize("a,b", [(a, b) for a in ("gt", "ge", "lt", "le") for b in ("gt", "ge", "lt", "le")])
def test_two_censored_rows_explicitly_unsupported_but_noise_survives(a, b):
    source = sheet(reference_relation=a, test_relation=b)
    result = populate_binding_model(source, model(source))
    assert result["diagnostics"]["likelihood_case"] == "two_censored"
    for name in ("log_parameter_contrast", "source_profile_log_ratio", "source_signed_index"):
        assert result["cells"][name]["unavailable_reason"] == "two_censored_observations_unsupported"
    assert value(result, "log_contrast_noise_variance") == pytest.approx(.11)


def test_canonical_measurement_key_has_exact_shared_serialization_and_no_value_identity():
    source = sheet()
    first = source["reference_rows"][0]["source"]
    physical = {name: first[name] for name in ("source_ref", "artifact_ref", "table_id", "row_index", "locator")}
    canonical = json.dumps({"parameter_kind": "ic50", "physical": physical}, sort_keys=True,
                           ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    keys = binding_model_operand_keys(source)
    assert keys["reference"] == "binding_measurement_" + sha256(canonical).hexdigest()
    equal_values = sheet(10, 10)
    assert binding_model_operand_keys(equal_values)["reference"] != binding_model_operand_keys(equal_values)["test"]
    altered = row(11)
    assert binding_model_operand_keys(from_rows([altered], source["test_rows"]))["reference"] == keys["reference"]


def visual(value=10, alias="a"):
    result = row(value)
    result["origin"] = "visual_transcription"
    result["source"].update(representation="retained_visual_transcription", artifact_ref=alias,
        locator={"original_source_ref": "synthetic original", "original_artifact_ref": "synthetic image",
                 "image_region": [0, 1, 20, 30]})
    return result


def test_visual_aliases_share_owner_but_source_reading_conflict_is_retained():
    original = visual()
    alias = visual(alias="b")
    alias["source"]["row_index"] = 22
    alias["source"]["source_ref"] = "synthetic alternate wrapper"
    plain = from_rows([original], [row(20, index=1, ligand="test")])
    both = from_rows([original, alias], plain["test_rows"])
    assert len(both["reference_rows"]) == 2
    assert binding_model_operand_keys(both) == binding_model_operand_keys(plain)
    assert populate_binding_model(both, model(both))["cells"] == populate_binding_model(plain, model(plain))["cells"]
    alias["value"] = 11
    conflict = from_rows([original, alias], plain["test_rows"])
    assert binding_model_operand_keys(conflict)["reference"] is None
    result = populate_binding_model(conflict)
    assert result["cells"]["log_parameter_contrast"]["unavailable_reason"] == "conflicting_source_identity"
    assert result["cells"]["source_signed_index"]["status"] == "conflicting"


@pytest.mark.parametrize("reference_rows,reason", [
    ([], "missing_reference_arm"),
    ([row(None, relation="unreported")], "source_measurement_unavailable"),
    ([row(), row(index=2)], "ambiguous_reference_arm"),
])
def test_missing_unreported_ambiguous_arms_have_null_keys_and_specific_reason(reference_rows, reason):
    source = from_rows(reference_rows, [row(20, index=1, ligand="test")])
    assert binding_model_operand_keys(source)["reference"] is None
    result = populate_binding_model(source)
    assert all(cell["unavailable_reason"] == reason for cell in result["cells"].values())


def test_mismatched_comparison_context_retains_owner_but_no_model_scores():
    reference, test = row(), row(20, index=1, ligand="test")
    test["subject"] = "synthetic other subject"
    source = from_rows([reference], [test])
    result = populate_binding_model(source, model(source))
    assert all(cell["unavailable_reason"] == "comparison_context_mismatch" for cell in result["cells"].values())
    assert all(result["measurement_keys"].values())


@pytest.mark.parametrize("matrix", [
    [[0, 0], [0, 1]], [[-1, 0], [0, 1]], [[1, 1], [1, 1]],
    [[1, 2], [2, 1]], [[1e-300, 1e-200], [1e-200, 1e-300]],
    [[1e308, 1e308], [1e308, 1e308]],
])
def test_invalid_covariance_is_rejected_without_jitter(matrix):
    source = sheet()
    with pytest.raises(ExperimentalContractError, match="positive_definite_binding_covariance_required"):
        populate_binding_model(source, model(source, matrix))


@pytest.mark.parametrize("field,bad", [
    ("version", "bad"), ("parameter_kind", "reported_hill_kd"),
    ("measurement_order", ["test", "reference"]), ("measurement_order", ("reference", "test")),
    ("measurement_keys", ["unowned", "unowned2"]), ("measurement_keys", [None, None]),
    ("variance_status", "sem"), ("censoring_model", "fitted_curve_limit"),
    ("log_basis", "log10_nM"), ("origin", "inferred"),
    ("log_covariance", [[.1, .01], [.02, .1]]), ("log_covariance", [[1], [1]]),
    ("log_covariance", [[True, 0], [0, 1]]), ("log_covariance", [[float("nan"), 0], [0, 1]]),
    ("log_covariance", [[float("inf"), 0], [0, 1]]),
    ("log_covariance", [[10**1000, 0], [0, 1]]),
])
def test_model_calculator_independently_validates_malformed_models(field, bad):
    source = sheet()
    supplied = model(source)
    supplied[field] = bad
    with pytest.raises(ExperimentalContractError) as caught:
        populate_binding_model(source, supplied)
    assert caught.value.field.startswith("model")


def test_duplicate_owner_cannot_be_two_density_observations():
    source = from_rows([row()], [row()])
    assert binding_model_operand_keys(source)["reference"] == binding_model_operand_keys(source)["test"]
    assert value(populate_binding_model(source), "log_parameter_contrast") == 0
    with pytest.raises(ExperimentalContractError, match="binding_covariance_owner_conflict"):
        populate_binding_model(source, model(source))


@pytest.mark.parametrize("target", ["sheet", "model"])
def test_undeclared_fields_are_rejected(target):
    source = sheet()
    supplied = model(source)
    (source if target == "sheet" else supplied)["unexpected"] = 1
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        populate_binding_model(source, supplied)


def test_source_sheet_is_recomputed_rather_than_trusting_a_saved_cell():
    source = sheet()
    source["cells"]["log_native_parameter_ratio"]["value"] = 100
    with pytest.raises(ExperimentalContractError, match="binding_sheet_recalculation_mismatch"):
        populate_binding_model(source)


def test_finite_score_is_preserved_when_bounded_normalization_would_round_to_one():
    source = sheet(1, math.exp(10))
    result = populate_binding_model(source, model(source, [[.5, 0], [0, .5]]))
    assert value(result, "source_profile_log_ratio") == 50
    assert value(result, "source_signed_index") is None
    assert result["cells"]["source_signed_index"]["unavailable_reason"] == "numerical_model_range"


@pytest.mark.parametrize("matrix", [
    [[1e308, 0], [0, 1e308]], [[5e-324, 0], [0, 5e-324]],
])
def test_valid_extreme_covariance_retains_native_contrast_without_nonfinite_cells(matrix):
    source = sheet()
    result = populate_binding_model(source, model(source, matrix))
    assert value(result, "log_parameter_contrast") == pytest.approx(math.log(2))
    assert value(result, "source_profile_log_ratio") is None
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "numerical_model_range"
    json.dumps(result, allow_nan=False)


def test_decimal_covariance_validation_avoids_determinant_overflow_and_underflow():
    source = sheet()
    for scale in (1e-200, 1e200):
        result = populate_binding_model(source, model(source, [[scale, scale / 2], [scale / 2, scale]]))
        assert value(result, "log_contrast_noise_variance") == scale
        assert value(result, "log_contrast_noise_sd") == math.sqrt(scale)
    near_singular = [[1, math.nextafter(1, 0)], [math.nextafter(1, 0), 1]]
    result = populate_binding_model(source, model(source, near_singular))
    assert value(result, "log_contrast_noise_variance") == 2 * (1 - math.nextafter(1, 0))


def test_huge_censor_tail_does_not_become_exact_zero_evidence():
    source = sheet(1, math.exp(-100), test_relation="gt")
    result = populate_binding_model(source, model(source, [[1, 0], [0, 1]]))
    assert value(result, "source_profile_log_ratio") is None
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "numerical_model_range"
    assert value(result, "log_parameter_contrast") == -100


def test_small_censor_tail_is_preserved_without_a_pseudocount():
    source = sheet(1, math.exp(-10), test_relation="gt")
    result = populate_binding_model(source, model(source, [[1, 0], [0, 1]]))
    assert 0 < value(result, "source_profile_log_ratio") < 1e-20
    assert 0 < value(result, "source_signed_index") < 1e-20


def test_censor_solver_handles_large_covariance_slope_without_a_fixed_parameter_window():
    source = sheet(1, math.exp(2), test_relation="gt")
    covariance = [[1, .999], [.999, .998002]]
    result = populate_binding_model(source, model(source, covariance))
    assert value(result, "source_profile_log_ratio") is not None
    assert result["diagnostics"]["conditional_censored_noise_sd"] < .002
    assert result["diagnostics"]["boundary_detected_mean_shift"] > 100


def test_zero_cdf_slope_has_exact_global_boundary_fit():
    source = sheet(1, 2, test_relation="gt")
    covariance = [[1, 1], [1, 2]]
    result = populate_binding_model(source, model(source, covariance))
    assert result["diagnostics"]["boundary_detected_mean_shift"] == 0
    assert value(result, "source_profile_log_ratio") == pytest.approx(-norm.logcdf(-math.log(2)))


def test_nearby_large_native_values_preserve_nonzero_log_contrast():
    a = 1e300
    source = sheet(a, math.nextafter(a, math.inf))
    result = populate_binding_model(source, model(source))
    assert value(result, "log_parameter_contrast") > 0
    assert value(result, "source_profile_log_ratio") > 0
    assert value(result, "source_signed_index") > 0


def test_hill_kind_is_retained_without_intrinsic_affinity_interpretation():
    source = sheet()
    source["parameter_kind"] = "reported_hill_kd"
    # Rebuild because the caller supplied a complete descriptive sheet.
    result = populate_binding_model(source, model(source))
    assert result["parameter_kind"] == "reported_hill_kd"
    assert result["contrast_meaning"] == "test_parameter_exceeds_reference"


@pytest.mark.parametrize("component,replacement", [
    ("reference_parameter", True), ("test_parameter", True),
    ("log_native_parameter_ratio", False), ("native_parameter_ratio", True),
])
def test_boolean_cell_tampering_is_not_numeric_equality(component, replacement):
    source = sheet(1, 1)
    source["cells"][component]["value"] = replacement
    with pytest.raises(ExperimentalContractError, match="binding_sheet_recalculation_mismatch"):
        populate_binding_model(source)


def test_nonfinite_tampered_saved_cell_has_repairable_contract_error():
    source = sheet()
    source["cells"]["log_native_parameter_ratio"]["value"] = float("nan")
    with pytest.raises(ExperimentalContractError, match="binding_sheet_recalculation_mismatch"):
        populate_binding_model(source)


def test_true_nonzero_profile_underflow_is_unavailable_and_noise_is_retained():
    source = sheet(1, math.nextafter(1, math.inf))
    result = populate_binding_model(source, model(source, [[1e308, 0], [0, 1]]))
    assert value(result, "log_parameter_contrast") > 0
    assert value(result, "log_contrast_noise_variance") == 1e308
    assert value(result, "source_profile_log_ratio") is None
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "numerical_model_range"
