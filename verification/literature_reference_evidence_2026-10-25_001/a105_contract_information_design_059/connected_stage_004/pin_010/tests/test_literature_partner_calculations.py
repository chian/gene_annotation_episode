"""Experimental meanings, shared censor domains and numeric boundary checks."""
from copy import deepcopy
from fractions import Fraction
import math
import sys

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_calculations import (
    COMPONENTS, VERSION, populate_partner_components,
)


def _arm(value, identity, *, present=True):
    return {
        "subject_ref": "subject:assayed_construct", "partner_ref": "partner:construct",
        "partner_state": "present" if present else "absent",
        "endpoint_ref": "endpoint:product_formation", "normalization_ref": "normalization:subject_amount",
        "unit": "pmol/min/mg",
        "conditions": {"coverage": "complete", "factors": [
            {"factor": "nitrogen_source", "level": "glutamine", "unit": "identity"},
            {"factor": "temperature", "level": 37, "unit": "degC"},
            {"factor": "subject_amount", "level": 20, "unit": "uM"},
        ]},
        "measurement": {"measurement_id": identity, "status": "observed", "value": value,
            "origin": "synthetic", "spread": {"kind": "unreported", "magnitude": None}},
    }


def _inputs(w=100, o=20, a=90):
    return {"version": "literature_partner_inputs_v1", "arms": {
        "reference": _arm(w, "physical:W"),
        "omitted": _arm(o, "physical:O", present=False),
        "addback": _arm(a, "physical:A"),
    }}


def _set(record, path, value):
    target = record
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value


def _contains(cell, low, high):
    assert Fraction(cell["lower"]) <= low
    assert Fraction(cell["upper"]) >= high


def test_matched_components_are_actual_differences_and_fractions():
    source = _inputs()
    original = deepcopy(source)
    result = populate_partner_components(source)
    assert source == original and result["inputs"] == original
    assert result["version"] == VERSION
    assert tuple(result["cells"]) == COMPONENTS
    expected = (100, 20, 90, 80, .8, 70, .875, .7)
    for component, value in zip(COMPONENTS, expected):
        cell = result["cells"][component]
        assert cell["value"] == pytest.approx(value)
        assert cell["status"] == "populated"
        assert cell["bound_kind"] == "point_only_not_uncertainty"
        assert cell["unavailable_reason"] is None
        assert set(cell) == {"value", "lower", "upper", "unit", "origin", "bound_kind", "status", "unavailable_reason"}
    assert result["cells"]["restored_reference_fraction"]["value"] == pytest.approx(
        result["cells"]["partner_loss_fraction"]["value"] * result["cells"]["addback_fraction"]["value"])
    result["inputs"]["arms"]["reference"]["conditions"]["factors"].clear()
    assert source == original


def test_censored_omission_reuses_one_primitive_in_both_ratio_positions():
    source = _inputs(o=5)
    source["arms"]["omitted"]["measurement"]["status"] = "upper_bound"
    cells = populate_partner_components(source)["cells"]
    expected = {
        "partner_loss": (Fraction(95), Fraction(100)),
        "partner_loss_fraction": (Fraction(95, 100), Fraction(1)),
        "addback_gain": (Fraction(85), Fraction(90)),
        "addback_fraction": (Fraction(85, 95), Fraction(9, 10)),
        "restored_reference_fraction": (Fraction(85, 100), Fraction(9, 10)),
    }
    for component, (low, high) in expected.items():
        cell = cells[component]
        assert cell["value"] is None and cell["status"] == "bounded"
        assert cell["bound_kind"] == "conditional_input_domain_not_CI"
        assert cell["unavailable_reason"] == "censored_point_unreported"
        _contains(cell, low, high)
        assert cell["lower"] == pytest.approx(float(low))
        assert cell["upper"] == pytest.approx(float(high))
    assert cells["omitted_rate"]["value"] is None
    assert cells["omitted_rate"]["lower"] == 0
    assert cells["omitted_rate"]["upper"] == 5
    # Naive division of independent numerator/denominator intervals would give
    # .85..90/95. The true shared-O result is the narrower 85/95...9.
    assert cells["addback_fraction"]["lower"] > .89
    assert cells["addback_fraction"]["upper"] < .901


def test_pdx_crossed_nitrogen_sources_preserve_native_values_without_necessity():
    source = _inputs(774, 284)
    source["arms"]["addback"] = None
    for role, spread in (("reference", 58), ("omitted", 33)):
        arm = source["arms"][role]
        arm["normalization_ref"] = None
        arm["measurement"]["origin"] = "reported"
        arm["measurement"]["spread"] = {"kind": "unspecified", "magnitude": spread}
    source["arms"]["omitted"]["conditions"]["factors"][0]["level"] = "ammonium_sulfate"
    result = populate_partner_components(source)
    assert result["cells"]["reference_rate"]["value"] == 774
    assert result["cells"]["omitted_rate"]["value"] == 284
    check = result["comparison_checks"]["reference_omitted"]
    assert check == {"status": "different", "differing_factors": ["nitrogen_source"],
                     "unavailable_reason": "nonpartner_conditions_differ"}
    assert all(result["cells"][name]["value"] is None for name in COMPONENTS[3:])
    assert result["inputs"] == source


def test_reported_spread_is_not_converted_to_a_sampling_interval():
    source = _inputs()
    for role, kind in zip(source["arms"], ("SD", "SEM", "CI")):
        source["arms"][role]["measurement"]["spread"] = {"kind": kind, "magnitude": 999}
    result = populate_partner_components(source)
    assert result["cells"]["reference_rate"]["lower"] == 100
    assert result["cells"]["reference_rate"]["upper"] == 100
    assert result["cells"]["partner_loss"]["value"] == 80
    assert result["inputs"] == source


def test_missing_addback_preserves_the_two_arm_contrast():
    source = _inputs()
    source["arms"]["addback"] = None
    cells = populate_partner_components(source)["cells"]
    assert cells["partner_loss_fraction"]["value"] == .8
    assert cells["addback_rate"]["unavailable_reason"] == "arm_unreported"
    assert cells["addback_rate"]["origin"] is None
    for name in ("addback_gain", "addback_fraction", "restored_reference_fraction"):
        assert cells[name]["unavailable_reason"] == "arm_unreported"


def test_missing_reference_still_allows_a_distinct_addback_omission_contrast():
    source = _inputs()
    source["arms"]["reference"] = None
    cells = populate_partner_components(source)["cells"]
    assert cells["addback_gain"]["value"] == 70
    assert cells["addback_fraction"]["value"] is None
    assert cells["restored_reference_fraction"]["value"] is None


def test_unknown_reference_measurement_identity_does_not_erase_addback_pair():
    source = _inputs()
    source["arms"]["reference"]["measurement"]["measurement_id"] = None
    cells = populate_partner_components(source)["cells"]
    assert cells["addback_gain"]["value"] == 70
    assert cells["addback_fraction"]["unavailable_reason"] == "measurement_identity_unreported"


def test_baseline_copy_cannot_manufacture_an_addback():
    source = _inputs(a=100)
    source["arms"]["addback"]["measurement"]["measurement_id"] = "physical:W"
    result = populate_partner_components(source)
    assert result["cells"]["partner_loss"]["value"] == 80
    assert result["comparison_checks"]["reference_omitted"]["status"] == "matched"
    for name in ("addback_gain", "addback_fraction", "restored_reference_fraction"):
        assert result["cells"][name]["unavailable_reason"] == "role_measurement_not_distinct"


def test_equal_distinct_measurements_are_valid_but_addback_ratio_denominator_is_zero():
    result = populate_partner_components(_inputs(100, 100, 120))
    cells = result["cells"]
    assert cells["partner_loss"]["value"] == 0
    assert cells["partner_loss_fraction"]["value"] == 0
    assert cells["addback_gain"]["value"] == 20
    assert cells["addback_fraction"]["unavailable_reason"] == "zero_or_straddling_loss_domain"
    assert cells["restored_reference_fraction"]["value"] == .2


@pytest.mark.parametrize("values,expected", [
    ((100, 150, 90), (-50, -.5, -60, 1.2, -.6)),
    ((100, 20, 140), (80, .8, 120, 1.5, 1.2)),
    ((0, 20, 10), (-20, None, -10, .5, None)),
])
def test_negative_changes_and_overshoot_are_not_clipped(values, expected):
    cells = populate_partner_components(_inputs(*values))["cells"]
    for component, value in zip(COMPONENTS[3:], expected):
        if value is None:
            assert cells[component]["unavailable_reason"] == "nonpositive_reference_domain"
        else:
            assert cells[component]["value"] == pytest.approx(value)


@pytest.mark.parametrize("role", ["reference", "omitted", "addback"])
def test_unreported_numeric_measurement_remains_unknown(role):
    source = _inputs()
    source["arms"][role]["measurement"].update(status="unreported", value=None)
    result = populate_partner_components(source)
    name = {"reference": "reference_rate", "omitted": "omitted_rate", "addback": "addback_rate"}[role]
    assert result["cells"][name]["unavailable_reason"] == "measurement_unreported"
    assert result["cells"]["restored_reference_fraction"]["value"] is None


def test_censored_reference_reaching_zero_blocks_fraction_but_not_loss():
    source = _inputs()
    source["arms"]["reference"]["measurement"]["status"] = "upper_bound"
    cells = populate_partner_components(source)["cells"]
    _contains(cells["partner_loss"], Fraction(-20), Fraction(80))
    assert cells["partner_loss_fraction"]["unavailable_reason"] == "nonpositive_reference_domain"
    assert cells["addback_fraction"]["unavailable_reason"] == "zero_or_straddling_loss_domain"


def test_censored_omission_straddling_loss_does_not_erase_other_bounded_components():
    source = _inputs(100, 150, 90)
    source["arms"]["omitted"]["measurement"]["status"] = "upper_bound"
    cells = populate_partner_components(source)["cells"]
    assert cells["addback_fraction"]["unavailable_reason"] == "zero_or_straddling_loss_domain"
    _contains(cells["partner_loss_fraction"], Fraction(-1, 2), Fraction(1))
    _contains(cells["restored_reference_fraction"], Fraction(-3, 5), Fraction(9, 10))


def test_known_condition_difference_survives_partial_metadata():
    source = _inputs()
    source["arms"]["omitted"]["conditions"]["coverage"] = "partial"
    source["arms"]["omitted"]["conditions"]["factors"][2]["level"] = 10
    result = populate_partner_components(source)
    check = result["comparison_checks"]["reference_omitted"]
    assert check["status"] == "different" and check["differing_factors"] == ["subject_amount"]
    assert result["cells"]["partner_loss_fraction"]["value"] is None


def test_condition_factor_order_is_irrelevant_and_input_order_is_preserved():
    source = _inputs()
    source["arms"]["omitted"]["conditions"]["factors"].reverse()
    original = deepcopy(source)
    result = populate_partner_components(source)
    assert result["cells"]["partner_loss"]["value"] == 80
    assert result["inputs"] == source == original


@pytest.mark.parametrize("field,value,reason", [
    ("subject_ref", None, "subject_unreported"),
    ("subject_ref", "another:subject", "subject_mismatch"),
    ("partner_ref", None, "partner_unreported"),
    ("partner_ref", "another:partner", "partner_mismatch"),
    ("endpoint_ref", None, "endpoint_unreported"),
    ("endpoint_ref", "another:endpoint", "endpoint_mismatch"),
    ("normalization_ref", None, "normalization_unreported"),
    ("normalization_ref", "normalization:total_mixture", "normalization_mismatch"),
    ("unit", "per_min", "unit_mismatch"),
    ("partner_state", "present", "partner_presence_not_established"),
    ("partner_state", "unreported", "partner_presence_not_established"),
])
def test_scientific_relationships_qualify_the_numeric_contrast(field, value, reason):
    source = _inputs()
    source["arms"]["omitted"][field] = value
    cells = populate_partner_components(source)["cells"]
    assert cells["omitted_rate"]["value"] == 20
    assert cells["partner_loss"]["unavailable_reason"] == reason


def test_unknown_condition_level_is_unresolved_not_a_known_difference():
    source = _inputs()
    cond = source["arms"]["omitted"]["conditions"]
    cond["coverage"] = "partial"
    cond["factors"][0]["level"] = None
    check = populate_partner_components(source)["comparison_checks"]["reference_omitted"]
    assert check == {"status": "unresolved", "differing_factors": [],
                     "unavailable_reason": "conditions_incomplete"}


def test_known_factor_unit_difference_survives_an_unresolved_factor_scope():
    source = _inputs()
    source["arms"]["omitted"]["conditions"]["factors"][1]["unit"] = "K"
    source["arms"]["omitted"]["conditions"]["factors"].pop(0)
    check = populate_partner_components(source)["comparison_checks"]["reference_omitted"]
    assert check["differing_factors"] == ["temperature"]
    assert check["status"] == "different"


@pytest.mark.parametrize("coverage", ["partial", "complete"])
def test_one_sided_condition_factor_is_missing_information_not_a_difference(coverage):
    source = _inputs()
    cond = source["arms"]["omitted"]["conditions"]
    cond["coverage"] = coverage
    cond["factors"].pop(0)
    result = populate_partner_components(source)
    check = result["comparison_checks"]["reference_omitted"]
    assert check == {"status": "unresolved", "differing_factors": [],
                     "unavailable_reason": "condition_factor_scope_unresolved"}
    assert result["cells"]["partner_loss"]["value"] is None


def test_multiple_censored_arms_share_omission_in_every_derived_component():
    source = _inputs(100, 5, 90)
    for role in ("omitted", "addback"):
        source["arms"][role]["measurement"]["status"] = "upper_bound"
    cells = populate_partner_components(source)["cells"]
    _contains(cells["addback_fraction"], Fraction(-5, 95), Fraction(9, 10))
    _contains(cells["restored_reference_fraction"], Fraction(-1, 20), Fraction(9, 10))
    for omitted in range(6):
        for addback in range(91):
            truth = Fraction(addback - omitted, 100 - omitted)
            assert Fraction(cells["addback_fraction"]["lower"]) <= truth <= Fraction(cells["addback_fraction"]["upper"])


def test_same_physical_measurement_is_not_an_independent_role():
    source = _inputs(100, 100, 90)
    source["arms"]["omitted"]["measurement"]["measurement_id"] = "physical:W"
    cells = populate_partner_components(source)["cells"]
    assert cells["reference_rate"]["value"] == cells["omitted_rate"]["value"] == 100
    assert cells["partner_loss"]["unavailable_reason"] == "role_measurement_not_distinct"


@pytest.mark.parametrize("change", ["value", "status", "unit"])
def test_conflicting_values_status_or_units_under_shared_id_fail(change):
    source = _inputs(100, 100, 90)
    source["arms"]["omitted"]["measurement"]["measurement_id"] = "physical:W"
    if change == "unit":
        source["arms"]["omitted"]["unit"] = "nmol/min/mg"
    elif change == "value":
        source["arms"]["omitted"]["measurement"]["value"] = 99
    else:
        source["arms"]["omitted"]["measurement"]["status"] = "upper_bound"
    with pytest.raises(ExperimentalContractError) as caught:
        populate_partner_components(source)
    assert caught.value.code == "shared_measurement_conflict"


def test_large_cancellation_retains_representable_ratio_when_raw_difference_overflows():
    source = _inputs(1, sys.float_info.max, 0)
    cells = populate_partner_components(source)["cells"]
    assert cells["partner_loss"]["status"] == "populated"
    assert cells["addback_fraction"]["value"] == 1
    assert math.isfinite(cells["restored_reference_fraction"]["value"])
    # A larger integer is a finite source literal. Native preservation and
    # per-cell output conversion are separate from exact-rational arithmetic.
    source = _inputs(10**400, 2 * 10**400, 3 * 10**400)
    cells = populate_partner_components(source)["cells"]
    assert cells["reference_rate"]["value"] == 10**400
    assert cells["partner_loss"]["unavailable_reason"] == "numerical_model_range"
    assert cells["partner_loss_fraction"]["value"] == -1
    assert cells["addback_fraction"]["value"] == -1
    assert cells["restored_reference_fraction"]["value"] == 1


def test_nonzero_underflow_is_unavailable_but_other_components_survive():
    tiny = math.nextafter(0.0, 1.0)
    source = _inputs(sys.float_info.max, 0, tiny)
    cells = populate_partner_components(source)["cells"]
    assert cells["addback_gain"]["value"] == tiny
    assert cells["partner_loss_fraction"]["value"] == 1
    assert cells["restored_reference_fraction"]["unavailable_reason"] == "numerical_model_range"
    assert cells["addback_fraction"]["unavailable_reason"] == "numerical_model_range"


def test_all_absent_arms_return_specific_unknowns():
    source = {"version": "literature_partner_inputs_v1", "arms": dict.fromkeys(("reference", "omitted", "addback"))}
    result = populate_partner_components(source)
    assert all(cell["value"] is None for cell in result["cells"].values())
    assert all(cell["unavailable_reason"] == "arm_unreported" for cell in result["cells"].values())


_BASE = ("arms", "reference")
@pytest.mark.parametrize("path,value,code", [
    (("extra",), 1, "closed_fields_required"),
    (("version",), "bad", "unsupported_input_version"),
    (_BASE + ("unit",), "kg", "unsupported_value"),
    (_BASE + ("subject_ref",), " ", "nonempty_identity_required"),
    (_BASE + ("partner_state",), [], "unsupported_value"),
    (_BASE + ("measurement", "value"), True, "finite_number_required"),
    (_BASE + ("measurement", "value"), math.inf, "finite_number_required"),
    (_BASE + ("measurement", "value"), math.nan, "finite_number_required"),
    (_BASE + ("measurement", "value"), -1, "nonnegative_value_required"),
    (_BASE + ("measurement", "value"), None, "observed_value_required"),
    (_BASE + ("measurement", "status"), "unreported", "unreported_measurement_has_value"),
    (_BASE + ("measurement", "origin"), "invented_probability", "unsupported_value"),
    (_BASE + ("measurement", "spread", "kind"), "SD", "spread_kind_magnitude_mismatch"),
    (_BASE + ("measurement", "spread", "magnitude"), 1, "spread_kind_magnitude_mismatch"),
    (_BASE + ("measurement", "spread", "magnitude"), False, "finite_number_required"),
    (_BASE + ("conditions", "coverage"), "unreported", "unreported_conditions_have_factors"),
    (_BASE + ("conditions", "factors"), [], "complete_conditions_require_known_factors"),
    (_BASE + ("conditions", "factors", 0, "level"), None, "complete_conditions_require_known_factors"),
    (_BASE + ("conditions", "factors", 0, "level"), True, "finite_condition_level_required"),
    (_BASE + ("conditions", "factors", 0, "level"), math.inf, "finite_condition_level_required"),
    (_BASE + ("conditions", "factors", 0, "unit"), "", "nonempty_identity_required"),
    (_BASE + ("conditions", "factors", 1, "factor"), "nitrogen_source", "duplicate_condition_factor"),
])
def test_closed_input_and_cross_field_validation(path, value, code):
    source = _inputs()
    _set(source, path, value)
    with pytest.raises(ExperimentalContractError) as caught:
        populate_partner_components(source)
    assert caught.value.code == code
    assert isinstance(caught.value.field, str) and caught.value.field


def test_unreported_units_are_allowed_only_without_measurements():
    source = _inputs()
    source["arms"]["reference"]["unit"] = "unreported"
    with pytest.raises(ExperimentalContractError) as caught:
        populate_partner_components(source)
    assert caught.value.code == "observed_unit_required"
    source["arms"]["reference"]["measurement"].update(status="unreported", value=None)
    cells = populate_partner_components(source)["cells"]
    assert cells["reference_rate"]["unit"] is None
    assert cells["reference_rate"]["unavailable_reason"] == "measurement_unreported"


@pytest.mark.parametrize("path", [
    ("arms",), _BASE, _BASE + ("conditions",),
    _BASE + ("conditions", "factors", 0),
    _BASE + ("measurement",), _BASE + ("measurement", "spread"),
])
def test_nested_unknown_fields_are_rejected(path):
    source = _inputs()
    target = source
    for key in path:
        target = target[key]
    target["extra"] = 1
    with pytest.raises(ExperimentalContractError) as caught:
        populate_partner_components(source)
    assert caught.value.code == "closed_fields_required"
