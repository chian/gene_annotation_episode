"""Synthetic source summaries test arithmetic/meaning, not biological evidence."""
from copy import deepcopy
import json
import math

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast


def extraction(a=3.0, b=1.0, *, sd=2.0, count=5):
    rows = []
    for index, (arm, condition, value) in enumerate((
            ("reference", "without_inhibitor", a), ("test", "with_inhibitor", b)), 2):
        rows.append({"arm": arm, "condition": condition, "endpoint": "oxygen_consumption",
            "normalization": "per_preparation", "value": value, "unit": "umol/min",
            "status": "observed", "bound": "none", "approximate": False,
            "uncertainty": {"kind": "sd", "magnitude": sd, "count": count,
                            "sampling_basis": "unspecified"},
            "origin": "synthetic", "source": {
                "source_ref": "source_synthetic", "artifact_ref": "artifact_synthetic",
                "representation": "synthetic_fixture", "row_number": index,
                "header": "synthetic summary header", "raw_row": "synthetic summary row"}})
    return {"version": "a105_rate_extraction_v1", "subject": "SyntheticConstruct",
            "experiment": "synthetic_rate_comparison", "rows": rows}


def populate(data=None, **kwargs):
    selection = {"reference_arm": "reference", "test_arm": "test",
                 "reference_condition": "without_inhibitor", "test_condition": "with_inhibitor"}
    selection.update(kwargs)
    return populate_rate_contrast(extraction() if data is None else data, **selection)


def modeled(data=None, **kwargs):
    return populate(data, dependence="independent", observation_model="independent_normal_groups", **kwargs)


def value(result, cell):
    return result["cells"][cell]["value"]


def reason(result, cell):
    return result["cells"][cell]["unavailable_reason"]


def test_measured_summaries_survive_without_a_statistical_model():
    data = extraction()
    before = deepcopy(data)
    result = populate(data)
    assert value(result, "reference_rate") == 3
    assert value(result, "test_rate") == 1
    assert value(result, "rate_difference") == 2
    assert value(result, "retained_fraction") == pytest.approx(1/3)
    assert value(result, "fractional_decrease") == pytest.approx(2/3)
    assert reason(result, "reference_mean_se") == "observation_model_unspecified"
    assert reason(result, "signed_profile_log_ratio") == "observation_model_unspecified"
    assert data == before
    assert result["extraction"] == before
    result["extraction"]["rows"][0]["value"] = 100
    assert data == before
    assert result["scope"] == "source_preparation_endpoint"
    assert result["annotation_credit"] is None
    assert result["molecule_specific_product_rate"] is None
    assert result["model"]["sampling_basis_inferred"] is False


def test_explicit_model_calculates_source_uncertainty_and_profile():
    result = modeled()
    assert value(result, "reference_mean_se") == pytest.approx(2/math.sqrt(5))
    assert value(result, "difference_se") == pytest.approx(math.sqrt(8/5))
    # Here the global boundary maximum is the midpoint. Each group's MLE
    # variance is 16/5 and the loss is 5 log(1+1/(16/5)).
    expected_s = 5*math.log1p(5/16)
    assert value(result, "signed_profile_log_ratio") == pytest.approx(expected_s)
    assert value(result, "source_signed_index") == pytest.approx(math.tanh(expected_s/2))
    assert result["cells"]["source_signed_index"]["origin"] == "proposed"
    assert result["cells"]["source_signed_index"]["conditional_on"] == [
        "independent_normal_groups", "independent_groups"]
    assert result["source_uncertainty"]["reference"]["sampling_basis"] == "unspecified"
    assert result["profile_diagnostics"]["boundary_mean"] == pytest.approx(2)


def test_all_three_stationary_roots_are_evaluated_instead_of_assuming_midpoint():
    result = modeled(extraction(a=2, b=0, sd=1, count=3))
    profile = result["profile_diagnostics"]
    assert len(profile["stationary_boundary_means"]) == 3
    assert sorted(profile["stationary_boundary_means"]) == pytest.approx([
        1-math.sqrt(1/3), 1, 1+math.sqrt(1/3)])
    expected_s = 1.5*math.log(6)
    midpoint_s = 3*math.log(2.5)
    assert value(result, "signed_profile_log_ratio") == pytest.approx(expected_s)
    assert value(result, "signed_profile_log_ratio") < midpoint_s
    assert profile["boundary_mean"] != pytest.approx(1)


def test_unequal_sample_sizes_and_variances_against_independent_scalar_optimization():
    from scipy.optimize import minimize_scalar
    data = extraction(a=10, b=0, sd=.1, count=3)
    data["rows"][1]["uncertainty"].update(magnitude=.15, count=7)
    result = modeled(data)
    na, nb = 3, 7
    va, vb = (na-1)*.1**2/na, (nb-1)*.15**2/nb
    def loss(mu):
        return .5*(na*math.log1p((10-mu)**2/va)+nb*math.log1p(mu**2/vb))
    independent = min(
        minimize_scalar(loss, bounds=(0, 1), method="bounded").fun,
        minimize_scalar(loss, bounds=(9, 10), method="bounded").fun,
        loss(0), loss(10))
    assert value(result, "signed_profile_log_ratio") == pytest.approx(independent, rel=1e-9)
    assert len(result["profile_diagnostics"]["stationary_boundary_means"]) == 3


def test_reversing_the_order_reverses_profile_not_its_strength():
    forward = modeled()
    reverse = modeled(reference_arm="test", test_arm="reference",
                      reference_condition="with_inhibitor", test_condition="without_inhibitor")
    for name in ("rate_difference", "signed_profile_log_ratio", "source_signed_index"):
        assert value(reverse, name) == pytest.approx(-value(forward, name))


def test_unit_conversion_scales_rates_and_errors_but_not_profile():
    original = modeled()
    data = extraction()
    for row in data["rows"]:
        row["value"] *= 1000
        row["uncertainty"]["magnitude"] *= 1000
        row["unit"] = "nmol/min"
    converted = modeled(data)
    for name in original["cells"]:
        assert value(converted, name) == pytest.approx(value(original, name))
    assert converted["cells"]["reference_rate"]["unit"] == "umol/min"
    assert converted["extraction"]["rows"][0]["unit"] == "nmol/min"


def test_different_but_compatible_units_are_converted_before_comparison():
    data = extraction()
    data["rows"][1]["unit"] = "nmol/min"
    data["rows"][1]["value"] = 1000
    data["rows"][1]["uncertainty"]["magnitude"] = 2000
    assert value(modeled(data), "rate_difference") == 2


def test_reported_sem_is_preserved_without_reverse_inventing_sd_or_n():
    data = extraction()
    for row in data["rows"]:
        row["uncertainty"].update(kind="sem", magnitude=.4, count=None)
    result = populate(data, dependence="independent")
    assert value(result, "reference_mean_se") == .4
    assert value(result, "difference_se") == pytest.approx(math.hypot(.4, .4))
    assert reason(modeled(data), "signed_profile_log_ratio") == "profile_requires_sample_sd"
    assert result["source_uncertainty"]["reference"]["count"] is None


def test_unknown_between_arm_dependence_prevents_difference_error_and_profile():
    result = populate(observation_model="independent_normal_groups")
    assert value(result, "reference_mean_se") is not None
    assert value(result, "rate_difference") == 2
    assert reason(result, "difference_se") == "dependence_unknown"
    assert reason(result, "signed_profile_log_ratio") == "dependence_unknown"


@pytest.mark.parametrize("mutation,expected", [
    ({"count": None}, "measurement_count_unreported"),
    ({"count": 1}, "insufficient_measurement_count"),
    ({"magnitude": 0}, "positive_sd_required"),
    ({"kind": "unspecified"}, "profile_requires_sample_sd"),
    ({"kind": "unreported", "magnitude": None}, "profile_requires_sample_sd"),
])
def test_unsupported_statistical_inputs_remain_missing(mutation, expected):
    data = extraction()
    data["rows"][0]["uncertainty"].update(mutation)
    result = modeled(data)
    assert reason(result, "signed_profile_log_ratio") == expected
    assert value(result, "rate_difference") == 2


@pytest.mark.parametrize("state,bound,point,expected", [
    ("unavailable", "none", None, "source_measurement_unavailable"),
    ("censored", "lt", .1, "censored_measurement"),
    ("censored", "ge", .1, "censored_measurement"),
    ("conflicting", "none", None, "conflicting_measurement"),
])
def test_partial_results_preserve_valid_arm_without_using_limit_as_point(state, bound, point, expected):
    data = extraction()
    data["rows"][1].update(status=state, bound=bound, value=point)
    result = modeled(data)
    assert value(result, "reference_rate") == 3
    for name in ("test_rate", "rate_difference", "retained_fraction", "source_signed_index"):
        assert value(result, name) is None
        assert reason(result, name) == expected
    assert result["extraction"]["rows"][1]["bound"] == bound
    assert result["extraction"]["rows"][1]["value"] == point


def test_duplicate_representation_leaves_all_numerical_cells_unchanged():
    data = extraction()
    original = modeled(data)
    data["rows"].append(deepcopy(data["rows"][0]))
    duplicated = modeled(data)
    assert duplicated["cells"] == original["cells"]
    assert len(duplicated["extraction"]["rows"]) == 3


def test_same_source_identity_cannot_have_two_values():
    data = extraction()
    duplicate = deepcopy(data["rows"][0])
    duplicate["value"] = 9
    data["rows"].append(duplicate)
    result = modeled(data)
    assert reason(result, "reference_rate") == "conflicting_source_identity"
    assert value(result, "test_rate") == 1
    assert value(result, "source_signed_index") is None


def test_relabelling_one_source_row_as_two_arms_does_not_create_a_comparison():
    data = extraction()
    data["rows"][1]["source"] = deepcopy(data["rows"][0]["source"])
    result = modeled(data)
    assert reason(result, "reference_rate") == "conflicting_source_identity"
    assert reason(result, "test_rate") == "conflicting_source_identity"


def test_equal_numbers_from_distinct_source_rows_are_not_collapsed():
    data = extraction()
    repeated = deepcopy(data["rows"][0])
    repeated["source"]["row_number"] = 4
    data["rows"].append(repeated)
    result = modeled(data)
    assert reason(result, "reference_rate") == "ambiguous_reference_arm"
    assert value(result, "test_rate") == 1


def test_missing_arm_is_not_a_zero_measurement():
    data = extraction()
    data["rows"] = data["rows"][:1]
    result = modeled(data)
    assert value(result, "reference_rate") == 3
    assert reason(result, "test_rate") == "missing_test_arm"
    assert value(result, "rate_difference") is None
    assert value(result, "source_signed_index") is None


@pytest.mark.parametrize("field,replacement,code", [
    ("condition", "wrong_condition", "condition_mismatch"),
    ("endpoint", "product_formation", "endpoint_mismatch"),
    ("normalization", "per_mg", "normalization_mismatch"),
    ("unit", "uM/min", "incompatible_rate_dimensions"),
])
def test_comparison_meanings_are_validated(field, replacement, code):
    data = extraction()
    data["rows"][1][field] = replacement
    with pytest.raises(ExperimentalContractError) as error:
        modeled(data)
    assert error.value.code == code


def test_zero_reference_rate_preserves_difference_but_not_ratio():
    result = modeled(extraction(a=0, b=1))
    assert value(result, "rate_difference") == -1
    assert reason(result, "retained_fraction") == "zero_reference_rate"
    assert reason(result, "fractional_decrease") == "zero_reference_rate"
    assert value(result, "source_signed_index") < 0


def test_equal_zero_means_do_not_make_a_ratio_or_infinite_evidence():
    result = modeled(extraction(a=0, b=0))
    assert value(result, "rate_difference") == 0
    assert value(result, "signed_profile_log_ratio") == 0
    assert value(result, "source_signed_index") == 0
    assert reason(result, "retained_fraction") == "zero_reference_rate"


def test_finite_extreme_inputs_cannot_create_nonfinite_sheet_cells():
    result = modeled(extraction(a=1e308, b=-1e308, sd=1e308))
    assert reason(result, "rate_difference") == "nonfinite_calculation"
    assert reason(result, "signed_profile_log_ratio") == "numerical_model_range"
    json.dumps(result, allow_nan=False)


def test_unit_conversion_underflow_is_not_a_measured_zero():
    data = extraction(a=5e-324)
    data["rows"][0]["unit"] = "nmol/min"
    result = populate(data)
    assert reason(result, "reference_rate") == "numerical_model_range"
    assert value(result, "test_rate") == 1
    assert result["extraction"]["rows"][0]["value"] == 5e-324


def test_ratio_underflow_does_not_silently_assert_complete_inhibition():
    result = populate(extraction(a=1e308, b=1e-308))
    assert reason(result, "retained_fraction") == "numerical_model_range"
    assert value(result, "fractional_decrease") is None


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf")])
def test_invalid_native_numbers_do_not_reach_arithmetic(bad):
    data = extraction()
    data["rows"][0]["value"] = bad
    with pytest.raises(ExperimentalContractError):
        modeled(data)


def test_serialization_preserves_values_assumptions_and_source_provenance():
    result = modeled()
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["cells"]["rate_difference"]["input_rows"] == [
        {"source_ref": "source_synthetic", "artifact_ref": "artifact_synthetic", "row_number": 2},
        {"source_ref": "source_synthetic", "artifact_ref": "artifact_synthetic", "row_number": 3}]
