"""Synthetic model fixtures only; no source papers, packets or network reads."""
from copy import deepcopy
from fractions import Fraction
import json
import math

import numpy as np
import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_transport_calculations import (
    COMPONENTS, PRIMITIVE_ORDER, VERSION, populate_transport_response,
)


def example():
    return {"values": {"substrate_test": 8., "substrate_reference": 32., "km": 12.},
            "curve_keys": dict.fromkeys(PRIMITIVE_ORDER, "synthetic_curve_A"),
            "measurement_keys": dict(zip(PRIMITIVE_ORDER, ("test_mean", "reference_mean", "fit_km"))),
            "covariance": [[4., 1., -.5], [1., 9., 2.], [-.5, 2., 1.]],
            "variance_status": "known", "observation_model": "michaelis_menten",
            "origin": "synthetic"}


def cells(inputs=None):
    return populate_transport_response(example() if inputs is None else inputs)["cells"]


def test_exact_interface_analytic_example_and_detached_inputs():
    inputs = example()
    before = deepcopy(inputs)
    result = populate_transport_response(inputs)
    assert set(result) == {"version", "primitive_order", "inputs", "cells"}
    assert result["version"] == VERSION == "a105_transport_response_v2"
    assert result["primitive_order"] == list(PRIMITIVE_ORDER)
    assert set(result["cells"]) == set(COMPONENTS)
    expected = {"substrate_test": 8., "substrate_reference": 32., "apparent_km": 12.,
                "test_saturation": .4, "reference_saturation": 8/11,
                "condition_response": .55, "log_condition_response": math.log(.55)}
    for name, value in expected.items():
        assert result["cells"][name]["value"] == pytest.approx(value)
    for cell in result["cells"].values():
        assert set(cell) == {"value", "unit", "status", "formula", "origin",
                             "unavailable_reason", "conditional_on"}
        assert cell["formula"]
        assert cell["status"] == "populated"
        assert cell["unavailable_reason"] is None
    assert inputs == before
    result["inputs"]["values"]["km"] = -1
    assert inputs == before
    json.dumps(result, allow_nan=False)


def test_conditions_units_and_native_origin():
    result = cells()
    for name in COMPONENTS[:3]:
        assert result[name]["conditional_on"] == []
        assert result[name]["origin"] == "synthetic"
        assert result[name]["unit"] == "uM"
    for name in COMPONENTS[3:7]:
        assert result[name]["conditional_on"] == ["same_kinetic_curve", "michaelis_menten_response"]
        assert result[name]["origin"] == "derived"
        assert result[name]["unit"] == "dimensionless"
    for name in COMPONENTS[7:]:
        assert result[name]["conditional_on"] == ["same_kinetic_curve", "michaelis_menten_response",
                                                  "first_order_covariance_propagation"]
    assert result["condition_response_variance"]["unit"] == "dimensionless_squared"


def test_full_jacobian_against_independent_finite_differences():
    inputs = example()
    x = np.array([inputs["values"][key] for key in PRIMITIVE_ORDER])

    def f(z):
        st, sr, k = z
        return (st/(k+st))/(sr/(k+sr))

    numerical = []
    for index in range(3):
        step = np.zeros(3)
        step[index] = 1e-4
        numerical.append((f(x+step)-f(x-step))/(2e-4))
    numerical = np.array(numerical)
    covariance = np.array(inputs["covariance"])
    expected_variance = numerical @ covariance @ numerical
    result = cells(inputs)
    assert result["condition_response_variance"]["value"] == pytest.approx(expected_variance, rel=1e-9)
    assert result["condition_response_standard_uncertainty"]["value"] == pytest.approx(math.sqrt(expected_variance))
    # Each coordinate separately checks the derivative, rather than relying on
    # a potentially compensating error in the complete quadratic form.
    for i in range(3):
        inputs["covariance"] = np.diag([float(j == i) for j in range(3)]).tolist()
        assert cells(inputs)["condition_response_variance"]["value"] == pytest.approx(numerical[i]**2, rel=1e-9)


def test_shared_km_occurs_once_and_cancels_between_two_saturations():
    inputs = example()
    inputs["covariance"] = [[0., 0., 0.], [0., 0., 0.], [0., 0., 4.]]
    # dh/dKm = (St/Sr)*(St-Sr)/(Km+St)^2 = -0.015 here.
    assert cells(inputs)["condition_response_variance"]["value"] == pytest.approx(.015**2*4)
    # The tempting independent-Km calculation is explicitly different.
    h = .55
    independent_wrong = h*h*4*((1/44)**2+(1/20)**2)
    assert cells(inputs)["condition_response_variance"]["value"] != pytest.approx(independent_wrong)


def test_equal_substrates_distinct_measurements_do_not_collapse():
    inputs = example()
    inputs["values"]["substrate_reference"] = 8.
    inputs["covariance"] = [[4., 0., 0.], [0., 4., 0.], [0., 0., 1.]]
    result = cells(inputs)
    assert result["condition_response"]["value"] == 1
    assert result["log_condition_response"]["value"] == 0
    assert result["condition_response_variance"]["value"] == pytest.approx(2*4*.075**2)


def test_identical_physical_substrates_have_exact_zero_variance():
    inputs = example()
    inputs["values"]["substrate_reference"] = 8.
    inputs["measurement_keys"]["substrate_reference"] = "test_mean"
    inputs["covariance"] = [[4., 4., 1.], [4., 4., 1.], [1., 1., 1.]]
    result = cells(inputs)
    assert result["condition_response"]["value"] == 1
    assert result["condition_response_variance"]["value"] == 0
    assert result["condition_response_standard_uncertainty"]["value"] == 0


def test_all_same_physical_measurement_and_singular_covariance():
    inputs = example()
    inputs["values"] = dict.fromkeys(PRIMITIVE_ORDER, 8.)
    inputs["measurement_keys"] = dict.fromkeys(PRIMITIVE_ORDER, "same_mean")
    inputs["covariance"] = [[4.]*3 for _ in range(3)]
    assert cells(inputs)["condition_response_variance"]["value"] == 0


@pytest.mark.parametrize("status", ["known", "estimated"])
def test_known_or_estimated_covariance_can_propagate_without_score(status):
    inputs = example()
    inputs["variance_status"] = status
    result = cells(inputs)
    assert result["condition_response_variance"]["value"] > 0
    assert not any("score" in name or "credit" in name or "likelihood" in name for name in result)


@pytest.mark.parametrize("covariance,status,reason", [
    (None, "known", "primitive_covariance_not_supplied"),
    (None, "unknown", "primitive_covariance_not_supplied"),
    ([[0.]*3 for _ in range(3)], "unknown", "primitive_variance_status_unknown"),
])
def test_missing_or_unknown_covariance_never_becomes_independence(covariance, status, reason):
    inputs = example()
    inputs.update(covariance=covariance, variance_status=status)
    result = cells(inputs)
    assert result["condition_response"]["value"] == pytest.approx(.55)
    for name in COMPONENTS[7:]:
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == reason


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
def test_missing_input_preserves_unaffected_native_values_and_saturation(name):
    inputs = example()
    inputs["values"][name] = None
    result = cells(inputs)
    for primitive, native in zip(PRIMITIVE_ORDER, COMPONENTS[:3]):
        assert result[native]["value"] == inputs["values"][primitive]
    for affected in COMPONENTS[5:]:
        assert result[affected]["value"] is None
        assert result[affected]["unavailable_reason"] == "concentration_inputs_not_supplied"
    if name == "substrate_test":
        assert result["reference_saturation"]["value"] is not None
    elif name == "substrate_reference":
        assert result["test_saturation"]["value"] is not None
    else:
        assert result["test_saturation"]["value"] is None
        assert result["reference_saturation"]["value"] is None


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
@pytest.mark.parametrize("value", [0., -2.])
def test_nonpositive_native_values_survive_with_unavailable_calculation(name, value):
    inputs = example()
    inputs["values"][name] = value
    result = cells(inputs)
    native = COMPONENTS[PRIMITIVE_ORDER.index(name)]
    assert result[native]["value"] == value
    for affected in COMPONENTS[5:]:
        assert result[affected]["value"] is None
        assert result[affected]["unavailable_reason"] == "positive_concentration_required"


def test_differing_curve_preserves_native_and_only_applicable_saturation():
    inputs = example()
    inputs["curve_keys"]["substrate_reference"] = "synthetic_other_preparation"
    result = cells(inputs)
    assert result["substrate_reference"]["value"] == 32
    assert result["test_saturation"]["value"] == .4
    assert result["reference_saturation"]["value"] is None
    for affected in COMPONENTS[5:]:
        assert result[affected]["value"] is None
        assert result[affected]["unavailable_reason"] == "different_kinetic_curves"


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
def test_unknown_curve_cannot_establish_same_curve(name):
    inputs = example()
    inputs["curve_keys"][name] = None
    result = cells(inputs)
    assert result["condition_response"]["value"] is None
    assert result["condition_response"]["unavailable_reason"] == "kinetic_curve_identity_not_supplied"


def test_model_is_not_inferred_from_positive_numbers():
    inputs = example()
    inputs["observation_model"] = "unknown"
    result = cells(inputs)
    assert all(result[name]["value"] is not None for name in COMPONENTS[:3])
    assert all(result[name]["value"] is None for name in COMPONENTS[3:])
    assert result["condition_response"]["unavailable_reason"] == "observation_model_unspecified"


def test_all_unknown_inputs_remain_unknown():
    inputs = example()
    for field in ("values", "curve_keys", "measurement_keys"):
        inputs[field] = dict.fromkeys(PRIMITIVE_ORDER)
    inputs.update(covariance=None, variance_status="unknown", observation_model="unknown")
    assert all(cell["value"] is None for cell in cells(inputs).values())


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf"), "12", 10**1000])
def test_invalid_number_rejected(value):
    inputs = example()
    inputs["values"]["km"] = value
    with pytest.raises(ExperimentalContractError) as error:
        cells(inputs)
    assert (error.value.code, error.value.field) == ("finite_number_required", "values.km")


@pytest.mark.parametrize("field", ["curve_keys", "measurement_keys"])
@pytest.mark.parametrize("value", [True, 1, "", " ", [], {}])
def test_invalid_identity_rejected(field, value):
    inputs = example()
    inputs[field]["km"] = value
    with pytest.raises(ExperimentalContractError, match="nonempty_identity_required"):
        cells(inputs)


@pytest.mark.parametrize("field", ["values", "curve_keys", "measurement_keys"])
def test_closed_nested_fields(field):
    inputs = example()
    inputs[field]["extra"] = 1
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        cells(inputs)


@pytest.mark.parametrize("mutation,code", [
    (lambda z: z.update(extra=1), "closed_fields_required"),
    (lambda z: z.update(variance_status=[]), "unsupported_variance_status"),
    (lambda z: z.update(observation_model="hill"), "unsupported_observation_model"),
    (lambda z: z.update(origin="proposed"), "unsupported_origin"),
    (lambda z: z.update(covariance=[[1.]]), "three_by_three_covariance_required"),
    (lambda z: z.update(covariance=((1., 0., 0.),)*3), "three_by_three_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(1, .2), "symmetric_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(0, -1.), "positive_semidefinite_covariance_required"),
    (lambda z: z["covariance"][0].__setitem__(0, True), "finite_number_required"),
    (lambda z: z["covariance"][0].__setitem__(0, float("nan")), "finite_number_required"),
])
def test_invalid_closed_contract_and_covariance(mutation, code):
    inputs = example()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        cells(inputs)


@pytest.mark.parametrize("covariance", [
    [[1., 2., 0.], [2., 1., 0.], [0., 0., 1.]],
    [[1., -.75, -.75], [-.75, 1., -.75], [-.75, -.75, 1.]],
    [[1e308, 0., 0.], [0., 1e-300, 2e-300], [0., 2e-300, 1e-300]],
    [[0., 1e-300, 0.], [1e-300, 1., 0.], [0., 0., 1.]],
])
def test_every_psd_principal_minor_checked_without_scale_tolerance(covariance):
    inputs = example()
    inputs["covariance"] = covariance
    with pytest.raises(ExperimentalContractError, match="positive_semidefinite_covariance_required"):
        cells(inputs)


def test_shared_measurement_values_must_match_even_without_covariance():
    inputs = example()
    inputs["measurement_keys"]["substrate_reference"] = "test_mean"
    inputs["covariance"] = None
    with pytest.raises(ExperimentalContractError, match="shared_measurement_value_mismatch"):
        cells(inputs)


def test_shared_measurement_covariance_rows_must_match():
    inputs = example()
    inputs["values"]["substrate_reference"] = 8.
    inputs["measurement_keys"]["substrate_reference"] = "test_mean"
    with pytest.raises(ExperimentalContractError, match="shared_measurement_covariance_mismatch"):
        cells(inputs)


@pytest.mark.parametrize("name", PRIMITIVE_ORDER)
def test_missing_measurement_identity_preserves_response_without_uncertainty(name):
    inputs = example()
    inputs["measurement_keys"][name] = None
    result = cells(inputs)
    assert result["condition_response"]["value"] == pytest.approx(.55)
    assert result["log_condition_response"]["value"] == pytest.approx(math.log(.55))
    for native in COMPONENTS[:3]:
        assert result[native]["value"] is not None
    for uncertainty in COMPONENTS[7:]:
        assert result[uncertainty]["value"] is None
        assert result[uncertainty]["unavailable_reason"] == "primitive_measurement_identity_not_supplied"


def test_zero_covariance_does_not_impute_missing_physical_ownership():
    inputs = example()
    inputs["measurement_keys"] = dict.fromkeys(PRIMITIVE_ORDER)
    inputs["covariance"] = [[0.]*3 for _ in range(3)]
    result = cells(inputs)
    assert result["condition_response"]["value"] == pytest.approx(.55)
    assert result["condition_response_variance"]["value"] is None
    assert result["condition_response_variance"]["unavailable_reason"] == "primitive_measurement_identity_not_supplied"


def test_large_concentrations_avoid_sum_product_and_derivative_overflow():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e308, 5e307, 1e308)))
    inputs["covariance"] = [[1e308, 0., 0.], [0., 1e308, 0.], [0., 0., 1e308]]
    result = cells(inputs)
    assert result["test_saturation"]["value"] == .5
    assert result["reference_saturation"]["value"] == pytest.approx(1/3)
    assert result["condition_response"]["value"] == pytest.approx(1.5)
    assert result["condition_response_variance"]["value"] > 0
    assert result["condition_response_variance"]["value"] < 1e-307


def test_tiny_concentrations_keep_finite_variance_despite_out_of_range_gradient():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e-310, 2e-310, 1e-310)))
    inputs["covariance"] = [[0.]*3 for _ in range(3)]
    result = cells(inputs)
    assert result["condition_response"]["value"] == pytest.approx(.75)
    assert result["condition_response_variance"]["value"] == 0


@pytest.mark.parametrize("values", [(1e-300, 1e300, 1e300), (1e300, 1e-300, 1e300)])
def test_response_range_does_not_erase_finite_log_response(values):
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, values))
    result = cells(inputs)
    assert result["condition_response"]["value"] is None
    assert result["condition_response"]["unavailable_reason"] == "numerical_model_range"
    assert math.isfinite(result["log_condition_response"]["value"])
    json.dumps(result, allow_nan=False)


def test_near_unity_log_contrast_not_lost_to_rounded_response():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1., 2., 1e-30)))
    result = cells(inputs)
    assert result["condition_response"]["value"] == 1
    assert result["log_condition_response"]["value"] == pytest.approx(-5e-31, rel=1e-14, abs=0)


def test_log_contrast_underflow_is_explicit():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e300, 2e300, 1e-300)))
    result = cells(inputs)
    assert result["condition_response"]["value"] == 1
    assert result["log_condition_response"]["value"] is None
    assert result["log_condition_response"]["unavailable_reason"] == "numerical_model_range"


def test_variance_underflow_does_not_erase_representable_standard_uncertainty():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e200, 2e200, 1e200)))
    inputs["covariance"] = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    result = cells(inputs)
    assert result["condition_response_variance"]["value"] is None
    assert result["condition_response_variance"]["unavailable_reason"] == "numerical_model_range"
    assert 0 < result["condition_response_standard_uncertainty"]["value"] < 1e-199


def test_variance_overflow_does_not_erase_representable_standard_uncertainty():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e-200, 2e-200, 1e-200)))
    inputs["covariance"] = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
    result = cells(inputs)
    assert result["condition_response_variance"]["value"] is None
    assert result["condition_response_variance"]["unavailable_reason"] == "numerical_model_range"
    assert 1e199 < result["condition_response_standard_uncertainty"]["value"] < 1e200


def test_full_signed_covariance_changes_variance_relative_to_diagonal_only():
    inputs = example()
    full_variance = cells(inputs)["condition_response_variance"]["value"]
    inputs["covariance"] = np.diag([4., 9., 1.]).tolist()
    independent_variance = cells(inputs)["condition_response_variance"]["value"]
    assert full_variance != pytest.approx(independent_variance)
    # An independent analytic gradient retains the signs of every cross term.
    gradient = (.55*.075, -.55*12/(32*44), .55*(1/44-1/20))
    expected_difference = 2*(gradient[0]*gradient[1]
                             -.5*gradient[0]*gradient[2]
                             +2*gradient[1]*gradient[2])
    assert full_variance-independent_variance == pytest.approx(expected_difference)


def test_exact_quadratic_form_survives_signed_cancellation_and_overflow():
    inputs = example()
    # The complete quadratic form is zero although its floating summands would
    # overflow. Repeated measurement ownership establishes the cancellation.
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (1e-200, 1e-200, 1e-200)))
    inputs["measurement_keys"]["substrate_reference"] = "test_mean"
    inputs["covariance"] = [[1e308, 1e308, 0.], [1e308, 1e308, 0.], [0., 0., 0.]]
    assert cells(inputs)["condition_response_variance"]["value"] == 0


def test_exact_analytic_shared_km_special_case_for_arbitrary_native_means():
    inputs = example()
    inputs["values"] = dict(zip(PRIMITIVE_ORDER, (3., 7., 5.)))
    inputs["covariance"] = [[0., 0., 0.], [0., 0., 0.], [0., 0., 9.]]
    derivative = Fraction(3, 7)*Fraction(3-7, (5+3)**2)
    assert cells(inputs)["condition_response_variance"]["value"] == float(9*derivative**2)
