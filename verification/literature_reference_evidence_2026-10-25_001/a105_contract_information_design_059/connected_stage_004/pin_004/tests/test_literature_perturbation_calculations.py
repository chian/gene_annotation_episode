"""Synthetic fixtures only: source point arithmetic, never measured biology."""
from copy import deepcopy
from fractions import Fraction
import json
import math
import sys

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_perturbation_calculations import (
    VERSION, PRIMITIVE_ORDER, COMPONENTS, REASONS, CONDITIONAL_CODES,
    populate_source_restoration,
)


def example():
    return {
        "values": dict(zip(PRIMITIVE_ORDER, (100., 20., 90., 100., 90., 8., 7.))),
        "measurement_keys": {role: "synthetic_" + role for role in PRIMITIVE_ORDER},
        "endpoint_unit": "events_per_100000_cells", "exposure_unit": "molecules_per_cell",
        "design": "native_deletion_restoration", "measurement_status": "validated_ratio_scale",
        "same_endpoint_scope": "yes", "amount_role": "nuisance", "orientation": 1,
        "origin": "synthetic",
    }


def cells(inputs=None):
    return populate_source_restoration(example() if inputs is None else inputs)["cells"]


def test_exact_interface_and_synthetic_point_example():
    inputs = example()
    saved = deepcopy(inputs)
    result = populate_source_restoration(inputs)
    assert set(result) == {"version", "inputs", "primitive_order", "cells"}
    assert result["version"] == VERSION == "a106_source_restoration_v1"
    assert result["primitive_order"] == list(PRIMITIVE_ORDER)
    assert tuple(result["cells"]) == COMPONENTS
    expected = (100., 20., 90., 80., 2/3, .875, .875, .9, .9, .9, .9, .4725)
    for name, number in zip(COMPONENTS, expected):
        assert result["cells"][name]["value"] == pytest.approx(number)
    for name, cell in result["cells"].items():
        assert set(cell) == {"value", "unit", "status", "formula", "origin", "unavailable_reason", "conditional_on"}
        assert cell["formula"]
        assert cell["unavailable_reason"] is None or cell["unavailable_reason"] in REASONS
        assert set(cell["conditional_on"]) <= set(CONDITIONAL_CODES)
        assert cell["status"] == ("unavailable" if name in COMPONENTS[-2:] else "populated")
    assert inputs == saved
    result["inputs"]["values"]["W"] = -1
    assert inputs == saved
    json.dumps(result, allow_nan=False)


def test_meaning_units_origins_and_no_target_or_final_credit():
    result = cells()
    for name in COMPONENTS[:3]:
        assert result[name]["origin"] == "synthetic"
        assert result[name]["conditional_on"] == []
    for name in (*COMPONENTS[:4],):
        assert result[name]["unit"] == "events_per_100000_cells"
    for name in COMPONENTS[4:]:
        assert result[name]["unit"] == "dimensionless"
    for name in ("perturbation_difference", "symmetric_effect", "restoration_fraction_raw"):
        assert result[name]["origin"] == "derived"
    for name in COMPONENTS[6:]:
        assert result[name]["origin"] == "proposed"
    assert result["reference_restoration_index"]["conditional_on"] == ["source_restoration_convention"]
    assert not any(token in name for name in result for token in ("credit", "homology", "likelihood", "probability"))


@pytest.mark.parametrize("orientation,expected", [(1, .4725), (-1, -.4725), (None, None)])
def test_orientation_only_affects_source_index(orientation, expected):
    inputs = example()
    inputs["orientation"] = orientation
    result = cells(inputs)
    assert result["reference_restoration_index"]["value"] == pytest.approx(expected) if expected is not None else result["reference_restoration_index"]["value"] is None
    assert result["symmetric_effect"]["value"] == pytest.approx(2/3)
    assert result["restoration_agreement"]["value"] == .875
    if orientation is None:
        assert result["reference_restoration_index"]["unavailable_reason"] == "orientation_unreported"


def test_inhibitory_assertion_preserves_effect_sign_and_orients_source_index():
    inputs = example()
    inputs["values"].update(W=20., K=100., R=30.)
    assert cells(inputs)["symmetric_effect"]["value"] == pytest.approx(-2/3)
    assert cells(inputs)["reference_restoration_index"]["value"] == pytest.approx(-.4725)
    inputs["orientation"] = -1
    assert cells(inputs)["reference_restoration_index"]["value"] == pytest.approx(.4725)


@pytest.mark.parametrize("restored,raw,agreement", [(100, 1, 1), (110, 1.125, .875), (180, 2, 0), (260, 3, 0), (10, -.125, 0)])
def test_restoration_overshoot_unrestricted_raw_and_bounded_agreement(restored, raw, agreement):
    inputs = example()
    inputs["values"]["R"] = restored
    result = cells(inputs)
    assert result["restoration_fraction_raw"]["value"] == raw
    assert result["restoration_agreement"]["value"] == agreement


@pytest.mark.parametrize("design", ["cas_free_reconstitution", "variant_replacement", "other_explicit", "unknown", "conflicting"])
def test_no_fabricated_restoration_in_other_designs(design):
    inputs = example()
    inputs["design"] = design
    result = cells(inputs)
    assert result["symmetric_effect"]["value"] == pytest.approx(2/3)
    assert result["perturbation_isolation"]["value"] == .9
    for name in ("restoration_fraction_raw", "restoration_agreement", "restoration_isolation", "effect_isolation", "reference_restoration_index"):
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == "restoration_design_not_established"


def test_selective_perturbation_design_permits_matched_restoration():
    inputs = example()
    inputs["design"] = "selective_perturbation_restoration"
    assert cells(inputs)["reference_restoration_index"]["value"] == pytest.approx(.4725)


@pytest.mark.parametrize("field,value,reason", [
    ("measurement_status", "unknown", "ratio_scale_not_validated"),
    ("measurement_status", "conflicting", "ratio_scale_not_validated"),
    ("same_endpoint_scope", "unknown", "same_endpoint_not_established"),
    ("same_endpoint_scope", "no", "same_endpoint_not_established"),
    ("same_endpoint_scope", "conflicting", "same_endpoint_not_established"),
])
def test_unvalidated_endpoint_preserves_native_measurements(field, value, reason):
    inputs = example()
    inputs[field] = value
    result = cells(inputs)
    assert [result[name]["value"] for name in COMPONENTS[:3]] == [100, 20, 90]
    for name in ("perturbation_difference", "symmetric_effect", "restoration_fraction_raw", "perturbation_isolation", "reference_restoration_index"):
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == reason
    assert result["amount_comparability"]["value"] == .9


@pytest.mark.parametrize("role", ["W", "K", "R"])
def test_qualitative_endpoint_rejects_any_numeric_endpoint(role):
    inputs = example()
    inputs["measurement_status"] = "qualitative_only"
    inputs["values"].update(W=None, K=None, R=None)
    inputs["values"][role] = 0
    with pytest.raises(ExperimentalContractError, match="qualitative_endpoint_has_no_numeric_values"):
        cells(inputs)


def test_qualitative_endpoint_with_missing_values_stays_unknown():
    inputs = example()
    inputs["measurement_status"] = "qualitative_only"
    inputs["values"].update(W=None, K=None, R=None)
    result = cells(inputs)
    assert all(result[name]["value"] is None for name in COMPONENTS[:7])


@pytest.mark.parametrize("role", PRIMITIVE_ORDER)
def test_missing_primitive_never_invents_complete_source_index(role):
    inputs = example()
    inputs["values"][role] = None
    result = cells(inputs)
    assert result["reference_restoration_index"]["value"] is None
    if role not in ("W", "K"):
        assert result["symmetric_effect"]["value"] == pytest.approx(2/3)
    if role == "B_rest":
        assert result["perturbation_isolation"]["value"] == .9
        assert result["restoration_isolation"]["unavailable_reason"] == "effect_bound_unreported"


@pytest.mark.parametrize("role", ["W", "K", "R"])
def test_missing_endpoint_identity_preserves_native_and_rejects_affected_contrast(role):
    inputs = example()
    inputs["measurement_keys"][role] = None
    result = cells(inputs)
    assert all(result[name]["value"] is not None for name in COMPONENTS[:3])
    assert result["restoration_fraction_raw"]["unavailable_reason"] == "role_measurement_identity_unreported"
    if role == "R":
        assert result["symmetric_effect"]["value"] == pytest.approx(2/3)
    else:
        assert result["symmetric_effect"]["value"] is None


@pytest.mark.parametrize("left,right", [("W", "K"), ("W", "R"), ("K", "R")])
def test_shared_actual_endpoint_does_not_establish_distinct_arms(left, right):
    inputs = example()
    inputs["values"][right] = inputs["values"][left]
    inputs["measurement_keys"][right] = inputs["measurement_keys"][left]
    result = cells(inputs)
    assert result["restoration_fraction_raw"]["unavailable_reason"] == "role_measurement_not_distinct"
    assert all(result[name]["value"] is not None for name in COMPONENTS[:3])
    if (left, right) == ("W", "K"):
        assert result["perturbation_difference"]["value"] is None
    else:
        assert result["perturbation_difference"]["value"] == 80


def test_equal_endpoints_with_distinct_keys_mean_measured_zero_difference():
    inputs = example()
    inputs["values"]["K"] = 100
    result = cells(inputs)
    assert result["perturbation_difference"]["value"] == 0
    assert result["symmetric_effect"]["value"] == 0
    assert result["restoration_agreement"]["unavailable_reason"] == "zero_perturbation_difference"
    assert result["perturbation_isolation"]["unavailable_reason"] == "zero_effect_denominator"
    assert result["reference_restoration_index"]["value"] is None


def test_same_nuisance_amount_measurement_can_be_used_without_independence_claim():
    inputs = example()
    inputs["values"]["A_restored"] = inputs["values"]["A_reference"]
    inputs["measurement_keys"]["A_restored"] = inputs["measurement_keys"]["A_reference"]
    assert cells(inputs)["amount_comparability"]["value"] == 1
    assert cells(inputs)["reference_restoration_index"]["value"] == pytest.approx(.525)


def test_same_identity_requires_same_values_even_with_missing_operand():
    inputs = example()
    inputs["measurement_keys"]["R"] = inputs["measurement_keys"]["W"]
    with pytest.raises(ExperimentalContractError, match="shared_measurement_value_mismatch"):
        cells(inputs)
    inputs["values"]["R"] = None
    with pytest.raises(ExperimentalContractError, match="shared_measurement_value_mismatch"):
        cells(inputs)


@pytest.mark.parametrize("endpoint,exposure", [("fraction", "molecules_per_cell"), ("minutes", "normalized_signal"), ("per_min", "mg_per_mL")])
def test_same_physical_measurement_cannot_have_incompatible_units(endpoint, exposure):
    inputs = example()
    inputs.update(endpoint_unit=endpoint, exposure_unit=exposure)
    inputs["measurement_keys"]["A_reference"] = inputs["measurement_keys"]["W"]
    with pytest.raises(ExperimentalContractError, match="shared_measurement_unit_mismatch"):
        cells(inputs)


@pytest.mark.parametrize("role", ["intended_change", "unknown"])
def test_no_nuisance_penalty_inferred_for_intended_or_unknown_amount_role(role):
    inputs = example()
    inputs["amount_role"] = role
    result = cells(inputs)
    assert result["amount_comparability"]["value"] is None
    assert result["reference_restoration_index"]["value"] is None
    assert result["restoration_agreement"]["value"] == .875


@pytest.mark.parametrize("a,b,expected", [(0, 100, 0), (100, 0, 0), (100, 25, .25), (25, 100, .25), (0, 0, None)])
def test_amount_comparability_symmetric_and_zero_denominator_explicit(a, b, expected):
    inputs = example()
    inputs["values"].update(A_reference=a, A_restored=b)
    result = cells(inputs)
    assert result["amount_comparability"]["value"] == expected
    if expected is None:
        assert result["amount_comparability"]["unavailable_reason"] == "zero_amount_denominator"


@pytest.mark.parametrize("bound,component,effect", [("B_pert", "perturbation_isolation", 80), ("B_rest", "restoration_isolation", 70)])
@pytest.mark.parametrize("multiple,expected", [(0, 1), (.25, .75), (1, 0), (2, 0)])
def test_supplied_nonnegative_isolation_bound_clips_at_effect(bound, component, effect, multiple, expected):
    inputs = example()
    inputs["values"][bound] = effect * multiple
    result = cells(inputs)
    assert result[component]["value"] == expected
    assert result["effect_isolation"]["value"] == min(expected, .9)


def test_unrestored_endpoint_has_undefined_isolation_even_with_zero_bound():
    inputs = example()
    inputs["values"].update(R=20, B_rest=0)
    result = cells(inputs)
    assert result["restoration_agreement"]["value"] == 0
    assert result["restoration_isolation"]["unavailable_reason"] == "zero_effect_denominator"
    assert result["reference_restoration_index"]["value"] is None


def test_zero_factor_never_hides_unknown_other_component():
    inputs = example()
    inputs["values"].update(A_restored=0, B_rest=None)
    result = cells(inputs)
    assert result["amount_comparability"]["value"] == 0
    assert result["reference_restoration_index"]["value"] is None


def test_all_zero_endpoints_preserve_native_and_difference_not_fake_ratio():
    inputs = example()
    inputs["values"].update(W=0, K=0, R=0)
    result = cells(inputs)
    assert result["perturbation_difference"]["value"] == 0
    assert result["symmetric_effect"]["unavailable_reason"] == "zero_endpoint_sum"
    assert result["reference_restoration_index"]["value"] is None


def test_joint_uncertainty_bounds_unknown_even_with_complete_points():
    result = cells()
    assert result["reference_restoration_index"]["value"] == pytest.approx(.4725)
    for name in COMPONENTS[-2:]:
        assert result[name]["value"] is None
        assert result[name]["unavailable_reason"] == "joint_uncertainty_unreported"


def test_all_missing_operands_and_units_are_explicit_unknowns():
    inputs = example()
    inputs.update(values=dict.fromkeys(PRIMITIVE_ORDER), measurement_keys=dict.fromkeys(PRIMITIVE_ORDER),
                  endpoint_unit="unreported", exposure_unit="unreported", design="unknown",
                  measurement_status="unknown", same_endpoint_scope="unknown", amount_role="unknown", orientation=None)
    result = cells(inputs)
    assert all(cell["value"] is None for cell in result.values())
    assert result["reference_endpoint"]["unit"] == "unreported"


@pytest.mark.parametrize("field,roles", [("endpoint_unit", ("W", "K", "R", "B_pert", "B_rest")), ("exposure_unit", ("A_reference", "A_restored"))])
def test_unreported_unit_only_permitted_for_absent_corresponding_values(field, roles):
    inputs = example()
    inputs[field] = "unreported"
    with pytest.raises(ExperimentalContractError, match="observed_unit_required"):
        cells(inputs)
    for role in roles:
        inputs["values"][role] = None
    cells(inputs)


@pytest.mark.parametrize("bad", [True, False, float("inf"), -float("inf"), float("nan"), "3", [], {}, 10**1000])
@pytest.mark.parametrize("role", ["W", "A_reference", "B_pert"])
def test_malformed_numeric_input_rejected(bad, role):
    inputs = example()
    inputs["values"][role] = bad
    with pytest.raises(ExperimentalContractError) as error:
        cells(inputs)
    assert (error.value.code, error.value.field) == ("finite_number_required", "values." + role)


@pytest.mark.parametrize("role", PRIMITIVE_ORDER)
def test_negative_native_values_rejected(role):
    inputs = example()
    inputs["values"][role] = -1
    with pytest.raises(ExperimentalContractError, match="nonnegative_value_required"):
        cells(inputs)


@pytest.mark.parametrize("bad", [True, False, 0, 2, -2, 1., "1", [], {}])
def test_orientation_must_be_literal_signed_int_or_null(bad):
    inputs = example()
    inputs["orientation"] = bad
    with pytest.raises(ExperimentalContractError, match="signed_orientation_required"):
        cells(inputs)


@pytest.mark.parametrize("bad", [True, 1, "", " ", [], {}])
def test_identity_must_be_nonempty_string_or_null(bad):
    inputs = example()
    inputs["measurement_keys"]["W"] = bad
    with pytest.raises(ExperimentalContractError, match="nonempty_identity_required"):
        cells(inputs)


@pytest.mark.parametrize("field", ["endpoint_unit", "exposure_unit", "design", "measurement_status", "same_endpoint_scope", "amount_role", "origin"])
@pytest.mark.parametrize("bad", [[], None, "unsupported"])
def test_closed_categorical_contract(field, bad):
    inputs = example()
    inputs[field] = bad
    with pytest.raises(ExperimentalContractError, match="unsupported_" + field):
        cells(inputs)


@pytest.mark.parametrize("field", [None, "values", "measurement_keys"])
def test_extra_and_missing_fields_rejected(field):
    for operation in ("add", "remove"):
        inputs = example()
        target = inputs if field is None else inputs[field]
        if operation == "add":
            target["extra"] = 1
        else:
            target.pop(next(iter(target)))
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            cells(inputs)


@pytest.mark.parametrize("scale", [1e-300, 1e300])
def test_scale_invariance_avoids_preventable_sum_ratio_overflow_and_underflow(scale):
    inputs = example()
    inputs["values"] = {role: value * scale for role, value in inputs["values"].items()}
    result = cells(inputs)
    for component in COMPONENTS[4:-2]:
        assert result[component]["value"] == pytest.approx(cells()[component]["value"])
    assert math.isfinite(result["perturbation_difference"]["value"])


def test_max_float_endpoints_do_not_overflow_symmetric_sum():
    inputs = example()
    high = sys.float_info.max
    inputs["values"].update(W=high, K=high/2, R=high, B_pert=0, B_rest=0)
    result = cells(inputs)
    assert result["symmetric_effect"]["value"] == pytest.approx(1/3)
    assert result["restoration_agreement"]["value"] == 1
    assert result["reference_restoration_index"]["value"] == pytest.approx(.3)


def test_extreme_raw_restoration_overflow_does_not_erase_clipped_agreement():
    inputs = example()
    inputs["values"].update(W=1e-300, K=0, R=1e300, B_pert=0, B_rest=0)
    result = cells(inputs)
    assert result["restoration_fraction_raw"]["value"] is None
    assert result["restoration_fraction_raw"]["unavailable_reason"] == "numerical_model_range"
    assert result["restoration_agreement"]["value"] == 0
    assert result["reference_restoration_index"]["value"] == 0
    json.dumps(result, allow_nan=False)


def test_extreme_amount_ratio_underflow_not_fabricated_zero():
    inputs = example()
    inputs["values"].update(A_reference=1e-300, A_restored=1e300)
    result = cells(inputs)
    assert result["amount_comparability"]["value"] is None
    assert result["amount_comparability"]["unavailable_reason"] == "numerical_model_range"
    assert result["reference_restoration_index"]["value"] is None
    assert result["reference_restoration_index"]["unavailable_reason"] == "numerical_model_range"


def test_smallest_native_float_preserved_and_tiny_contrasts_exact():
    inputs = example()
    tiny = math.ulp(0.)
    inputs["values"].update(W=2*tiny, K=tiny, R=2*tiny, B_pert=0, B_rest=0)
    result = cells(inputs)
    assert result["perturbed_endpoint"]["value"] == tiny
    assert result["perturbation_difference"]["value"] == tiny
    assert result["symmetric_effect"]["value"] == pytest.approx(1/3)
    assert result["reference_restoration_index"]["value"] == pytest.approx(.3)


def test_repeated_W_K_R_usage_is_one_exact_formula_not_independent_multipliers():
    inputs = example()
    w, k, r, a, ar, bp, br = (Fraction(inputs["values"][role]) for role in PRIMITIVE_ORDER)
    expected = (w-k)/(w+k) * (1-abs(r-w)/abs(w-k)) * min(a, ar)/max(a, ar) * min(1-bp/abs(w-k), 1-br/abs(r-k))
    assert cells(inputs)["reference_restoration_index"]["value"] == float(expected)
