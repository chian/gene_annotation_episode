"""Selected grayscale gel display pixels and source custody, separate from scores.

An investigating episode nominates lane meanings and complete ROI assignments.
Literal witnesses authenticate source spans, not those scientific meanings.
Original 8-bit grayscale PNG/JPEG pixels are measured without display transforms.
Saved checks establish representation consistency; an original immutable outcome
digest supplies external custody. This module performs no acquisition or inference.
"""
from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from fractions import Fraction
import hashlib
from io import BytesIO
import json
import re
import warnings

from PIL import Image, UnidentifiedImageError, __version__ as PILLOW_VERSION

from .literature_assay_inputs import _Sources
from .literature_experimental_contracts import ExperimentalContractError


VERSION = "gel_lane_selection_v1"
EXTRACTION_VERSION = "gel_lane_extraction_v1"
VERSION_V2 = "gel_lane_selection_v2"
EXTRACTION_VERSION_V2 = "gel_lane_extraction_v2"
CONTEXT_FIELDS = ("experiment", "organism", "genotype", "subject", "construct",
                  "system", "endpoint", "intended_variable")
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
CONTROL_ROLES = ("protein_free", "protein_present", "competitor", "reference", "other")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _list(value, field):
    if type(value) is not list:
        _fail("list_required", field)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          allow_nan=False, separators=(",", ":")).encode()
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ExperimentalContractError("finite_json_required", "value") from error


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _same(left, right):
    # bool is not an integer; 1 is not a substituted saved float1.0.
    return _canonical(left) == _canonical(right)


def _rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _box_shape(box, field):
    if box is not None and (type(box) is not list or len(box) != 4
                           or any(type(v) is not int for v in box)):
        _fail("integer_region_required", field)


def _box_reason(box, width, height):
    if box is None:
        return "region_not_selected"
    left, top, right, bottom = box
    if left < 0 or top < 0 or right <= left or bottom <= top:
        return "invalid_region"
    if right > width or bottom > height:
        return "region_outside_image"
    return None


def _witness_shape(value, field):
    _keys(value, ("source_ref", "representation", "start", "end", "quote"), field)
    _text(value["source_ref"], field + ".source_ref")
    _text(value["quote"], field + ".quote")
    if value["representation"] not in ("original", "text"):
        _fail("unknown_source_representation", field)
    if (type(value["start"]) is not int or type(value["end"]) is not int
            or not 0 <= value["start"] < value["end"]):
        _fail("nonempty_source_span_required", field)


def _witnesses(arguments):
    for name in CONTEXT_FIELDS:
        yield from arguments["context"][name]["witnesses"]
    for lane in arguments["lanes"]:
        for name in ("subject", "construct", "endpoint", "condition", "control_role"):
            yield from lane[name]["witnesses"]


def _interpretation(value, field, *, choices=None):
    _keys(value, ("state", "value", "witnesses"), field)
    if value["state"] not in ("known", "unknown", "conflicting"):
        _fail("unknown_interpretation_state", field)
    _list(value["witnesses"], field + ".witnesses")
    if value["state"] == "known":
        _text(value["value"], field + ".value")
        if choices is not None and value["value"] not in choices:
            _fail("unknown_interpretation_value", field + ".value")
        if not value["witnesses"]:
            _fail("interpretation_witness_required", field)
    elif value["value"] is not None:
        _fail("unresolved_interpretation_value_must_be_null", field)
    # A single actual passage can describe a conflict; no artificial minimum
    # number of independent sources is a prerequisite for retaining that fact.


def gel_arguments_schema(*, version=VERSION):
    """Closed selected image and literal/interpretation/geometry nominations."""
    def obj(properties):
        return {"type": "object", "properties": properties,
                "required": list(properties), "additionalProperties": False}
    text = {"type": "string", "minLength": 1}
    nullable_text = {"anyOf": [text, {"type": "null"}]}
    box = {"anyOf": [{"type": "array", "items": {"type": "integer"},
                      "minItems": 4, "maxItems": 4}, {"type": "null"}]}
    witness = obj({"source_ref": text, "representation": {"enum": ["original", "text"]},
                   "start": {"type": "integer", "minimum": 0},
                   "end": {"type": "integer", "minimum": 1}, "quote": text})
    witnesses = {"type": "array", "items": witness}
    def interpretation(choices=None):
        value = nullable_text if choices is None else {"anyOf": [{"enum": list(choices)}, {"type": "null"}]}
        return obj({"state": {"enum": ["known", "unknown", "conflicting"]},
                    "value": value, "witnesses": witnesses})
    if version not in (VERSION, VERSION_V2):
        _fail("unsupported_gel_selection_version", "version")
    lane_rois = obj({"lane_id": text, "background": box, "whole_lane": box,
                     "bands": {"type": "array", "items": obj({"band_id": text,
                        "role": {"enum": ["shifted", "free", "other"]}, "region": box})}})
    if version == VERSION_V2:
        lane_rois["properties"]["background_method"] = {"enum": ["mean", "median"]}
        lane_rois["required"].append("background_method")
    return obj({"version": {"const": version}, "image": obj({"source_ref": text,
        "artifact_ref": text, "byte_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "width": {"type": "integer", "minimum": 1}, "height": {"type": "integer", "minimum": 1},
        "source_kind": {"enum": list(SOURCE_KINDS)}}),
        "context": obj({name: interpretation() for name in CONTEXT_FIELDS}),
        "lanes": {"type": "array", "minItems": 1, "items": obj({"lane_id": text,
            "observation_id": text, **{name: interpretation() for name in
                ("subject", "construct", "endpoint", "condition")},
            "control_role": interpretation(CONTROL_ROLES)})},
        "roi_assignments": {"type": "array", "minItems": 1, "items": obj({
            "assignment_id": text, "lanes": {"type": "array", "items": lane_rois}})}})


def validate_gel_selection(arguments):
    _keys(arguments, ("version", "image", "context", "lanes", "roi_assignments"), "arguments")
    if arguments["version"] not in (VERSION, VERSION_V2):
        _fail("unsupported_gel_selection_version", "version")
    image = arguments["image"]
    _keys(image, ("source_ref", "artifact_ref", "byte_sha256", "width", "height", "source_kind"), "image")
    for name in ("source_ref", "artifact_ref"):
        _text(image[name], "image." + name)
    if not isinstance(image["byte_sha256"], str) or not _HEX.fullmatch(image["byte_sha256"]):
        _fail("sha256_required", "image.byte_sha256")
    for name in ("width", "height"):
        if type(image[name]) is not int or image[name] < 1:
            _fail("positive_integer_dimension_required", "image." + name)
    if image["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "image.source_kind")
    _keys(arguments["context"], CONTEXT_FIELDS, "context")
    for name in CONTEXT_FIELDS:
        _interpretation(arguments["context"][name], "context." + name)
    _list(arguments["lanes"], "lanes")
    lane_ids = []
    for lane in arguments["lanes"]:
        _keys(lane, ("lane_id", "observation_id", "subject", "construct", "endpoint", "condition", "control_role"), "lanes")
        for name in ("lane_id", "observation_id"):
            _text(lane[name], "lanes." + name)
        for name in ("subject", "construct", "endpoint", "condition"):
            _interpretation(lane[name], "lanes." + name)
        _interpretation(lane["control_role"], "lanes.control_role", choices=CONTROL_ROLES)
        lane_ids.append(lane["lane_id"])
    if not lane_ids or len(lane_ids) != len(set(lane_ids)):
        _fail("unique_nonempty_lane_roster_required", "lanes")
    for index, witness in enumerate(_witnesses(arguments)):
        _witness_shape(witness, f"witnesses[{index}]")
    _list(arguments["roi_assignments"], "roi_assignments")
    ids = []
    for assignment in arguments["roi_assignments"]:
        _keys(assignment, ("assignment_id", "lanes"), "roi_assignments")
        _text(assignment["assignment_id"], "roi_assignments.assignment_id")
        ids.append(assignment["assignment_id"])
        _list(assignment["lanes"], "roi_assignments.lanes")
        if [row.get("lane_id") for row in assignment["lanes"] if isinstance(row, dict)] != lane_ids:
            _fail("exact_ordered_lane_roster_required", "roi_assignments.lanes")
        for row in assignment["lanes"]:
            row_keys = ("lane_id", "background", "whole_lane", "bands")
            if arguments["version"] == VERSION_V2:
                row_keys += ("background_method",)
            _keys(row, row_keys, "roi_assignments.lanes")
            if arguments["version"] == VERSION_V2 and row["background_method"] not in ("mean", "median"):
                _fail("unsupported_background_method", "roi_assignments.lanes.background_method")
            for name in ("background", "whole_lane"):
                _box_shape(row[name], "roi_assignments.lanes." + name)
            _list(row["bands"], "roi_assignments.lanes.bands")
            band_ids = []
            for band in row["bands"]:
                _keys(band, ("band_id", "role", "region"), "bands")
                _text(band["band_id"], "bands.band_id")
                band_ids.append(band["band_id"])
                if band["role"] not in ("shifted", "free", "other"):
                    _fail("unknown_band_role", "bands.role")
                _box_shape(band["region"], "bands.region")
            if len(band_ids) != len(set(band_ids)):
                _fail("duplicate_band_id", "bands")
    if not ids or len(ids) != len(set(ids)):
        _fail("unique_nonempty_assignment_roster_required", "roi_assignments")
    _canonical(arguments)
    return deepcopy(arguments)


def _summary(region, pixels, *, reason=None):
    result = {"region": deepcopy(region), "status": "unavailable" if reason else "measured",
        "unavailable_reason": reason, "pixel_bytes_base64": None, "pixel_sha256": None,
        "pixel_count": None, "sum_gray": None, "sum_darkness": None,
        "minimum_gray": None, "maximum_gray": None, "zero_gray_count": None}
    if reason:
        return result
    result.update(pixel_bytes_base64=base64.b64encode(pixels).decode("ascii"),
        pixel_sha256=_hash(pixels), pixel_count=len(pixels), sum_gray=sum(pixels),
        sum_darkness=255 * len(pixels) - sum(pixels), minimum_gray=min(pixels),
        maximum_gray=max(pixels), zero_gray_count=pixels.count(0))
    return result


def _corrected(signal, background, method=None):
    reason = signal["unavailable_reason"] or background["unavailable_reason"]
    if reason:
        result = {"exact": None, "unavailable_reason": reason}
        level = None
    else:
        if method == "median":
            pixels = base64.b64decode(background["pixel_bytes_base64"], validate=True)
            ordered = sorted(255 - gray for gray in pixels)
            n = len(ordered)
            level = Fraction(ordered[(n - 1) // 2] + ordered[n // 2], 2)
        else:
            level = Fraction(background["sum_darkness"], background["pixel_count"])
        value = Fraction(signal["sum_darkness"]) - signal["pixel_count"] * level
        result = {"exact": _rational(value), "unavailable_reason": None}
    if method is not None:
        result.update(background_method=method,
                      background_per_pixel=None if level is None else _rational(level))
    return result


def _decode(content):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                fmt, mode, size = source.format, source.mode, source.size
                if fmt not in ("PNG", "JPEG"):
                    return None, "unsupported_image_format"
                if mode != "L":
                    return None, "unsupported_native_grayscale_mode"
                if getattr(source, "n_frames", 1) != 1:
                    return None, "single_frame_required"
                source.verify()
            with Image.open(BytesIO(content)) as source:
                orientation = source.getexif().get(274, 1)
                if type(orientation) is not int or orientation != 1:
                    return None, "unsupported_image_orientation"
                source.load()
                if (source.size != size or source.mode != mode or source.format != fmt
                        or getattr(source, "n_frames", 1) != 1):
                    return None, "image_decode_failed"
                return (source.copy(), fmt), None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        return None, "image_decode_failed"


def _result(selection, image, sources, witnesses, assignments):
    result = {"version": EXTRACTION_VERSION if selection["version"] == VERSION else EXTRACTION_VERSION_V2,
        "selection": deepcopy(selection),
        "image": image, "sources": sources, "authenticated_witnesses": witnesses,
        "interpretation_basis": "investigating_episode_nominations",
        "intensity_meaning": "selected_display_darkness_255_minus_gray",
        "origin": "synthetic" if selection["image"]["source_kind"] == "synthetic_fixture" else "graph_derived",
        "assignments": assignments, "independent_preparation_count": None,
        "sampling_uncertainty": None, "calibrated_molecular_occupancy": None}
    result["extraction_digest"] = _hash(_canonical(result))
    return result


def _source_aliases(records):
    by_artifact = {}
    for record in records:
        artifact, digest = record["artifact_ref"], record["byte_sha256"]
        if artifact in by_artifact and by_artifact[artifact] != digest:
            _fail("gel_artifact_byte_identity_conflict", "sources")
        by_artifact[artifact] = digest


def read_gel_inputs(arguments, *, read_source):
    """Read exact original bytes and nominated regions, keeping local failures.

    The callback owns authorization; every nominated source is authorized before
    image decoding. Callback failures propagate rather than becoming evidence.
    No supplied number is treated as detector calibration or biological n.
    """
    selected = validate_gel_selection(arguments)
    sources = _Sources(read_source)
    spec = selected["image"]
    raw = sources.source(spec["source_ref"], "original")
    witnesses = [sources.witness(w, "witnesses") for w in _witnesses(selected)]
    if raw["artifact_ref"] != spec["artifact_ref"] or _hash(raw["content"]) != spec["byte_sha256"]:
        _fail("original_image_identity_mismatch", "image")
    source_records = [{"source_ref": ref, "representation": rep, "artifact_ref": record["artifact_ref"],
        "byte_sha256": _hash(record["content"])} for (ref, rep), record in sources.cache.items()]
    _source_aliases(source_records)
    decoded, error = _decode(raw["content"])
    frame, fmt = decoded if decoded else (None, None)
    try:
        if frame is not None and frame.size != (spec["width"], spec["height"]):
            _fail("original_image_dimensions_mismatch", "image")
        image = {**deepcopy(spec), "mode": frame.mode if frame else None,
            "format": fmt, "status": "decoded" if frame else "unsupported",
            "unavailable_reason": error, "pillow_version": PILLOW_VERSION,
            "geometric_transform": "identity", "contrast_transform": "identity"}
        assignments = []
        for assignment in selected["roi_assignments"]:
            rows = []
            for lane in assignment["lanes"]:
                method = lane.get("background_method")
                def roi(region):
                    reason = error or _box_reason(region, spec["width"], spec["height"])
                    if reason:
                        return _summary(region, None, reason=reason)
                    with frame.crop(tuple(region)) as crop:
                        return _summary(region, crop.tobytes())
                background = roi(lane["background"])
                bands = []
                for band in lane["bands"]:
                    record = {**deepcopy(band), "measurement": roi(band["region"])}
                    record["corrected_signal"] = _corrected(record["measurement"], background, method)
                    bands.append(record)
                whole = roi(lane["whole_lane"])
                row = {"lane_id": lane["lane_id"], "background": background,
                    "whole_lane": whole, "whole_lane_corrected_signal": _corrected(whole, background, method),
                    "bands": bands}
                if method is not None:
                    row["background_method"] = method
                rows.append(row)
            assignments.append({"assignment_id": assignment["assignment_id"], "lanes": rows})
        return _result(selected, image, source_records, witnesses, assignments)
    finally:
        if frame is not None:
            frame.close()


def validate_gel_extraction(arguments, extraction, *, expected_digest=None):
    """Validate retained pixels and equations without source IO or image decoding.

    A host may compare its original immutable-record digest. Without that trusted
    association this validates consistency, not historical pixel/source custody.
    """
    selected = validate_gel_selection(arguments)
    _keys(extraction, ("version", "selection", "image", "sources", "authenticated_witnesses",
        "interpretation_basis", "intensity_meaning", "origin", "assignments",
        "independent_preparation_count", "sampling_uncertainty", "calibrated_molecular_occupancy",
        "extraction_digest"), "extraction")
    digest = _hash(_canonical({k: v for k, v in extraction.items() if k != "extraction_digest"}))
    if extraction["extraction_digest"] != digest or expected_digest is not None and expected_digest != digest:
        _fail("gel_extraction_digest_mismatch", "extraction")
    if not _same(extraction["selection"], selected):
        _fail("gel_selection_binding_mismatch", "extraction.selection")
    spec = selected["image"]
    image = extraction["image"]
    _keys(image, (*spec, "mode", "format", "status", "unavailable_reason", "pillow_version",
                  "geometric_transform", "contrast_transform"), "extraction.image")
    if not _same({k: image[k] for k in spec}, spec):
        _fail("original_image_identity_mismatch", "extraction.image")
    if image["geometric_transform"] != "identity" or image["contrast_transform"] != "identity":
        _fail("transformed_gel_image_unsupported", "extraction.image")
    _text(image["pillow_version"], "extraction.image.pillow_version")
    if image["status"] == "decoded":
        if image["mode"] != "L" or image["format"] not in ("PNG", "JPEG") or image["unavailable_reason"] is not None:
            _fail("gel_decode_state_mismatch", "extraction.image")
    elif image["status"] == "unsupported":
        if image["mode"] is not None or image["format"] is not None or image["unavailable_reason"] not in (
                "unsupported_image_format", "unsupported_native_grayscale_mode", "single_frame_required",
                "unsupported_image_orientation", "image_decode_failed"):
            _fail("gel_decode_state_mismatch", "extraction.image")
    else:
        _fail("gel_decode_state_mismatch", "extraction.image")
    expected_closure = list(dict.fromkeys([(spec["source_ref"], "original")] +
        [(w["source_ref"], w["representation"]) for w in _witnesses(selected)]))
    _list(extraction["sources"], "extraction.sources")
    if len(extraction["sources"]) != len(expected_closure):
        _fail("gel_source_closure_mismatch", "extraction.sources")
    records = {}
    for record, key in zip(extraction["sources"], expected_closure):
        _keys(record, ("source_ref", "representation", "artifact_ref", "byte_sha256"), "extraction.sources")
        if (record["source_ref"], record["representation"]) != key:
            _fail("gel_source_closure_mismatch", "extraction.sources")
        _text(record["artifact_ref"], "extraction.sources.artifact_ref")
        if not isinstance(record["byte_sha256"], str) or not _HEX.fullmatch(record["byte_sha256"]):
            _fail("sha256_required", "extraction.sources.byte_sha256")
        records[key] = record
    if records[(spec["source_ref"], "original")]["artifact_ref"] != spec["artifact_ref"] or records[(spec["source_ref"], "original")]["byte_sha256"] != spec["byte_sha256"]:
        _fail("original_image_identity_mismatch", "extraction.sources")
    _source_aliases(extraction["sources"])
    wanted_witnesses = [{**deepcopy(w), "artifact_ref": records[(w["source_ref"], w["representation"])]["artifact_ref"]}
                        for w in _witnesses(selected)]
    if not _same(wanted_witnesses, extraction["authenticated_witnesses"]):
        _fail("gel_witness_binding_mismatch", "extraction.authenticated_witnesses")
    selected_pixels = {}
    def roi(saved, region):
        reason = image["unavailable_reason"] or _box_reason(region, spec["width"], spec["height"])
        if reason:
            expected = _summary(region, None, reason=reason)
        else:
            if not isinstance(saved, dict) or not isinstance(saved.get("pixel_bytes_base64"), str):
                _fail("saved_gel_pixels_required", "extraction.assignments")
            try:
                pixels = base64.b64decode(saved["pixel_bytes_base64"], validate=True)
            except (binascii.Error, ValueError) as error:
                raise ExperimentalContractError("saved_gel_pixels_invalid", "extraction.assignments") from error
            if len(pixels) != (region[2] - region[0]) * (region[3] - region[1]):
                _fail("saved_gel_pixel_count_mismatch", "extraction.assignments")
            width = region[2] - region[0]
            for offset, gray in enumerate(pixels):
                coordinate = (region[0] + offset % width, region[1] + offset // width)
                if coordinate in selected_pixels and selected_pixels[coordinate] != gray:
                    _fail("saved_gel_shared_pixel_conflict", "extraction.assignments")
                selected_pixels[coordinate] = gray
            expected = _summary(region, pixels)
        if not _same(saved, expected):
            _fail("saved_gel_pixel_summary_mismatch", "extraction.assignments")
        return expected
    _list(extraction["assignments"], "extraction.assignments")
    if len(extraction["assignments"]) != len(selected["roi_assignments"]):
        _fail("gel_assignment_roster_mismatch", "extraction.assignments")
    checked = []
    for saved, choice in zip(extraction["assignments"], selected["roi_assignments"]):
        _keys(saved, ("assignment_id", "lanes"), "extraction.assignments")
        if saved["assignment_id"] != choice["assignment_id"] or type(saved["lanes"]) is not list or len(saved["lanes"]) != len(choice["lanes"]):
            _fail("gel_assignment_roster_mismatch", "extraction.assignments")
        rows = []
        for row, nom in zip(saved["lanes"], choice["lanes"]):
            row_keys = ("lane_id", "background", "whole_lane", "whole_lane_corrected_signal", "bands")
            method = nom.get("background_method")
            if method is not None:
                row_keys += ("background_method",)
            _keys(row, row_keys, "extraction.lanes")
            if row["lane_id"] != nom["lane_id"] or type(row["bands"]) is not list or len(row["bands"]) != len(nom["bands"]):
                _fail("gel_lane_roster_mismatch", "extraction.lanes")
            background, whole = roi(row["background"], nom["background"]), roi(row["whole_lane"], nom["whole_lane"])
            bands = []
            for band, definition in zip(row["bands"], nom["bands"]):
                _keys(band, (*definition, "measurement", "corrected_signal"), "extraction.bands")
                if not _same({k: band[k] for k in definition}, definition):
                    _fail("gel_band_binding_mismatch", "extraction.bands")
                measurement = roi(band["measurement"], definition["region"])
                bands.append({**deepcopy(definition), "measurement": measurement,
                              "corrected_signal": _corrected(measurement, background, method)})
            checked_row = {"lane_id": nom["lane_id"], "background": background,
                "whole_lane": whole, "whole_lane_corrected_signal": _corrected(whole, background, method), "bands": bands}
            if method is not None:
                checked_row["background_method"] = method
            rows.append(checked_row)
        checked.append({"assignment_id": choice["assignment_id"], "lanes": rows})
    expected = _result(selected, deepcopy(image), deepcopy(extraction["sources"]), wanted_witnesses, checked)
    if not _same(expected, extraction):
        _fail("saved_gel_extraction_mismatch", "extraction")
    return deepcopy(extraction)


__all__ = ["VERSION", "EXTRACTION_VERSION", "VERSION_V2", "EXTRACTION_VERSION_V2",
           "CONTEXT_FIELDS", "SOURCE_KINDS", "CONTROL_ROLES",
           "gel_arguments_schema", "validate_gel_selection", "read_gel_inputs", "validate_gel_extraction"]
