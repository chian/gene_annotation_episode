"""Synthetic-only scientific and numerical checks; no retained paper fixtures."""
from copy import deepcopy
import ast
from functools import lru_cache
import importlib.util
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.literature_binding_interaction_calculations import (
    CONTEXT_FIELDS, ID_FIELDS, INPUT_VERSION, MODEL_VERSION, RELATIONS, ROLES,
    UNCERTAINTY_PARTIAL_CODES,
    binding_interaction_operand_keys, populate_binding_interaction,
    validate_binding_interaction_inputs,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def witness(index=0, kind="utf8_span"):
    base = {"source_ref": "synthetic:source", "artifact_ref": "synthetic:artifact", "kind": kind}
    if kind == "utf8_span":
        return {**base, "start": index * 10, "end": index * 10 + 5}
    if kind == "image_region":
        return {**base, "region": [index, 0, index + 1, 2]}
    return {**base, "table_id": "synthetic-table", "row_index": index, "column": "value"}


def example(values=(5, 40, 2, 4)):
    operands = {}
    for index, role in enumerate(ROLES):
        subject = "subject-A" if index < 2 else "subject-B"
        ligand = "ligand-reference" if index % 2 == 0 else "ligand-test"
        ids = {name: None for name in ID_FIELDS}
        ids.update(subject=subject, construct=subject + "-construct", state="state-source",
                   preparation=subject + "-preparation", experiment=subject + "-assay",
                   ligand=ligand, readout="readout-source", normalization="normalization-source",
                   conditions="conditions-source", parameter_definition="IC50-source-definition")
        context = {name: ("literal " + ids[name] if ids[name] else None) for name in CONTEXT_FIELDS}
        operands[role] = {"value": values[index], "relation": "eq", "reported_spread": None,
            "origin": "synthetic", "context": context, "canonical_ids": ids,
            "physical_fit_id": "synthetic-fit-" + str(index), "source": witness(index),
            "expression": str(values[index]), "uncertainty": {
                "statistic": "unreported", "basis": "unknown", "interval": None,
                "confidence_level": None, "exact_count": None, "minimum_count": None,
                "repetition_basis": "unspecified"}}
    return {"version": INPUT_VERSION, "parameter_kind": "ic50", "unit": "nM",
        "comparison_scope": "reported_protocols", "operands": operands,
        "relationships": {name: {"status": "matched" if name == "common_conditions" else
            "supported", "sources": [witness(10)]} for name in RELATIONS}}


def observation_model(inputs, matrix=None, status="known"):
    if matrix is None:
        matrix = [[0.04 if i == j else 0.0 for j in range(4)] for i in range(4)]
    keys = binding_interaction_operand_keys(inputs)
    return {"version": MODEL_VERSION, "parameter_kind": inputs["parameter_kind"],
        "measurement_order": list(ROLES), "measurement_keys": [keys[role] for role in ROLES],
        "physical_fit_ids": [None if inputs["operands"][role] is None else
            inputs["operands"][role]["physical_fit_id"] for role in ROLES],
        "log_basis": "natural_log_nM", "distribution": "normal", "variance_status": status,
        "log_covariance": matrix, "source": witness(11), "reporting_event": "unknown",
        "reporting_event_source": None}


def cells(inputs=None, model=None):
    return populate_binding_interaction(example() if inputs is None else inputs, model)["cells"]


def test_four_source_parameters_two_partial_ratios_and_interaction_meanings():
    result = cells()
    assert len(result) == 12
    assert [result[name]["value"] for name in
            ("parameter_rr", "parameter_rt", "parameter_tr", "parameter_tt")] == [5, 40, 2, 4]
    assert result["reference_subject_ratio"]["value"] == 8
    assert result["test_subject_ratio"]["value"] == 2
    assert result["interaction_ratio"]["value"] == 4
    assert result["log_interaction"]["value"] == pytest.approx(math.log(4))
    assert result["signed_profile_log_ratio"]["reason"] == "observation_model_missing"
    assert result["log_interaction_variance"]["unit"] == "dimensionless_squared"


def test_covariance_score_and_dependent_bounded_representation():
    inputs = example()
    model = observation_model(inputs)
    result = cells(inputs, model)
    variance = 0.16
    score = math.log(4) ** 2 / (2 * variance)
    assert result["log_interaction_variance"]["value"] == pytest.approx(variance)
    assert result["log_interaction_standard_uncertainty"]["value"] == pytest.approx(0.4)
    assert result["signed_profile_log_ratio"]["value"] == pytest.approx(score)
    assert result["signed_index"]["value"] == pytest.approx(math.tanh(score / 2))
    assert "dependent_representations" in populate_binding_interaction(inputs, model)["qualifications"]


def test_subject_exchange_reverses_effect_and_common_scale_cancels():
    first = cells(example())
    second = cells(example((2, 4, 5, 40)))
    scaled = cells(example((50, 400, 20, 40)))
    assert second["interaction_ratio"]["value"] == 0.25
    assert second["log_interaction"]["value"] == -first["log_interaction"]["value"]
    assert scaled["interaction_ratio"]["value"] == first["interaction_ratio"]["value"]


def test_unknown_or_missing_pair_retains_other_partial_and_original_cause():
    inputs = example()
    inputs["operands"][ROLES[2]] = None
    inputs["relationships"]["ligand_correspondence"] = {"status": "unknown", "sources": []}
    result = cells(inputs)
    assert result["reference_subject_ratio"]["value"] == 8
    assert result["parameter_tt"]["value"] == 4
    for name in ("test_subject_ratio", "interaction_ratio", "log_interaction_variance",
                 "signed_profile_log_ratio", "signed_index"):
        assert result[name]["reason"] == "missing_operand:" + ROLES[2]


@pytest.mark.parametrize("field", ("subject", "construct", "state", "parameter_definition",
                                   "readout", "normalization"))
@pytest.mark.parametrize("replacement,suffix", ((None, "unknown"), ("different-source-id", "conflicting")))
def test_required_pair_mappings_known_consistent_and_explicit(field, replacement, suffix):
    inputs = example()
    inputs["operands"][ROLES[1]]["canonical_ids"][field] = replacement
    result = cells(inputs)
    assert result["reference_subject_ratio"]["reason"] == f"canonical_{field}_{suffix}"
    assert result["test_subject_ratio"]["value"] == 2
    assert result["parameter_rt"]["value"] == 40


def test_same_literal_does_not_replace_mapping_and_source_mapping_can_bridge_literal_labels():
    inputs = example()
    inputs["operands"][ROLES[1]]["context"]["subject"] = "an exact alternative source spelling"
    assert cells(inputs)["interaction_ratio"]["value"] == 4
    inputs["operands"][ROLES[1]]["canonical_ids"]["subject"] = None
    assert cells(inputs)["interaction_ratio"]["reason"] == "canonical_subject_unknown"


def test_cross_pair_ligands_and_parameter_definitions_must_correspond():
    inputs = example()
    inputs["operands"][ROLES[3]]["canonical_ids"]["ligand"] = "other-ligand"
    assert cells(inputs)["test_subject_ratio"]["value"] == 2
    assert cells(inputs)["interaction_ratio"]["reason"] == "canonical_ligand_conflicting"
    inputs = example()
    for role in ROLES[2:]:
        inputs["operands"][role]["canonical_ids"]["parameter_definition"] = "different-definition"
    assert cells(inputs)["interaction_ratio"]["reason"] == "canonical_parameter_definition_conflicting"


@pytest.mark.parametrize("status", ("not_matched", "unknown", "conflicting"))
def test_reported_protocols_survive_qualified_conditions_but_common_claim_does_not(status):
    inputs = example()
    inputs["relationships"]["common_conditions"]["status"] = status
    assert cells(inputs)["interaction_ratio"]["value"] == 4
    assert "common_conditions_" + status in populate_binding_interaction(inputs)["qualifications"]
    inputs["comparison_scope"] = "common_conditions"
    assert cells(inputs)["interaction_ratio"]["reason"] == "common_conditions_" + status
    assert cells(inputs)["parameter_rt"]["value"] == 40


def test_different_cross_subject_readout_preserved_and_unknown_preparation_not_independence():
    inputs = example()
    for role in ROLES[2:]:
        inputs["operands"][role]["canonical_ids"]["readout"] = "other-readout"
        inputs["operands"][role]["canonical_ids"]["preparation"] = None
    sheet = populate_binding_interaction(inputs)
    assert sheet["cells"]["interaction_ratio"]["value"] == 4
    assert "canonical_readout_differs" in sheet["qualifications"]
    assert "canonical_preparation_partly_unknown" in sheet["qualifications"]
    assert sheet["inputs"] == inputs


def test_common_condition_claim_cannot_override_known_different_canonical_conditions():
    inputs = example()
    for role in ROLES[2:]:
        inputs["operands"][role]["canonical_ids"]["conditions"] = "different-conditions"
    assert cells(inputs)["interaction_ratio"]["value"] == 4
    assert "common_conditions_claim_conflicts_with_canonical_ids" in populate_binding_interaction(inputs)["qualifications"]
    inputs["comparison_scope"] = "common_conditions"
    assert cells(inputs)["reference_subject_ratio"]["value"] == 8
    assert cells(inputs)["test_subject_ratio"]["value"] == 2
    assert cells(inputs)["interaction_ratio"]["reason"] == "common_conditions_claim_conflicts_with_canonical_ids"


def test_same_scientific_subject_state_is_not_a_variant_interaction():
    inputs = example()
    for role in ROLES[2:]:
        for name in ("subject", "construct", "state"):
            inputs["operands"][role]["canonical_ids"][name] = inputs["operands"][ROLES[0]]["canonical_ids"][name]
    assert cells(inputs)["interaction_ratio"]["reason"] == "subject_roles_not_distinct"
    assert cells(inputs)["test_subject_ratio"]["value"] == 2
    for role in ROLES[2:]:
        inputs["operands"][role]["canonical_ids"]["state"] = "other-source-state"
    assert cells(inputs)["interaction_ratio"]["value"] == 4


def test_multiple_same_direction_printed_limits_and_strictness():
    inputs = example()
    for role, relation in zip(ROLES, ("lt", "ge", "ge", "le")):
        inputs["operands"][role]["relation"] = relation
    result = cells(inputs)
    for name, threshold, relation in (("reference_subject_ratio", 8, "gt"),
            ("test_subject_ratio", 2, "le"), ("interaction_ratio", 4, "gt")):
        assert result[name]["threshold"] == threshold
        assert result[name]["value"] is None
        assert result[name]["relation"] == relation
        assert result[name]["status"] == "reported_limit_arithmetic"
    assert result["parameter_rr"]["value"] is None
    assert result["parameter_rr"]["threshold"] == 5
    assert result["log_interaction"]["threshold"] == pytest.approx(math.log(4))
    assert result["signed_profile_log_ratio"]["reason"] == "censored_joint_likelihood_unimplemented"
    inputs["operands"][ROLES[0]]["relation"] = "le"
    assert cells(inputs)["interaction_ratio"]["relation"] == "ge"


def test_opposing_limits_do_not_create_threshold_ratio_bound_or_point_score():
    inputs = example()
    for role in ROLES[:2]:
        inputs["operands"][role]["relation"] = "lt"
    result = cells(inputs, observation_model(inputs))
    assert result["test_subject_ratio"]["value"] == 2
    assert result["log_interaction_variance"]["value"] == pytest.approx(0.16)
    for name in ("reference_subject_ratio", "interaction_ratio", "log_interaction", "signed_profile_log_ratio"):
        assert result[name]["value"] is None
        assert result[name]["threshold"] is None
        assert result[name]["reason"] == "opposing_reported_limits"


def test_source_defined_reporting_event_does_not_implement_censored_likelihood():
    inputs = example()
    inputs["operands"][ROLES[1]]["relation"] = "gt"
    model = observation_model(inputs)
    first = populate_binding_interaction(inputs, model)
    assert "censor_reporting_event_unknown" in first["qualifications"]
    model.update(reporting_event="source_defined", reporting_event_source=witness(12))
    second = populate_binding_interaction(inputs, model)
    assert "censor_reporting_event_unknown" not in second["qualifications"]
    assert second["cells"]["signed_profile_log_ratio"]["reason"] == "censored_joint_likelihood_unimplemented"


@pytest.mark.parametrize("reuse", ("source", "physical_fit_id"))
def test_role_reuse_preserves_raw_values_without_manufacturing_effect(reuse):
    inputs = example()
    inputs["operands"][ROLES[2]][reuse] = deepcopy(inputs["operands"][ROLES[0]][reuse])
    result = cells(inputs)
    assert result["parameter_tr"]["value"] == 2
    assert result["reference_subject_ratio"]["value"] == 8
    assert result["test_subject_ratio"]["value"] == 2
    assert result["interaction_ratio"]["reason"] == ("reused_source_token" if reuse == "source"
                                                     else "reused_physical_fit")


def test_shared_controls_across_calls_retain_identity_and_no_credit_count():
    first = example()
    second = deepcopy(first)
    for index in (1, 3):
        second["operands"][ROLES[index]]["value"] *= 2
        second["operands"][ROLES[index]]["physical_fit_id"] += "-new"
        second["operands"][ROLES[index]]["source"] = witness(index + 20)
    sheets = [populate_binding_interaction(inputs) for inputs in (first, second)]
    for index in (0, 2):
        assert sheets[0]["operand_keys"][ROLES[index]] == sheets[1]["operand_keys"][ROLES[index]]
        assert sheets[0]["physical_fit_ids"][ROLES[index]] == sheets[1]["physical_fit_ids"][ROLES[index]]
    assert all("credit" not in sheet and "observation_count" not in sheet for sheet in sheets)


@pytest.mark.parametrize("status", ("estimated", "unknown"))
def test_unknown_and_estimated_covariance_not_known_normal_success(status):
    inputs = example()
    model = observation_model(inputs, status=status)
    result = cells(inputs, model)
    assert result["signed_profile_log_ratio"]["reason"] == (
        "covariance_estimated_not_known" if status == "estimated" else "covariance_status_unknown")
    if status == "estimated":
        assert result["log_interaction_variance"]["value"] == pytest.approx(0.16)
    else:
        assert result["log_interaction_variance"]["value"] is None
        assert populate_binding_interaction(inputs, model)["model"]["log_covariance"] == model["log_covariance"]
        model["log_covariance"] = None
        assert cells(inputs, model)["log_interaction_variance"]["reason"] == "covariance_status_unknown"


def test_unknown_covariance_is_still_validated_and_unspecified_distribution_cannot_score():
    inputs = example()
    model = observation_model(inputs, status="unknown")
    model["log_covariance"][0][0] = -1
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        cells(inputs, model)
    model = observation_model(inputs)
    model["distribution"] = "unspecified"
    result = cells(inputs, model)
    assert result["log_interaction_variance"]["value"] == pytest.approx(0.16)
    assert result["signed_profile_log_ratio"]["reason"] == "normal_log_observation_model_unspecified"


def test_models_bound_to_exact_context_kind_and_physical_owners():
    inputs = example()
    model = observation_model(inputs)
    inputs["operands"][ROLES[0]]["context"]["conditions"] = "another exact condition record"
    with pytest.raises(ExperimentalContractError, match="model_estimate_owner_mismatch"):
        cells(inputs, model)
    model = observation_model(inputs)
    model["physical_fit_ids"][0] = "other physical owner"
    with pytest.raises(ExperimentalContractError, match="model_physical_owner_mismatch"):
        cells(inputs, model)
    oldkeys = binding_interaction_operand_keys(inputs)
    inputs["parameter_kind"] = "reported_hill_kd"
    assert oldkeys != binding_interaction_operand_keys(inputs)


def test_covariance_full_matrix_correlations_singular_and_invalid_models():
    inputs = example()
    matrix = [[0.04 if i == j else 0 for j in range(4)] for i in range(4)]
    matrix[0][1] = matrix[1][0] = 0.01
    assert cells(inputs, observation_model(inputs, matrix))["log_interaction_variance"]["value"] == pytest.approx(0.14)
    singular = observation_model(inputs, [[0.04] * 4 for _ in range(4)])
    result = cells(inputs, singular)
    assert result["log_interaction_variance"]["value"] == 0
    assert result["signed_profile_log_ratio"]["reason"] == "zero_interaction_variance"
    matrix[0][1] = matrix[1][0] = 1.0
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        cells(inputs, observation_model(inputs, matrix))
    model = observation_model(inputs)
    model["log_covariance"] = [[1, 0], [0, 1]]
    with pytest.raises(ExperimentalContractError, match="four_by_four_covariance_required"):
        cells(inputs, model)


def test_known_covariance_requires_supplied_physical_owners_and_no_spread_inference():
    inputs = example()
    for operand in inputs["operands"].values():
        operand["physical_fit_id"] = None
        operand["reported_spread"] = 0.1
        operand["uncertainty"].update(statistic="sem", exact_count=12, minimum_count=3,
                                      basis="fit_to_averaged_curve")
    assert cells(inputs)["signed_profile_log_ratio"]["reason"] == "observation_model_missing"
    with pytest.raises(ExperimentalContractError, match="actual_covariance_and_physical_owners_required"):
        cells(inputs, observation_model(inputs))


def test_uncertainty_endpoints_counts_and_nonfinite_validation():
    inputs = example()
    operand = inputs["operands"][ROLES[0]]
    operand["uncertainty"].update(statistic="confidence_interval", interval=[4, 6], confidence_level=0.95)
    assert cells(inputs)["interaction_ratio"]["value"] == 4
    operand["uncertainty"]["interval"] = [-1, 6]
    assert populate_binding_interaction(inputs)["inputs"]["operands"][ROLES[0]]["uncertainty"]["interval"] == [-1, 6]
    operand["reported_spread"] = 1
    with pytest.raises(ExperimentalContractError, match="symmetric_spread_not_applicable"):
        cells(inputs)
    operand["reported_spread"] = None
    operand["uncertainty"]["interval"] = None
    partial = populate_binding_interaction(inputs)
    assert partial["inputs"]["operands"][ROLES[0]]["uncertainty"]["interval"] is None
    assert partial["cells"]["interaction_ratio"]["value"] == 4
    inputs = example()
    inputs["operands"][ROLES[0]]["uncertainty"].update(exact_count=2, minimum_count=3)
    with pytest.raises(ExperimentalContractError, match="exact_count_below_minimum"):
        cells(inputs)
    for bad in (float("nan"), float("inf"), True, 0, -1):
        inputs = example()
        inputs["operands"][ROLES[0]]["value"] = bad
        with pytest.raises(ExperimentalContractError):
            cells(inputs)


def test_methods_byte_image_and_table_witness_union_and_closed_fields():
    inputs = example()
    inputs["relationships"]["separate_assays"]["sources"] = [witness(15, "utf8_span"),
        witness(16, "image_region"), witness(17, "table_cell")]
    assert cells(inputs)["interaction_ratio"]["value"] == 4
    inputs["relationships"]["separate_assays"]["sources"] = []
    with pytest.raises(ExperimentalContractError, match="relationship_witness_required"):
        cells(inputs)
    inputs = example()
    inputs["operands"][ROLES[0]]["source"]["extra"] = "not a field"
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        cells(inputs)


def test_extreme_raw_ratio_failure_does_not_destroy_log_or_score():
    inputs = example((1e-200, 1e200, 1e200, 1e-200))
    result = cells(inputs, observation_model(inputs))
    assert result["interaction_ratio"]["reason"] == "numerical_representation_range"
    assert result["log_interaction"]["value"] == pytest.approx(800 * math.log(10))
    assert result["signed_profile_log_ratio"]["value"] > 0
    assert result["signed_index"]["value"] == 1
    inputs = example((1e200, 1e-200, 1e-200, 1e200))
    result = cells(inputs)
    assert result["interaction_ratio"]["value"] is None
    assert result["log_interaction"]["value"] < 0


def test_large_variance_unrepresentable_but_std_and_score_survive():
    inputs = example()
    matrix = [[1e308 if i == j else 0 for j in range(4)] for i in range(4)]
    result = cells(inputs, observation_model(inputs, matrix))
    assert result["log_interaction_variance"]["reason"] == "variance_representation_range"
    assert result["log_interaction_standard_uncertainty"]["value"] == pytest.approx(2e154)
    assert result["signed_profile_log_ratio"]["value"] > 0


def test_profile_overflow_retains_representable_bounded_index_without_certainty_claim():
    inputs = example()
    matrix = [[5e-324 if i == j else 0 for j in range(4)] for i in range(4)]
    sheet = populate_binding_interaction(inputs, observation_model(inputs, matrix))
    assert sheet["cells"]["signed_profile_log_ratio"]["reason"] == "profile_log_ratio_representation_range"
    assert sheet["cells"]["signed_index"]["value"] == 1
    assert "signed_index_rounded_endpoint_not_certainty" in sheet["qualifications"]


def test_exact_product_cancellation_and_near_unit_log_are_not_false_zero():
    inputs = example((1e200, 1e200 * (1 + 1e-15), 1e200, 1e200))
    result = cells(inputs)
    assert result["log_interaction"]["value"] > 0
    null = cells(example((1e200, 1e-200, 1e200, 1e-200)))
    assert null["interaction_ratio"]["value"] == 1
    assert null["log_interaction"]["value"] == 0


def test_detached_inputs_models_and_sheet_are_strict_finite_json():
    inputs = example()
    model = observation_model(inputs)
    snapshot = deepcopy((inputs, model))
    result = populate_binding_interaction(inputs, model)
    assert (inputs, model) == snapshot
    json.dumps(result, allow_nan=False)
    result["inputs"]["operands"][ROLES[0]]["value"] = 999
    result["model"]["log_covariance"][0][0] = 999
    assert (inputs, model) == snapshot
    detached = validate_binding_interaction_inputs(inputs)
    detached["operands"][ROLES[0]]["value"] = 999
    assert inputs["operands"][ROLES[0]]["value"] == 5


def _linear_solve(matrix, rhs):
    """Independent pivoted elimination used only by constrained-normal checks."""
    rows = [list(row) + [value] for row, value in zip(matrix, rhs)]
    count = len(rows)
    for column in range(count):
        pivot = max(range(column, count), key=lambda i: abs(rows[i][column]))
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        assert abs(divisor) > 1e-12
        rows[column] = [value / divisor for value in rows[column]]
        for index in range(count):
            if index != column:
                factor = rows[index][column]
                rows[index] = [a - factor * b for a, b in zip(rows[index], rows[column])]
    return [row[-1] for row in rows]


@pytest.mark.parametrize("values", ((5, 40, 2, 4), (5, 4, 2, 40)))
@pytest.mark.parametrize("partial", (False, True))
def test_score_matches_independent_joint_constrained_normal_optimization(values, partial):
    inputs = example(values)
    if partial:
        _partial_uncertainty(inputs, "level_unknown")
    matrix = [[0.16, 0.02, -0.01, 0.0], [0.02, 0.09, 0.0, 0.01],
              [-0.01, 0.0, 0.25, 0.03], [0.0, 0.01, 0.03, 0.36]]
    # Invert by solving four independent unit-vector systems. Then fit the
    # constrained normal mean using the precision-matrix KKT equations, rather
    # than computing c'C c or the production S expression.
    columns = [_linear_solve(matrix, [int(i == j) for i in range(4)]) for j in range(4)]
    precision = [list(row) for row in zip(*columns)]
    observations = [math.log(value) for value in values]
    constraint = [-1, 1, 1, -1]
    kkt = [row + [constraint[i]] for i, row in enumerate(precision)] + [constraint + [0]]
    rhs = [sum(row[j] * observations[j] for j in range(4)) for row in precision] + [0]
    constrained_mean = _linear_solve(kkt, rhs)[:4]
    assert sum(c * mean for c, mean in zip(constraint, constrained_mean)) == pytest.approx(0, abs=1e-12)
    residual = [observation - mean for observation, mean in zip(observations, constrained_mean)]
    deviance_half = sum(residual[i] * precision[i][j] * residual[j]
                        for i in range(4) for j in range(4)) / 2
    signed_optimum = math.copysign(deviance_half, sum(c * x for c, x in zip(constraint, observations)))
    assert cells(inputs, observation_model(inputs, matrix))["signed_profile_log_ratio"]["value"] == pytest.approx(signed_optimum)


def _partial_uncertainty(inputs, case):
    operand = inputs["operands"][ROLES[0]]
    if case == "unresolved":
        operand["uncertainty"] = None
        return
    uncertainty = operand["uncertainty"]
    if case in ("sd", "sem", "unspecified"):
        uncertainty["statistic"] = case
        return
    uncertainty.update(statistic="confidence_interval", interval=[4, 6], confidence_level=0.95)
    if case == "level_unknown":
        uncertainty["confidence_level"] = None
    elif case == "interval_unknown":
        uncertainty["interval"] = None
    elif case == "lower_unknown":
        uncertainty["interval"][0] = None
    elif case == "upper_unknown":
        uncertainty["interval"][1] = None
    elif case == "endpoints_and_level_unknown":
        uncertainty.update(interval=[None, None], confidence_level=None)
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case,codes", (
    ("unresolved", (0,)), ("sd", (1,)), ("sem", (1,)), ("unspecified", (1,)),
    ("level_unknown", (3,)), ("interval_unknown", (2,)),
    ("lower_unknown", (2,)), ("upper_unknown", (2,)),
    ("endpoints_and_level_unknown", (2, 3)),
))
@pytest.mark.parametrize("relation", ("eq", "gt"))
def test_partial_uncertainty_preserves_parameters_and_descriptive_contrasts(case, codes, relation):
    inputs = example()
    inputs["operands"][ROLES[0]]["relation"] = relation
    baseline = populate_binding_interaction(inputs)
    _partial_uncertainty(inputs, case)
    original = deepcopy(inputs)
    result = populate_binding_interaction(inputs)
    assert inputs == original == result["inputs"]
    assert result["inputs"] is not inputs
    for name in ("parameter_rr", "parameter_rt", "parameter_tr", "parameter_tt",
                 "reference_subject_ratio", "test_subject_ratio", "interaction_ratio", "log_interaction"):
        assert result["cells"][name] == baseline["cells"][name]
    interaction = result["cells"]["interaction_ratio"]
    assert interaction["value"] == (4 if relation == "eq" else None)
    assert interaction["threshold"] == (None if relation == "eq" else 4)
    assert interaction["relation"] == ("eq" if relation == "eq" else "lt")
    for name in ("log_interaction_variance", "log_interaction_standard_uncertainty",
                 "signed_profile_log_ratio", "signed_index"):
        assert result["cells"][name]["value"] is None
    added = [code + ":" + ROLES[0] for index, code in enumerate(UNCERTAINTY_PARTIAL_CODES)
             if index in codes]
    assert result["qualifications"] == baseline["qualifications"][:3] + added + baseline["qualifications"][3:]
    json.dumps(result, allow_nan=False)


def test_unresolved_metadata_is_distinct_from_supplied_unreported_statistic():
    inputs = example()
    before = populate_binding_interaction(inputs)
    inputs["operands"][ROLES[0]].update(uncertainty=None, reported_spread=0.3)
    result = populate_binding_interaction(inputs)
    assert result["inputs"]["operands"][ROLES[0]]["uncertainty"] is None
    assert result["inputs"]["operands"][ROLES[0]]["reported_spread"] == 0.3
    assert result["operand_keys"][ROLES[0]] != before["operand_keys"][ROLES[0]]
    assert result["physical_fit_ids"] == before["physical_fit_ids"]


@pytest.mark.parametrize("spread", (True, -0.1, float("nan"), float("inf")))
def test_null_metadata_never_skips_spread_validation(spread):
    inputs = example()
    inputs["operands"][ROLES[0]].update(uncertainty=None, reported_spread=spread)
    with pytest.raises(ExperimentalContractError):
        populate_binding_interaction(inputs)


@pytest.mark.parametrize("uncertainty", (None, "unreported"))
def test_unreported_parameter_cannot_have_spread_with_or_without_metadata(uncertainty):
    inputs = example()
    operand = inputs["operands"][ROLES[0]]
    operand.update(value=None, relation="unreported", reported_spread=0.1)
    if uncertainty is None:
        operand["uncertainty"] = None
    with pytest.raises(ExperimentalContractError, match="symmetric_spread_not_applicable"):
        populate_binding_interaction(inputs)
    operand["reported_spread"] = None
    result = populate_binding_interaction(inputs)
    assert result["cells"]["parameter_rt"]["value"] == 40
    assert result["cells"]["test_subject_ratio"]["value"] == 2
    assert result["cells"]["interaction_ratio"]["value"] is None


@pytest.mark.parametrize("interval", ([], [4], [4, 5, 6], (4, 6), [True, None],
                                     [None, float("nan")], [float("inf"), None], [6, 4], ["4", None]))
def test_partial_ci_still_requires_valid_known_endpoints(interval):
    inputs = example()
    _partial_uncertainty(inputs, "level_unknown")
    inputs["operands"][ROLES[0]]["uncertainty"]["interval"] = interval
    with pytest.raises(ExperimentalContractError):
        populate_binding_interaction(inputs)


@pytest.mark.parametrize("level", (True, 0, 1, -0.1, float("nan"), float("inf"), "0.95"))
def test_partial_ci_still_requires_valid_known_level(level):
    inputs = example()
    _partial_uncertainty(inputs, "interval_unknown")
    inputs["operands"][ROLES[0]]["uncertainty"]["confidence_level"] = level
    with pytest.raises(ExperimentalContractError):
        populate_binding_interaction(inputs)


@pytest.mark.parametrize("statistic,spread,interval,level", (
    ("sd", None, [None, 6], None), ("sem", None, None, 0.95),
    ("unspecified", None, [4, 6], 0.95), ("unreported", 0.1, None, None),
    ("confidence_interval", 0.1, [4, None], None),
))
def test_partial_metadata_rejects_contradictory_statistic_fields(statistic, spread, interval, level):
    inputs = example()
    operand = inputs["operands"][ROLES[0]]
    operand["reported_spread"] = spread
    operand["uncertainty"].update(statistic=statistic, interval=interval, confidence_level=level)
    with pytest.raises(ExperimentalContractError):
        populate_binding_interaction(inputs)


def test_ci_missing_whole_interval_and_missing_endpoints_remain_as_supplied():
    inputs = example()
    _partial_uncertainty(inputs, "interval_unknown")
    first = populate_binding_interaction(inputs)
    inputs["operands"][ROLES[0]]["uncertainty"]["interval"] = [None, None]
    second = populate_binding_interaction(inputs)
    assert first["inputs"]["operands"][ROLES[0]]["uncertainty"]["interval"] is None
    assert second["inputs"]["operands"][ROLES[0]]["uncertainty"]["interval"] == [None, None]
    assert first["operand_keys"][ROLES[0]] != second["operand_keys"][ROLES[0]]
    assert first["cells"] == second["cells"]


@pytest.mark.parametrize("status", ("known", "estimated", "unknown"))
def test_partial_reported_uncertainty_does_not_select_or_upgrade_a_separate_model(status):
    inputs = example()
    old_model = observation_model(inputs, status=status)
    before = populate_binding_interaction(inputs, old_model)
    _partial_uncertainty(inputs, "level_unknown")
    result = populate_binding_interaction(inputs, observation_model(inputs, status=status))
    assert result["cells"] == before["cells"]
    assert result["model"]["variance_status"] == status
    if status != "known":
        assert result["cells"]["signed_profile_log_ratio"]["value"] is None
    with pytest.raises(ExperimentalContractError):
        populate_binding_interaction(inputs, old_model)


@lru_cache(maxsize=1)
def _baseline_module():
    path = Path(__file__).resolve().parents[1] / "verification" / "literature_reference_evidence_2026-10-25_001" / "a105_binding_partial_uncertainty_053" / "baseline_001" / "gene_annotation_episode" / "literature_binding_interaction_calculations.py"
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._binding_interaction_baseline_053", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _complete_baseline_cases():
    cases = [example(values) for values in ((5, 40, 2, 4), (5, 4, 2, 40), (2, 4, 5, 40),
                                          (1e-300, 1e300, 1e300, 1e-300),
                                          (1e300, 1e-300, 1e-300, 1e300))]
    for statistic in ("sd", "sem", "unspecified", "confidence_interval"):
        inputs = example()
        operand = inputs["operands"][ROLES[0]]
        operand["uncertainty"].update(statistic=statistic, exact_count=8, minimum_count=3,
            basis="between_independent_fitted_parameters", repetition_basis="biological_preparations")
        if statistic == "confidence_interval":
            operand["uncertainty"].update(interval=[-1, 6], confidence_level=0.95)
        else:
            operand["reported_spread"] = 0.1
        cases.append(inputs)
    for scope in ("reported_protocols", "common_conditions"):
        for status in ("matched", "not_matched", "unknown", "conflicting"):
            inputs = example()
            inputs["comparison_scope"] = scope
            inputs["relationships"]["common_conditions"] = {
                "status": status, "sources": [] if status == "unknown" else [witness(10)]}
            cases.append(inputs)
    for relations in (("gt", "eq", "eq", "eq"), ("lt", "gt", "eq", "eq"),
                      ("lt", "eq", "eq", "gt")):
        inputs = example()
        for role, relation in zip(ROLES, relations):
            inputs["operands"][role]["relation"] = relation
        cases.append(inputs)
    inputs = example()
    inputs["parameter_kind"] = "reported_hill_kd"
    cases.append(inputs)
    return cases


def test_previously_accepted_complete_result_dictionaries_are_exact():
    baseline = _baseline_module()
    for inputs in _complete_baseline_cases():
        for model in [None] + [observation_model(inputs, status=status)
                               for status in ("known", "estimated", "unknown")]:
            old = baseline.populate_binding_interaction(inputs, model)
            new = populate_binding_interaction(inputs, model)
            assert new == old
            # Sorted JSON comparison also distinguishes signed zero and exact
            # number serialization that Python dictionary equality can hide.
            assert json.dumps(new, sort_keys=True, allow_nan=False) == json.dumps(old, sort_keys=True, allow_nan=False)


def test_numeric_model_identity_and_relationship_code_is_unchanged_from_048():
    baseline = _baseline_module()
    baseline_tree = ast.parse(Path(baseline.__file__).read_text())
    current_tree = ast.parse((Path(__file__).resolve().parents[1] / "gene_annotation_episode" /
                              "literature_binding_interaction_calculations.py").read_text())
    old_functions = {node.name: node for node in baseline_tree.body if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: node for node in current_tree.body if isinstance(node, ast.FunctionDef)}
    assert set(new_functions) - set(old_functions) == {"_uncertainty_qualifications"}
    assert set(old_functions) <= set(new_functions)
    for name, node in old_functions.items():
        if name not in ("_uncertainty", "populate_binding_interaction"):
            assert ast.dump(node) == ast.dump(new_functions[name]), name
    current_populate = deepcopy(new_functions["populate_binding_interaction"])
    additions = [node for node in current_populate.body if isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                 and isinstance(node.value.func.value, ast.Name)
                 and node.value.func.value.id == "qualifications" and node.value.func.attr == "extend"
                 and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Call)
                 and isinstance(node.value.args[0].func, ast.Name)
                 and node.value.args[0].func.id == "_uncertainty_qualifications"]
    assert len(additions) == 1
    current_populate.body.remove(additions[0])
    assert ast.dump(current_populate) == ast.dump(old_functions["populate_binding_interaction"])
