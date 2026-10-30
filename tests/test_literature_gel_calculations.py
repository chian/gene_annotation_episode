from copy import deepcopy
from fractions import Fraction
from io import BytesIO
import json
import hashlib

from PIL import Image
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import literature_gel_inputs as inputs
from gene_annotation_episode import literature_gel_calculations as calc
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from test_literature_gel_inputs import make_case, select_v2


def populated(mutator=None):
    selected, read, sources, _, comparison = make_case()
    if mutator:
        mutator(selected, sources, comparison)
    extraction = inputs.read_gel_inputs(selected, read_source=read)
    return selected, extraction, comparison, calc.populate_gel_components(extraction, comparison)


def exact(cell):
    return None if cell["exact"] is None else Fraction(int(cell["exact"]["numerator"]), int(cell["exact"]["denominator"]))


def pixels_mutation(sources, selected, coordinates):
    record = sources[("source_image", "original")]
    with Image.open(BytesIO(record["content"])) as image:
        image.load()
        for coordinate, value in coordinates.items():
            image.putpixel(coordinate, value)
        output = BytesIO()
        image.save(output, format="PNG")
    record["content"] = output.getvalue()
    selected["image"]["byte_sha256"] = hashlib.sha256(record["content"]).hexdigest()


def test_analytical_band_sums_fractions_and_shared_control_factorization():
    _, extraction, comparison, sheet = populated()
    Draft202012Validator.check_schema(calc.gel_comparison_schema())
    Draft202012Validator(calc.gel_comparison_schema()).validate(comparison)
    result = sheet["assignments"][0]
    assert [exact(row["cells"]["shifted_display_fraction"]) for row in result["lanes"]] == [0, Fraction(4, 5), Fraction(1, 5)]
    cells = result["cells"]
    assert exact(cells["protein_associated_display_shift"]) == Fraction(4, 5)
    assert exact(cells["competitor_residual_display_fraction"]) == Fraction(1, 4)
    assert exact(cells["displaced_display_fraction"]) == Fraction(3, 4)
    assert exact(cells["factorized_competitor_sensitive_shift"]) == exact(cells["direct_competitor_sensitive_shift"]) == Fraction(3, 5)
    assert result["dependence"]["factorization_equal_to_direct"] is True
    assert result["dependence"]["independence_established"] is False
    assert {d["lane_id"] for d in cells["direct_competitor_sensitive_shift"]["dependencies"]} == {"protein", "competitor"}
    assert sheet["sampling_uncertainty"] == {"status": "not_supplied", "value": None}
    assert sheet["independent_preparation_count"] is None
    assert sheet["annotation_credit"] is None
    assert calc.validate_gel_sheet(extraction, comparison, sheet) == sheet


def test_off_band_and_total_signal_ratios_are_display_diagnostics():
    *_, sheet = populated()
    for row in sheet["assignments"][0]["lanes"]:
        assert exact(row["cells"]["off_band_display_fraction"]) == Fraction(1, 11)
        assert exact(row["cells"]["display_total_ratio_to_protein_lane"]) == 1
        assert "not_calibration_recovery" in row["cells"]["display_total_ratio_to_protein_lane"]["qualifications"][0]


@pytest.mark.parametrize("missing", ["not_selected", "invalid_baseline", "zero_delta"])
def test_direct_competitor_contrast_survives_unavailable_factorization(missing):
    def mutate(selected, sources, comparison):
        if missing == "not_selected":
            comparison["baseline_lane_id"] = None
        elif missing == "invalid_baseline":
            selected["roi_assignments"][0]["lanes"][0]["background"] = [0, 0, 1, 99]
        else:
            pixels_mutation(sources, selected, {(0, 1): 175, (0, 3): 235})
    *_, sheet = populated(mutate)
    cells = sheet["assignments"][0]["cells"]
    assert exact(cells["direct_competitor_sensitive_shift"]) == Fraction(3, 5)
    assert cells["factorized_competitor_sensitive_shift"]["exact"] is None
    assert cells["displaced_display_fraction"]["exact"] is None


def test_background_failure_does_not_erase_raw_black_pixel_diagnostic():
    def mutate(selected, sources, _comparison):
        pixels_mutation(sources, selected, {(1, 1): 0})
        selected["roi_assignments"][0]["lanes"][1]["background"] = None
    *_, sheet = populated(mutate)
    row = sheet["assignments"][0]["lanes"][1]["cells"]
    assert row["shifted_display_fraction"]["exact"] is None
    black = row["display_black_pixel_fraction"]
    assert exact(black) == Fraction(1, 2)
    assert all(d["background_region"] is None for d in black["dependencies"])
    assert black["sampling_standard_uncertainty"] is None


def test_negative_corrected_bands_and_outside_range_fractions_are_not_clipped():
    def mutate(selected, sources, _comparison):
        # BackgroundD30, shiftedD10, freeD100 -> correctedB=-20,F=70,T=50,f=-.4.
        pixels_mutation(sources, selected, {(1, 0): 225, (1, 1): 245, (1, 3): 155})
    *_, sheet = populated(mutate)
    row = sheet["assignments"][0]["lanes"][1]["cells"]
    assert exact(row["shifted_display_darkness"]) == -20
    assert exact(row["shifted_display_fraction"]) == Fraction(-2, 5)
    assert "display_fraction_outside_unit_interval_retained" in row["shifted_display_fraction"]["qualifications"]
    cells = sheet["assignments"][0]["cells"]
    assert exact(cells["displaced_display_fraction"]) == Fraction(3, 2)
    assert exact(cells["direct_competitor_sensitive_shift"]) == Fraction(-3, 5)


def test_nonpositive_total_has_no_fraction_but_keeps_negative_band_values():
    def mutate(selected, sources, _comparison):
        pixels_mutation(sources, selected, {(1, 0): 155})
    *_, sheet = populated(mutate)
    row = sheet["assignments"][0]["lanes"][1]["cells"]
    assert exact(row["selected_total_display_darkness"]) == -100
    assert row["shifted_display_fraction"]["unavailable_reason"] == "nonpositive_total_display_darkness"
    assert row["display_black_pixel_fraction"]["exact"] is not None


def test_overlapping_bands_never_count_as_two_independent_signal_regions():
    def mutate(selected, _sources, _comparison):
        selected["roi_assignments"][0]["lanes"][1]["bands"][1]["region"] = [1, 1, 2, 2]
    *_, sheet = populated(mutate)
    row = sheet["assignments"][0]["lanes"][1]["cells"]
    assert exact(row["shifted_display_darkness"]) == 80
    assert exact(row["free_display_darkness"]) == 80
    assert row["selected_total_display_darkness"]["unavailable_reason"] == "overlapping_band_regions"
    assert row["display_black_pixel_fraction"]["exact"] is None


def test_coherent_alternatives_and_partial_available_range_do_not_infer_missing_choice():
    def mutate(selected, _sources, _comparison):
        second = deepcopy(selected["roi_assignments"][0])
        second["assignment_id"] = "explicit_second"
        third = deepcopy(second)
        third["assignment_id"] = "explicit_unavailable"
        third["lanes"][1]["bands"][0]["region"] = [1, 1, 2, 50]
        selected["roi_assignments"].extend([second, third])
    *_, sheet = populated(mutate)
    assert [a["assignment_id"] for a in sheet["assignments"]] == ["declared", "explicit_second", "explicit_unavailable"]
    interval = sheet["roi_sensitivity"]["direct_competitor_sensitive_shift"]
    assert interval["status"] == "partial"
    assert interval["included_assignment_ids"] == ["declared", "explicit_second"]
    assert interval["unavailable_assignment_ids"] == ["explicit_unavailable"]
    assert interval["bounds_unavailable_assignments"] is False
    assert interval["sampling_confidence_level"] is None


def test_same_physical_lane_reused_returns_descriptive_zero_not_replication():
    def mutate(_selected, _sources, comparison):
        comparison["competitor_lane_id"] = "protein"
    *_, sheet = populated(mutate)
    result = sheet["assignments"][0]
    direct = result["cells"]["direct_competitor_sensitive_shift"]
    assert exact(direct) == 0
    assert "same_physical_display_measurement_reused_nondiscriminating" in direct["qualifications"]
    assert "competitor_role_does_not_establish_requested_experimental_meaning" in result["scientific_interpretation"]["reasons"]


@pytest.mark.parametrize("field,state", [("subject", "conflicting"), ("endpoint", "known"), ("condition", "unknown")])
def test_scientific_unknown_conflict_or_mismatch_qualifies_without_erasing_display_values(field, state):
    def mutate(selected, _sources, _comparison):
        meaning = selected["lanes"][2][field]
        meaning.update(state=state, value="different endpoint" if state == "known" else None)
    *_, sheet = populated(mutate)
    result = sheet["assignments"][0]
    assert exact(result["cells"]["direct_competitor_sensitive_shift"]) == Fraction(3, 5)
    expected = "unknown" if state == "unknown" else "conflicting"
    assert result["scientific_interpretation"]["status"] == expected


def test_saved_sheet_reconstruction_forbids_public_acquisition_decoding_and_populators(monkeypatch):
    _, extraction, comparison, sheet = populated()
    extraction, sheet = json.loads(json.dumps(extraction)), json.loads(json.dumps(sheet))
    def forbidden(*_args, **_kwargs):
        pytest.fail("public reader/decoder/calculator called during saved check")
    monkeypatch.setattr(inputs, "read_gel_inputs", forbidden)
    monkeypatch.setattr(inputs, "_decode", forbidden)
    monkeypatch.setattr(calc, "populate_gel_components", forbidden)
    monkeypatch.setattr(Image, "open", forbidden)
    assert calc.validate_gel_sheet(extraction, comparison, sheet,
        expected_extraction_digest=extraction["extraction_digest"]) == sheet
    changed = deepcopy(sheet)
    changed["assignments"][0]["cells"]["direct_competitor_sensitive_shift"]["value"] = True
    with pytest.raises(ExperimentalContractError, match="saved_gel_sheet_mismatch"):
        calc.validate_gel_sheet(extraction, comparison, changed)


def test_absent_comparison_role_is_not_selected_by_best_number():
    selected, extraction, comparison, _sheet = populated()
    comparison["competitor_lane_id"] = "undeclared"
    with pytest.raises(ExperimentalContractError, match="selected_gel_lane_required"):
        calc.populate_gel_components(extraction, comparison)


def test_v2_mean_median_explicit_alternatives_keep_method_dependencies_and_partial_raws():
    def mutate(selected, sources, _comparison):
        select_v2(selected, "mean")
        # Original mean10 versus median0 fromD[0,0,30]; same actual image,
        # three declared coherent whole-assignment alternatives, not replicates.
        pixels_mutation(sources, selected, {(0, 4): 255, (1, 4): 255, (2, 4): 225})
        selected["roi_assignments"][0]["lanes"][1]["background"] = [0, 4, 3, 5]
        median = deepcopy(selected["roi_assignments"][0])
        median["assignment_id"] = "declared_median"
        for lane in median["lanes"]:
            lane["background_method"] = "median"
        partial = deepcopy(median)
        partial["assignment_id"] = "declared_missing_background"
        partial["lanes"][1]["background"] = None
        selected["roi_assignments"].extend([median, partial])
    _selected, extraction, comparison, sheet = populated(mutate)
    assert sheet["version"] == calc.VERSION_V2
    mean, median, partial = sheet["assignments"]
    assert exact(mean["lanes"][1]["cells"]["shifted_display_darkness"]) == 70
    assert exact(median["lanes"][1]["cells"]["shifted_display_darkness"]) == 80
    assert {d["background_method"] for d in median["cells"]["direct_competitor_sensitive_shift"]["dependencies"]} == {"median"}
    assert partial["lanes"][1]["cells"]["shifted_display_fraction"]["exact"] is None
    assert partial["lanes"][1]["cells"]["display_black_pixel_fraction"]["exact"] is not None
    assert "background_method" not in partial["lanes"][1]["cells"]["display_black_pixel_fraction"]["dependencies"][0]
    assert sheet["roi_sensitivity"]["direct_competitor_sensitive_shift"]["status"] == "partial"
    assert sheet["independent_preparation_count"] is None
    assert calc.validate_gel_sheet(extraction, comparison, sheet) == sheet
