"""Synthetic logical/domain/design fixtures, never habitat or assay measurements."""
from copy import deepcopy
from fractions import Fraction
import json
import math

import pytest

from gene_annotation_episode.literature_context_calculations import (
    COMPONENTS, FORMULAS, REASONS, CONDITIONAL_CODES,
    empty_context_inputs, populate_context_compatibility,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def interval(low, high=None, lc=True, uc=True):
    if high is None and low is not None:
        high = low
    return dict(lower=low, upper=high, lower_closed=lc, upper_closed=uc)


def observation(key, value=1, *, measurement=None, unit="state", relation="supported"):
    return dict(requirement_key=key, measurement_key=measurement or key, unit=unit,
        interval=None if unit == "state" else interval(value), relation=relation if unit == "state" else "numeric",
        reported_sd=None, reported_sem=None, reported_plusminus=None, reported_count=None,
        count_relation="unknown", replicate_kind="unknown")


def fixture(values=(True,), *, remainder=False):
    result = empty_context_inputs()
    result.update(question_kind="sample_context_coverage", origin="synthetic", scope_status="defined",
        frame_status="defined", pairing="paired", sampling_design="census", permitted_remainder=remainder,
        requirements=[dict(key="r", unit="state", supported=[], incompatible=[])],
        routes=[dict(key="route", requirements=["r"], requirements_complete=True, joint_support="established")])
    result["contexts"] = [dict(key=f"c{i}", weight=1, cluster_key=f"cluster{i}", scope_match="matched",
        observations=[observation("r", measurement=f"m{i}", relation="supported" if value is True else "incompatible" if value is False else "unresolved")])
        for i, value in enumerate(values)]
    return result


def calc(value):
    return populate_context_compatibility(value)


def cell(result, key):
    return result["cells"][key]["value"]


def bounds(result, prefix):
    return cell(result, prefix + "_lower"), cell(result, prefix + "_upper")


def numeric_fixture(value, supported, incompatible=(), *, unit="mM"):
    inputs = fixture()
    inputs["requirements"][0].update(unit=unit, supported=supported, incompatible=list(incompatible))
    inputs["contexts"][0]["observations"] = [observation("r", unit=unit, value=1)]
    inputs["contexts"][0]["observations"][0]["interval"] = value
    return inputs


def test_output_closed_cells_constants_and_deepcopy():
    inputs = fixture((True, False, None))
    result = calc(inputs)
    assert set(result) == {"version", "inputs", "cells", "memberships", "routes_by_context", "contexts", "counts", "qualifications"}
    assert tuple(result["cells"]) == COMPONENTS
    assert result["inputs"] == inputs
    result["inputs"]["contexts"][0]["weight"] = 10
    assert inputs["contexts"][0]["weight"] == 1
    for key, value in result["cells"].items():
        assert set(value) == {"value", "unit", "status", "formula", "origin", "unavailable_reason", "conditional_on"}
        assert value["formula"] == FORMULAS[key]
        assert value["unavailable_reason"] is None or value["unavailable_reason"] in REASONS
        assert set(value["conditional_on"]) <= set(CONDITIONAL_CODES)
    assert set(result["qualifications"]) <= set(REASONS)
    json.dumps(result, allow_nan=False)


def test_missing_question_does_not_default_to_capability_or_empty_conjunction():
    missing = empty_context_inputs()
    result = calc(missing)
    for prefix in ("coverage", "capability", "selected"):
        assert bounds(result, prefix) == (0, 1)
        assert cell(result, prefix + "_point") is None
    assert result["counts"]["context_units"] == 0
    inputs = fixture()
    inputs.update(question_kind="unreported", routes=[dict(key="r", requirements=[], requirements_complete=True, joint_support="established")])
    assert bounds(calc(inputs), "selected") == (0, 1)


def test_original_ten_unit_paired_five_joint_and_uncertain_variants():
    inputs = fixture([True] * 10)
    inputs["requirements"] = [dict(key=key, unit="state", supported=[], incompatible=[]) for key in ("access", "exposure", "oxygen")]
    inputs["routes"][0]["requirements"] = [r["key"] for r in inputs["requirements"]]
    for i, context in enumerate(inputs["contexts"]):
        context["observations"] = [observation(key, measurement=f"{key}{i}", relation="supported" if i < cutoff else "incompatible")
            for key, cutoff in (("access", 8), ("exposure", 6), ("oxygen", 5))]
    result = calc(inputs)
    assert bounds(result, "coverage") == (.5, .5)
    assert cell(result, "coverage_point") == .5
    assert cell(result, "capability_point") == 1
    assert [cell(result, key) for key in COMPONENTS[:4]] == [10, 5, 0, 5]
    inputs["contexts"][0]["observations"][2]["relation"] = "unresolved"
    assert bounds(calc(inputs), "coverage") == (math.nextafter(.4, -math.inf), .5)
    inputs["contexts"][0]["observations"][2]["relation"] = "supported"
    inputs["contexts"][5]["observations"][2]["relation"] = "unresolved"
    result = calc(inputs)
    assert bounds(result, "coverage") == (.5, math.nextafter(.6, math.inf))
    assert cell(result, "coverage_point") is None


def test_rare_witness_capability_is_not_sample_coverage_and_remainder_unknown():
    inputs = fixture([True] + [False] * 11, remainder=True)
    result = calc(inputs)
    assert cell(result, "coverage_point") == pytest.approx(1 / 12)
    assert cell(result, "capability_point") == 1
    assert cell(result, "selected_point") == cell(result, "coverage_point")
    inputs["question_kind"] = "organism_capability"
    assert cell(calc(inputs), "selected_point") == 1
    inputs = fixture([False] * 12, remainder=True)
    assert bounds(calc(inputs), "capability") == (0, 1)
    inputs["permitted_remainder"] = False
    assert bounds(calc(inputs), "capability") == (0, 0)
    inputs["contexts"] = []
    inputs["permitted_remainder"] = None
    assert bounds(calc(inputs), "capability") == (0, 1)


@pytest.mark.parametrize("value,regions,expected", [
    (interval(1, 3), [interval(0, 2), interval(2, 4, False, True)], (1, 1)),
    (interval(1, 3), [interval(0, 2, True, False), interval(2, 4, False, True)], (0, 1)),
    (interval(2), [interval(0, 2, True, False)], (0, 1)),
    (interval(0, 2, False, False), [interval(0, 2, False, False)], (1, 1)),
    (dict(lower=None, upper=0, lower_closed=False, upper_closed=False),
        [dict(lower=None, upper=0, lower_closed=False, upper_closed=True)], (1, 1)),
    (dict(lower=3, upper=None, lower_closed=False, upper_closed=False),
        [dict(lower=2, upper=None, lower_closed=True, upper_closed=False)], (1, 1)),
])
def test_union_containment_gaps_open_and_unbounded_endpoints(value, regions, expected):
    result = calc(numeric_fixture(value, regions))
    member = result["memberships"][0]
    assert (member["ell"], member["u"]) == expected
    assert bounds(result, "coverage") == expected


def test_incompatible_requires_full_union_containment_and_conflicting_domains_unknown():
    result = calc(numeric_fixture(interval(7, 8), [interval(0, 2)], [interval(6, 9)]))
    assert bounds(result, "coverage") == (0, 0)
    result = calc(numeric_fixture(interval(3), [interval(0, 2)]))
    assert bounds(result, "coverage") == (0, 1)  # outside D+ is not failure
    result = calc(numeric_fixture(interval(1), [interval(0, 4)], [interval(3, 5)]))
    assert bounds(result, "coverage") == (0, 1)
    assert "domain_conflict" in result["memberships"][0]["reasons"]
    # A shared excluded endpoint is no overlap.
    result = calc(numeric_fixture(interval(1), [interval(0, 2)], [interval(2, 5, False, True)]))
    assert bounds(result, "coverage") == (1, 1)


def test_wrong_unit_bases_and_sd_do_not_create_conversion_or_admissible_interval():
    inputs = numeric_fixture(interval(1), [interval(0, 2)], unit="ppmv_H2_gas")
    obs = inputs["contexts"][0]["observations"][0]
    obs["unit"] = "ppbv_H2_gas"
    result = calc(inputs)
    assert bounds(result, "coverage") == (0, 1)
    assert "unit_basis_mismatch" in result["qualifications"]
    obs["unit"] = "ppmv_H2_gas"
    obs.update(interval=None, reported_sd=.1, reported_sem=.03, reported_plusminus=.2,
        reported_count=3, count_relation="at_least", replicate_kind="technical")
    result = calc(inputs)
    assert bounds(result, "coverage") == (0, 1)
    assert "value_unreported" in result["qualifications"]
    assert result["counts"]["context_units"] == 1


def test_missing_predicate_incomplete_route_and_unknown_alternative():
    inputs = fixture()
    inputs["contexts"][0]["observations"] = []
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs = fixture()
    inputs["routes"][0]["requirements_complete"] = False
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs = fixture((False,))
    inputs["routes"].append(dict(key="unknown_alternative", requirements=[], requirements_complete=False, joint_support="unresolved"))
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs["routes"][1]["requirements_complete"] = True
    assert bounds(calc(inputs), "coverage") == (1, 1)
    inputs["routes"] = None
    assert bounds(calc(inputs), "coverage") == (0, 1)


def test_multivariate_joint_support_suppresses_positive_but_retains_necessary_failure():
    inputs = fixture()
    inputs["requirements"].append(dict(key="other", unit="state", supported=[], incompatible=[]))
    inputs["routes"][0].update(requirements=["r", "other"], joint_support="unresolved")
    inputs["contexts"][0]["observations"].append(observation("other", measurement="other"))
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs["contexts"][0]["observations"][0]["relation"] = "incompatible"
    assert bounds(calc(inputs), "coverage") == (0, 0)
    inputs["routes"][0]["joint_support"] = "conflicting"
    assert bounds(calc(inputs), "coverage") == (0, 0)


@pytest.mark.parametrize("scope", ["unresolved", "conflicting"])
def test_unmatched_scope_prevents_supported_and_incompatible_claims(scope):
    inputs = fixture((True, False))
    for context in inputs["contexts"]:
        context["scope_match"] = scope
    assert bounds(calc(inputs), "coverage") == (0, 1)
    assert bounds(calc(inputs), "capability") == (0, 1)
    inputs["scope_status"] = "unreported"
    assert bounds(calc(inputs), "coverage") == (0, 1)


def test_unknown_frame_or_weight_preserves_capability_without_fabricated_denominator():
    inputs = fixture((True, False))
    inputs["contexts"][0]["weight"] = None
    result = calc(inputs)
    assert bounds(result, "coverage") == (0, 1)
    assert all(cell(result, key) is None for key in COMPONENTS[:4])
    assert result["cells"]["sample_weight"]["unavailable_reason"] == "weight_unreported"
    assert result["contexts"][1]["weight"] == 1
    assert result["contexts"][1]["U"] == 0
    assert cell(result, "capability_point") == 1
    inputs["contexts"][0]["weight"] = 1
    inputs["frame_status"] = "unreported"
    result = calc(inputs)
    assert bounds(result, "coverage") == (0, 1)
    assert cell(result, "capability_point") == 1
    assert all(cell(result, key) is None for key in COMPONENTS[:4])
    assert result["cells"]["sample_weight"]["unavailable_reason"] == "frame_unreported"


def test_exact_duplicate_original_unit_coalesces_not_equal_values_different_ids():
    inputs = fixture((True, False))
    inputs["contexts"].append(deepcopy(inputs["contexts"][0]))
    result = calc(inputs)
    assert result["counts"]["context_units"] == 2
    assert cell(result, "coverage_point") == .5
    assert "duplicate_context_coalesced" in result["qualifications"]
    inputs["contexts"][-1]["key"] = "new-original-context"
    result = calc(inputs)
    assert result["counts"]["context_units"] == 3
    assert cell(result, "coverage_point") == pytest.approx(2 / 3)
    assert "shared_measurement_dependency" in result["qualifications"]


def test_duplicate_context_conflict_and_inconsistent_alias_fail_specifically():
    inputs = fixture()
    inputs["contexts"].append(deepcopy(inputs["contexts"][0]))
    inputs["contexts"][-1]["observations"][0]["relation"] = "incompatible"
    with pytest.raises(ExperimentalContractError) as err:
        calc(inputs)
    assert err.value.code == "duplicate_context_conflict"
    inputs["contexts"][-1]["key"] = "other"
    with pytest.raises(ExperimentalContractError) as err:
        calc(inputs)
    assert err.value.code == "duplicate_measurement_conflict"


def test_measured_weights_exact_normalization_and_per_cell_overflow():
    inputs = fixture((True, False))
    inputs["weight_basis"] = "measured_duration"
    inputs["contexts"][0]["weight"] = 1e308
    inputs["contexts"][1]["weight"] = 1e308
    result = calc(inputs)
    assert cell(result, "sample_weight") is None
    assert result["cells"]["sample_weight"]["unavailable_reason"] == "numerical_model_range"
    assert cell(result, "supported_weight") == 1e308
    assert cell(result, "incompatible_weight") == 1e308
    assert cell(result, "coverage_point") == .5
    inputs["contexts"][0]["weight"] = math.ulp(0.0)
    result = calc(inputs)
    assert cell(result, "coverage_lower") == 0
    assert cell(result, "coverage_upper") == math.ulp(0.0)
    assert cell(result, "coverage_point") is None
    assert result["cells"]["coverage_point"]["unavailable_reason"] == "numerical_model_range"


def unpaired(values=(.8, .8, .9)):
    inputs = fixture(())
    inputs["pairing"] = "unpaired_marginals"
    inputs["requirements"] = [dict(key=f"r{i}", unit="state", supported=[], incompatible=[]) for i in range(len(values))]
    inputs["routes"][0]["requirements"] = [r["key"] for r in inputs["requirements"]]
    inputs["marginals"] = [dict(requirement_key=f"r{i}", lower=v, upper=v) for i, v in enumerate(values)]
    return inputs


def test_unpaired_frechet_not_product_and_never_organism_witness():
    result = calc(unpaired())
    assert bounds(result, "coverage") == pytest.approx((.5, .8))
    assert cell(result, "coverage_point") is None
    assert bounds(result, "capability") == (0, 1)
    assert "unpaired_capability_unavailable" in result["qualifications"]
    assert cell(result, "coverage_lower") != pytest.approx(.576)
    exact = sum((Fraction(v) for v in (.8, .8, .9)), Fraction(0)) - 2
    assert Fraction(cell(result, "coverage_lower")) <= exact
    inputs = unpaired()
    inputs["marginals"].pop()
    assert bounds(calc(inputs), "coverage") == (0, .8)
    assert "marginal_unreported" in calc(inputs)["qualifications"]


def test_unpaired_other_route_design_or_frame_remains_unknown():
    inputs = unpaired()
    inputs["routes"][0]["requirements_complete"] = False
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs = unpaired()
    inputs["routes"].append(dict(key="alternate", requirements=[], requirements_complete=True, joint_support="established"))
    assert bounds(calc(inputs), "coverage") == (0, 1)
    inputs = unpaired()
    inputs["frame_status"] = "unreported"
    assert bounds(calc(inputs), "coverage") == (0, 1)


def test_independent_equal_weight_hoeffding_actual_n_and_analytical_separation():
    inputs = fixture([True] * 5 + [False] * 5)
    inputs.update(sampling_design="independent_equal_weight", alpha=.05)
    for context in inputs["contexts"]:
        context["observations"][0].update(reported_count=300, count_relation="at_least", replicate_kind="technical")
    result = calc(inputs)
    assert result["counts"]["actual_sampling_n"] == 10
    assert bounds(result, "coverage") == (.5, .5)
    assert bounds(result, "sampling") == pytest.approx((.07053059165, .92946940835))
    inputs["contexts"][0]["observations"][0]["relation"] = "unresolved"
    result = calc(inputs)
    assert bounds(result, "sampling")[0] < .071
    assert bounds(result, "sampling")[1] == pytest.approx(.92946940835)
    inputs["alpha"] = math.ulp(0.0)
    assert bounds(calc(inputs), "sampling") == (0, 1)


@pytest.mark.parametrize("change,reason", [
    ({"question_kind": "organism_capability"}, "sampling_question_not_coverage"),
    ({"pairing": "unknown"}, "sampling_requires_paired_contexts"),
    ({"scope_status": "unreported"}, "sampling_requires_defined_scope"),
    ({"frame_status": "unreported"}, "sampling_requires_defined_frame"),
    ({"weight_basis": "measured_volume"}, "sampling_requires_equal_weights"),
    ({"sampling_design": "census"}, "sampling_census"),
    ({"sampling_design": "unknown"}, "sampling_design_unknown"),
    ({"alpha": None}, "sampling_alpha_unreported"),
])
def test_sampling_limited_to_declared_valid_design(change, reason):
    inputs = fixture((True, False))
    inputs.update(sampling_design="independent_equal_weight", alpha=.05)
    inputs.update(change)
    result = calc(inputs)
    assert bounds(result, "sampling") == (None, None)
    assert result["cells"]["sampling_lower"]["unavailable_reason"] == reason
    assert result["counts"]["actual_sampling_n"] is None


def test_sampling_missing_clusters_or_shared_clusters_do_not_invent_independent_n():
    inputs = fixture((True, False))
    inputs.update(sampling_design="independent_equal_weight", alpha=.05)
    inputs["contexts"][0]["cluster_key"] = None
    assert calc(inputs)["cells"]["sampling_lower"]["unavailable_reason"] == "sampling_cluster_unreported"
    inputs["contexts"][0]["cluster_key"] = inputs["contexts"][1]["cluster_key"]
    result = calc(inputs)
    assert result["cells"]["sampling_lower"]["unavailable_reason"] == "sampling_clusters_not_unique"
    assert result["counts"]["distinct_known_clusters"] == 1


@pytest.mark.parametrize("mutate,code", [
    (lambda x: x.update(extra=1), "closed_fields_required"),
    (lambda x: x.update(alpha=True), "finite_number_required"),
    (lambda x: x.update(alpha=0), "alpha_between_zero_and_one_required"),
    (lambda x: x.update(alpha=float("nan")), "finite_number_required"),
    (lambda x: x["contexts"][0].update(weight=0), "positive_value_required"),
    (lambda x: x["contexts"][0].update(weight=2), "equal_unit_weight_must_be_one"),
    (lambda x: x["contexts"][0]["observations"][0].update(reported_count=True), "nonnegative_integer_required"),
    (lambda x: x["contexts"][0]["observations"][0].update(count_relation="exact"), "missing_count_relation_must_be_unknown"),
    (lambda x: x["contexts"][0]["observations"][0].update(reported_sd=-1), "nonnegative_value_required"),
    (lambda x: x["routes"][0].update(requirements=["missing"]), "unknown_requirement_key"),
    (lambda x: x["routes"][0].update(requirements=["r", "r"]), "duplicate_route_requirement"),
    (lambda x: x["contexts"][0]["observations"][0].update(interval=interval(1)), "state_relation_required"),
    (lambda x: x["requirements"][0].update(supported=[interval(1)]), "state_domains_must_be_empty"),
])
def test_calculator_validates_closed_inputs_without_reader(mutate, code):
    inputs = fixture()
    mutate(inputs)
    with pytest.raises(ExperimentalContractError) as err:
        calc(inputs)
    assert err.value.code == code


@pytest.mark.parametrize("bad", [
    dict(lower=None, upper=1, lower_closed=True, upper_closed=True),
    dict(lower=1, upper=1, lower_closed=False, upper_closed=True),
    dict(lower=2, upper=1, lower_closed=True, upper_closed=True),
])
def test_invalid_or_empty_intervals_rejected(bad):
    with pytest.raises(ExperimentalContractError):
        calc(numeric_fixture(bad, [interval(0, 3)]))


def test_absent_or_unpaired_inputs_have_no_sample_mass_zero_substitution():
    for inputs, reason in ((empty_context_inputs(), "frame_unreported"),
            (unpaired(), "sample_denominator_requires_paired_contexts"),
            (fixture(()), "no_context_units")):
        result = calc(inputs)
        for key in COMPONENTS[:4]:
            assert cell(result, key) is None
            assert result["cells"][key]["unavailable_reason"] == reason


@pytest.mark.parametrize("magnitude", ["reported_sd", "reported_sem", "reported_plusminus"])
def test_state_relations_cannot_have_numeric_uncertainty_magnitudes(magnitude):
    inputs = fixture()
    inputs["contexts"][0]["observations"][0][magnitude] = .1
    with pytest.raises(ExperimentalContractError) as err:
        calc(inputs)
    assert err.value.code == "state_uncertainty_requires_numeric_unit"


@pytest.mark.parametrize("joint", ["unresolved", "conflicting"])
def test_unpaired_marginals_do_not_establish_unsupported_joint_operating_domain(joint):
    inputs = unpaired()
    inputs["routes"][0]["joint_support"] = joint
    result = calc(inputs)
    assert bounds(result, "coverage") == (0, .8)
    assert "joint_support_" + joint in result["qualifications"]
    inputs["marginals"][0].update(lower=0, upper=0)
    assert bounds(calc(inputs), "coverage") == (0, 0)
