"""Synthetic source bytes only; custody tests cannot verify visual transcription."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json

import jsonschema
from PIL import Image, ImageDraw
import pytest

from gene_annotation_episode.literature_binding_calculations import populate_binding_contrast
from gene_annotation_episode.literature_binding_reader import read_binding_parameter_table
from gene_annotation_episode.literature_binding_visual_inputs import (
    binding_visual_arguments_schema, read_binding_visual_inputs,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def encoded(image, fmt="PNG", **kwargs):
    stream = BytesIO()
    image.save(stream, format=fmt, **kwargs)
    return stream.getvalue()


def image_witness(quote, region=None, image_id="original"):
    return {"kind": "image", "image_id": image_id,
            "region": list(region or [0, 0, 20, 20]), "quote": quote}


def transcription(quote, region=None, image_id="original"):
    return {"status": "exact", "candidates": [image_witness(quote, region, image_id)], "fragments": []}


def text_witness(quote, source_ref="methods"):
    return {"kind": "text", "source_ref": source_ref, "representation": "text",
            "start": 0, "end": len(quote.encode("utf-8")), "quote": quote}


def interpreted(value, witness):
    return {"value": value, "witnesses": [deepcopy(witness)]}


def fixture():
    # An asymmetric image makes wrong geometric mappings detectably different.
    image = Image.new("RGB", (100, 80))
    for y in range(80):
        for x in range(100):
            image.putpixel((x, y), (x * 2, y * 3, (x + y) % 256))
    ImageDraw.Draw(image).text((1, 21), "synthetic", fill="white")
    methods = "Synthetic fixture: fitted averaged curve; minimum 3 experiments."
    witness = text_witness(methods)
    arguments = {
        "version": "binding_visual_inputs_v1", "table_id": "synthetic-table",
        "images": [{"image_id": "original", "source_ref": "image-source",
                    "original_source_ref": "image-source", "mapping": None}],
        "context": {name: interpreted(value, witness) for name, value in
                    (("subject", "SyntheticProtein"), ("state", "synthetic-state"),
                     ("experiment", "synthetic-experiment"))},
        "parameter_kind": interpreted("ic50", witness),
        "unit": transcription("nM"),
        "uncertainty_basis": interpreted("fit_to_averaged_curve", witness),
        "minimum_experiment_count": {"literal": "3", "witness": witness},
        "cells": [{"cell_id": name, "image_id": "original", "cell_region": region,
                   "ligand": interpreted(ligand, witness), "expression": transcription(token, region)}
                  for name, region, ligand, token in
                  (("reference", [0, 20, 40, 40], "synthetic-reference", "7.25 ± 0.35"),
                   ("test", [40, 20, 80, 40], "synthetic-test", ">=23.8"))],
    }
    sources = {"image-source": encoded(image), "methods": methods.encode("utf-8")}
    return arguments, sources, image


def reader(sources, calls=None):
    def read(reference, representation):
        if calls is not None:
            calls.append((reference, representation))
        content = sources[reference]
        if isinstance(content, Exception):
            raise content
        return {"artifact_ref": "artifact:" + hashlib.sha256(content).hexdigest(), "content": content}
    return read


def run(arguments, sources):
    return read_binding_visual_inputs(arguments, read_source=reader(sources))


def old_extract(table):
    # These source IDs are created by this test harness only, not by the reader.
    return read_binding_parameter_table({"source_ref": "synthetic-retained-source",
        "artifact_ref": "synthetic-retained-artifact", "text": json.dumps(table),
        "representation": "retained_visual_transcription"}, expected_subject="SyntheticProtein",
        expected_state="synthetic-state", expected_experiment="synthetic-experiment",
        reference_ligand="synthetic-reference", test_ligand="synthetic-test", parameter_kind="ic50")


def add_crop(arguments, sources, image, region=(0, 20, 80, 40), *, colour="preserve"):
    crop = image.crop(region)
    if colour == "rgb":
        crop = crop.convert("RGB")
    sources["crop-source"] = encoded(crop)
    arguments["images"].append({"image_id": "crop", "source_ref": "crop-source",
        "original_source_ref": "image-source", "mapping": {
            "original_region": list(region), "colour_conversion": colour}})


def test_complete_custody_literal_meanings_and_existing_reader_bridge():
    arguments, sources, _ = fixture()
    before = deepcopy(arguments)
    calls = []
    result = read_binding_visual_inputs(arguments, read_source=reader(sources, calls))
    assert arguments == before
    assert result == json.loads(json.dumps(result))
    assert result["compatibility"]["status"] == "complete"
    assert result["minimum_experiment_count"]["value"] == 3
    assert result["uncertainty_basis"]["value"] == "fit_to_averaged_curve"
    assert result["cells"][0]["parsed_measurement"] == {
        "value": 7.25, "relation": "eq", "reported_spread": .35, "unit": "nM"}
    assert result["cells"][1]["parsed_measurement"]["relation"] == "ge"
    assert result["cells"][0]["expression"]["candidates"][0]["authentication"] == "image_bytes_and_geometry_only"
    assert result["context"]["subject"]["interpretation_attribution"] == "investigating_episode_interpretation"
    image = result["images"][0]
    assert (image["actual_format"], image["actual_mode"], image["width"], image["height"], image["frame_count"]) == (
        "PNG", "RGB", 100, 80, 1)
    assert image["byte_sha256"] == hashlib.sha256(sources["image-source"]).hexdigest()
    assert calls.count(("image-source", "original")) == 1
    assert calls.count(("methods", "text")) == 1
    sheet = populate_binding_contrast(old_extract(result["compatibility"]["table"]))
    assert sheet["cells"]["native_parameter_ratio"]["value"] == pytest.approx(23.8 / 7.25)
    assert sheet["cells"]["native_parameter_ratio"]["relation"] == "ge"
    assert sheet["independent_preparation_count"] is None
    assert sheet["cells"]["source_profile_log_ratio"]["value"] is None


def test_schema_is_closed_and_malformed_request_does_not_read_sources():
    arguments, sources, _ = fixture()
    schema = binding_visual_arguments_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(arguments, schema)
    arguments["scientific_confidence"] = .9
    calls = []
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        read_binding_visual_inputs(arguments, read_source=reader(sources, calls))
    assert calls == []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(arguments, schema)
    schema["properties"].clear()
    assert binding_visual_arguments_schema()["properties"]


@pytest.mark.parametrize("change,code", [
    (lambda a: a["cells"].append(deepcopy(a["cells"][0])), "duplicate_cell_id"),
    (lambda a: a["images"].append(deepcopy(a["images"][0])), "duplicate_image_id"),
    (lambda a: a["cells"][0].update(image_id="missing"), "undeclared_image_id"),
    (lambda a: a["cells"][0].update(cell_region=[False, 0, 10, 10]), "nonempty_integer_image_region_required"),
    (lambda a: a["unit"].update(status="exact", candidates=[]), "one_exact_candidate_required"),
    (lambda a: a["uncertainty_basis"].update(witnesses=[]), "interpretation_witness_required"),
    (lambda a: a["minimum_experiment_count"].update(literal="0"), "positive_integer_literal_required"),
    (lambda a: a["parameter_kind"].update(value="affinity"), "unsupported_value"),
])
def test_malformed_closed_relationships(change, code):
    arguments, sources, _ = fixture()
    change(arguments)
    with pytest.raises(ExperimentalContractError) as error:
        run(arguments, sources)
    assert error.value.code == code


@pytest.mark.parametrize("unit,multiplier", [("nM", 1), ("uM", 1000), ("µM", 1000),
                                             ("μM", 1000), ("mM", 1000000)])
def test_source_units_normalize_without_changing_native_compatibility_token(unit, multiplier):
    arguments, sources, _ = fixture()
    arguments["unit"]["candidates"][0]["quote"] = unit
    result = run(arguments, sources)
    assert result["cells"][0]["parsed_measurement"]["value"] == pytest.approx(7.25 * multiplier)
    assert result["compatibility"]["table"]["unit"] == unit
    assert old_extract(result["compatibility"]["table"])["reference_rows"][0]["value"] == pytest.approx(7.25 * multiplier)


def test_nd_is_only_literal_unavailable_and_never_an_expanded_scientific_claim():
    arguments, sources, _ = fixture()
    arguments["cells"][1]["expression"]["candidates"][0]["quote"] = " n.d. "
    result = run(arguments, sources)
    cell = result["cells"][1]
    assert cell["parse_status"] == "reported_unavailable"
    assert cell["expression"]["candidates"][0]["witness"]["quote"] == " n.d. "
    assert cell["parsed_measurement"] == {"value": None, "relation": "unreported", "reported_spread": None, "unit": "nM"}
    assert result["compatibility"]["table"]["rows"][1]["expression"] == " n.d. "
    assert "nondetected" not in json.dumps(result)
    assert "not determined" not in json.dumps(result)


@pytest.mark.parametrize("state", ["ambiguous", "unreadable", "conflicting"])
def test_readability_states_preserve_raw_candidates_and_valid_partial(state):
    arguments, sources, _ = fixture()
    old = arguments["cells"][1]["expression"]["candidates"][0]
    if state == "unreadable":
        expression = {"status": state, "candidates": [], "fragments": [{**old, "quote": "2?"}]}
    else:
        expression = {"status": state, "candidates": [{**old, "quote": "23.8"}, {**old, "quote": "28.8"}], "fragments": []}
    arguments["cells"][1]["expression"] = expression
    result = run(arguments, sources)
    assert result["cells"][0]["parsed_measurement"]["value"] == 7.25
    assert result["cells"][1]["parse_status"] == state
    assert result["cells"][1]["parsed_measurement"] is None
    for part in ("candidates", "fragments"):
        assert [w["witness"] for w in result["cells"][1]["expression"][part]] == expression[part]
    compatibility = result["compatibility"]
    assert compatibility["status"] == "partial_requires_adapter"
    assert compatibility["included_cell_ids"] == ["reference"]
    assert compatibility["withheld_cell_ids"] == ["test"]
    assert len(compatibility["table"]["rows"]) == 1
    assert "n.d." not in json.dumps(result)


@pytest.mark.parametrize("token", ["~23.8", "[20,30]", "0", "-4", "1e999", "1e-999", ">23 ± 1"])
def test_unsupported_expressions_retain_the_raw_reading_and_other_cell(token):
    arguments, sources, _ = fixture()
    arguments["cells"][1]["expression"]["candidates"][0]["quote"] = token
    result = run(arguments, sources)
    assert result["cells"][1]["parse_status"] == "unsupported_expression"
    assert result["cells"][1]["expression"]["candidates"][0]["witness"]["quote"] == token
    assert result["compatibility"]["status"] == "partial_requires_adapter"


def test_canonical_owner_survives_crop_wrappers_and_same_cell_cannot_conflict_silently():
    arguments, sources, image = fixture()
    add_crop(arguments, sources, image)
    copy = deepcopy(arguments["cells"][0])
    copy.update(cell_id="crop-reference", image_id="crop", cell_region=[0, 0, 40, 20])
    copy["expression"] = transcription("7.25 ± 0.35", [0, 0, 40, 20], "crop")
    arguments["cells"].append(copy)
    result = run(arguments, sources)
    first, _, crop = result["cells"]
    assert first["canonical_locator"] == crop["canonical_locator"]
    assert first["physical_cell_key"] == crop["physical_cell_key"]
    assert result["compatibility"]["status"] == "complete"
    # Old calculator sees one original physical operand, even with two wrappers.
    sheet = populate_binding_contrast(old_extract(result["compatibility"]["table"]))
    assert sheet["cells"]["reference_parameter"]["value"] == 7.25
    arguments["cells"][-1]["expression"]["candidates"][0]["quote"] = "8.25 ± 0.35"
    result = run(arguments, sources)
    assert [result["cells"][i]["parse_status"] for i in (0, 2)] == ["conflicting", "conflicting"]
    assert all(result["cells"][i]["parsed_measurement"] is None for i in (0, 2))
    assert result["cells"][1]["parsed_measurement"]["value"] == 23.8
    assert result["compatibility"]["status"] == "partial_requires_adapter"
    assert "physical_cell_conflict" in result["compatibility"]["reasons"]


def test_alternate_candidate_view_must_map_inside_canonical_cell():
    arguments, sources, image = fixture()
    add_crop(arguments, sources, image)
    arguments["cells"][0]["expression"] = transcription("7.25 ± 0.35", [0, 0, 40, 20], "crop")
    result = run(arguments, sources)
    assert result["cells"][0]["mapped_candidates"][0]["original_region"] == [0, 20, 40, 40]
    arguments["cells"][0]["expression"]["candidates"][0]["region"] = [40, 0, 80, 20]
    result = run(arguments, sources)
    assert result["cells"][0]["error"]["code"] == "expression_outside_canonical_cell"
    assert result["cells"][1]["parsed_measurement"]["value"] == 23.8


def test_overlaps_are_not_physical_identity_or_independence():
    arguments, sources, _ = fixture()
    arguments["cells"][1]["cell_region"] = [30, 20, 80, 40]
    result = run(arguments, sources)
    assert result["cells"][0]["physical_cell_key"] != result["cells"][1]["physical_cell_key"]
    assert result["geometry_overlaps"] == [{"left_cell_id": "reference", "right_cell_id": "test"}]
    assert all(cell["parsed_measurement"] is not None for cell in result["cells"])
    assert "independent_preparation_count" not in result


@pytest.mark.parametrize("failure", ["callback", "bytes", "wrong-crop", "bounds"])
def test_source_failures_leave_independent_valid_cells_and_raw_operands(failure):
    arguments, sources, image = fixture()
    add_crop(arguments, sources, image)
    arguments["cells"][1].update(image_id="crop", cell_region=[40, 0, 80, 20])
    arguments["cells"][1]["expression"] = transcription(">=23.8", [40, 0, 80, 20], "crop")
    if failure == "callback":
        sources["crop-source"] = RuntimeError("synthetic unavailable source")
    elif failure == "bytes":
        sources["crop-source"] = b"synthetic corrupt image"
    elif failure == "wrong-crop":
        sources["crop-source"] = encoded(Image.new("RGB", (80, 20)))
    else:
        arguments["images"][1]["mapping"]["original_region"] = [0, 70, 80, 90]
    result = run(arguments, sources)
    assert result["cells"][0]["parse_status"] == "parsed"
    assert result["cells"][1]["parse_status"] == "source_unavailable"
    assert result["cells"][1]["expression"]["candidates"][0]["witness"]["quote"] == ">=23.8"
    assert result["images"][1]["error"] is not None
    assert result["compatibility"]["status"] == "partial_requires_adapter"


def test_label_witness_failure_is_local_to_its_cell():
    arguments, sources, _ = fixture()
    arguments["cells"][1]["ligand"]["witnesses"] = [text_witness("missing", "unavailable")]
    sources["unavailable"] = PermissionError("synthetic scoped callback denied")
    result = run(arguments, sources)
    assert result["cells"][0]["parsed_measurement"]["value"] == 7.25
    assert result["cells"][1]["parse_status"] == "source_unavailable"
    assert result["cells"][1]["ligand"]["witnesses"][0]["error"]["code"] == "source_read_failed"


def test_shared_qualification_failure_retains_parsed_cells_but_cannot_fabricate_count():
    arguments, sources, _ = fixture()
    arguments["minimum_experiment_count"]["witness"] = text_witness("minimum 3", "unavailable")
    sources["unavailable"] = RuntimeError("synthetic unavailable")
    result = run(arguments, sources)
    assert all(cell["parsed_measurement"] is not None for cell in result["cells"])
    assert result["minimum_experiment_count"]["value"] is None
    assert result["compatibility"]["table"] is None
    assert result["compatibility"]["status"] == "unavailable"


@pytest.mark.parametrize("kind", ["bad_unit", "ambiguous_unit", "bad_span", "count_substring"])
def test_shared_operand_and_witness_limits(kind):
    arguments, sources, _ = fixture()
    if kind == "bad_unit":
        arguments["unit"]["candidates"][0]["quote"] = "mg/mL"
    elif kind == "ambiguous_unit":
        arguments["unit"]["status"] = "ambiguous"
        arguments["unit"]["candidates"].append(image_witness("uM"))
    elif kind == "bad_span":
        arguments["context"]["subject"]["witnesses"][0]["quote"] = "x" * len(sources["methods"])
    else:
        sources["count"] = b"13"
        arguments["minimum_experiment_count"]["witness"] = {
            "kind": "text", "source_ref": "count", "representation": "text",
            "start": 1, "end": 2, "quote": "3"}
    result = run(arguments, sources)
    assert result["compatibility"]["status"] == "unavailable"
    assert result["compatibility"]["table"] is None
    if kind == "count_substring":
        assert result["minimum_experiment_count"]["value"] is None
        assert all(cell["parsed_measurement"] is not None for cell in result["cells"])


@pytest.mark.parametrize("fmt,mode", [("JPEG", "RGB"), ("PNG", "L"), ("PNG", "RGBA")])
def test_supported_decoded_formats_and_modes(fmt, mode):
    arguments, sources, image = fixture()
    sources["image-source"] = encoded(image.convert(mode), fmt)
    result = run(arguments, sources)
    assert result["images"][0]["actual_format"] == fmt
    assert result["images"][0]["actual_mode"] == mode
    assert result["compatibility"]["status"] == "complete"


def test_explicit_rgb_mapping_and_jpeg_decoded_crop():
    arguments, sources, image = fixture()
    image = image.convert("L")
    sources["image-source"] = encoded(image)
    add_crop(arguments, sources, image, colour="rgb")
    assert run(arguments, sources)["images"][1]["error"] is None
    arguments["images"][1]["mapping"]["colour_conversion"] = "preserve"
    assert run(arguments, sources)["images"][1]["error"]["code"] == "image_mapping_pixels_mismatch"
    arguments, sources, image = fixture()
    sources["image-source"] = encoded(image, "JPEG")
    with Image.open(BytesIO(sources["image-source"])) as decoded:
        decoded.load()
        add_crop(arguments, sources, decoded)
    assert run(arguments, sources)["images"][1]["error"] is None


@pytest.mark.parametrize("case,code", [("format", "unsupported_image_format"),
                                       ("mode", "unsupported_image_mode"),
                                       ("frames", "single_frame_required"),
                                       ("bounds", "image_region_out_of_bounds")])
def test_unsupported_images_and_roi_are_not_readable_cells(case, code):
    arguments, sources, image = fixture()
    if case == "format":
        sources["image-source"] = encoded(image, "GIF")
    elif case == "mode":
        sources["image-source"] = encoded(image.convert("P"))
    elif case == "frames":
        sources["image-source"] = encoded(image, save_all=True, append_images=[Image.new("RGB", image.size, "white")])
    else:
        arguments["cells"][0]["cell_region"] = [0, 20, 101, 40]
    result = run(arguments, sources)
    assert result["cells"][0]["error"]["code"] == code
    assert result["cells"][0]["parsed_measurement"] is None


def test_no_claim_of_ocr_or_interpretation_truth_from_a_successful_read():
    arguments, sources, _ = fixture()
    # Deliberately nominate text not printed in the synthetic image. The reader
    # authenticates the selected source and geometry, not the text's truth.
    arguments["cells"][0]["expression"]["candidates"][0]["quote"] = "137.125"
    arguments["uncertainty_basis"] = {"value": "unknown", "witnesses": []}
    arguments["minimum_experiment_count"] = None
    result = run(arguments, sources)
    assert result["cells"][0]["parsed_measurement"]["value"] == 137.125
    assert result["cells"][0]["expression"]["interpretation_attribution"] == "investigating_episode_interpretation"
    assert result["uncertainty_basis"]["value"] == "unknown"
    assert result["minimum_experiment_count"] is None


def test_reported_hill_kind_remains_distinct_and_no_covariance_argument_is_accepted():
    arguments, sources, _ = fixture()
    arguments["parameter_kind"]["value"] = "reported_hill_kd"
    assert run(arguments, sources)["compatibility"]["table"]["parameter_kind"] == "reported_hill_kd"
    arguments["log_covariance"] = [[1, 0], [0, 1]]
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        run(arguments, sources)
