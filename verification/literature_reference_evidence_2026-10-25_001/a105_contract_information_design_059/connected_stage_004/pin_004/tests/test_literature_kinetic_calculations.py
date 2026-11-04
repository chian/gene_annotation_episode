"""Synthetic kinetic parameters; no source paper, Store or model acquisition."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math

import numpy as np
import pytest
from scipy.optimize import minimize

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_calculations import (
    COMPONENTS, CONDITIONAL_CODES, FORMULAS, INPUT_UNAVAILABLE_REASONS, INPUT_VERSION,
    MODEL_VERSION, PARAMETER_UNITS, REASONS, kinetic_operand_keys,
    populate_kinetic_contrast, validate_kinetic_inputs,
)


def operand(value=12, *, role="numerator", kind="catalytic_efficiency"):
    return {"parameter_kind": kind, "unit": PARAMETER_UNITS[kind], "value": value,
        "status": "point", "relation": "eq", "approximate": False, "origin": "synthetic",
        "measurement_id": "synthetic-token-" + role, "physical_measurement_id": "synthetic-physical-" + role,
        "subject": {"organism": "synthetic organism", "genotype": None,
            "molecule": "synthetic molecule", "construct": "synthetic construct"},
        "context": {"substrate": "synthetic substrate-" + role, "preparation": None,
            "experiment": "synthetic experiment", "experimental_system": "synthetic purified system",
            "conditions": "synthetic conditions-" + role, "endpoint": "synthetic endpoint-" + role,
            "normalization": "synthetic fitted parameter"},
        "uncertainty": {"statistic": "unspecified", "magnitude": .7, "interval": None,
            "confidence_level": None, "count": 5, "repetition_basis": "unspecified", "estimate_basis": "unknown"},
        "source": {"source_ref": "synthetic source", "artifact_ref": "synthetic artifact",
            "representation": "synthetic", "start": 10 if role == "numerator" else 30,
            "end": 15 if role == "numerator" else 35}, "unavailable_reason": None}


def inputs(n=12, d=3, *, kind="catalytic_efficiency"):
    return {"version": INPUT_VERSION, "numerator": operand(n, kind=kind),
        "denominator": operand(d, role="denominator", kind=kind),
        "subject_relationship": "same_molecule_and_construct", "parameter_definition_relationship": "same",
        "substrate_arrangement": "separate_assays", "comparison_scope": "reported_protocols",
        "nonintended_conditions_relationship": "different"}


def model(extraction, covariance=None, **updates):
    keys = kinetic_operand_keys(extraction)
    result = {"version": MODEL_VERSION, "measurement_order": ["numerator", "denominator"],
        "measurement_keys": [keys["numerator"], keys["denominator"]],
        "covariance": [[.09, .02], [.02, .16]] if covariance is None else covariance,
        "variance_status": "known", "observation_model": "known_normal_log_parameters",
        "log_basis": "natural_log_canonical_parameter", "origin": "synthetic",
        "source": {"source_ref": "synthetic covariance", "artifact_ref": "synthetic covariance artifact",
            "representation": "synthetic", "start": 0, "end": 20}}
    result.update(updates)
    return result


def value(result, name):
    return result["cells"][name]["value"]


def test_synthetic_sheet_has_actual_numerical_meanings_and_detached_closed_values():
    source = inputs()
    observation_model = model(source)
    before = deepcopy((source, observation_model))
    result = populate_kinetic_contrast(source, observation_model)
    expected_e = math.log(4)
    expected_s = expected_e ** 2 / .42
    assert value(result, "numerator_parameter") == 12
    assert value(result, "denominator_parameter") == 3
    assert value(result, "parameter_difference") == 9
    assert value(result, "parameter_ratio") == 4
    assert value(result, "log_parameter_contrast") == pytest.approx(expected_e)
    assert value(result, "log_contrast_variance") == pytest.approx(.21)
    assert value(result, "log_contrast_standard_uncertainty") == pytest.approx(math.sqrt(.21))
    assert value(result, "source_profile_log_ratio") == pytest.approx(expected_s)
    assert value(result, "source_signed_index") == pytest.approx(math.tanh(expected_s / 2))
    assert result["annotation_credit"] is result["independent_preparation_count"] is None
    assert result["contrast_meaning"] == "numerator_parameter_exceeds_denominator"
    assert result["physical_measurement_ids"] == {role: source[role]["physical_measurement_id"] for role in ("numerator", "denominator")}
    assert set(result["cells"]) == set(COMPONENTS)
    for name, cell in result["cells"].items():
        assert set(cell) == {"value", "unit", "status", "formula", "origin", "unavailable_reason",
            "approximate", "conditional_on", "threshold", "relation"}
        assert cell["formula"] == FORMULAS[name]
        assert cell["unavailable_reason"] is None or cell["unavailable_reason"] in REASONS
        assert set(cell["conditional_on"]) <= set(CONDITIONAL_CODES)
    assert (source, observation_model) == before
    result["inputs"]["numerator"]["context"]["conditions"] = "changed saved copy"
    result["model"]["covariance"][0][0] = 999
    assert (source, observation_model) == before
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("kind", list(PARAMETER_UNITS))
@pytest.mark.parametrize("n,d", [(12, 3), (3, 12), (7, 7)])
@pytest.mark.parametrize("covariance", [[[.3, .1], [.1, .5]], [[1, -.4], [-.4, 2]]])
def test_signed_profile_matches_distinct_constrained_two_mean_fit(kind, n, d, covariance):
    source = inputs(n, d, kind=kind)
    result = populate_kinetic_contrast(source, model(source, covariance))
    y = np.log([n, d])
    precision = np.linalg.inv(covariance)
    def loss(means):
        residual = y - means
        return .5 * residual @ precision @ residual
    fitted = minimize(loss, [y.mean()] * 2, method="SLSQP",
        constraints={"type": "eq", "fun": lambda means: means[0] - means[1]},
        options={"ftol": 1e-13, "maxiter": 200})
    assert fitted.success, fitted.message
    expected = math.copysign(fitted.fun, n - d) if n != d else 0
    assert value(result, "source_profile_log_ratio") == pytest.approx(expected, abs=1e-11)
    assert result["cells"]["parameter_difference"]["unit"] == PARAMETER_UNITS[kind]
    assert result["inputs"]["numerator"]["context"]["preparation"] is None


@pytest.mark.parametrize("n,d,difference,ratio", [(0, 3, -3, 0), (-6, 3, -9, -2), (6, -3, 9, -2), (3, 0, 3, None), (0, 0, 0, None)])
def test_signed_noisy_points_survive_without_invalid_logs(n, d, difference, ratio):
    result = populate_kinetic_contrast(inputs(n, d))
    assert value(result, "parameter_difference") == difference
    assert value(result, "parameter_ratio") == ratio
    assert result["cells"]["log_parameter_contrast"]["unavailable_reason"] == "positive_parameters_required_for_log"
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "positive_parameters_required_for_log"


@pytest.mark.parametrize("role", ["numerator", "denominator"])
@pytest.mark.parametrize("status,relation", [("censored", "lt"), ("censored", "ge"), ("missing", "none"), ("conflicting", "none")])
def test_missing_conflicting_censored_arms_keep_other_raw_point_and_real_reason(role, status, relation):
    source = inputs()
    source[role].update(status=status, relation=relation, value=source[role]["value"] if status == "censored" else None)
    result = populate_kinetic_contrast(source)
    expected = {"censored": "censored_measurement", "missing": "source_measurement_missing", "conflicting": "conflicting_measurement"}[status]
    assert value(result, role + "_parameter") is None
    raw = result["cells"][role + "_parameter"]
    assert raw["threshold"] == (source[role]["value"] if status == "censored" else None)
    assert raw["relation"] == relation
    for name in COMPONENTS[2:]:
        assert result["cells"][name]["unavailable_reason"] == expected
    other = "denominator" if role == "numerator" else "numerator"
    assert value(result, other + "_parameter") == source[other]["value"]


@pytest.mark.parametrize("reason", INPUT_UNAVAILABLE_REASONS)
def test_specific_reader_limit_is_not_overwritten_by_model_missing(reason):
    source = inputs()
    source["denominator"].update(value=None, status="missing", relation="none", unit=None, unavailable_reason=reason)
    result = populate_kinetic_contrast(source)
    for name in ("denominator_parameter", *COMPONENTS[2:]):
        assert result["cells"][name]["unavailable_reason"] == reason
    assert result["cells"]["denominator_parameter"]["unit"] is None


def test_null_operand_is_specific_and_cannot_receive_known_covariance():
    source = inputs()
    source["numerator"] = None
    result = populate_kinetic_contrast(source)
    assert kinetic_operand_keys(source)["numerator"] is None
    assert result["cells"]["parameter_ratio"]["unavailable_reason"] == "numerator_measurement_missing"
    with pytest.raises(ExperimentalContractError, match="known_physical_measurement_owner_required"):
        populate_kinetic_contrast(source, model(source))


@pytest.mark.parametrize("name,meaning,reason", [
    ("subject_relationship", "different", "subject_relationship_different"),
    ("subject_relationship", "unknown", "subject_relationship_unknown"),
    ("parameter_definition_relationship", "conflicting", "parameter_definition_relationship_conflicting"),
    ("substrate_arrangement", "mixed_substrates", "mixed_substrates_unsupported"),
    ("substrate_arrangement", "unknown", "substrate_arrangement_unknown"),
    ("comparison_scope", "conflicting", "comparison_scope_conflicting"),
])
def test_unresolved_scientific_relationship_never_becomes_arithmetic_grade(name, meaning, reason):
    source = inputs()
    source[name] = meaning
    result = populate_kinetic_contrast(source, model(source))
    assert value(result, "numerator_parameter") == 12
    for component in COMPONENTS[2:]:
        assert result["cells"][component]["unavailable_reason"] == reason


@pytest.mark.parametrize("relationship", ["different", "unknown", "conflicting", "matched"])
def test_protocol_magnitude_and_common_condition_scope_remain_different(relationship):
    source = inputs()
    source["nonintended_conditions_relationship"] = relationship
    protocol = populate_kinetic_contrast(source)
    assert value(protocol, "parameter_ratio") == 4
    source["comparison_scope"] = "common_conditions"
    common = populate_kinetic_contrast(source)
    assert value(common, "parameter_ratio") == (4 if relationship == "matched" else None)
    if relationship != "matched":
        assert common["cells"]["parameter_ratio"]["unavailable_reason"] == "common_conditions_not_matched"


def test_parameter_kind_is_not_inferred_from_rate_dimensions():
    source = inputs()
    source["denominator"] = operand(3, role="denominator", kind="kcat")
    result = populate_kinetic_contrast(source)
    assert result["cells"]["parameter_ratio"]["unavailable_reason"] == "parameter_kind_mismatch"
    source["denominator"]["unit"] = "uM/min"
    with pytest.raises(ExperimentalContractError, match="canonical_kinetic_parameter_unit_required"):
        populate_kinetic_contrast(source)


@pytest.mark.parametrize("identity", ["locator", "physical", "measurement"])
@pytest.mark.parametrize("conflict", [False, True])
def test_identity_relabelling_cannot_manufacture_pair(identity, conflict):
    source = inputs()
    source["denominator"] = deepcopy(source["numerator"])
    source["denominator"]["measurement_id"] = "renamed token"
    source["denominator"]["physical_measurement_id"] = "renamed physical"
    source["denominator"]["source"]["start"] += 50
    source["denominator"]["source"]["end"] += 50
    if identity == "locator":
        source["denominator"]["source"] = deepcopy(source["numerator"]["source"])
    elif identity == "physical":
        source["denominator"]["physical_measurement_id"] = source["numerator"]["physical_measurement_id"]
    else:
        source["denominator"]["measurement_id"] = source["numerator"]["measurement_id"]
    if conflict:
        source["denominator"]["value"] += 1
    result = populate_kinetic_contrast(source)
    assert value(result, "denominator_parameter") == source["denominator"]["value"]
    assert result["cells"]["parameter_ratio"]["unavailable_reason"] == (
        "conflicting_source_observation" if conflict else "reused_source_observation")


def test_exact_estimate_key_matches_contract_and_does_not_replace_physical_owner():
    source = inputs()
    keys = kinetic_operand_keys(source)
    expected = {"version": "kinetic_estimate_identity_v1", "operand": source["numerator"]}
    encoded = json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    assert keys["numerator"] == "kinetic_estimate_" + hashlib.sha256(encoded).hexdigest()
    old_model = model(source)
    source["numerator"]["context"]["conditions"] = "different selected context"
    assert kinetic_operand_keys(source)["numerator"] != keys["numerator"]
    with pytest.raises(ExperimentalContractError, match="kinetic_model_measurement_owner_mismatch"):
        populate_kinetic_contrast(source, old_model)


@pytest.mark.parametrize("name", ["value", "physical_measurement_id", "parameter_kind", "source", "uncertainty"])
def test_changed_selected_estimate_cannot_reuse_covariance(name):
    source = inputs()
    old_model = model(source)
    if name == "value":
        source["numerator"][name] += 1
    elif name == "physical_measurement_id":
        source["numerator"][name] = "other physical owner"
    elif name == "parameter_kind":
        source["numerator"].update(parameter_kind="Km", unit="uM")
    elif name == "source":
        source["numerator"]["source"]["source_ref"] = "other source"
    else:
        source["numerator"]["uncertainty"]["statistic"] = "sd"
    with pytest.raises(ExperimentalContractError, match="kinetic_model_measurement_owner_mismatch"):
        populate_kinetic_contrast(source, old_model)


def test_missing_physical_identity_stays_unknown_instead_of_becoming_token_identity():
    source = inputs()
    source["numerator"]["physical_measurement_id"] = None
    result = populate_kinetic_contrast(source)
    assert value(result, "parameter_ratio") == 4
    assert result["measurement_keys"]["numerator"] is None
    with pytest.raises(ExperimentalContractError, match="known_physical_measurement_owner_required"):
        populate_kinetic_contrast(source, model(source))
    unknown = model(source, variance_status="unknown", covariance=None, source=None)
    assert populate_kinetic_contrast(source, unknown)["variance_status"] == "unknown"


def test_shared_physical_estimate_survives_distinct_source_views_without_independence_or_joint_score():
    first = inputs()
    second = inputs(12, 2)
    second["numerator"]["source"]["source_ref"] = "synthetic alternate view"
    second["numerator"]["measurement_id"] = "synthetic alternate token"
    second["denominator"]["physical_measurement_id"] = "synthetic third physical estimate"
    second["denominator"]["measurement_id"] = "synthetic third token"
    results = [populate_kinetic_contrast(source, model(source)) for source in (first, second)]
    assert results[0]["measurement_keys"]["numerator"] != results[1]["measurement_keys"]["numerator"]
    assert results[0]["physical_measurement_ids"]["numerator"] == results[1]["physical_measurement_ids"]["numerator"]
    for result in results:
        assert result["independent_preparation_count"] is None
        assert "joint_score" not in result
        assert "shared_physical_estimates_remain_dependent_across_comparisons" in result["interpretation_limits"]
    # The converse: identical numbers at distinct received source/physical
    # identities are valid distinct operands, without a claim of independence.
    equal = inputs(6, 6)
    result = populate_kinetic_contrast(equal, model(equal))
    assert value(result, "parameter_ratio") == 1
    assert value(result, "source_profile_log_ratio") == 0
    assert result["independent_preparation_count"] is None


@pytest.mark.parametrize("variance_status", ["known", "estimated", "unknown"])
@pytest.mark.parametrize("observation_model", ["known_normal_log_parameters", "unspecified"])
def test_covariance_status_and_model_have_distinct_numerical_roles(variance_status, observation_model):
    source = inputs()
    result = populate_kinetic_contrast(source, model(source, variance_status=variance_status, observation_model=observation_model))
    assert value(result, "log_contrast_variance") == (None if variance_status == "unknown" else pytest.approx(.21))
    if variance_status != "known" or observation_model != "known_normal_log_parameters":
        assert value(result, "source_profile_log_ratio") is None
    else:
        assert value(result, "source_profile_log_ratio") > 0


def test_source_spread_count_ci_and_technical_repetitions_do_not_create_covariance():
    source = inputs()
    source["numerator"]["uncertainty"].update(statistic="ci", magnitude=None, interval=[8, 16],
        confidence_level=.95, count=100, repetition_basis="technical_measurements", estimate_basis="fit_to_averaged_curve")
    source["denominator"]["uncertainty"].update(statistic="sem", magnitude=.2, count=1000)
    result = populate_kinetic_contrast(source)
    assert value(result, "parameter_ratio") == 4
    assert value(result, "log_contrast_variance") is None
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "kinetic_log_model_unreported"
    assert result["inputs"]["numerator"]["uncertainty"]["interval"] == [8, 16]
    assert result["independent_preparation_count"] is None


def test_approximate_parameter_arithmetic_is_flagged_and_not_normal_evidence():
    source = inputs()
    source["numerator"]["approximate"] = True
    result = populate_kinetic_contrast(source, model(source))
    for name in ("parameter_difference", "parameter_ratio", "log_parameter_contrast", "log_contrast_variance"):
        assert value(result, name) is not None and result["cells"][name]["approximate"]
    assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "approximate_parameter_model_unsupported"


@pytest.mark.parametrize("covariance", [[[0, 0], [0, 0]], [[1, 1], [1, 1]], [[0, 0], [0, 2]]])
def test_psd_covariance_retains_degenerate_variance_without_infinite_score(covariance):
    source = inputs()
    result = populate_kinetic_contrast(source, model(source, covariance))
    expected = covariance[0][0] + covariance[1][1] - 2 * covariance[0][1]
    assert value(result, "log_contrast_variance") == expected
    if expected == 0:
        assert result["cells"]["source_profile_log_ratio"]["unavailable_reason"] == "positive_log_contrast_variance_required"
    else:
        assert value(result, "source_profile_log_ratio") > 0


@pytest.mark.parametrize("covariance", [
    [[-1, 0], [0, 1]], [[1, 2], [2, 1]], [[0, 1], [1, 2]],
    [[1e-300, 1e-200], [1e-200, 1e-300]],
])
def test_indefinite_covariance_is_not_repaired(covariance):
    source = inputs()
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_kinetic_covariance_required"):
        populate_kinetic_contrast(source, model(source, covariance))


def test_exact_covariance_cancellation_and_huge_finite_covariance_preserve_useful_partials():
    source = inputs()
    shared = 1e200
    edge = math.nextafter(shared, math.inf)
    result = populate_kinetic_contrast(source, model(source, [[edge, shared], [shared, edge]]))
    exact = 2 * (Fraction(edge) - Fraction(shared))
    assert value(result, "log_contrast_variance") == float(exact)
    huge = populate_kinetic_contrast(source, model(source, [[1e308, -1e308], [-1e308, 1e308]]))
    assert value(huge, "log_contrast_variance") is None
    assert value(huge, "log_contrast_standard_uncertainty") == pytest.approx(2e154)
    assert value(huge, "source_profile_log_ratio") > 0
    json.dumps(huge, allow_nan=False)


@pytest.mark.parametrize("n,d", [(1e308, 1e-300), (1e-300, 1e308)])
def test_log_contrast_survives_ratio_numerical_range(n, d):
    result = populate_kinetic_contrast(inputs(n, d))
    assert value(result, "parameter_ratio") is None
    assert math.isfinite(value(result, "log_parameter_contrast"))


def test_nearby_unequal_integer_estimates_keep_nonzero_log_and_profile():
    source = inputs(10 ** 100 + 1, 10 ** 100)
    result = populate_kinetic_contrast(source, model(source))
    assert value(result, "log_parameter_contrast") == pytest.approx(1e-100, rel=1e-15, abs=0)
    assert value(result, "source_profile_log_ratio") > 0
    assert value(result, "parameter_difference") == 1


def test_rounded_bounded_index_is_unknown_while_finite_profile_survives():
    source = inputs()
    result = populate_kinetic_contrast(source, model(source, [[1e-8, 0], [0, 1e-8]]))
    assert value(result, "source_profile_log_ratio") > 1000
    assert result["cells"]["source_signed_index"]["unavailable_reason"] == "numerical_model_range"


@pytest.mark.parametrize("value_", [True, False, math.nan, math.inf, -math.inf, 10 ** 1000, "12", []])
def test_nonfinite_boolean_and_huge_numeric_operands_have_structured_errors(value_):
    source = inputs()
    source["numerator"]["value"] = value_
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        populate_kinetic_contrast(source)


@pytest.mark.parametrize("field", ["subject_relationship", "parameter_definition_relationship", "substrate_arrangement",
    "comparison_scope", "nonintended_conditions_relationship"])
@pytest.mark.parametrize("bad", [True, 1, None, [], {}])
def test_scientific_enums_are_type_strict(field, bad):
    source = inputs()
    source[field] = bad
    with pytest.raises(ExperimentalContractError, match="unsupported_kinetic_meaning"):
        populate_kinetic_contrast(source)


@pytest.mark.parametrize("mutation,code", [
    (lambda x: x.update(extra="field"), "closed_fields_required"),
    (lambda x: x["numerator"].update(approximate=1), "boolean_required"),
    (lambda x: x["numerator"].update(unit=None), "canonical_kinetic_parameter_unit_required"),
    (lambda x: x["numerator"].update(unavailable_reason="source_measurement_unreported"), "reported_value_cannot_have_unavailable_reason"),
    (lambda x: x["numerator"]["source"].update(start=True), "nonnegative_integer_offset_required"),
    (lambda x: x["numerator"]["source"].update(end=5), "nonempty_source_span_required"),
    (lambda x: x["numerator"]["uncertainty"].update(count=True), "positive_integer_count_required"),
    (lambda x: x["numerator"]["uncertainty"].update(interval=[1, 2]), "ci_statistic_required"),
    (lambda x: x["numerator"]["uncertainty"].update(statistic="ci"), "ci_endpoints_not_halfwidth_required"),
])
def test_closed_relationship_contract_rejects_incoherent_inputs(mutation, code):
    source = inputs()
    mutation(source)
    with pytest.raises(ExperimentalContractError, match=code):
        validate_kinetic_inputs(source)


@pytest.mark.parametrize("mutation,code", [
    (lambda m: m.update(measurement_order=["denominator", "numerator"]), "kinetic_model_measurement_order_mismatch"),
    (lambda m: m.update(measurement_keys=["forged", "keys"]), "kinetic_model_measurement_owner_mismatch"),
    (lambda m: m.update(source=None), "kinetic_covariance_source_required"),
    (lambda m: m.update(covariance=None), "kinetic_covariance_required"),
    (lambda m: m.update(covariance=[[1, 0], [1, 1]]), "symmetric_kinetic_covariance_required"),
    (lambda m: m.update(covariance=[[True, 0], [0, 1]]), "finite_number_required"),
    (lambda m: m.update(covariance=[[10 ** 1000, 0], [0, 1]]), "finite_number_required"),
])
def test_covariance_model_binding_and_shape_fail_deliberately(mutation, code):
    source = inputs()
    observation_model = model(source)
    mutation(observation_model)
    with pytest.raises(ExperimentalContractError, match=code):
        populate_kinetic_contrast(source, observation_model)
