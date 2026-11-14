"""Pure source-bound signed linear-bar rate operands for the A105 sheet.

The caller owns access and scientific nominations. Image quotations, terminal
identity and axis association remain episode interpretations, never OCR. This
module does not select evidence, calculate a score, infer sampling uncertainty,
register an operation or persist a source. Digitization bounds are conditional.
The caller must already nominate a linear-bar representation and its axis/object
meaning. Pillow supplies decoding and pixel operations; graph-type discovery,
gel lane/band quantification and automated text recognition are outside this API.
Other representation readers may populate the same experimental sheet.
"""
from __future__ import annotations

from copy import deepcopy
import errno
from fractions import Fraction
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
import warnings

from PIL import Image, UnidentifiedImageError

from .literature_assay_inputs import _Sources
from .literature_binding_visual_inputs import _Inputs, _box, _inside, _witness_shape
from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
from .literature_rate_native_inputs import _number, _unit, _plain_unit, _field_contexts

_VERSION = "controlled_response_rate_figure_selection_v1"
_RESULT_VERSION = "controlled_response_rate_figure_extraction_v1"
_COUNTER_VERSION = "controlled_response_bar_runs_v1"
_COUNT_FIELDS = ("roi", "rgb_min", "rgb_max", "minimum_row_fraction", "minimum_run_rows")
_REF = re.compile(r"(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)\Z")
_LITERAL = re.compile(r"[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\Z")
_BASE = {"amount_rate": "umol/min", "concentration_rate": "uM/min",
         "turnover_rate": "per_min", "specific_amount_rate": "umol/min/mg"}
_DECODE_CODES = {"unsupported_image_format", "unsupported_image_mode", "single_frame_required",
                 "unsupported_image_orientation", "image_decode_failed"}
# These are capability/lexical partials. Clipped tokens remain selection errors.
_NUMBER_PARTIALS = {"literal_source_number_required", "source_number_unit_role_mismatch",
    "postfix_source_approximation_unsupported", "plain_source_point_required",
    "composite_source_comparator_unsupported", "negated_source_comparator_unsupported",
    "interval_source_number_unsupported", "numerical_model_range",
    "approximate_source_number_unsupported", "lower_bound_source_number_unsupported",
    "postfix_source_bound_unsupported", "untyped_limit_source_number"}
_SCALE_PHRASES = {"linear scale": "linear", "linear axis": "linear",
    "logarithmic scale": "logarithmic", "logarithmic axis": "logarithmic",
    "log scale": "logarithmic", "log axis": "logarithmic",
    "nonlinear scale": "nonlinear", "nonlinear axis": "nonlinear",
    "non-linear scale": "nonlinear", "non-linear axis": "nonlinear"}
_MULTIPLIER = re.compile(r"(?:[×*⋅·]|\bx\s*)\s*10(?:\s*(?:\^|[+−-]?[0-9]|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺])|\b)", re.I)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _enum(value, choices, field):
    if not isinstance(value, str) or value not in choices:
        _fail("unsupported_value", field)


def _finite(value, field, code="finite_number_required"):
    if type(value) not in (int, float) or type(value) is float and not math.isfinite(value):
        _fail(code, field)
    return Fraction(value)


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _bounds(lower, upper):
    return {"lower": _rational(lower), "upper": _rational(upper)}


def _diagnostic(code, field, refs=(), domain="reader_capability"):
    return {"code": code, "field": field, "domain": domain,
            "source_refs": list(dict.fromkeys(refs))}


def _count_recipe(selection, width=None, height=None):
    _keys(selection, _COUNT_FIELDS, "selection")
    roi = selection["roi"]
    _keys(roi, ("left", "top", "right", "bottom"), "selection.roi")
    if any(type(value) is not int for value in roi.values()):
        _fail("malformed_count_roi", "selection.roi")
    if (roi["left"] < 0 or roi["top"] < 0 or roi["left"] >= roi["right"]
            or roi["top"] >= roi["bottom"] or width is not None and roi["right"] > width
            or height is not None and roi["bottom"] > height):
        _fail("invalid_count_roi_bounds", "selection.roi")
    for name in ("rgb_min", "rgb_max"):
        values = selection[name]
        if (not isinstance(values, list) or len(values) != 3
                or any(type(v) is not int or not 0 <= v <= 255 for v in values)):
            _fail("malformed_count_rgb_bounds", "selection." + name)
    if any(a > b for a, b in zip(selection["rgb_min"], selection["rgb_max"])):
        _fail("invalid_count_rgb_range", "selection.rgb_max")
    fraction = _finite(selection["minimum_row_fraction"], "selection.minimum_row_fraction",
                       "finite_count_row_fraction_required")
    if not 0 < fraction <= 1:
        _fail("invalid_count_row_fraction", "selection.minimum_row_fraction")
    if type(selection["minimum_run_rows"]) is not int or selection["minimum_run_rows"] < 1:
        _fail("positive_count_run_rows_required", "selection.minimum_run_rows")
    return fraction


def _count_bar_runs(*, rgb_bytes: bytes, width: int, height: int, selection):
    """Count every qualifying maximal run; no source or ordinate semantics."""
    if any(type(v) is not int or v < 1 for v in (width, height)):
        _fail("invalid_count_dimensions", "image_size")
    if type(rgb_bytes) is not bytes:
        _fail("immutable_rgb_bytes_required", "rgb_bytes")
    if len(rgb_bytes) != 3 * width * height:
        _fail("count_raster_length_mismatch", "rgb_bytes")
    fraction = _count_recipe(selection, width, height)
    roi = selection["roi"]
    low, high = selection["rgb_min"], selection["rgb_max"]
    runs, start = [], None
    for y in range(roi["top"], roi["bottom"]):
        matches = 0
        for x in range(roi["left"], roi["right"]):
            offset = 3 * (y * width + x)
            if all(low[c] <= rgb_bytes[offset + c] <= high[c] for c in range(3)):
                matches += 1
        qualifies = (matches * fraction.denominator >=
                     (roi["right"] - roi["left"]) * fraction.numerator)
        if qualifies and start is None:
            start = y
        if start is not None and (not qualifies or y == roi["bottom"] - 1):
            bottom = y + 1 if qualifies else y
            if bottom - start >= selection["minimum_run_rows"]:
                runs.append({"top": start, "bottom": bottom})
            start = None
    return {"version": _COUNTER_VERSION, "raster_rgb_sha256": _hash(rgb_bytes),
        "image_size": {"width": width, "height": height}, "selection": deepcopy(selection),
        "row_fraction_exact": _rational(fraction), "qualifying_runs": runs,
        "status": "no_run" if not runs else "single_run" if len(runs) == 1 else "multiple_runs"}


def _strict_decode(content, field):
    """Decode immutable authorized bytes; caller closes the returned native frame."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                fmt, mode, size = source.format, source.mode, source.size
                count = getattr(source, "n_frames", 1)
                if fmt not in ("PNG", "JPEG"):
                    _fail("unsupported_image_format", field)
                if mode not in ("RGB", "RGBA", "L"):
                    _fail("unsupported_image_mode", field)
                if count != 1:
                    _fail("single_frame_required", field)
                if fmt == "PNG" and not content.endswith(b"\x00\x00\x00\x00IEND\xaeB\x60\x82"):
                    _fail("image_decode_failed", field)
                source.verify()
            with Image.open(BytesIO(content)) as source:
                orientation = source.getexif().get(274, 1)
                if type(orientation) is not int or orientation != 1:
                    _fail("unsupported_image_orientation", field)
                source.load()
                if (source.size != size or source.mode != mode or source.format != fmt
                        or getattr(source, "n_frames", 1) != count):
                    _fail("image_decode_failed", field)
                return source.copy(), fmt, count
    except ExperimentalContractError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ExperimentalContractError("image_decode_failed", field) from error


def _witnesses(value):
    if isinstance(value, dict):
        if value.get("kind") in ("text", "image"):
            yield value
        else:
            for item in value.values():
                yield from _witnesses(item)
    elif isinstance(value, list):
        for item in value:
            yield from _witnesses(item)


def _distinct(values):
    return len({json.dumps(value, sort_keys=True, ensure_ascii=True) for value in values})


def _validate(arguments):
    _keys(arguments, ("version", "images", "measurement"), "arguments")
    _enum(arguments["version"], (_VERSION,), "version")
    if not isinstance(arguments["images"], list):
        _fail("list_required", "images")
    ids = set()
    for index, image in enumerate(arguments["images"]):
        field = f"images[{index}]"
        _keys(image, ("image_id", "source_ref", "original_source_ref", "mapping"), field)
        for name in ("image_id", "source_ref", "original_source_ref"):
            _text(image[name], field + "." + name)
        for name in ("source_ref", "original_source_ref"):
            if not _REF.fullmatch(image[name]):
                _fail("invalid_source_reference", field + "." + name)
        if image["image_id"] in ids:
            _fail("duplicate_image_id", field)
        ids.add(image["image_id"])
        if image["mapping"] is None:
            if image["source_ref"] != image["original_source_ref"]:
                _fail("unmapped_original_source_mismatch", field)
        else:
            _keys(image["mapping"], ("original_region", "colour_conversion"), field + ".mapping")
            _box(image["mapping"]["original_region"], field + ".mapping.original_region")
            _enum(image["mapping"]["colour_conversion"], ("preserve", "rgb"), field + ".mapping")
    measurement = arguments["measurement"]
    _keys(measurement, ("kind", "image_id", "bar_selection", "axis", "terminal_edge"), "measurement")
    _enum(measurement["kind"], ("linear_bar",), "measurement.kind")
    _text(measurement["image_id"], "measurement.image_id")
    if measurement["image_id"] not in ids:
        _fail("undeclared_image_id", "measurement.image_id")
    _enum(measurement["terminal_edge"], ("upper", "lower"), "measurement.terminal_edge")
    bar = measurement["bar_selection"]
    _keys(bar, (*_COUNT_FIELDS, "edge_tolerance_pixels"), "measurement.bar_selection")
    _count_recipe({name: bar[name] for name in _COUNT_FIELDS})
    if _finite(bar["edge_tolerance_pixels"], "edge_tolerance_pixels") < 0:
        _fail("nonnegative_tolerance_required", "edge_tolerance_pixels")
    axis = measurement["axis"]
    _keys(axis, ("first", "second", "unit", "scale"), "measurement.axis")
    literals = [("unit", axis["unit"])]
    for name in ("first", "second"):
        _keys(axis[name], ("pixel", "tick"), "axis." + name)
        if _finite(axis[name]["pixel"], "axis." + name + ".pixel") < 0:
            _fail("nonnegative_pixel_required", "axis." + name + ".pixel")
        literals.append((name, axis[name]["tick"]))
    for name, literal in literals:
        _keys(literal, ("status", "candidates", "fragments"), "axis." + name)
        _enum(literal["status"], ("exact", "ambiguous", "unreadable", "conflicting"), "axis." + name)
        for part in ("candidates", "fragments"):
            if not isinstance(literal[part], list):
                _fail("list_required", "axis." + name + "." + part)
        count = len(literal["candidates"])
        if literal["status"] == "exact" and (count != 1 or literal["fragments"]):
            _fail("one_exact_candidate_required", "axis." + name)
        if literal["status"] == "unreadable" and count:
            _fail("unreadable_has_no_candidate", "axis." + name)
        if literal["status"] in ("ambiguous", "conflicting") and _distinct(literal["candidates"]) < 2:
            _fail("distinct_transcription_candidates_required", "axis." + name)
    scale = axis["scale"]
    _keys(scale, ("status", "kind", "basis", "witnesses"), "axis.scale")
    _enum(scale["status"], ("known", "unknown", "conflicting"), "axis.scale.status")
    if not isinstance(scale["witnesses"], list):
        _fail("list_required", "axis.scale.witnesses")
    if scale["status"] == "known":
        _enum(scale["kind"], ("linear", "logarithmic", "nonlinear"), "axis.scale.kind")
        _enum(scale["basis"], ("source_text_literal", "image_episode_interpretation"), "axis.scale.basis")
        if not scale["witnesses"]:
            _fail("interpretation_witness_required", "axis.scale")
        if scale["basis"] == "source_text_literal" and any(w.get("kind") != "text" for w in scale["witnesses"] if isinstance(w, dict)):
            _fail("text_scale_witness_required", "axis.scale")
        if scale["basis"] == "image_episode_interpretation" and not any(isinstance(w, dict) and w.get("kind") == "image" for w in scale["witnesses"]):
            _fail("image_scale_witness_required", "axis.scale")
    elif scale["kind"] is not None or scale["basis"] != "unresolved":
        _fail("unresolved_scale_contract_required", "axis.scale")
    if scale["status"] == "conflicting" and _distinct(scale["witnesses"]) < 2:
        _fail("distinct_scale_witnesses_required", "axis.scale")
    for index, witness in enumerate(_witnesses(measurement)):
        field = f"measurement.witnesses[{index}]"
        _witness_shape(witness, field)
        if witness["kind"] == "image" and witness["image_id"] not in ids:
            _fail("undeclared_image_id", field)
        if witness["kind"] == "text" and not _REF.fullmatch(witness["source_ref"]):
            _fail("invalid_source_reference", field)
    # Walk the declared witness lists themselves: unknown kinds cannot evade discovery.
    nominated = [w for _, lit in literals for p in ("candidates", "fragments") for w in lit[p]] + scale["witnesses"]
    for w in nominated:
        _witness_shape(w, "witness")


def _unavailable(error):
    return (isinstance(error, FileNotFoundError) and error.errno == errno.ENOENT
            or isinstance(error, OSError) and not isinstance(error, PermissionError)
            and error.errno in (errno.EIO, errno.ETIMEDOUT))


class _Context:
    def __init__(self, arguments, read_source):
        if not callable(read_source):
            _fail("source_reader_required", "read_source")
        closure = []
        for image in arguments["images"]:
            closure.extend([(image["source_ref"], "original"), (image["original_source_ref"], "original")])
        closure.extend((w["source_ref"], w["representation"]) for w in _witnesses(arguments["measurement"]) if w["kind"] == "text")
        self.cache, self.source_records, self.frames = {}, [], []
        # Actual callback errors are outside every frozen helper's broad catch.
        for key in dict.fromkeys(closure):
            try:
                source = read_source(*key)
            except OSError as error:
                if not _unavailable(error):
                    raise
                self.cache[key] = error
                source = None
            if source is not None:
                _keys(source, ("artifact_ref", "content"), "source_result")
                _text(source["artifact_ref"], "source_result.artifact_ref")
                if type(source["content"]) is not bytes:
                    _fail("source_bytes_required", "source_result.content")
                self.cache[key] = dict(source)
            elif key not in self.cache:
                _fail("closed_fields_required", "source_result")
            self.source_records.append({"source_ref": key[0], "representation": key[1],
                "artifact_ref": source["artifact_ref"] if source else None,
                "byte_sha256": _hash(source["content"]) if source else None,
                "state": "available" if source else "unavailable", "diagnostics": [] if source else [
                    _diagnostic("graph_image_unavailable", "sources", [key[0]], "dependency")]})
        self.sources = _Sources(self.read)
        self.inputs = _Inputs(self.read)
        try:
            for reference in dict.fromkeys(ref for spec in arguments["images"] for ref in (spec["source_ref"], spec["original_source_ref"])):
                source = self.cache[(reference, "original")]
                if isinstance(source, Exception):
                    self.inputs.decoded[reference] = source
                    continue
                try:
                    frame, fmt, count = _strict_decode(source["content"], reference)
                except ExperimentalContractError as error:
                    if error.code not in _DECODE_CODES:
                        raise
                    self.inputs.decoded[reference] = error
                else:
                    self.frames.append(frame)
                    self.inputs.decoded[reference] = (source, frame, fmt, count)
            self.images = []
            for spec in arguments["images"]:
                image = self.inputs.image(spec)
                if image["error"] and image["error"]["code"] not in _DECODE_CODES | {"source_read_failed"}:
                    _fail(image["error"]["code"], image["error"]["field"])
                # Decode failure never erases independently authenticated byte identities.
                for ref_field, art_field, hash_field in (("source_ref", "artifact_ref", "byte_sha256"),
                        ("original_source_ref", "original_artifact_ref", "original_byte_sha256")):
                    record = self.cache[(spec[ref_field], "original")]
                    if not isinstance(record, Exception):
                        image[art_field], image[hash_field] = record["artifact_ref"], _hash(record["content"])
                self.inputs.images[spec["image_id"]] = image
                self.images.append(image)
        except BaseException:
            self.close()
            raise

    def close(self):
        for frame in self.frames:
            frame.close()
        self.frames.clear()

    def read(self, reference, representation):
        record = self.cache[(reference, representation)]  # no fallback / external lookup
        if isinstance(record, Exception):
            raise record
        return dict(record)

    def image_locator(self, image_id, region):
        location = self.inputs.location(image_id, region)
        image = self.inputs.images[image_id]
        return {"kind": "image", "original_source_ref": location["original_source_ref"],
            "original_artifact_ref": location["original_artifact_ref"],
            "original_byte_sha256": image["original_byte_sha256"], "region": location["image_region"]}

    def witness(self, selected, field):
        result = {"selection": deepcopy(selected), "artifact_ref": None, "byte_sha256": None,
            "canonical_locator": None, "authentication": "unavailable",
            "attribution": "literal_source_record" if selected["kind"] == "text" else "investigating_episode_interpretation",
            "diagnostics": []}
        if selected["kind"] == "text":
            record = self.cache[(selected["source_ref"], selected["representation"])]
            if isinstance(record, Exception):
                result["diagnostics"].append(_diagnostic("graph_image_unavailable", field, [selected["source_ref"]], "dependency"))
                return result
            native = {k: v for k, v in selected.items() if k != "kind"}
            self.sources.witness(native, field)  # authentication errors propagate
            digest = _hash(record["content"])
            result.update(artifact_ref=record["artifact_ref"], byte_sha256=digest,
                authentication="exact_utf8_byte_span", canonical_locator={"kind": "text",
                "source_ref": selected["source_ref"], "artifact_ref": record["artifact_ref"],
                "byte_sha256": digest, "start": selected["start"], "end": selected["end"]})
        else:
            image = self.inputs.images[selected["image_id"]]
            if image["error"]:
                code = "graph_image_unavailable" if image["error"]["code"] == "source_read_failed" else "graph_image_unsupported"
                result["diagnostics"].append(_diagnostic(code, field, [image["source_ref"]], "dependency"))
                return result
            result.update(artifact_ref=image["artifact_ref"], byte_sha256=image["byte_sha256"],
                authentication="image_bytes_and_geometry_only",
                canonical_locator=self.image_locator(selected["image_id"], selected["region"]))
            result["diagnostics"].append(_diagnostic("graph_image_label_interpretation", field,
                [image["source_ref"]], "source_interpretation"))
        return result


def _native_witness(witness):
    return {k: v for k, v in witness.items() if k != "kind"}


def _literal(context, selected, field, *, unit=False):
    candidates = [context.witness(w, field + ".candidates") for w in selected["candidates"]]
    fragments = [context.witness(w, field + ".fragments") for w in selected["fragments"]]
    diagnostics = [d for record in candidates + fragments for d in record["diagnostics"]]
    result = {"selection": deepcopy(selected), "candidates": candidates, "fragments": fragments,
        "raw_literal": None, "exact_value": None, "qualification": "unresolved",
        "status": selected["status"] if selected["status"] != "exact" else "unsupported", "diagnostics": diagnostics}
    if any(w["authentication"] == "unavailable" for w in candidates + fragments):
        result["status"] = "dependency_unavailable"
    if selected["status"] != "exact":
        diagnostics.append(_diagnostic("graph_" + ("unit" if unit else "tick") + "_" + selected["status"], field))
        return result
    candidate = candidates[0]
    if candidate["authentication"] == "unavailable":
        result["status"] = "dependency_unavailable"
        return result
    w = candidate["selection"]
    result.update(raw_literal=w["quote"], qualification="source_text_literal" if w["kind"] == "text" else "episode_image_transcription")
    if unit:
        result["status"] = "parsed"
        return result
    token = w["quote"].strip()
    if not _LITERAL.fullmatch(token):
        diagnostics.append(_diagnostic("graph_tick_literal_unsupported", field))
        return result
    if w["kind"] == "text":
        start = len(w["quote"]) - len(w["quote"].lstrip())
        try:
            parsed = _number({"witness": _native_witness(w), "number_start": start,
                "number_end": start + len(token)}, context.sources, "condition")
        except ExperimentalContractError as error:
            if error.code not in _NUMBER_PARTIALS:
                raise
            diagnostics.append(_diagnostic("graph_tick_literal_numeric_range" if error.code == "numerical_model_range" else "graph_tick_literal_unsupported", field))
            return result
        if parsed["relation"] != "point" or parsed["approximate"]:
            diagnostics.append(_diagnostic("graph_tick_literal_unsupported", field))
            return result
    exact = Fraction(token.replace("−", "-"))
    result.update(exact_value=_rational(exact), status="parsed")
    try:
        projected = _finite_float(exact)
    except OverflowError:
        if w["kind"] == "text":
            diagnostics.append(_diagnostic("graph_tick_literal_numeric_range", field))
            result.update(exact_value=None, status="unsupported")
    else:
        if Fraction(str(projected)) != exact:
            diagnostics.append(_diagnostic("graph_tick_projection_rounded", field))
    return result


def _scale(context, selected):
    witnesses = [context.witness(w, "axis.scale.witnesses") for w in selected["witnesses"]]
    diagnostics = [d for w in witnesses for d in w["diagnostics"]]
    result = {"selection": deepcopy(selected), "witnesses": witnesses,
        "effective_kind": selected["kind"] or selected["status"], "support": "unresolved", "diagnostics": diagnostics}
    if selected["status"] != "known":
        diagnostics.append(_diagnostic("graph_scale_" + selected["status"], "axis.scale", domain="source_interpretation"))
        return result
    diagnostics.append(_diagnostic("graph_axis_scale_interpretation", "axis.scale", domain="source_interpretation"))
    if any(w["authentication"] == "unavailable" for w in witnesses):
        result.update(effective_kind="unknown", support="unavailable")
        return result
    if selected["basis"] == "image_episode_interpretation":
        result["support"] = "episode_image_interpretation"
    else:
        for w in selected["witnesses"]:
            prefix, suffix = _field_contexts(context.sources, _native_witness(w), 0, len(w["quote"]))
            phrase = w["quote"].strip().lower()
            if (_SCALE_PHRASES.get(phrase) != selected["kind"]
                    or re.search(r"[\w-]$", prefix) or re.match(r"[\w-]", suffix)
                    or re.search(r"\b(?:not|non|no|without)(?:\s+(?:a|an|the|necessarily|strictly|entirely))*\s*$", prefix, re.I)
                    or re.match(r"\s*(?:is\s+)?(?:not|false)\b", suffix, re.I)):
                diagnostics.append(_diagnostic("graph_scale_literal_unsupported", "axis.scale"))
                result.update(effective_kind="unknown", support="unresolved")
                return result
        result["support"] = "literal_source_text"
    if selected["kind"] != "linear":
        diagnostics.append(_diagnostic("graph_scale_unsupported", "axis.scale"))
    return result


def _graph_unit(context, literal):
    result = {"selection": deepcopy(literal["selection"]), "witness": None,
        "raw_unit": literal["raw_literal"], "canonical_unit": None, "exact_scale": None,
        "native_registry_unit": None, "definition_witnesses": None,
        "status": "unknown", "diagnostics": []}
    if literal["status"] != "parsed":
        result["status"] = "dependency_unavailable" if literal["status"] == "dependency_unavailable" else "unknown"
        result["diagnostics"].append(_diagnostic("graph_unit_unknown", "axis.unit"))
        return result
    w = literal["candidates"][0]["selection"]
    result["witness"] = deepcopy(literal["candidates"][0])
    raw = w["quote"]
    if w["kind"] == "text":
        prefix, suffix = _field_contexts(context.sources, _native_witness(w), 0, len(raw))
        if _MULTIPLIER.search(prefix + raw + suffix):
            result["status"] = "unsupported"
            result["diagnostics"].append(_diagnostic("graph_axis_multiplier_unsupported", "axis.unit"))
            return result
        _unit(_native_witness(w), context.sources, None)  # boundary errors propagate
    elif _MULTIPLIER.search(raw):
        result["status"] = "unsupported"
        result["diagnostics"].append(_diagnostic("graph_axis_multiplier_unsupported", "axis.unit"))
        return result
    parsed = _plain_unit(raw)
    if parsed is None:
        result["status"] = "unsupported"
        code = "graph_unit_defined_bridge_unselected" if re.fullmatch(r"\s*U\s*/\s*mg\s*", raw) else "graph_unit_unsupported"
        result["diagnostics"].append(_diagnostic(code, "axis.unit"))
        return result
    canonical, scale = parsed
    native = next(name for name, (dimension, factor) in RATE_UNITS.items()
                  if _BASE[dimension] == canonical and Fraction(str(factor)) == scale)
    result.update(canonical_unit=canonical, exact_scale=_rational(scale), native_registry_unit=native, status="supported")
    return result


def _finite_float(exact):
    value = float(exact)
    if not math.isfinite(value) or value == 0 and exact != 0:
        raise OverflowError
    return value


def _outward(exact, direction):
    value = float(exact)
    if not math.isfinite(value):
        raise OverflowError
    while (Fraction(str(value)) > exact if direction < 0 else Fraction(str(value)) < exact):
        value = math.nextafter(value, -math.inf if direction < 0 else math.inf)
        if not math.isfinite(value):
            raise OverflowError
    return value


def _pixels(context, selected, literals, scale, unit):
    spec = next(s for s in context.images if s["image_id"] == selected["image_id"])
    recipe, edge = selected["bar_selection"], selected["terminal_edge"]
    diagnostics = []
    result = {"version": "controlled_response_rate_pixels_v1", "status": "unsupported",
        "image_id": spec["image_id"], "image_sha256": spec["byte_sha256"],
        "original_image_sha256": spec["original_byte_sha256"], "mapped_roi": None,
        "recipe": deepcopy(recipe), "terminal_edge": edge, "image_size": None,
        "qualifying_runs": [], "pixel_edge": None, "axis": None, "native_ordinate": None,
        "native_bounds": None, "bound_kind": "conditional_digitization_not_confidence_interval",
        "counter_version": _COUNTER_VERSION, "counter_module_sha256": _hash(Path(__file__).read_bytes()),
        "diagnostics": diagnostics}
    if spec["error"]:
        missing = any(isinstance(context.cache[(spec[name], "original")], Exception)
                      for name in ("source_ref", "original_source_ref"))
        result["status"] = "dependency_unavailable" if missing else "unsupported"
        diagnostics.append(_diagnostic("graph_image_unavailable" if missing else "graph_image_unsupported", "measurement.image_id", [spec["source_ref"]], "dependency"))
        return result
    width, height = spec["width"], spec["height"]
    result["image_size"] = {"width": width, "height": height}
    for name in ("first", "second"):
        if not 0 <= Fraction(selected["axis"][name]["pixel"]) < height:
            _fail("calibration_outside_image", "axis." + name + ".pixel")
    count_selection = {k: recipe[k] for k in _COUNT_FIELDS}
    _count_recipe(count_selection, width, height)
    roi = recipe["roi"]
    region = [roi[k] for k in ("left", "top", "right", "bottom")]
    result["mapped_roi"] = context.image_locator(spec["image_id"], region)
    selected_frame = context.inputs.decoded[spec["source_ref"]][1]
    original_frame = context.inputs.decoded[spec["original_source_ref"]][1]
    # Frozen geometry used exactly these strict frames; do not decode a substitute.
    for frame, box in ((selected_frame, region), (original_frame, result["mapped_roi"]["region"])):
        if frame.mode == "RGBA":
            with frame.crop(tuple(box)) as cropped:
                with cropped.getchannel("A") as alpha:
                    if alpha.getextrema() != (255, 255):
                        diagnostics.append(_diagnostic("graph_nonopaque_roi", "measurement.bar_selection.roi", [spec["source_ref"], spec["original_source_ref"]]))
                        return result
    with selected_frame.convert("RGB") as rgb:
        count = _count_bar_runs(rgb_bytes=rgb.tobytes(), width=width, height=height, selection=count_selection)
    result["qualifying_runs"] = count["qualifying_runs"]
    if len(count["qualifying_runs"]) != 1:
        result["status"] = "ambiguous" if count["qualifying_runs"] else "unreadable"
        diagnostics.append(_diagnostic("graph_ambiguous_bar_runs" if count["qualifying_runs"] else "graph_no_bar_pixels", "measurement.bar_selection"))
        return result
    run = count["qualifying_runs"][0]
    terminal_clipped = run["top"] == roi["top"] if edge == "upper" else run["bottom"] == roi["bottom"]
    if terminal_clipped:
        result["status"] = "unreadable"
        diagnostics.append(_diagnostic("graph_terminal_edge_clipped", "measurement.terminal_edge"))
        return result
    opposite_clipped = run["bottom"] == roi["bottom"] if edge == "upper" else run["top"] == roi["top"]
    if opposite_clipped:
        diagnostics.append(_diagnostic("graph_opposite_edge_clipped", "measurement.terminal_edge", domain="source_interpretation"))
    tolerance = Fraction(recipe["edge_tolerance_pixels"])
    if edge == "upper":
        nominal, lower, upper = Fraction(run["top"]) + Fraction(1, 2), Fraction(run["top"]) - tolerance, Fraction(run["top"] + 1) + tolerance
    else:
        nominal, lower, upper = Fraction(run["bottom"]) - Fraction(1, 2), Fraction(run["bottom"] - 1) - tolerance, Fraction(run["bottom"]) + tolerance
    result["pixel_edge"] = {"terminal_edge": edge, "nominal": _rational(nominal), "bounds": _bounds(lower, upper)}
    if not 0 <= lower <= upper < height:
        diagnostics.append(_diagnostic("graph_pixel_bounds_outside_image", "measurement.bar_selection.edge_tolerance_pixels"))
        return result
    if (scale["effective_kind"] != "linear" or scale["support"] not in ("literal_source_text", "episode_image_interpretation")
            or unit["status"] != "supported" or any(literals[n]["status"] != "parsed" for n in ("first", "second"))):
        return result
    p1, p2 = (Fraction(selected["axis"][n]["pixel"]) for n in ("first", "second"))
    v1, v2 = (_fraction(literals[n]["exact_value"]) for n in ("first", "second"))
    if p1 == p2 or v1 == v2:
        diagnostics.append(_diagnostic("graph_axis_degenerate", "measurement.axis"))
        return result
    slope = (v2 - v1) / (p2 - p1)
    result["axis"] = {"first_pixel": _rational(p1), "second_pixel": _rational(p2),
        "first_value": _rational(v1), "second_value": _rational(v2), "unit": unit["native_registry_unit"], "slope": _rational(slope)}
    ordinate = lambda pixel: v1 + (pixel - p1) * slope
    lo, hi = sorted((ordinate(lower), ordinate(upper)))
    result.update(status="measured", native_ordinate=_rational(ordinate(nominal)), native_bounds=_bounds(lo, hi))
    diagnostics.append(_diagnostic("graph_conditional_digitization", "measurement", domain="source_interpretation"))
    return result


def read_controlled_response_rate_figure(arguments, *, read_source):
    """Authenticate the full closure and return signed conditional rate operands.

    Malformed requests, source authentication/authorization and unexpected caller
    failures propagate. Only declared ENOENT/EIO/ETIMEDOUT I/O is unavailable.
    Independent witnesses and pixels survive unsupported scientific calibration.
    The request is an episode's nominated linear bar, axis and terminal edge;
    the reader supplies neither figure classification nor gel/OCR extraction.
    """
    _validate(arguments)
    arguments = deepcopy(arguments)
    context = _Context(arguments, read_source)
    try:
        selected = arguments["measurement"]
        axis = selected["axis"]
        literals = {name: _literal(context, axis[name]["tick"], "axis." + name) for name in ("first", "second")}
        literals["unit"] = _literal(context, axis["unit"], "axis.unit", unit=True)
        scale = _scale(context, axis["scale"])
        unit = _graph_unit(context, literals["unit"])
        pixels = _pixels(context, selected, literals, scale, unit)
        diagnostics = [d for item in [*literals.values(), scale, unit, pixels] for d in item["diagnostics"]]
        states = []
        if any(r["state"] == "unavailable" for r in context.source_records) or any(w["authentication"] == "unavailable" for w in scale["witnesses"]):
            states.append("dependency_unavailable")
        states.extend(lit["status"] for lit in literals.values() if lit["status"] != "parsed")
        if axis["scale"]["status"] == "conflicting":
            states.append("conflicting")
        states.append({"measured": "graph_digitized"}.get(pixels["status"], pixels["status"]))
        status = next(s for s in ("dependency_unavailable", "conflicting", "ambiguous", "unreadable", "unsupported", "graph_digitized") if s in states)
        projection = {"value": None, "threshold": None, "relation": "none", "approximate": True,
            "unit": unit["native_registry_unit"], "status": "missing" if status in ("dependency_unavailable", "unreadable") else status,
            "origin": "graph_derived", "digitization_interval": None}
        display = {"value": None, "threshold": None, "unit": unit["canonical_unit"], "relation": "none", "approximate": True, "diagnostics": []}
        identity = None
        if status == "graph_digitized":
            exact = _fraction(pixels["native_ordinate"])
            lo, hi = (_fraction(pixels["native_bounds"][s]) for s in ("lower", "upper"))
            try:
                nominal, lower, upper = _finite_float(exact), _outward(lo, -1), _outward(hi, 1)
            except OverflowError:
                status = "unsupported"
                projection["status"] = "unsupported"
                diagnostics.append(_diagnostic("graph_numerical_model_range", "operand_projection"))
            else:
                projection.update(value=nominal, relation="interval", status="point",
                    digitization_interval={"lower": min(lower, nominal), "upper": max(upper, nominal)})
                if any(Fraction(str(v)) != q for v, q in ((nominal, exact), (lower, lo), (upper, hi))):
                    diagnostics.append(_diagnostic("graph_ordinate_projection_rounded", "operand_projection"))
                identity_record = {"version": _RESULT_VERSION, "selection": arguments, "images": context.images,
                    "literals": literals, "scale": scale, "unit": unit, "pixels": pixels}
                identity = "controlled_response_graph_" + _hash(json.dumps(identity_record, sort_keys=True, ensure_ascii=True, allow_nan=False).encode())
                try:
                    display["value"] = _finite_float(exact * _fraction(unit["exact_scale"]))
                except OverflowError:
                    d = _diagnostic("graph_canonical_display_range", "measurement.canonical_display")
                    display["diagnostics"].append(d)
                    diagnostics.append(d)
                else:
                    display["relation"] = "eq"
        fragments = [w for lit in literals.values() for w in lit["fragments"]]
        witnesses = [w for lit in literals.values() for part in ("candidates", "fragments") for w in lit[part]] + scale["witnesses"]
        measurement = {"selection": deepcopy(selected), "candidates": [], "fragments": fragments,
            "unit": unit, "graph_witnesses": witnesses, "reading_status": status,
            "source_observation_id": identity, "canonical_display": display,
            "pixel_result": pixels, "diagnostics": deepcopy(diagnostics)}
        return {"version": _RESULT_VERSION, "selection": arguments, "sources": context.source_records,
            "images": context.images, "axis_scale": scale, "axis_literals": literals,
            "measurement": measurement, "operand_projection": projection, "diagnostics": diagnostics}
    finally:
        context.close()


__all__ = ["read_controlled_response_rate_figure"]
