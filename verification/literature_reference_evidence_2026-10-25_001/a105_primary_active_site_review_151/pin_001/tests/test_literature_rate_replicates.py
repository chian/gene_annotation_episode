"""Constructed examples, not primary measurements or completed assay graders."""
from copy import deepcopy
import csv
import io
import json
import math

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_replicate_inputs import (
    HEADERS, read_rate_replicate_table, validate_rate_replicate_extraction,
)
from gene_annotation_episode.literature_rate_replicate_calculations import (
    summarize_rate_replicates, populate_rate_replicate_contrast,
)


def table(rows, *, delimiter="\t", newline="\n"):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator=newline)
    writer.writerow(HEADERS)
    for index, changes in enumerate(rows):
        row = dict(zip(HEADERS, ("ConstructX", "assay-1", "reference", "buffer A",
            "oxygen consumption", "preparation", "prep-A", "biological_preparations",
            f"obs-{index}", "10", "nmol/min", "synthetic")))
        row.update(changes)
        writer.writerow([row[name] for name in HEADERS])
    return {"source_ref": "source_fixture", "artifact_ref": "artifact_fixture",
            "representation": "synthetic_fixture", "delimiter": delimiter, "text": stream.getvalue()}


def read(rows, **kwargs):
    return read_rate_replicate_table(table(rows, **kwargs),
        expected_subject="ConstructX", expected_experiment="assay-1")


def unbalanced():
    return read([{"value": "9"}, {"value": "11"},
                 {"sampling_unit": "prep-B", "value": "19"},
                 {"sampling_unit": "prep-B", "value": "20"},
                 {"sampling_unit": "prep-B", "value": "21"}])


def test_unbalanced_technical_repeats_do_not_increase_preparation_weight_or_n():
    extraction = unbalanced()
    before = deepcopy(extraction)
    result = summarize_rate_replicates(extraction, unit_model="iid_units")
    group, = result["groups"]
    assert group["measurement_count"] == 5
    assert group["sampling_unit_count"] == group["complete_unit_count"] == 2
    assert [unit["measurement_count"] for unit in group["units"]] == [2, 3]
    assert [unit["cells"]["mean"]["value"] for unit in group["units"]] == pytest.approx([.01, .02])
    assert group["cells"]["mean"]["value"] == pytest.approx(.015)
    assert group["cells"]["sample_sd"]["value"] == pytest.approx(math.sqrt(.00005))
    assert group["cells"]["mean_se"]["value"] == pytest.approx(.005)
    assert group["cells"]["mean_se"]["conditional_on"] == ["iid_units"]
    assert result["annotation_credit"] is result["assay_error_rate"] is None
    assert len(group["cells"]["mean"]["input_rows"]) == 5
    assert result == json.loads(json.dumps(result, allow_nan=False))
    assert extraction == before


def test_default_model_preserves_descriptive_summaries_without_inventing_se():
    group, = summarize_rate_replicates(unbalanced())["groups"]
    assert group["cells"]["mean"]["value"] == pytest.approx(.015)
    assert group["cells"]["sample_sd"]["value"] is not None
    assert group["cells"]["mean_se"]["value"] is None
    assert group["cells"]["mean_se"]["unavailable_reason"] == "unit_model_unspecified"


@pytest.mark.parametrize("basis", ("technical_measurements", "", "biological_preparations"))
def test_basis_is_retained_and_never_inferred_from_count_or_iid_model(basis):
    data = read([{"value": "1", "sampling_basis": basis},
                 {"value": "3", "sampling_unit": "B", "sampling_basis": basis}])
    result = summarize_rate_replicates(data, unit_model="iid_units")
    group, = result["groups"]
    assert group["sampling_basis"] == (basis or "unspecified")
    assert result["model"]["sampling_basis_inferred"] is False
    assert group["cells"]["mean_se"]["value"] == pytest.approx(.001)


def test_duplicate_representations_are_preserved_but_not_additional_measurements():
    data = read([{"observation_id": "same", "value": "1000"},
                 {"observation_id": "same", "value": "1", "unit": "umol/min"},
                 {"sampling_unit": "B", "observation_id": "other", "value": "3000"}])
    group, = summarize_rate_replicates(data, unit_model="iid_units")["groups"]
    assert group["representation_count"] == 3
    assert group["measurement_count"] == 2
    assert group["cells"]["mean"]["value"] == 2
    assert group["cells"]["mean_se"]["value"] == pytest.approx(1)
    assert group["units"][0]["representation_count"] == 2
    assert len(group["cells"]["mean"]["input_rows"]) == 3


def test_equal_values_with_different_observation_ids_are_not_duplicates():
    data = read([{"value": "10"}, {"value": "10"}, {"sampling_unit": "B", "value": "10"}])
    group, = summarize_rate_replicates(data, unit_model="iid_units")["groups"]
    assert group["measurement_count"] == 3
    assert group["sampling_unit_count"] == 2
    assert group["cells"]["sample_sd"]["value"] == 0
    assert group["cells"]["mean_se"]["value"] == 0


def test_shared_unit_ids_across_arms_preserve_pairing_without_assuming_arm_independence():
    data = read([{"value": "10"}, {"arm": "test", "value": "4"}])
    result = summarize_rate_replicates(data)
    assert len(result["groups"]) == 2
    assert [group["units"][0]["sampling_unit"] for group in result["groups"]] == ["prep-A", "prep-A"]
    assert "dependence" not in result["model"]


def test_conflicting_physical_identity_does_not_erase_other_series():
    data = read([{"observation_id": "same", "value": "10"},
                 {"observation_id": "same", "value": "11"},
                 {"arm": "other", "value": "20"}])
    first, other = summarize_rate_replicates(data)["groups"]
    assert first["cells"]["mean"]["value"] is None
    assert first["units"][0]["limitations"] == ["conflicting_observation_identity"]
    assert other["cells"]["mean"]["value"] == pytest.approx(.02)
    assert len(first["cells"]["mean"]["input_rows"]) == 2


@pytest.mark.parametrize("token,status", (("", "unavailable"), ("ND", "not_detected"),
    ("not detected", "not_detected"), ("<5", "censored"), (">=5", "censored")))
def test_missing_and_limits_are_not_points_or_silent_complete_case_deletions(token, status):
    data = read([{"value": "10"}, {"value": token},
                 {"sampling_unit": "B", "value": "20"}])
    assert data["rows"][1]["status"] == status
    group, = summarize_rate_replicates(data, unit_model="iid_units")["groups"]
    assert group["measurement_count"] == 3 and group["sampling_unit_count"] == 2
    assert group["complete_unit_count"] == 1
    assert all(cell["value"] is None for cell in group["cells"].values())
    first, second = group["units"]
    assert first["cells"]["observed_point_mean"]["value"] == pytest.approx(.01)
    assert first["cells"]["mean"]["value"] is None
    assert second["cells"]["mean"]["value"] == pytest.approx(.02)
    assert first["point_observation_ids"] == ["obs-0"]


@pytest.mark.parametrize("change", ({"endpoint": "product formation"}, {"condition": "buffer B"},
                                   {"normalization": "total protein"}, {"arm": "test"}))
def test_different_experimental_relationships_remain_separate(change):
    result = summarize_rate_replicates(read([{}, change]))
    assert len(result["groups"]) == 2
    assert all(group["sampling_unit_count"] == 1 for group in result["groups"])


def test_mixed_dimensions_preserve_valid_unit_values_without_combining():
    data = read([{"value": "10"}, {"sampling_unit": "B", "value": "2", "unit": "uM/min"}])
    group, = summarize_rate_replicates(data)["groups"]
    assert group["cells"]["mean"]["unavailable_reason"] == "incompatible_rate_dimensions"
    assert [unit["cells"]["mean"]["unit"] for unit in group["units"]] == ["umol/min", "uM/min"]
    assert [unit["cells"]["mean"]["value"] for unit in group["units"]] == pytest.approx([.01, 2])


def test_mixed_dimensions_within_one_unit_do_not_create_a_mean():
    data = read([{"value": "10"}, {"value": "2", "unit": "uM/min"}])
    group, = summarize_rate_replicates(data)["groups"]
    assert group["units"][0]["cells"]["mean"]["value"] is None
    assert group["units"][0]["limitations"][0] == "incompatible_rate_dimensions"


def test_mixed_sampling_bases_are_not_blended_into_one_population_mean():
    group, = summarize_rate_replicates(read([{}, {"sampling_unit": "B",
        "sampling_basis": "technical_measurements"}]), unit_model="iid_units")["groups"]
    assert group["sampling_basis"] is None
    assert group["cells"]["mean"]["unavailable_reason"] == "sampling_basis_mismatch"
    assert all(unit["cells"]["mean"]["value"] is not None for unit in group["units"])


@pytest.mark.parametrize("delimiter", (",", "\t"))
@pytest.mark.parametrize("newline", ("\n", "\r\n", "\r"))
def test_literal_custody_survives_csv_variants_and_detached_json(delimiter, newline):
    data = read([{"condition": 'buffer, "A"'}, {"condition": 'buffer, "A"', "value": "11"}],
                delimiter=delimiter, newline=newline)
    detached = json.loads(json.dumps(data))
    assert validate_rate_replicate_extraction(detached) == data
    assert [row["source"]["row_number"] for row in data["rows"]] == [2, 3]
    assert summarize_rate_replicates(detached) == summarize_rate_replicates(data)


@pytest.mark.parametrize("mutation", ("value", "identity", "origin", "row", "boolean"))
def test_detached_edited_operands_are_rejected_without_reacquisition(mutation):
    data = read([{"value": "1"}])
    row = data["rows"][0]
    if mutation == "value":
        row["value"] = 2
    elif mutation == "identity":
        row["observation_id"] = "edited"
    elif mutation == "origin":
        row["origin"] = "reported"
    elif mutation == "row":
        row["source"]["row_number"] = 3
    else:
        row["value"] = True
    with pytest.raises(ExperimentalContractError, match="detached_source_operand_mismatch"):
        summarize_rate_replicates(data)


@pytest.mark.parametrize("token", ("1e9999", "1e-9999", "NaN", "1 ± .1", "1/2"))
def test_nonfinite_underflow_or_unparsed_numbers_are_not_measurements(token):
    with pytest.raises(ExperimentalContractError):
        read([{"value": token}])


def test_large_finite_means_do_not_overflow_a_naive_sum():
    group, = summarize_rate_replicates(read([{"value": "1e308", "unit": "umol/min"},
        {"value": "1e308", "unit": "umol/min", "sampling_unit": "B"}]))["groups"]
    assert group["cells"]["mean"]["value"] == 1e308


def test_conversion_underflow_is_unavailable_not_zero():
    group, = summarize_rate_replicates(read([{"value": "1e-323"}]))["groups"]
    assert group["cells"]["mean"]["value"] is None
    assert group["cells"]["mean"]["unavailable_reason"] == "numerical_model_range"


def test_approximation_is_preserved_through_summaries():
    group, = summarize_rate_replicates(read([{"value": "~10"}]))["groups"]
    assert group["cells"]["mean"]["value"] == pytest.approx(.01)
    assert group["cells"]["mean"]["approximate"] is True


def test_empty_table_supplies_no_measurements_or_observations():
    assert summarize_rate_replicates(read([]))["groups"] == []


@pytest.mark.parametrize("changes", ({"subject": "other"}, {"experiment": "other"},
    {"observation_id": ""}, {"sampling_unit": ""}, {"sampling_basis": "independent"},
    {"origin": "reported"}, {"unit": "unknown"}, {"condition": "line1\nline2"}))
def test_wrong_subject_or_unusable_mapping_returns_structured_failure(changes):
    with pytest.raises(ExperimentalContractError):
        read([changes])


def contrast(data=None, **overrides):
    selection = {"reference": {"arm": "reference", "condition": "buffer A",
                 "endpoint": "oxygen consumption", "normalization": "preparation"},
                 "test": {"arm": "test", "condition": "buffer A",
                 "endpoint": "oxygen consumption", "normalization": "preparation"},
                 "unit_model": "iid_units", "dependence": "paired_units"}
    selection.update(overrides)
    return populate_rate_replicate_contrast(paired_data() if data is None else data, **selection)


def paired_data(independent=False):
    rows = []
    for i, (a, b) in enumerate(((10, 9), (20, 18), (30, 27))):
        rows.extend(({
            "sampling_unit": f"prep-{i}", "observation_id": f"ref-{i}", "value": str(a)}, {
            "sampling_unit": f"other-{i}" if independent else f"prep-{i}",
            "observation_id": f"test-{i}", "arm": "test", "value": str(b)}))
    return read(rows)


def test_paired_contrast_uses_unit_differences_and_preserves_all_source_operands():
    result = contrast()
    cells = result["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(.02)
    assert cells["test_rate"]["value"] == pytest.approx(.018)
    assert cells["rate_difference"]["value"] == pytest.approx(.002)
    assert cells["retained_fraction"]["value"] == pytest.approx(.9)
    assert cells["fractional_decrease"]["value"] == pytest.approx(.1)
    assert cells["paired_sample_sd"]["value"] == pytest.approx(.001)
    assert cells["difference_se"]["value"] == pytest.approx(.001/math.sqrt(3))
    assert cells["difference_se"]["conditional_on"] == ["iid_unit_pairs"]
    assert len(cells["rate_difference"]["input_rows"]) == 6
    assert result["pairing"] == {"shared_units": ["prep-0", "prep-1", "prep-2"],
                                  "reference_only": [], "test_only": []}
    assert contrast(json.loads(json.dumps(result["summary"]["extraction"]))) == result


def test_independent_contrast_has_different_se_for_distinct_units_with_same_values():
    result = contrast(paired_data(independent=True), dependence="independent")
    assert result["cells"]["rate_difference"]["value"] == pytest.approx(.002)
    assert result["cells"]["difference_se"]["value"] == pytest.approx(math.sqrt((.01**2+.009**2)/3))
    assert result["pairing"]["shared_units"] == []


def test_explicitly_shared_units_cannot_supply_independent_group_se():
    result = contrast(dependence="independent")
    assert result["cells"]["rate_difference"]["value"] == pytest.approx(.002)
    assert result["cells"]["difference_se"]["value"] is None
    assert result["cells"]["difference_se"]["unavailable_reason"] == "shared_sampling_units"


@pytest.mark.parametrize("overrides,reason", (({"unit_model": "none"}, "unit_model_unspecified"),
    ({"dependence": "unknown"}, "dependence_unknown")))
def test_unspecified_models_preserve_effect_but_do_not_manufacture_se(overrides, reason):
    cells = contrast(**overrides)["cells"]
    assert cells["rate_difference"]["value"] == pytest.approx(.002)
    assert cells["difference_se"]["value"] is None
    assert cells["difference_se"]["unavailable_reason"] == reason


def test_incomplete_pairing_is_visible_and_does_not_delete_group_measurements():
    data = paired_data()
    lines = data["table"]["text"].splitlines()
    source = deepcopy(data["table"])
    source["text"] = "\n".join(lines[:-1]) + "\n"
    result = contrast(read_rate_replicate_table(source, expected_subject="ConstructX", expected_experiment="assay-1"))
    assert result["cells"]["rate_difference"]["value"] == pytest.approx(.0065)
    assert result["cells"]["difference_se"]["unavailable_reason"] == "pairing_incomplete"
    assert result["pairing"]["reference_only"] == ["prep-2"]
    assert len(result["summary"]["extraction"]["rows"]) == 5


def test_different_endpoint_does_not_silently_become_a_functional_contrast():
    data = read([{}, {"arm": "test", "endpoint": "product formation", "value": "2"}])
    result = contrast(data, test={"arm": "test", "condition": "buffer A",
        "endpoint": "product formation", "normalization": "preparation"})
    assert result["cells"]["reference_rate"]["value"] == pytest.approx(.01)
    assert result["cells"]["test_rate"]["value"] == pytest.approx(.002)
    assert result["cells"]["rate_difference"]["value"] is None
    assert result["cells"]["rate_difference"]["unavailable_reason"] == "endpoint_mismatch"


def test_missing_selected_group_is_explicit_and_preserves_existing_group():
    cells = contrast(read([{}]))["cells"]
    assert cells["reference_rate"]["value"] == pytest.approx(.01)
    assert cells["test_rate"]["value"] is None
    assert cells["retained_fraction"]["unavailable_reason"] == "missing_test_group"


def test_zero_reference_is_a_valid_measurement_but_cannot_normalize_a_ratio():
    data = read([{"value": "0"}, {"arm": "test", "value": "1"}])
    cells = contrast(data)["cells"]
    assert cells["rate_difference"]["value"] == pytest.approx(-.001)
    assert cells["retained_fraction"]["value"] is None
    assert cells["retained_fraction"]["unavailable_reason"] == "zero_reference_rate"


def test_paired_difference_uses_exact_source_decimals_before_float_projection():
    data = read([{"value": "10000000000000001", "unit": "umol/min"},
                 {"arm": "test", "value": "10000000000000000", "unit": "umol/min"}])
    cells = contrast(data)["cells"]
    assert cells["rate_difference"]["value"] == 1
    assert cells["rate_difference"]["source_exact_value"] == {"numerator": "1", "denominator": "1"}
    assert cells["fractional_decrease"]["value"] == pytest.approx(1/10000000000000001)
    assert cells["difference_se"]["value"] is None
    assert cells["difference_se"]["unavailable_reason"] == "insufficient_measurement_count"
