"""Synthetic numerical checks; these are not published assay measurements."""
from copy import deepcopy
import math

import numpy as np
import pytest

from gene_annotation_episode.literature_activity_calculations import (
    COMPONENTS, PRIMITIVE_ORDER, populate_corrected_activity,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def example():
    return {"values": {"q": 1., "g": .15, "k": 1., "E": 1., "u": 2., "v": 1.6},
            "covariance": np.diag([.04, .0225, .0025, .01, .01, .01]).tolist(),
            "variance_status": "known", "distinct_residual_variance": .0625,
            "observation_model": "known_normal_nonnegative_presence"}


def test_reproduces_complete_correction_example_and_preserves_input():
    inputs = example()
    original = deepcopy(inputs)
    sheet = populate_corrected_activity(inputs)
    expected = {"corrected_activity": .68, "effect_variance": .11124225,
                "effect_standard_uncertainty": math.sqrt(.11124225),
                "effect_precision": 1/.11124225,
                "source_profile_log_ratio": 2.078347030916760,
                "source_presence_index": .777561486078909}
    assert sheet["primitive_order"] == list(PRIMITIVE_ORDER)
    assert set(sheet["cells"]) == set(COMPONENTS)
    for name, value in expected.items():
        assert sheet["cells"][name]["value"] == pytest.approx(value)
        assert sheet["cells"][name]["status"] == "populated"
    assert sheet["cells"]["source_presence_index"]["origin"] == "proposed"
    assert inputs == original
    sheet["inputs"]["values"]["q"] = 100
    assert inputs == original


def test_shared_primitive_covariance_has_signed_cross_terms():
    inputs = example()
    inputs["covariance"][0][1] = inputs["covariance"][1][0] = .01
    # q and g have opposite derivatives, so positive shared error cancels.
    sheet = populate_corrected_activity(inputs)
    assert sheet["cells"]["effect_variance"]["value"] == pytest.approx(.11124225 - 2*.8*.8*.01)


def test_jacobian_matches_independent_finite_difference_calculation():
    inputs = example()
    covariance = np.array(inputs["covariance"])
    covariance[0, 4] = covariance[4, 0] = .001
    covariance[2, 5] = covariance[5, 2] = -.0005
    inputs["covariance"] = covariance.tolist()
    x = np.array([inputs["values"][name] for name in PRIMITIVE_ORDER])

    def f(z):
        q, g, k, e, u, v = z
        return (q-g)*v/(k*e*u)

    derivatives = []
    for i in range(6):
        step = np.zeros(6)
        step[i] = 1e-5
        derivatives.append((f(x+step)-f(x-step))/(2e-5))
    d = np.array(derivatives)
    expected = d @ covariance @ d + inputs["distinct_residual_variance"]
    assert populate_corrected_activity(inputs)["cells"]["effect_variance"]["value"] == pytest.approx(expected)


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
def test_missing_primitive_does_not_become_default_or_zero(name):
    inputs = example()
    inputs["values"][name] = None
    cells = populate_corrected_activity(inputs)["cells"]
    assert all(cell["value"] is None for cell in cells.values())
    assert all(cell["unavailable_reason"] == "correction_inputs_not_supplied" for cell in cells.values())


def test_native_unknown_input_boundary_is_accepted_without_fabricating_score():
    inputs = {"values": dict.fromkeys(PRIMITIVE_ORDER), "covariance": None,
              "variance_status": "unknown", "distinct_residual_variance": None,
              "observation_model": "none"}
    cells = populate_corrected_activity(inputs)["cells"]
    assert all(cell["value"] is None for cell in cells.values())


@pytest.mark.parametrize("field,reason", [("covariance", "primitive_covariance_not_supplied"),
    ("distinct_residual_variance", "distinct_residual_variance_not_supplied")])
def test_missing_uncertainty_preserves_effect_but_not_invented_precision(field, reason):
    inputs = example()
    inputs[field] = None
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["corrected_activity"]["value"] == pytest.approx(.68)
    for name in COMPONENTS[1:]:
        assert cells[name]["value"] is None
        assert cells[name]["unavailable_reason"] == reason


@pytest.mark.parametrize("status", ["estimated", "unknown"])
def test_estimated_or_unknown_variance_is_not_known_normal_evidence(status):
    inputs = example()
    inputs["variance_status"] = status
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["effect_variance"]["value"] == pytest.approx(.11124225)
    assert cells["effect_precision"]["value"] == pytest.approx(1/.11124225)
    assert cells["source_profile_log_ratio"]["value"] is None
    assert cells["source_profile_log_ratio"]["unavailable_reason"] == "known_variance_required"


def test_explicit_observation_model_required_even_with_known_covariance():
    inputs = example()
    inputs["observation_model"] = "none"
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["effect_variance"]["value"] is not None
    assert cells["source_presence_index"]["value"] is None
    assert cells["source_presence_index"]["unavailable_reason"] == "observation_model_unspecified"


def test_negative_corrected_effect_remains_signed_without_positive_presence():
    inputs = example()
    inputs["values"]["q"] = -.5
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["corrected_activity"]["value"] == pytest.approx(-.52)
    assert cells["source_profile_log_ratio"]["value"] == 0
    assert cells["source_presence_index"]["value"] == 0


def test_zero_effect_is_valid_distinct_from_missing_measurement():
    inputs = example()
    inputs["values"]["q"] = inputs["values"]["g"]
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["corrected_activity"]["status"] == "populated"
    assert cells["corrected_activity"]["value"] == 0
    assert cells["source_presence_index"]["value"] == 0


def test_zero_covariance_is_permitted_but_zero_total_variance_not_infinite_evidence():
    inputs = example()
    inputs["covariance"] = np.zeros((6, 6)).tolist()
    inputs["distinct_residual_variance"] = 0
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["effect_variance"]["value"] == 0
    assert cells["effect_standard_uncertainty"]["value"] == 0
    assert cells["effect_precision"]["value"] is None
    assert cells["source_presence_index"]["value"] is None
    assert cells["source_presence_index"]["unavailable_reason"] == "positive_effect_variance_required"


def test_singular_psd_covariance_does_not_require_artificial_jitter():
    inputs = example()
    inputs["covariance"] = np.ones((6, 6)).tolist()
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["effect_variance"]["value"] > 0
    assert cells["source_presence_index"]["value"] is not None


@pytest.mark.parametrize("name", ["k", "E", "u", "v"])
@pytest.mark.parametrize("value", [0, -1])
def test_nonpositive_normalization_operands_rejected(name, value):
    inputs = example()
    inputs["values"][name] = value
    with pytest.raises(ExperimentalContractError, match="positive_normalization_operand_required"):
        populate_corrected_activity(inputs)


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), "1.0", 10**1000])
def test_invalid_primitive_number_rejected(value):
    inputs = example()
    inputs["values"]["q"] = value
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        populate_corrected_activity(inputs)


@pytest.mark.parametrize("mutation,code", [
    (lambda z: z.update(extra=0), "closed_fields_required"),
    (lambda z: z["values"].update(extra=0), "closed_fields_required"),
    (lambda z: z.update(variance_status="SD"), "unsupported_variance_status"),
    (lambda z: z.update(observation_model="normal"), "unsupported_observation_model"),
    (lambda z: z.update(distinct_residual_variance=-.1), "nonnegative_variance_required"),
    (lambda z: z.update(covariance=[[1]]), "six_by_six_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(1, .001), "symmetric_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(0, -.1), "positive_semidefinite_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(0, True), "finite_number_required"),
])
def test_invalid_closed_contract_and_covariance(mutation, code):
    inputs = example()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        populate_corrected_activity(inputs)


def test_indefinite_covariance_rejected_even_with_positive_diagonal():
    inputs = example()
    inputs["covariance"][0][1] = inputs["covariance"][1][0] = 2
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        populate_corrected_activity(inputs)


def test_overflow_returns_specific_unavailable_not_nonfinite_json():
    inputs = example()
    inputs["values"].update(q=1e308, g=-1e308)
    cells = populate_corrected_activity(inputs)["cells"]
    assert all(cell["value"] is None for cell in cells.values())
    assert all(cell["unavailable_reason"] == "numerical_model_range" for cell in cells.values())


def test_underflow_is_not_reported_as_exact_measured_zero():
    inputs = example()
    inputs["values"].update(q=1e-300, g=0, k=1e100, E=1, u=1, v=1)
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["corrected_activity"]["value"] is None
    assert cells["corrected_activity"]["unavailable_reason"] == "numerical_model_range"


def test_finite_effect_survives_out_of_range_derivative():
    inputs = example()
    inputs["values"].update(q=1e-309, g=0, k=1e-309, E=1, u=1, v=1)
    cells = populate_corrected_activity(inputs)["cells"]
    assert cells["corrected_activity"]["value"] == pytest.approx(1)
    assert cells["effect_variance"]["value"] is None
    assert cells["effect_variance"]["unavailable_reason"] == "numerical_model_range"
