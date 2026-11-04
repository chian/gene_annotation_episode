"""Invented parsed-input fixtures only; no paper, graph, model or episode run."""
from copy import deepcopy
from fractions import Fraction
import json
import math

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_controlled_response_calculations import (
    ARM_FIELDS, CELL_FIELDS, COMPONENTS, INPUT_VERSION, PRIMITIVE_ORDER, REASONS,
    RELATIONSHIP_FIELDS, VERSION, populate_controlled_response,
    validate_controlled_response_inputs,
)


def example():
    arms = {}
    for i, (name, value) in enumerate(zip(PRIMITIVE_ORDER, (12, 2, 5, 1))):
        protein = i % 2 == 0
        arms[name] = {"value": value, "threshold": None, "relation": "eq",
            "approximate": False, "unit": "nmol/min/mg", "status": "point",
            "endpoint_id": "synthetic_retained_tracer_initial_rate",
            "normalization_id": "synthetic_common_positive_paired_reference_protein_mass",
            "subject_construct_id": "synthetic_protein_construct" if protein else "synthetic_empty_preparation",
            "condition_id": "synthetic_condition1" if i < 2 else "synthetic_condition0",
            "physical_observation_id": "synthetic_actual_" + name,
            "source_observation_id": "synthetic_source_" + name,
            "origin": "synthetic", "digitization_interval": None,
            "protein_arrangement": "protein_present" if protein else "protein_free_control",
            "meaning_statuses": dict.fromkeys(("endpoint", "normalization", "subject_construct",
                                               "condition", "physical_observation"), "known")}
    return {"version": INPUT_VERSION, "arms": arms,
        "relationships": {"condition1_target": {"status": "known", "canonical_id": "synthetic_condition1"},
            "condition0_target": {"status": "known", "canonical_id": "synthetic_condition0"},
            "condition_levels_relation": "different",
            "condition1_control_application": "matched_condition_control",
            "condition0_control_application": "matched_condition_control",
            "subject_construct_across_conditions": "same", "control_reference_reuse": "distinct_observations",
            "nonintended_conditions": "unknown", "intended_factor": "synthetic_witness_intended_protocol_change"},
        "covariance": {"primitive_order": list(PRIMITIVE_ORDER),
            "physical_observation_ids": [arms[name]["physical_observation_id"] for name in PRIMITIVE_ORDER],
            "units": ["nmol/min/mg"] * 4,
            "matrix": [[(1, .25, .36, .09)[i] if i == j else 0 for j in range(4)] for i in range(4)]},
        "variance_status": "known", "model_kind": "none"}


def cells(inputs=None):
    return populate_controlled_response(example() if inputs is None else inputs)["cells"]


def no_covariance(inputs):
    inputs.update(covariance=None, variance_status="unknown")
    return inputs


def observed_bound(inputs, index, relation, threshold):
    inputs["arms"][PRIMITIVE_ORDER[index]].update(status="bound", value=None,
        threshold=threshold, relation=relation)


def meaning_state(inputs, index, meaning, state):
    arm = inputs["arms"][PRIMITIVE_ORDER[index]]
    arm["meaning_statuses"][meaning] = state
    arm[meaning + "_id"] = None


def shared_control():
    inputs = example()
    left = inputs["arms"][PRIMITIVE_ORDER[1]]
    right = inputs["arms"][PRIMITIVE_ORDER[3]]
    right.update(value=left["value"], condition_id=left["condition_id"],
        physical_observation_id=left["physical_observation_id"])
    inputs["relationships"].update(condition0_control_application="shared_reference_assumption",
        control_reference_reuse="same_reference_with_stated_invariance")
    inputs["covariance"]["physical_observation_ids"][3] = left["physical_observation_id"]
    inputs["covariance"]["matrix"] = [[1, 0, 0, 0], [0, .25, 0, .25],
        [0, 0, .36, 0], [0, .25, 0, .25]]
    return inputs


def test_frozen_exact_interface_and_synthetic_native_to_canonical_numbers():
    inputs = example()
    before = deepcopy(inputs)
    result = populate_controlled_response(inputs)
    assert set(result) == {"version", "primitive_order", "inputs", "cells"}
    assert result["version"] == VERSION == "controlled_response_sheet_v1"
    assert INPUT_VERSION == "controlled_response_inputs_v1"
    assert tuple(result["primitive_order"]) == PRIMITIVE_ORDER
    assert tuple(result["cells"]) == COMPONENTS
    assert set(inputs["relationships"]) == set(RELATIONSHIP_FIELDS)
    assert all(set(arm) == set(ARM_FIELDS) for arm in inputs["arms"].values())
    expected = (.012, .002, .005, .001, .010, .004, .006, .0000017,
                math.sqrt(.0000017), 1/.0000017)
    for name, value in zip(COMPONENTS, expected):
        assert result["cells"][name]["value"] == pytest.approx(value)
    assert result["cells"][COMPONENTS[7]]["unit"] == "(umol/min/mg)^2"
    assert result["cells"][COMPONENTS[9]]["unit"] == "(umol/min/mg)^-2"
    for name, cell in result["cells"].items():
        assert set(cell) == set(CELL_FIELDS)
        assert cell["origin"] == "synthetic"
        expected_bound_state = dict.fromkeys(("lower", "upper"), "not_applicable" if cell["value"] is not None else "unknown")
        assert cell["bound_state"] == expected_bound_state
        assert set(cell["unavailable_reason"] or ()) <= set(REASONS)
        assert cell["formula_code"]
    assert result["cells"][COMPONENTS[10]]["value"] is None
    assert result["cells"][COMPONENTS[10]]["unavailable_reason"] == ["observation_model_unselected"]
    assert inputs == before
    result["inputs"]["arms"][PRIMITIVE_ORDER[0]]["value"] = -1
    assert inputs == before
    assert validate_controlled_response_inputs(inputs) == inputs
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("values", [(1, 2, 5, 1), (6, 2, 5, 1), (0, -2, -5, -1)])
def test_signed_noisy_and_zero_values_without_logs_or_pseudocounts(values):
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    for name, value in zip(PRIMITIVE_ORDER, values):
        inputs["arms"][name]["value"] = value
    result = cells(inputs)
    e = values[0] - values[1] - values[2] + values[3]
    expected = e * abs(e) / (2 * 1.7)
    assert result[COMPONENTS[6]]["value"] == pytest.approx(e * .001)
    assert result[COMPONENTS[10]]["value"] == pytest.approx(expected)
    assert result[COMPONENTS[11]]["value"] == pytest.approx(math.tanh(expected / 2))


@pytest.mark.parametrize("condition", ["matched", "different", "unknown", "conflicting"])
def test_intended_factor_is_signal_other_cochanges_never_quality_penalty(condition):
    inputs = example()
    inputs["relationships"]["nonintended_conditions"] = condition
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .006
    if condition != "matched":
        assert "nonintended_conditions_" + condition in result[COMPONENTS[6]]["conditional_on"]


@pytest.mark.parametrize("index", range(4))
def test_absent_role_never_filled_or_zero_and_other_pair_survives(index):
    inputs = no_covariance(example())
    inputs["arms"][PRIMITIVE_ORDER[index]] = None
    result = cells(inputs)
    assert result[COMPONENTS[index]]["value"] is None
    assert result[COMPONENTS[6]]["value"] is None
    assert "missing_arm" in result[COMPONENTS[6]]["unavailable_reason"]
    other = COMPONENTS[5 if index < 2 else 4]
    assert result[other]["value"] == (.004 if index < 2 else .010)
    for i in range(4):
        if i != index:
            assert result[COMPONENTS[i]]["value"] is not None


@pytest.mark.parametrize("meaning", ["endpoint", "normalization", "condition"])
@pytest.mark.parametrize("state", ["unknown", "conflicting"])
def test_unknown_second_pair_never_erases_first_pair(meaning, state):
    inputs = example()
    meaning_state(inputs, 3, meaning, state)
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] == .010
    assert result[COMPONENTS[5]]["value"] is None
    assert result[COMPONENTS[6]]["value"] is None
    assert result[COMPONENTS[3]]["value"] == .001
    if state == "conflicting":
        assert result[COMPONENTS[5]]["status"] == "conflicting"


def test_common_unit_spelling_does_not_establish_biological_denominator():
    inputs = example()
    inputs["arms"][PRIMITIVE_ORDER[1]]["normalization_id"] = "synthetic_lipid_mass"
    result = cells(inputs)
    assert result[COMPONENTS[1]]["value"] == .002
    assert result[COMPONENTS[4]]["value"] is None
    assert "different_normalization" in result[COMPONENTS[4]]["unavailable_reason"]
    assert result[COMPONENTS[5]]["value"] == .004


@pytest.mark.parametrize("meaning", ["endpoint", "normalization"])
def test_two_locally_valid_pairs_with_different_cross_meaning_keep_both_pairs(meaning):
    inputs = example()
    for index in (2, 3):
        inputs["arms"][PRIMITIVE_ORDER[index]][meaning + "_id"] = "synthetic_distinct_" + meaning
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] == .010
    assert result[COMPONENTS[5]]["value"] == .004
    assert result[COMPONENTS[6]]["value"] is None


def test_cross_pair_dimensions_must_agree_even_when_local_pairs_and_ids_agree():
    inputs = no_covariance(example())
    for index, unit in enumerate(("umol/min", "umol/min", "uM/min", "uM/min")):
        inputs["arms"][PRIMITIVE_ORDER[index]]["unit"] = unit
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] == 10
    assert result[COMPONENTS[4]]["unit"] == "umol/min"
    assert result[COMPONENTS[5]]["value"] == 4
    assert result[COMPONENTS[5]]["unit"] == "uM/min"
    for name in COMPONENTS[6:]:
        assert result[name]["value"] is None
        assert "incompatible_unit_dimension" in result[name]["unavailable_reason"]


@pytest.mark.parametrize("field,value", [
    ("subject_construct_across_conditions", "unknown"),
    ("subject_construct_across_conditions", "different"),
    ("condition_levels_relation", "unknown"),
    ("condition_levels_relation", "same"),
    ("intended_factor", None),
    ("control_reference_reuse", "conflicting"),
])
def test_cross_condition_relationships_do_not_gate_local_pairs(field, value):
    inputs = example()
    inputs["relationships"][field] = value
    result = cells(inputs)
    assert [result[name]["value"] for name in COMPONENTS[4:6]] == [.010, .004]
    assert result[COMPONENTS[6]]["value"] is None


def test_unknown_reuse_and_ownership_qualify_magnitude_without_independence():
    inputs = no_covariance(example())
    inputs["relationships"]["control_reference_reuse"] = "unknown"
    for index in (1, 3):
        meaning_state(inputs, index, "physical_observation", "unknown")
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .006
    assert "unknown_control_reuse" in result[COMPONENTS[6]]["conditional_on"]
    assert result[COMPONENTS[7]]["value"] is None
    assert "unknown_covariance" in result[COMPONENTS[7]]["unavailable_reason"]


def test_source_condition_correspondence_not_inferred_from_role_label():
    inputs = example()
    inputs["arms"][PRIMITIVE_ORDER[1]]["condition_id"] = "synthetic_other_source_condition"
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] is None
    assert "different_condition_correspondence" in result[COMPONENTS[4]]["unavailable_reason"]
    inputs["relationships"]["condition1_control_application"] = "shared_reference_assumption"
    assert cells(inputs)[COMPONENTS[4]]["value"] == .010
    meaning_state(inputs, 1, "condition", "unknown")
    assert cells(inputs)[COMPONENTS[4]]["value"] is None


def test_actual_reused_control_keeps_its_measured_condition_and_cancels_jointly():
    inputs = shared_control()
    before = deepcopy(inputs)
    result = cells(inputs)
    assert [result[name]["value"] for name in COMPONENTS[4:7]] == [.010, .003, .007]
    assert result[COMPONENTS[7]]["value"] == .00000136
    assert inputs == before
    assert inputs["arms"][PRIMITIVE_ORDER[3]]["condition_id"] == "synthetic_condition1"
    inputs["relationships"]["condition0_control_application"] = "unknown"
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] == .010
    assert result[COMPONENTS[5]]["value"] is None
    assert result[COMPONENTS[6]]["value"] is None
    assert result[COMPONENTS[3]]["value"] == .002


def test_genuinely_shared_censored_control_cancels_but_is_never_a_profile_point():
    inputs = shared_control()
    inputs["model_kind"] = "known_joint_normal_source_means"
    observed_bound(inputs, 1, "ge", 2)
    observed_bound(inputs, 3, "ge", 2)
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] is None
    assert result[COMPONENTS[4]]["upper"] == .010
    assert result[COMPONENTS[5]]["upper"] == .003
    assert result[COMPONENTS[6]]["value"] == .007
    assert result[COMPONENTS[10]]["value"] is None
    assert "unresolved_censoring_model" in result[COMPONENTS[10]]["unavailable_reason"]
    no_covariance(inputs)
    inputs["arms"][PRIMITIVE_ORDER[3]] = None
    assert cells(inputs)[COMPONENTS[6]]["value"] is None


def test_unknown_reuse_cannot_create_alias_but_explicit_owner_identity_can():
    inputs = no_covariance(shared_control())
    inputs["relationships"]["control_reference_reuse"] = "unknown"
    observed_bound(inputs, 1, "ge", 2)
    observed_bound(inputs, 3, "ge", 2)
    result = cells(inputs)
    # Cancellation is established by consistent actual owner identity and the
    # explicit shared application, not by the unresolved reuse category.
    assert result[COMPONENTS[6]]["value"] == .007
    assert "unknown_control_reuse" in result[COMPONENTS[6]]["conditional_on"]
    for index in (1, 3):
        meaning_state(inputs, index, "physical_observation", "unknown")
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] is None
    assert result[COMPONENTS[6]]["unavailable_reason"] == ["uninformative_bounds"]
    # Equal thresholds under different actual owners do not supply identity.
    for index in (1, 3):
        arm = inputs["arms"][PRIMITIVE_ORDER[index]]
        arm["meaning_statuses"]["physical_observation"] = "known"
        arm["physical_observation_id"] = "synthetic_distinct_control_" + str(index)
    assert cells(inputs)[COMPONENTS[6]]["value"] is None


def test_conflicting_reused_source_value_without_covariance_preserves_raw_and_local_pairs():
    inputs = no_covariance(shared_control())
    inputs["arms"][PRIMITIVE_ORDER[3]]["value"] = 3
    result = cells(inputs)
    assert result[COMPONENTS[3]]["value"] == .003
    assert result[COMPONENTS[4]]["value"] == .010
    assert result[COMPONENTS[5]]["value"] == .002
    assert result[COMPONENTS[6]]["status"] == "conflicting"


def test_equal_values_or_shared_preparation_name_do_not_assert_physical_identity():
    inputs = example()
    inputs["arms"][PRIMITIVE_ORDER[3]]["value"] = 2
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .007
    assert result[COMPONENTS[7]]["value"] == .0000017
    assert result[COMPONENTS[7]]["value"] != .00000136


@pytest.mark.parametrize("index,relation", [(0, "lt"), (1, "gt"), (2, "gt"), (3, "lt")])
def test_each_fixed_sign_and_strict_limit_direction(index, relation):
    inputs = no_covariance(example())
    observed_bound(inputs, index, relation, (12, 2, 5, 1)[index])
    result = cells(inputs)
    effect = result[COMPONENTS[6]]
    assert effect["value"] is None and effect["upper"] == .006
    assert effect["relation"] == "lt" and effect["lower"] is None
    assert effect["bound_state"] == {"lower": "unbounded", "upper": "available"}
    assert effect["bound_kind"] == "reported_limit"


@pytest.mark.parametrize("strict", [False, True])
def test_signed_combination_of_reported_limits_preserves_strictness(strict):
    inputs = no_covariance(example())
    for index, relation in enumerate(("lt" if strict else "le", "ge", "ge", "le")):
        observed_bound(inputs, index, relation, (12, 2, 5, 1)[index])
    result = cells(inputs)[COMPONENTS[6]]
    assert result["upper"] == .006
    assert result["relation"] == ("lt" if strict else "le")


def test_opposing_uncensored_directions_are_uninformative_not_zero():
    inputs = no_covariance(example())
    observed_bound(inputs, 0, "lt", 12)
    observed_bound(inputs, 1, "lt", 2)
    result = cells(inputs)[COMPONENTS[4]]
    assert result["value"] is result["lower"] is result["upper"] is None
    assert result["unavailable_reason"] == ["uninformative_bounds"]
    assert result["bound_state"] == {"lower": "unbounded", "upper": "unbounded"}


def test_graph_nominal_and_interval_are_not_a_sampling_model():
    inputs = example()
    arm = inputs["arms"][PRIMITIVE_ORDER[0]]
    arm.update(origin="graph_derived", relation="interval", digitization_interval={"lower": 11, "upper": 13})
    inputs["model_kind"] = "known_joint_normal_source_means"
    result = cells(inputs)
    effect = result[COMPONENTS[6]]
    assert effect["value"] == .006
    assert (effect["lower"], effect["upper"]) == (.005, .007)
    assert effect["bound_kind"] == "conditional_digitization"
    assert result[COMPONENTS[10]]["value"] is None
    assert "unresolved_reading_model" in result[COMPONENTS[10]]["unavailable_reason"]


def test_mixed_graph_and_printed_limits_keep_different_bound_semantics():
    inputs = no_covariance(example())
    inputs["arms"][PRIMITIVE_ORDER[0]].update(origin="graph_derived", relation="interval",
        digitization_interval={"lower": 11, "upper": 13})
    observed_bound(inputs, 1, "gt", 2)
    result = cells(inputs)[COMPONENTS[6]]
    assert result["value"] is None and result["upper"] == .007 and result["relation"] == "lt"
    assert result["bound_kind"] == "mixed"


def test_known_normal_profile_requires_actual_selected_model_and_exact_reading():
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    result = cells(inputs)
    score = 36 / 3.4
    assert result[COMPONENTS[10]]["value"] == pytest.approx(score)
    assert result[COMPONENTS[11]]["value"] == pytest.approx(math.tanh(score / 2))
    inputs["arms"][PRIMITIVE_ORDER[0]]["approximate"] = True
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .006
    assert result[COMPONENTS[6]]["approximate"] is True
    assert result[COMPONENTS[7]]["value"] == .0000017
    assert result[COMPONENTS[10]]["value"] is None


def test_estimated_covariance_is_retained_but_never_a_known_model():
    inputs = example()
    inputs.update(variance_status="estimated", model_kind="known_joint_normal_source_means")
    result = cells(inputs)
    assert result[COMPONENTS[7]]["value"] == .0000017
    assert "estimated_covariance" in result[COMPONENTS[7]]["conditional_on"]
    assert result[COMPONENTS[10]]["unavailable_reason"] == ["estimated_covariance"]


def test_actual_full_covariance_and_common_offset_cancellation():
    inputs = example()
    inputs["covariance"]["matrix"] = [[value + .16 for value in row] for row in inputs["covariance"]["matrix"]]
    # Decimal addition before parsing can encode tiny different entries; build
    # the stipulated source decimals exactly, not rounded floating summands.
    inputs["covariance"]["matrix"] = [[1.16, .16, .16, .16], [.16, .41, .16, .16],
        [.16, .16, .52, .16], [.16, .16, .16, .25]]
    assert cells(inputs)[COMPONENTS[7]]["value"] == .0000017
    factor = [[1, 0], [.5, 2], [-1, 1], [0, -2]]
    inputs["covariance"]["matrix"] = [[sum(a*b for a,b in zip(left,right)) for right in factor] for left in factor]
    assert cells(inputs)[COMPONENTS[7]]["value"] == .00002725


def test_singular_full_common_covariance_retains_zero_without_jitter():
    inputs = example()
    inputs.update(model_kind="known_joint_normal_source_means")
    inputs["covariance"]["matrix"] = [[.16]*4 for _ in range(4)]
    result = cells(inputs)
    assert result[COMPONENTS[7]]["value"] == 0
    assert result[COMPONENTS[8]]["value"] == 0
    for name in COMPONENTS[9:]:
        assert result[name]["value"] is None
        assert "nonpositive_variance_for_model" in result[name]["unavailable_reason"]


def test_covariance_units_are_each_applied_once_and_alias_rows_reconciled_in_base_units():
    inputs = shared_control()
    inputs["arms"][PRIMITIVE_ORDER[3]].update(unit="umol/min/mg", value=.002)
    inputs["covariance"]["units"][3] = "umol/min/mg"
    inputs["covariance"]["matrix"] = [[1, 0, 0, 0], [0, .25, 0, .00025],
        [0, 0, .36, 0], [0, .00025, 0, .00000025]]
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .007
    assert result[COMPONENTS[7]]["value"] == .00000136


@pytest.mark.parametrize("matrix", [
    [[1, 2, 0, 0], [2, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    [[1, -.75, -.75, 0], [-.75, 1, -.75, 0], [-.75, -.75, 1, 0], [0, 0, 0, 1]],
    [[1 if i == j else -.4 for j in range(4)] for i in range(4)],
    [[0, 1e-300, 0, 0], [1e-300, 1, 0, 0], [0, 0, 1e308, 0], [0, 0, 0, 1]],
])
def test_all_psd_principal_minors_without_relative_tolerance(matrix):
    inputs = example()
    inputs["covariance"]["matrix"] = matrix
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        cells(inputs)


@pytest.mark.parametrize("mutation,code", [
    (lambda z: z["covariance"]["matrix"][0].__setitem__(1, .1), "symmetric_covariance_required"),
    (lambda z: z["covariance"]["physical_observation_ids"].__setitem__(0, "wrong"), "covariance_owner_mismatch"),
    (lambda z: z["covariance"]["units"].__setitem__(0, "uM/min"), "covariance_unit_mismatch"),
    (lambda z: z["covariance"].update(primitive_order=list(reversed(PRIMITIVE_ORDER))), "covariance_order_mismatch"),
    (lambda z: z.update(covariance=None), "covariance_status_mismatch"),
    (lambda z: z.update(variance_status="unknown"), "covariance_status_mismatch"),
])
def test_invalid_direct_covariance_raises_instead_of_becoming_independence(mutation, code):
    inputs = example()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        cells(inputs)


def test_shared_covariance_rows_must_match_and_cannot_hide_bad_source_values():
    inputs = shared_control()
    inputs["covariance"]["matrix"] = [[1, 0, 0, 0], [0, .25, 0, 0], [0, 0, .36, 0], [0, 0, 0, .25]]
    with pytest.raises(ExperimentalContractError, match="shared_measurement_covariance_mismatch"):
        cells(inputs)
    inputs = shared_control()
    inputs["arms"][PRIMITIVE_ORDER[3]]["value"] = 3
    with pytest.raises(ExperimentalContractError, match="shared_measurement_context_mismatch"):
        cells(inputs)


def test_reader_style_null_covariance_partial_preserves_magnitude_not_fake_statistics():
    inputs = no_covariance(example())
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == .006
    assert all(result[name]["value"] is None for name in COMPONENTS[7:])
    assert result[COMPONENTS[7]]["unavailable_reason"] == ["unknown_covariance"]


def test_final_variance_underflow_does_not_erase_uncertainty_precision_or_profile():
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    for name, value in zip(PRIMITIVE_ORDER, (2e-160, 0, 1e-160, 0)):
        inputs["arms"][name]["value"] = value
    inputs["covariance"]["matrix"] = [[1e-320 if i == j else 0 for j in range(4)] for i in range(4)]
    result = cells(inputs)
    assert result[COMPONENTS[7]]["value"] is None
    assert result[COMPONENTS[7]]["unavailable_reason"] == ["numeric_range_failure"]
    assert result[COMPONENTS[8]]["value"] == pytest.approx(2e-163, rel=1e-14, abs=0)
    assert result[COMPONENTS[9]]["value"] is None
    assert result[COMPONENTS[10]]["value"] == pytest.approx(.125)
    assert result[COMPONENTS[11]]["value"] == pytest.approx(math.tanh(.0625))


def test_scaled_raw_overflow_does_not_erase_canceled_effect():
    inputs = no_covariance(example())
    for arm in inputs["arms"].values():
        arm.update(unit="mmol/min", value=1e308)
        arm["normalization_id"] = "synthetic_common_unscaled_assay_basis"
    result = cells(inputs)
    assert all(result[name]["value"] is None for name in COMPONENTS[:4])
    assert result[COMPONENTS[4]]["value"] == 0
    assert result[COMPONENTS[5]]["value"] == 0
    assert result[COMPONENTS[6]]["value"] == 0


def test_variance_overflow_keeps_representable_uncertainty_precision_and_profile():
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    for arm in inputs["arms"].values():
        arm.update(unit="mmol/min", normalization_id="synthetic_common_unscaled_assay_basis")
    inputs["covariance"]["units"] = ["mmol/min"] * 4
    inputs["covariance"]["matrix"] = [[1e308 if i == j else 0 for j in range(4)] for i in range(4)]
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == 6000
    assert result[COMPONENTS[7]]["value"] is None
    assert result[COMPONENTS[8]]["value"] == 2e157
    assert result[COMPONENTS[9]]["value"] == pytest.approx(2.5e-315, rel=1e-8, abs=0)
    assert result[COMPONENTS[10]]["value"] == pytest.approx(4.5e-308, rel=1e-14, abs=0)
    assert result[COMPONENTS[11]]["value"] == pytest.approx(2.25e-308, rel=1e-14, abs=0)
    # The exact effect itself can exceed float range while S remains finite.
    for i, name in enumerate(PRIMITIVE_ORDER):
        inputs["arms"][name]["value"] = 1e308 if i == 0 else 0
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] is None
    assert result[COMPONENTS[10]]["value"] == 1.25e307
    assert result[COMPONENTS[11]]["value"] == 1


def test_tiny_nonzero_profile_and_index_do_not_silently_become_zero():
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    for i, name in enumerate(PRIMITIVE_ORDER):
        inputs["arms"][name]["value"] = 1e-170 if i == 0 else 0
    result = cells(inputs)
    assert result[COMPONENTS[6]]["value"] == 1e-173
    for name in COMPONENTS[10:]:
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == ["numeric_range_failure"]


@pytest.mark.parametrize("status,reason", [("missing", "missing_arm"),
    ("ambiguous", "ambiguous_source_literal"), ("conflicting", "conflicting_source_literal"),
    ("unsupported", "unsupported_source_expression")])
def test_unavailable_parsed_measurement_retains_other_raw_and_pair(status, reason):
    inputs = example()
    arm = inputs["arms"][PRIMITIVE_ORDER[3]]
    arm.update(status=status, value=None, relation="none")
    if status == "missing":
        arm["source_observation_id"] = None
    result = cells(inputs)
    assert result[COMPONENTS[4]]["value"] == .010
    assert result[COMPONENTS[0]]["value"] == .012
    assert result[COMPONENTS[3]]["value"] is None
    assert reason in result[COMPONENTS[3]]["unavailable_reason"]
    assert reason in result[COMPONENTS[6]]["unavailable_reason"]


def test_unknown_unit_preserves_native_input_without_a_dimensionless_numeric_cell():
    inputs = no_covariance(example())
    inputs["arms"][PRIMITIVE_ORDER[3]]["unit"] = None
    result = populate_controlled_response(inputs)
    raw = result["cells"][COMPONENTS[3]]
    assert raw["value"] is None and raw["unit"] is None and raw["status"] == "partial"
    assert result["inputs"]["arms"][PRIMITIVE_ORDER[3]]["value"] == 1
    assert result["cells"][COMPONENTS[4]]["value"] == .010
    assert result["cells"][COMPONENTS[5]]["value"] is None


def test_one_source_observation_cannot_be_relabelled_as_distinct_actual_measurements():
    inputs = no_covariance(shared_control())
    left = inputs["arms"][PRIMITIVE_ORDER[1]]
    right = inputs["arms"][PRIMITIVE_ORDER[3]]
    right["source_observation_id"] = left["source_observation_id"]
    right["physical_observation_id"] = "synthetic_false_distinct_owner"
    inputs["relationships"]["control_reference_reuse"] = "distinct_observations"
    assert cells(inputs)[COMPONENTS[6]]["status"] == "conflicting"


def test_bounded_range_partial_keeps_each_representable_endpoint_and_its_meaning():
    inputs = no_covariance(example())
    inputs["arms"][PRIMITIVE_ORDER[0]].update(unit="mmol/min", origin="graph_derived", value=1e305,
        relation="interval", digitization_interval={"lower": .001, "upper": 1e308})
    result = cells(inputs)[COMPONENTS[0]]
    assert result["value"] == 1e308
    assert result["lower"] == 1 and result["upper"] is None
    assert result["status"] == "partial" and result["relation"] == "ge"
    assert result["bound_state"] == {"lower": "available", "upper": "numeric_range_failure"}
    assert result["unavailable_reason"] == ["numeric_range_failure"]
    assert result["bound_kind"] == "conditional_digitization"


def test_nonzero_subnormal_bound_must_not_become_zero_or_known_unbounded():
    inputs = no_covariance(example())
    observed_bound(inputs, 0, "gt", 5e-324)
    result = cells(inputs)[COMPONENTS[0]]
    assert result["lower"] is None and result["status"] == "unavailable"
    assert result["bound_state"] == {"lower": "numeric_range_failure", "upper": "unbounded"}
    assert result["unavailable_reason"] == ["numeric_range_failure"]


def test_huge_profile_retains_representable_bounded_index():
    inputs = example()
    inputs["model_kind"] = "known_joint_normal_source_means"
    inputs["arms"][PRIMITIVE_ORDER[0]]["value"] = 1e308
    result = cells(inputs)
    assert result[COMPONENTS[10]]["value"] is None
    assert result[COMPONENTS[11]]["value"] == 1


@pytest.mark.parametrize("value", [True, False, float("inf"), float("nan"), "12", 10**1000])
def test_malformed_numbers_rejected(value):
    inputs = example()
    inputs["arms"][PRIMITIVE_ORDER[0]]["value"] = value
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        cells(inputs)


@pytest.mark.parametrize("mutation", [
    lambda z: z.update(extra=1),
    lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(count=3),
    lambda z: z["relationships"].update(endpoint_correspondence="same"),
    lambda z: z["arms"][PRIMITIVE_ORDER[0]]["meaning_statuses"].update(extra="known"),
    lambda z: z["covariance"].update(origin="derived"),
])
def test_closed_contract_prevents_numerical_and_statistical_shortcuts(mutation):
    inputs = example()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        cells(inputs)


@pytest.mark.parametrize("mutation,code", [
    (lambda z: z.update(version="future"), "unsupported_input_version"),
    (lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(approximate=0), "boolean_required"),
    (lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(unit="U/mg"), "unsupported_value"),
    (lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(endpoint_id=None), "meaning_identity_mismatch"),
    (lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(physical_observation_id=True), "nonempty_identity_required"),
    (lambda z: z["arms"][PRIMITIVE_ORDER[0]].update(threshold=0), "point_contract_mismatch"),
    (lambda z: z["relationships"]["condition1_target"].update(status="unknown"), "meaning_identity_mismatch"),
    (lambda z: z.update(model_kind="independent_normal_groups"), "unsupported_value"),
])
def test_semantic_contract_failures_are_actionable(mutation, code):
    inputs = example()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        cells(inputs)
