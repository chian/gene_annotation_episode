from copy import deepcopy
import hashlib
from io import BytesIO
import json

from PIL import Image
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import literature_gel_inputs as gel
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def make_case(*, mode="L"):
    # Analytically specified display darkness: B/F are0/100,80/20,20/80.
    image = Image.new("L", (3, 5), 255)
    for x, (shifted, free) in enumerate(((0, 100), (80, 20), (20, 80))):
        image.putpixel((x, 1), 255 - shifted)
        image.putpixel((x, 2), 245)  # Off-band display darkness10.
        image.putpixel((x, 3), 255 - free)
    if mode != "L":
        converted = image.convert(mode)
        image.close()
        image = converted
    output = BytesIO()
    image.save(output, format="PNG")
    image.close()
    image_bytes = output.getvalue()
    caption = b"Synthetic protein P construct C, DNA shift; lanes baseline, protein, competitor."
    witness = {"source_ref": "source_caption", "representation": "text", "start": 0,
               "end": len(caption), "quote": caption.decode()}
    def meaning(value):
        return {"state": "known", "value": value, "witnesses": [deepcopy(witness)]}
    context = {name: meaning("synthetic " + name) for name in gel.CONTEXT_FIELDS}
    lanes, rois = [], []
    for x, (name, role) in enumerate((("baseline", "protein_free"), ("protein", "protein_present"), ("competitor", "competitor"))):
        lanes.append({"lane_id": name, "observation_id": "observation_" + name,
            "subject": meaning("P"), "construct": meaning("C"), "endpoint": meaning("DNA shift"),
            "condition": meaning(name), "control_role": meaning(role)})
        rois.append({"lane_id": name, "background": [x, 0, x + 1, 1],
            "whole_lane": [x, 1, x + 1, 4], "bands": [
                {"band_id": "shifted", "role": "shifted", "region": [x, 1, x + 1, 2]},
                {"band_id": "free", "role": "free", "region": [x, 3, x + 1, 4]}]})
    selected = {"version": gel.VERSION, "image": {"source_ref": "source_image",
        "artifact_ref": "artifact_image", "byte_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "width": 3, "height": 5, "source_kind": "synthetic_fixture"}, "context": context,
        "lanes": lanes, "roi_assignments": [{"assignment_id": "declared", "lanes": rois}]}
    sources = {("source_image", "original"): {"artifact_ref": "artifact_image", "content": image_bytes},
               ("source_caption", "text"): {"artifact_ref": "artifact_caption", "content": caption}}
    calls = []
    def read(ref, representation):
        calls.append((ref, representation))
        return sources[(ref, representation)]
    comparison = {"version": "gel_competition_comparison_v1", "baseline_lane_id": "baseline",
                  "protein_lane_id": "protein", "competitor_lane_id": "competitor"}
    return selected, read, sources, calls, comparison


def resign(extraction):
    extraction["extraction_digest"] = gel._hash(gel._canonical(
        {key: value for key, value in extraction.items() if key != "extraction_digest"}))


def select_v2(selected, method="mean"):
    selected["version"] = gel.VERSION_V2
    for assignment in selected["roi_assignments"]:
        for lane in assignment["lanes"]:
            lane["background_method"] = method
    return selected


def test_closed_selection_schema_and_complete_source_closure_before_decode(monkeypatch):
    selected, read, _, calls, _ = make_case()
    schema = gel.gel_arguments_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(selected)
    original = gel._decode
    def decode(content):
        assert calls == [("source_image", "original"), ("source_caption", "text")]
        return original(content)
    monkeypatch.setattr(gel, "_decode", decode)
    result = gel.read_gel_inputs(selected, read_source=read)
    assert result["image"]["mode"] == "L"
    assert result["origin"] == "synthetic"
    assert result["sampling_uncertainty"] is None
    assert result["assignments"][0]["lanes"][1]["bands"][0]["corrected_signal"]["exact"] == {"numerator": "80", "denominator": "1"}
    assert len(calls) == 2


@pytest.mark.parametrize("path", ["width", "height"])
def test_bool_dimension_rejected_before_source_io(path):
    selected, read, _, calls, _ = make_case()
    selected["image"][path] = True
    with pytest.raises(ExperimentalContractError, match="positive_integer_dimension_required"):
        gel.read_gel_inputs(selected, read_source=read)
    assert calls == []


@pytest.mark.parametrize("mutation", ["artifact", "hash", "size"])
def test_original_image_binding_rejected(mutation):
    selected, read, _, _, _ = make_case()
    if mutation == "artifact":
        selected["image"]["artifact_ref"] = "artifact_wrong"
    elif mutation == "hash":
        selected["image"]["byte_sha256"] = "0" * 64
    else:
        selected["image"]["width"] = 4
    with pytest.raises(ExperimentalContractError, match="original_image_.*_mismatch"):
        gel.read_gel_inputs(selected, read_source=read)


def test_late_authorization_failure_propagates_before_decode(monkeypatch):
    selected, read, _, _, _ = make_case()
    monkeypatch.setattr(gel, "_decode", lambda *_: pytest.fail("decoded before complete authorization"))
    def denial(ref, representation):
        if ref == "source_caption":
            raise PermissionError("not received")
        return read(ref, representation)
    with pytest.raises(PermissionError):
        gel.read_gel_inputs(selected, read_source=denial)


def test_unsupported_mode_is_explicit_reader_partial():
    selected, read, _, _, _ = make_case(mode="RGB")
    result = gel.read_gel_inputs(selected, read_source=read)
    assert result["image"]["unavailable_reason"] == "unsupported_native_grayscale_mode"
    assert result["assignments"][0]["lanes"][0]["bands"][0]["corrected_signal"]["exact"] is None
    assert gel.validate_gel_extraction(selected, result) == result


def test_partial_geometry_preserves_unrelated_actual_pixels():
    selected, read, _, _, _ = make_case()
    selected["roi_assignments"][0]["lanes"][0]["bands"][0]["region"] = [-1, 1, 1, 2]
    result = gel.read_gel_inputs(selected, read_source=read)
    baseline, protein, _ = result["assignments"][0]["lanes"]
    assert baseline["bands"][0]["measurement"]["unavailable_reason"] == "invalid_region"
    assert baseline["bands"][1]["corrected_signal"]["exact"]["numerator"] == "100"
    assert protein["bands"][0]["corrected_signal"]["exact"]["numerator"] == "80"


def test_detached_validation_forbids_source_decode_and_reader(monkeypatch):
    selected, read, _, _, _ = make_case()
    extraction = json.loads(json.dumps(gel.read_gel_inputs(selected, read_source=read)))
    def forbidden(*_args, **_kwargs):
        pytest.fail("reacquisition or decoding during saved validation")
    monkeypatch.setattr(gel, "read_gel_inputs", forbidden)
    monkeypatch.setattr(gel, "_decode", forbidden)
    monkeypatch.setattr(Image, "open", forbidden)
    assert gel.validate_gel_extraction(selected, extraction,
        expected_digest=extraction["extraction_digest"]) == extraction
    with pytest.raises(ExperimentalContractError, match="gel_extraction_digest_mismatch"):
        gel.validate_gel_extraction(selected, extraction, expected_digest="0" * 64)


@pytest.mark.parametrize("mutation", ["bool", "float", "sum", "pixel", "identity", "role", "extra"])
def test_re_signed_self_consistent_digest_does_not_hide_arithmetic_or_binding_tamper(mutation):
    selected, read, _, _, _ = make_case()
    extraction = gel.read_gel_inputs(selected, read_source=read)
    band = extraction["assignments"][0]["lanes"][1]["bands"][0]
    if mutation == "bool":
        band["measurement"]["pixel_count"] = True
    elif mutation == "float":
        band["measurement"]["pixel_count"] = 1.0
    elif mutation == "sum":
        band["measurement"]["sum_darkness"] += 1
    elif mutation == "pixel":
        band["measurement"]["pixel_bytes_base64"] = "AA=="
    elif mutation == "identity":
        extraction["image"]["artifact_ref"] = "other"
    elif mutation == "role":
        band["role"] = "free"
    else:
        band["measurement"]["extra"] = 1
    resign(extraction)
    with pytest.raises(ExperimentalContractError):
        gel.validate_gel_extraction(selected, extraction)


def test_unknown_conflicting_interpretations_retain_literal_source_witnesses():
    selected, read, _, _, _ = make_case()
    selected["lanes"][1]["subject"].update(state="conflicting", value=None)
    selected["context"]["genotype"].update(state="unknown", value=None, witnesses=[])
    result = gel.read_gel_inputs(selected, read_source=read)
    assert result["selection"]["lanes"][1]["subject"]["state"] == "conflicting"
    assert result["assignments"][0]["lanes"][1]["bands"][0]["corrected_signal"]["exact"]["numerator"] == "80"


def test_known_meaning_needs_authentic_support_not_literal_enum_token():
    selected, read, _, _, _ = make_case()
    # 'protein_present' is an interpretation, not claimed to be literal text.
    gel.read_gel_inputs(selected, read_source=read)
    selected["lanes"][1]["control_role"]["witnesses"] = []
    with pytest.raises(ExperimentalContractError, match="interpretation_witness_required"):
        gel.read_gel_inputs(selected, read_source=read)


def test_coherently_resigned_overlapping_regions_must_agree_on_original_pixels():
    selected, read, _, _, _ = make_case()
    extraction = gel.read_gel_inputs(selected, read_source=read)
    row = extraction["assignments"][0]["lanes"][1]
    band = row["bands"][0]
    band["measurement"] = gel._summary(band["region"], b"\x00")
    band["corrected_signal"] = gel._corrected(band["measurement"], row["background"])
    resign(extraction)
    # Every changed local summary/equation/hash is consistent, but the original
    # whole-lane pixel at this coordinate still differs. No host digest needed.
    with pytest.raises(ExperimentalContractError, match="saved_gel_shared_pixel_conflict"):
        gel.validate_gel_extraction(selected, extraction)


def test_conflicting_artifact_alias_is_rejected_before_decode(monkeypatch):
    selected, read, sources, _, _ = make_case()
    sources[("source_caption", "text")]["artifact_ref"] = "artifact_image"
    monkeypatch.setattr(gel, "_decode", lambda *_: pytest.fail("decoded conflicting artifact alias"))
    with pytest.raises(ExperimentalContractError, match="gel_artifact_byte_identity_conflict"):
        gel.read_gel_inputs(selected, read_source=read)


def test_coherently_resigned_saved_artifact_alias_conflict_is_rejected():
    selected, read, _, _, _ = make_case()
    extraction = gel.read_gel_inputs(selected, read_source=read)
    extraction["sources"][1]["artifact_ref"] = "artifact_image"
    for witness in extraction["authenticated_witnesses"]:
        witness["artifact_ref"] = "artifact_image"
    resign(extraction)
    with pytest.raises(ExperimentalContractError, match="gel_artifact_byte_identity_conflict"):
        gel.validate_gel_extraction(selected, extraction)


def test_v2_explicit_method_contract_preserves_v1_schema_and_output():
    selected, read, _, _, _ = make_case()
    original = gel.read_gel_inputs(selected, read_source=read)
    assert original["version"] == "gel_lane_extraction_v1"
    assert "background_method" not in original["assignments"][0]["lanes"][0]
    v1_schema = gel.gel_arguments_schema()
    v2_schema = gel.gel_arguments_schema(version=gel.VERSION_V2)
    Draft202012Validator.check_schema(v2_schema)
    assert "background_method" not in v1_schema["properties"]["roi_assignments"]["items"]["properties"]["lanes"]["items"]["properties"]
    assert "background_method" in v2_schema["properties"]["roi_assignments"]["items"]["properties"]["lanes"]["items"]["required"]
    selected["version"] = gel.VERSION_V2
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        gel.validate_gel_selection(selected)
    select_v2(selected)
    Draft202012Validator(v2_schema).validate(selected)
    updated = gel.read_gel_inputs(selected, read_source=read)
    assert updated["version"] == "gel_lane_extraction_v2"
    corrected = updated["assignments"][0]["lanes"][1]["bands"][0]["corrected_signal"]
    assert corrected["background_method"] == "mean"
    assert corrected["exact"] == original["assignments"][0]["lanes"][1]["bands"][0]["corrected_signal"]["exact"]


def test_v2_unknown_background_method_is_rejected_before_source_io():
    selected, read, _, calls, _ = make_case()
    select_v2(selected, "favorable")
    with pytest.raises(ExperimentalContractError, match="unsupported_background_method"):
        gel.read_gel_inputs(selected, read_source=read)
    assert not calls


@pytest.mark.parametrize("darkness,expected", [([0, 20, 100], (20, 1)), ([0, 21], (21, 2)), ([30], (30, 1))])
def test_v2_median_actual_odd_even_single_pixel_order_statistics(darkness, expected):
    selected, read, sources, _, _ = make_case()
    select_v2(selected, "median")
    record = sources[("source_image", "original")]
    with Image.open(BytesIO(record["content"])) as image:
        image.load()
        for x, value in enumerate(darkness):
            image.putpixel((x, 4), 255 - value)
        output = BytesIO()
        image.save(output, format="PNG")
    record["content"] = output.getvalue()
    selected["image"]["byte_sha256"] = hashlib.sha256(record["content"]).hexdigest()
    selected["roi_assignments"][0]["lanes"][1]["background"] = [0, 4, len(darkness), 5]
    result = gel.read_gel_inputs(selected, read_source=read)
    corrected = result["assignments"][0]["lanes"][1]["bands"][0]["corrected_signal"]
    assert corrected["background_per_pixel"] == {"numerator": str(expected[0]), "denominator": str(expected[1])}
    assert gel._fraction(corrected["exact"]) == 80 - gel._fraction(corrected["background_per_pixel"])
    assert gel.validate_gel_extraction(selected, result) == result


def test_v2_saved_median_check_preserves_method_and_needs_no_decoder(monkeypatch):
    selected, read, _, _, _ = make_case()
    select_v2(selected, "median")
    extraction = gel.read_gel_inputs(selected, read_source=read)
    def forbidden(*_args, **_kwargs):
        pytest.fail("source acquisition or decoder during median saved validation")
    monkeypatch.setattr(gel, "read_gel_inputs", forbidden)
    monkeypatch.setattr(gel, "_decode", forbidden)
    monkeypatch.setattr(Image, "open", forbidden)
    assert gel.validate_gel_extraction(selected, extraction) == extraction
    extraction["assignments"][0]["lanes"][1]["background_method"] = "mean"
    resign(extraction)
    with pytest.raises(ExperimentalContractError, match="saved_gel_extraction_mismatch"):
        gel.validate_gel_extraction(selected, extraction)


@pytest.mark.parametrize("case", ["duplicate_assignment", "missing_lane", "duplicate_band", "bool_roi", "wrong_quote"])
def test_malformed_nominations_are_repairable_failures(case):
    selected, read, _, _, _ = make_case()
    if case == "duplicate_assignment":
        selected["roi_assignments"] *= 2
    elif case == "missing_lane":
        selected["roi_assignments"][0]["lanes"].pop()
    elif case == "duplicate_band":
        selected["roi_assignments"][0]["lanes"][0]["bands"] *= 2
    elif case == "bool_roi":
        selected["roi_assignments"][0]["lanes"][0]["background"][0] = False
    else:
        selected["lanes"][1]["subject"]["witnesses"][0]["quote"] = "wrong"
    with pytest.raises(ExperimentalContractError):
        gel.read_gel_inputs(selected, read_source=read)
