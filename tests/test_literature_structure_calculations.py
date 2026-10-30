"""Synthetic geometry/RSCC fixtures only; no source paper or deposit is read."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
import math

import pytest

from gene_annotation_episode.literature_structure_calculations import (
    COMPONENTS, CONDITIONAL_CODES, REASONS, VERSION,
    ExperimentalContractError, StructureCalculationError, populate_source_geometry,
)


def geometry(distance=2, **changes):
    result = {"endpoint_a": [[0, 0, 0]], "endpoint_b": [[distance, 0, 0]],
              "positive_max_A": 3, "incompatible_min_A": 5,
              "unavailable_reason": None}
    result.update(changes)
    return result


def local(rscc=.8, reason=None):
    return {"rscc": rscc, "unavailable_reason": reason}


def inputs(*, geometries=None, locals=None, **changes):
    result = {"geometry_members": [geometry()] if geometries is None else geometries,
              "local_members": [local()] if locals is None else locals,
              "validation_binding": "matching_entry_revision", "origin": "synthetic",
              "evaluation_scope": "conditional_deposited_model_geometry"}
    result.update(changes)
    return result


def missing_geometry(reason="endpoint_unmodeled"):
    return geometry(endpoint_b=None, unavailable_reason=reason)


def assert_cell(cell, value, low, high, reason=None):
    assert cell["value"] == pytest.approx(value) if value is not None else cell["value"] is None
    assert cell["lower"] == pytest.approx(low)
    assert cell["upper"] == pytest.approx(high)
    assert cell["unavailable_reason"] == reason
    assert cell["status"] == ("unavailable" if value is None else "populated")


def test_complete_fixed_panels_populate_six_separate_components():
    result = populate_source_geometry(inputs(
        geometries=[geometry(2), geometry(3), geometry(4), geometry(5)],
        locals=[local(.9), local(.8)]))
    assert result["version"] == VERSION
    assert set(result) == {"version", "inputs", "native_geometry", "cells"}
    assert tuple(result["cells"]) == COMPONENTS
    expected = [.64, .5, .25, .32, .16, .16]
    for name, value in zip(COMPONENTS, expected):
        assert_cell(result["cells"][name], value, value, value)
    assert [row["distance_A"] for row in result["native_geometry"]] == [2, 3, 4, 5]


def test_thresholds_are_inclusive_with_a_disjoint_unscored_gap():
    for distance, plus, minus in [(0, 1, 0), (3, 1, 0), (4, 0, 0), (5, 0, 1)]:
        cells = populate_source_geometry(inputs(geometries=[geometry(distance)]))["cells"]
        assert cells["geometry_support_fraction"]["value"] == plus
        assert cells["geometry_opposition_fraction"]["value"] == minus
    zero_cutoff = geometry(0, positive_max_A=0, incompatible_min_A=1)
    assert populate_source_geometry(inputs(geometries=[zero_cutoff]))["cells"]["geometry_support_fraction"]["value"] == 1


def test_group_minimum_preserves_every_requested_pair_in_flat_order():
    row = geometry(endpoint_a=[[0, 0, 0], [0, 3, 0]],
                   endpoint_b=[[4, 0, 0], [0, 0, 0]])
    native = populate_source_geometry(inputs(geometries=[row]))["native_geometry"][0]
    assert native == {"member_index": 0, "distance_A": 0,
                      "all_pair_distances_A": [4, 0, 5, 3], "unavailable_reason": None}


def test_partial_geometry_retains_denominator_and_paired_direction_bounds():
    cells = populate_source_geometry(inputs(
        geometries=[geometry(2), geometry(5), missing_geometry()], locals=[local(1)]))["cells"]
    for name in COMPONENTS[1:3]:
        assert_cell(cells[name], None, 1/3, 2/3, "geometry_inputs_unreported")
    assert_cell(cells["source_geometry_signed"], None, -1/3, 1/3, "geometry_inputs_unreported")
    for name in COMPONENTS[1:3]:
        assert Fraction(cells[name]["lower"]) <= Fraction(1, 3)
        assert Fraction(cells[name]["upper"]) >= Fraction(2, 3)


def test_missing_local_member_bounds_minimum_without_fabricating_a_point():
    cells = populate_source_geometry(inputs(locals=[local(.5), local(None, "local_rscc_unreported")]))["cells"]
    assert_cell(cells["local_fit_index"], None, 0, .25, "local_rscc_unreported")
    assert_cell(cells["source_geometry_positive"], None, 0, .25, "local_rscc_unreported")
    assert_cell(cells["source_geometry_opposing"], 0, 0, 0)


@pytest.mark.parametrize("rscc", [-1, -.2, 0])
def test_known_zero_local_transform_identifies_minimum_despite_missing_member(rscc):
    cells = populate_source_geometry(inputs(locals=[local(rscc), local(None, "local_endpoint_unmodeled")],
                                           geometries=[missing_geometry()]))["cells"]
    assert_cell(cells["local_fit_index"], 0, 0, 0)
    for name in COMPONENTS[3:]:
        assert_cell(cells[name], 0, 0, 0)
    assert cells["geometry_support_fraction"]["value"] is None


@pytest.mark.parametrize("binding", ["entry_mismatch", "revision_mismatch", "binding_unreported", "not_supplied"])
def test_invalid_validation_join_prevents_even_a_reported_zero_from_becoming_D(binding):
    result = populate_source_geometry(inputs(locals=[local(0)], validation_binding=binding))
    assert_cell(result["cells"]["local_fit_index"], None, 0, 1, "validation_not_joined")
    assert result["native_geometry"][0]["distance_A"] == 2
    assert result["inputs"]["local_members"][0]["rscc"] == 0


def test_shared_D_cancels_equal_known_support_and_opposition_with_unknown_D():
    cells = populate_source_geometry(inputs(geometries=[geometry(2), geometry(5)],
        locals=[local(None, "local_rscc_unreported")]))["cells"]
    assert_cell(cells["source_geometry_positive"], None, 0, .5, "local_rscc_unreported")
    assert_cell(cells["source_geometry_opposing"], None, 0, .5, "local_rscc_unreported")
    assert_cell(cells["source_geometry_signed"], 0, 0, 0)


def test_signed_interval_retains_shared_D_for_known_negative_direction():
    cells = populate_source_geometry(inputs(geometries=[geometry(5), geometry(5), geometry(2)],
        locals=[local(.5), local(None, "local_rscc_unreported")]))["cells"]
    assert_cell(cells["source_geometry_signed"], None, -1/12, 0, "local_rscc_unreported")


def test_all_missing_local_and_geometry_do_not_create_perfect_fits():
    cells = populate_source_geometry(inputs(geometries=[missing_geometry()],
        locals=[local(None, "local_rscc_unreported")]))["cells"]
    for name in COMPONENTS[:-1]:
        assert cells[name]["value"] is None
        assert (cells[name]["lower"], cells[name]["upper"]) == (0, 1)
    assert (cells[COMPONENTS[-1]]["lower"], cells[COMPONENTS[-1]]["upper"]) == (-1, 1)


def test_empty_panels_are_unknown_with_explicit_reasons():
    cells = populate_source_geometry(inputs(geometries=[], locals=[]))["cells"]
    assert_cell(cells["local_fit_index"], None, 0, 1, "local_panel_empty")
    assert_cell(cells["geometry_support_fraction"], None, 0, 1, "geometry_panel_empty")
    assert_cell(cells["geometry_opposition_fraction"], None, 0, 1, "geometry_panel_empty")
    assert_cell(cells["source_geometry_signed"], None, -1, 1, "local_panel_empty")


def test_exact_zero_product_can_be_known_while_its_other_factor_is_empty():
    cells = populate_source_geometry(inputs(geometries=[], locals=[local(0)]))["cells"]
    for name in COMPONENTS[3:]:
        assert_cell(cells[name], 0, 0, 0)


def test_known_gap_geometry_has_zero_products_despite_unknown_validation():
    cells = populate_source_geometry(inputs(geometries=[geometry(4)],
        validation_binding="not_supplied", locals=[local(None, "local_rscc_unreported")]))["cells"]
    for name in COMPONENTS[3:]:
        assert_cell(cells[name], 0, 0, 0)


def test_distance_overflow_retains_other_pairs_and_fixed_panel_count():
    row = geometry(endpoint_a=[[1e308, 0, 0], [0, 0, 0]],
                   endpoint_b=[[-1e308, 0, 0], [0, 0, 0]])
    result = populate_source_geometry(inputs(geometries=[row, geometry(2)]))
    native = result["native_geometry"][0]
    assert native["distance_A"] is None
    assert native["all_pair_distances_A"] == [None, 1e308, 1e308, 0]
    assert native["unavailable_reason"] == "numerical_model_range"
    assert_cell(result["cells"]["geometry_support_fraction"], None, .5, 1, "numerical_model_range")
    json.dumps(result, allow_nan=False)


def test_stable_norm_avoids_overflow_from_squaring_large_coordinates():
    result = populate_source_geometry(inputs(geometries=[geometry(endpoint_b=[[1e200, 1e200, 0]])]))
    assert result["native_geometry"][0]["distance_A"] == math.hypot(1e200, 1e200)


def test_unrepresentable_norm_is_a_missing_distance_even_with_finite_components():
    row = geometry(endpoint_b=[[1.7e308, 1.7e308, 0]])
    native = populate_source_geometry(inputs(geometries=[row]))["native_geometry"][0]
    assert native["distance_A"] is None
    assert native["all_pair_distances_A"] == [None]
    assert native["unavailable_reason"] == "numerical_model_range"


def test_large_integer_coordinates_do_not_erase_a_representable_small_distance():
    row = geometry(endpoint_a=[[10**20, 0, 0]], endpoint_b=[[10**20 + 1, 0, 0]])
    assert populate_source_geometry(inputs(geometries=[row]))["native_geometry"][0]["distance_A"] == 1


def test_subnormal_coordinate_distance_is_not_silently_zero():
    tiny = math.nextafter(0, 1)
    result = populate_source_geometry(inputs(geometries=[geometry(tiny)]))
    assert result["native_geometry"][0]["distance_A"] == tiny


def test_exact_nonzero_RSCC_square_underflow_is_unavailable_with_outward_bounds():
    cells = populate_source_geometry(inputs(locals=[local(1e-200)]))["cells"]
    for name in ("local_fit_index", "source_geometry_positive", "source_geometry_signed"):
        assert_cell(cells[name], None, 0, math.nextafter(0, 1), "numerical_model_range")
        assert cells[name]["upper"] > 0
    assert_cell(cells["source_geometry_opposing"], 0, 0, 0)


def test_exact_underflow_does_not_erase_shared_factor_cancellation():
    cells = populate_source_geometry(inputs(locals=[local(1e-200)],
        geometries=[geometry(2), geometry(5)]))["cells"]
    assert cells["local_fit_index"]["unavailable_reason"] == "numerical_model_range"
    assert_cell(cells["source_geometry_signed"], 0, 0, 0)


def test_all_cells_have_closed_meanings_and_proposed_origins_with_detached_inputs():
    original = inputs()
    before = deepcopy(original)
    result = populate_source_geometry(original)
    for name, cell in result["cells"].items():
        assert set(cell) == {"value", "lower", "upper", "unit", "status", "origin",
                             "unavailable_reason", "conditional_on", "formula_code"}
        assert cell["origin"] == "proposed"
        assert cell["unit"] == "dimensionless"
        assert cell["formula_code"] == f"structure_{name}_v1"
        assert set(cell["conditional_on"]) <= set(CONDITIONAL_CODES)
        assert cell["unavailable_reason"] is None or cell["unavailable_reason"] in REASONS
        assert "selected_model_assignment" in cell["conditional_on"]
    result["inputs"]["geometry_members"][0]["endpoint_a"][0][0] = 9
    assert original == before
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("path,value", [
    (("origin",), "derived"), (("evaluation_scope",), "physical_population"),
    (("validation_binding",), []), (("geometry_members",), {}),
    (("local_members",), ()), (("extra",), None),
    (("geometry_members", 0, "extra"), 1),
    (("local_members", 0, "extra"), 1),
    (("geometry_members", 0, "positive_max_A"), -1),
    (("geometry_members", 0, "incompatible_min_A"), 3),
    (("geometry_members", 0, "incompatible_min_A"), 2),
    (("geometry_members", 0, "positive_max_A"), True),
    (("geometry_members", 0, "incompatible_min_A"), float("inf")),
    (("geometry_members", 0, "endpoint_a"), []),
    (("geometry_members", 0, "endpoint_a"), [[1, 2]]),
    (("geometry_members", 0, "endpoint_a"), [[1, 2, False]]),
    (("geometry_members", 0, "endpoint_a"), [[1, 2, "3"]]),
    (("geometry_members", 0, "endpoint_a"), [[1, 2, float("nan")]]),
    (("geometry_members", 0, "endpoint_a"), [[1, 2, 10**1000]]),
    (("geometry_members", 0, "endpoint_a"), None),
    (("geometry_members", 0, "unavailable_reason"), "endpoint_unmodeled"),
    (("local_members", 0, "rscc"), True),
    (("local_members", 0, "rscc"), -1.01),
    (("local_members", 0, "rscc"), 1.01),
    (("local_members", 0, "rscc"), float("nan")),
    (("local_members", 0, "rscc"), None),
    (("local_members", 0, "unavailable_reason"), "local_rscc_unreported"),
])
def test_malformed_fields_and_relationships_raise_exported_repairable_error(path, value):
    fixture = inputs()
    target = fixture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(StructureCalculationError) as caught:
        populate_source_geometry(fixture)
    assert isinstance(caught.value, ExperimentalContractError)
    assert caught.value.code and caught.value.field


@pytest.mark.parametrize("reason", ["endpoint_unmodeled", "ambiguous_atom_selection",
                                   "endpoint_identity_mismatch", "coordinate_unreported"])
def test_declared_missing_endpoint_reasons_survive_in_native_rows(reason):
    result = populate_source_geometry(inputs(geometries=[missing_geometry(reason)]))
    assert result["native_geometry"][0] == {"member_index": 0, "distance_A": None,
        "all_pair_distances_A": [], "unavailable_reason": reason}


@pytest.mark.parametrize("reason", ["local_rscc_unreported", "local_endpoint_unmodeled",
                                   "ambiguous_local_selection", "local_identity_mismatch"])
def test_declared_missing_local_reasons_remain_specific(reason):
    cells = populate_source_geometry(inputs(locals=[local(None, reason)]))["cells"]
    assert_cell(cells["local_fit_index"], None, 0, 1, reason)


def test_joint_bounds_enclose_synthetic_completions_without_independent_subtraction():
    # Exhaust all three predicate outcomes for two missing members, and sample
    # the full local-fit domain's endpoints plus an interior transformed value.
    for fixed_distance in (2, 4, 6):
        incomplete = inputs(geometries=[geometry(fixed_distance), missing_geometry(), missing_geometry()],
                            locals=[local(.8), local(None, "local_rscc_unreported")])
        enclosing = populate_source_geometry(incomplete)["cells"]
        for distance_a, distance_b, rscc in product((2, 4, 6), (2, 4, 6), (0, .4, 1)):
            complete = inputs(geometries=[geometry(fixed_distance), geometry(distance_a), geometry(distance_b)],
                              locals=[local(.8), local(rscc)])
            populated = populate_source_geometry(complete)["cells"]
            for name in COMPONENTS:
                # Compare the exact represented operands, rather than testing
                # round-to-nearest points against enclosing float endpoints.
                d = min(Fraction(.8)**2, Fraction(rscc)**2)
                plus = Fraction(sum(distance <= 3 for distance in (fixed_distance, distance_a, distance_b)), 3)
                minus = Fraction(sum(distance >= 5 for distance in (fixed_distance, distance_a, distance_b)), 3)
                exact = dict(zip(COMPONENTS, (d, plus, minus, d*plus, d*minus, d*(plus-minus))))[name]
                assert Fraction(enclosing[name]["lower"]) <= exact <= Fraction(enclosing[name]["upper"])
                assert populated[name]["value"] is not None
