"""Source-image binding cells nominated by an investigating episode.

This is a pure, one-off reader, not OCR or a model invocation. Byte/geometry
authentication does not verify nominated image text or scientific interpretation.
The caller authorizes received sources, scope and original-document ancestry.
Partial transcriptions must not be passed unqualified to the old table route.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
import json
import re

from PIL import Image, __version__ as PILLOW_VERSION

# Reuse the literal grammar without inventing a retained table source receipt.
from .literature_binding_reader import _measurement, _SCALES
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "binding_visual_inputs_v1"
OUTPUT_VERSION = "binding_visual_extraction_v1"
STATES = ("exact", "ambiguous", "unreadable", "conflicting")
BASES = ("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown")
KINDS = ("ic50", "reported_hill_kd")
ATTRIBUTION = "investigating_episode_interpretation"


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _enum(value, choices, field):
    if not isinstance(value, str) or value not in choices:
        _fail("unsupported_value", field)


def _box(value, field):
    if (not isinstance(value, list) or len(value) != 4
            or any(type(item) is not int or item < 0 for item in value)
            or value[0] >= value[2] or value[1] >= value[3]):
        _fail("nonempty_integer_image_region_required", field)


def _list(value, field):
    if not isinstance(value, list):
        _fail("list_required", field)


def _witness_shape(value, field, *, image_only=False):
    if not isinstance(value, dict):
        _fail("closed_fields_required", field)
    kind = value.get("kind")
    if kind == "image":
        _keys(value, ("kind", "image_id", "region", "quote"), field)
        _text(value["image_id"], field + ".image_id")
        _box(value["region"], field + ".region")
    elif kind == "text" and not image_only:
        _keys(value, ("kind", "source_ref", "representation", "start", "end", "quote"), field)
        _text(value["source_ref"], field + ".source_ref")
        _enum(value["representation"], ("original", "text"), field + ".representation")
        if (type(value["start"]) is not int or type(value["end"]) is not int
                or not 0 <= value["start"] < value["end"]):
            _fail("nonempty_integer_source_span_required", field)
    else:
        _fail("unsupported_witness_kind", field)
    _text(value["quote"], field + ".quote")


def _interpretation_shape(value, field, *, choices=None, allow_empty=False):
    _keys(value, ("value", "witnesses"), field)
    if choices is None:
        _text(value["value"], field + ".value")
    else:
        _enum(value["value"], choices, field + ".value")
    _list(value["witnesses"], field + ".witnesses")
    if not value["witnesses"] and not allow_empty:
        _fail("interpretation_witness_required", field + ".witnesses")
    for index, witness in enumerate(value["witnesses"]):
        _witness_shape(witness, f"{field}.witnesses[{index}]")


def _transcription_shape(value, field):
    _keys(value, ("status", "candidates", "fragments"), field)
    _enum(value["status"], STATES, field + ".status")
    for part in ("candidates", "fragments"):
        _list(value[part], field + "." + part)
        for index, witness in enumerate(value[part]):
            _witness_shape(witness, f"{field}.{part}[{index}]", image_only=True)
    count = len(value["candidates"])
    if value["status"] == "exact" and (count != 1 or value["fragments"]):
        _fail("one_exact_candidate_required", field)
    if value["status"] == "unreadable" and count:
        _fail("unreadable_has_no_candidate", field)
    if value["status"] in ("ambiguous", "conflicting"):
        if len({witness["quote"] for witness in value["candidates"]}) < 2:
            _fail("distinct_transcription_candidates_required", field)


def _validate(arguments):
    _keys(arguments, ("version", "table_id", "images", "context", "parameter_kind", "unit",
                      "uncertainty_basis", "minimum_experiment_count", "cells"), "arguments")
    _enum(arguments["version"], (VERSION,), "version")
    _text(arguments["table_id"], "table_id")
    _list(arguments["images"], "images")
    image_ids = set()
    for index, image in enumerate(arguments["images"]):
        field = f"images[{index}]"
        _keys(image, ("image_id", "source_ref", "original_source_ref", "mapping"), field)
        for name in ("image_id", "source_ref", "original_source_ref"):
            _text(image[name], field + "." + name)
        if image["image_id"] in image_ids:
            _fail("duplicate_image_id", field)
        image_ids.add(image["image_id"])
        if image["mapping"] is None:
            if image["source_ref"] != image["original_source_ref"]:
                _fail("unmapped_original_source_mismatch", field)
        else:
            _keys(image["mapping"], ("original_region", "colour_conversion"), field + ".mapping")
            _box(image["mapping"]["original_region"], field + ".mapping.original_region")
            _enum(image["mapping"]["colour_conversion"], ("preserve", "rgb"),
                  field + ".mapping.colour_conversion")
    _keys(arguments["context"], ("subject", "state", "experiment"), "context")
    for name, value in arguments["context"].items():
        _interpretation_shape(value, "context." + name)
    _interpretation_shape(arguments["parameter_kind"], "parameter_kind", choices=KINDS)
    basis = arguments["uncertainty_basis"]
    _interpretation_shape(basis, "uncertainty_basis", choices=BASES,
                          allow_empty=isinstance(basis, dict) and basis.get("value") == "unknown")
    _transcription_shape(arguments["unit"], "unit")
    count = arguments["minimum_experiment_count"]
    if count is not None:
        _keys(count, ("literal", "witness"), "minimum_experiment_count")
        _text(count["literal"], "minimum_experiment_count.literal")
        if not re.fullmatch(r"[0-9]+", count["literal"]) or not count["literal"].strip("0"):
            _fail("positive_integer_literal_required", "minimum_experiment_count.literal")
        _witness_shape(count["witness"], "minimum_experiment_count.witness")
    _list(arguments["cells"], "cells")
    cell_ids = set()
    for index, cell in enumerate(arguments["cells"]):
        field = f"cells[{index}]"
        _keys(cell, ("cell_id", "image_id", "cell_region", "ligand", "expression"), field)
        _text(cell["cell_id"], field + ".cell_id")
        _text(cell["image_id"], field + ".image_id")
        if cell["cell_id"] in cell_ids:
            _fail("duplicate_cell_id", field)
        cell_ids.add(cell["cell_id"])
        _box(cell["cell_region"], field + ".cell_region")
        _interpretation_shape(cell["ligand"], field + ".ligand")
        _transcription_shape(cell["expression"], field + ".expression")
    # Bad references are malformed arguments, unlike unavailable source bytes.
    def references(value, field):
        if isinstance(value, dict):
            if "image_id" in value and value["image_id"] not in image_ids:
                _fail("undeclared_image_id", field + ".image_id")
            for key, item in value.items():
                references(item, field + "." + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                references(item, f"{field}[{index}]")
    references(arguments, "arguments")


def binding_visual_arguments_schema():
    """Closed structural schema; additional relationships are checked by reader."""
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}
    text = {"type": "string", "minLength": 1}
    box = {"type": "array", "minItems": 4, "maxItems": 4,
           "items": {"type": "integer", "minimum": 0}}
    iw = obj({"kind": {"const": "image"}, "image_id": text, "region": box, "quote": text})
    tw = obj({"kind": {"const": "text"}, "source_ref": text,
              "representation": {"enum": ["original", "text"]},
              "start": {"type": "integer", "minimum": 0},
              "end": {"type": "integer", "minimum": 1}, "quote": text})
    witness = {"oneOf": [iw, tw]}
    def interpretation(values=None):
        return obj({"value": {"enum": list(values)} if values else text,
                    "witnesses": {"type": "array", "items": witness}})
    transcription = obj({"status": {"enum": list(STATES)},
                         "candidates": {"type": "array", "items": iw},
                         "fragments": {"type": "array", "items": iw}})
    mapping = obj({"original_region": box, "colour_conversion": {"enum": ["preserve", "rgb"]}})
    image = obj({"image_id": text, "source_ref": text, "original_source_ref": text,
                 "mapping": {"anyOf": [mapping, {"type": "null"}]}})
    cell = obj({"cell_id": text, "image_id": text, "cell_region": box,
                "ligand": interpretation(), "expression": transcription})
    result = obj({"version": {"const": VERSION}, "table_id": text,
                  "images": {"type": "array", "items": image},
                  "context": obj({name: interpretation() for name in ("subject", "state", "experiment")}),
                  "parameter_kind": interpretation(KINDS), "unit": transcription,
                  "uncertainty_basis": interpretation(BASES),
                  "minimum_experiment_count": {"anyOf": [obj({"literal": text, "witness": witness}),
                                                           {"type": "null"}]},
                  "cells": {"type": "array", "items": cell}})
    return deepcopy(result)


def _error(error, field):
    return {"code": getattr(error, "code", "source_read_failed"),
            "field": getattr(error, "field", field)}


def _inside(inner, outer):
    return (outer[0] <= inner[0] < inner[2] <= outer[2]
            and outer[1] <= inner[1] < inner[3] <= outer[3])


def _hash(value):
    return hashlib.sha256(value).hexdigest()


class _Inputs:
    def __init__(self, read_source):
        self.read_source = read_source
        self.sources = {}
        self.decoded = {}
        self.references = []
        self.images = {}

    def source(self, reference, representation="original"):
        key = (reference, representation)
        if key not in self.sources:
            if reference not in self.references:
                self.references.append(reference)
            try:
                result = self.read_source(reference, representation)
                _keys(result, ("artifact_ref", "content"), "source_result")
                _text(result["artifact_ref"], "source_result.artifact_ref")
                if type(result["content"]) is not bytes:
                    _fail("source_bytes_required", "source_result.content")
                self.sources[key] = dict(result)
            except Exception as error:
                # Callback failures are data failures on this dependency only.
                self.sources[key] = error
        result = self.sources[key]
        if isinstance(result, Exception):
            raise result
        return result

    def decode(self, reference):
        if reference not in self.decoded:
            try:
                source = self.source(reference)
                try:
                    with Image.open(BytesIO(source["content"])) as image:
                        fmt, count = image.format, getattr(image, "n_frames", 1)
                        if fmt not in ("PNG", "JPEG"):
                            _fail("unsupported_image_format", reference)
                        if count != 1:
                            _fail("single_frame_required", reference)
                        image.seek(0)
                        image.load()
                        if image.mode not in ("L", "RGB", "RGBA"):
                            _fail("unsupported_image_mode", reference)
                        frame = image.copy()
                except ExperimentalContractError:
                    raise
                except (OSError, ValueError, SyntaxError) as error:
                    raise ExperimentalContractError("image_decode_failed", reference) from error
                self.decoded[reference] = (source, frame, fmt, count)
            except Exception as error:
                self.decoded[reference] = error
        result = self.decoded[reference]
        if isinstance(result, Exception):
            raise result
        return result

    def image(self, spec):
        result = {"image_id": spec["image_id"], "source_ref": spec["source_ref"],
                  "artifact_ref": None, "byte_sha256": None,
                  "original_source_ref": spec["original_source_ref"],
                  "original_artifact_ref": None, "original_byte_sha256": None,
                  "actual_format": None, "actual_mode": None, "width": None, "height": None,
                  "frame_count": None, "mapping": deepcopy(spec["mapping"]),
                  "pillow_version": PILLOW_VERSION, "error": None}
        try:
            source, frame, fmt, count = self.decode(spec["source_ref"])
            result.update(artifact_ref=source["artifact_ref"], byte_sha256=_hash(source["content"]),
                          actual_format=fmt, actual_mode=frame.mode, width=frame.width,
                          height=frame.height, frame_count=count)
            original, original_frame, _, _ = self.decode(spec["original_source_ref"])
            result.update(original_artifact_ref=original["artifact_ref"],
                          original_byte_sha256=_hash(original["content"]))
            if spec["mapping"] is not None:
                region = spec["mapping"]["original_region"]
                if not _inside(region, [0, 0, original_frame.width, original_frame.height]):
                    _fail("image_region_out_of_bounds", "mapping.original_region")
                expected = original_frame.crop(tuple(region))
                if spec["mapping"]["colour_conversion"] == "rgb":
                    expected = expected.convert("RGB")
                if (frame.size != expected.size or frame.mode != expected.mode
                        or frame.tobytes() != expected.tobytes()):
                    _fail("image_mapping_pixels_mismatch", "mapping")
        except Exception as error:
            result["error"] = _error(error, "images." + spec["image_id"])
        self.images[spec["image_id"]] = result
        return deepcopy(result)

    def location(self, image_id, region):
        image = self.images[image_id]
        if image["error"]:
            _fail(image["error"]["code"], image["error"]["field"])
        if not _inside(region, [0, 0, image["width"], image["height"]]):
            _fail("image_region_out_of_bounds", "region")
        left, top = image["mapping"]["original_region"][:2] if image["mapping"] else (0, 0)
        return {"original_source_ref": image["original_source_ref"],
                "original_artifact_ref": image["original_artifact_ref"],
                "image_region": [region[0] + left, region[1] + top,
                                 region[2] + left, region[3] + top]}

    def witness(self, witness):
        result = {"witness": deepcopy(witness), "artifact_ref": None,
                  "canonical_locator": None, "authentication": None,
                  "interpretation_attribution": ATTRIBUTION, "error": None}
        try:
            if witness["kind"] == "image":
                result["canonical_locator"] = self.location(witness["image_id"], witness["region"])
                result["artifact_ref"] = self.images[witness["image_id"]]["artifact_ref"]
                result["authentication"] = "image_bytes_and_geometry_only"
            else:
                source = self.source(witness["source_ref"], witness["representation"])
                result["artifact_ref"] = source["artifact_ref"]
                if witness["end"] > len(source["content"]):
                    _fail("source_span_out_of_bounds", "witness")
                try:
                    quote = source["content"][witness["start"]:witness["end"]].decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ExperimentalContractError("source_span_utf8_boundary_required", "witness") from error
                if quote != witness["quote"]:
                    _fail("source_quote_mismatch", "witness")
                result["authentication"] = "exact_utf8_byte_span"
        except Exception as error:
            result["error"] = _error(error, "witness")
        return result

    def interpretation(self, value):
        return {"value": value["value"], "witnesses": [self.witness(w) for w in value["witnesses"]],
                "interpretation_attribution": ATTRIBUTION}

    def transcription(self, value):
        return {"status": value["status"], "candidates": [self.witness(w) for w in value["candidates"]],
                "fragments": [self.witness(w) for w in value["fragments"]],
                "interpretation_attribution": ATTRIBUTION}


def _errors(value):
    if isinstance(value, dict):
        if value.get("error"):
            yield value["error"]
        for key, item in value.items():
            if key != "error":
                yield from _errors(item)
    elif isinstance(value, list):
        for item in value:
            yield from _errors(item)


def read_binding_visual_inputs(arguments, *, read_source):
    """Retain nominated source readings and a guarded old-table compatibility view.

    n.d. retains its raw spelling and means only an unavailable operand in that
    view; no expansion to 'not determined' or 'nondetected' is inferred. Source
    callback failures preserve independent valid cells. Malformed requests reject
    before any callback. No source/artifact receipt or statistical model is made.
    """
    _validate(arguments)
    if not callable(read_source):
        _fail("source_reader_required", "read_source")
    arguments = deepcopy(arguments)
    inputs = _Inputs(read_source)
    images = [inputs.image(spec) for spec in arguments["images"]]
    context = {name: inputs.interpretation(value) for name, value in arguments["context"].items()}
    parameter = inputs.interpretation(arguments["parameter_kind"])
    basis = inputs.interpretation(arguments["uncertainty_basis"])
    unit = inputs.transcription(arguments["unit"])
    count = arguments["minimum_experiment_count"]
    if count is not None:
        count = {**count, "witness": inputs.witness(count["witness"]), "value": None, "error": None}
        literal, witness = count["literal"], count["witness"]["witness"]
        # A complete token is required, not a substring of 13 or 3.5.
        matched = witness["quote"] == literal if witness["kind"] == "image" else False
        if witness["kind"] == "text" and not list(_errors(count)):
            source = inputs.source(witness["source_ref"], witness["representation"])["content"]
            pattern = r"(?<![\w.+−-])" + re.escape(literal) + r"(?![\w+−-]|\.\d)"
            for match in re.finditer(pattern, witness["quote"]):
                start = witness["start"] + len(witness["quote"][:match.start()].encode("utf-8"))
                end = start + len(literal.encode("utf-8"))
                before = source[max(0, start - 8):start].decode("utf-8", errors="ignore")
                after = source[end:end + 8].decode("utf-8", errors="ignore")
                if (not re.search(r"[\w.+−-]$", before)
                        and not re.match(r"[\w+−-]|\.\d", after)):
                    matched = True
                    break
        if not matched:
            count["error"] = {"code": "count_literal_not_in_witness", "field": "minimum_experiment_count"}
        elif not list(_errors(count)):
            try:
                count["value"] = int(literal)
            except ValueError:
                count["error"] = {"code": "integer_literal_range", "field": "minimum_experiment_count"}
    shared_errors = list(_errors([context, parameter]))
    qualification_errors = list(_errors([basis, count]))
    unit_errors = list(_errors(unit))
    raw_unit = (unit["candidates"][0]["witness"]["quote"] if unit["status"] == "exact" else None)
    supported_unit = not unit_errors and raw_unit in _SCALES
    cells = []
    for cell in arguments["cells"]:
        ligand = inputs.interpretation(cell["ligand"])
        expression = inputs.transcription(cell["expression"])
        result = {"cell_id": cell["cell_id"], "canonical_locator": None,
                  **deepcopy(context), "ligand": ligand, "expression": expression,
                  "mapped_candidates": [], "mapped_fragments": [], "physical_cell_key": None,
                  "parse_status": None, "parsed_measurement": None, "error": None}
        try:
            locator = inputs.location(cell["image_id"], cell["cell_region"])
            result["canonical_locator"] = locator
            encoded = json.dumps(locator, sort_keys=True, separators=(",", ":")).encode("utf-8")
            result["physical_cell_key"] = "binding_visual_cell_" + _hash(encoded)
            errors = shared_errors + list(_errors([ligand, expression]))
            if errors:
                _fail(errors[0]["code"], errors[0]["field"])
            for part in ("candidates", "fragments"):
                for witness in expression[part]:
                    mapped = witness["canonical_locator"]
                    if (any(mapped[name] != locator[name] for name in
                            ("original_source_ref", "original_artifact_ref"))
                            or not _inside(mapped["image_region"], locator["image_region"])):
                        _fail("expression_outside_canonical_cell", "expression." + part)
                    result["mapped_" + part].append({"witness": deepcopy(witness["witness"]),
                                                     "original_region": mapped["image_region"]})
            status = expression["status"]
            if status != "exact":
                result["parse_status"] = status
            elif unit_errors:
                _fail(unit_errors[0]["code"], unit_errors[0]["field"])
            elif not supported_unit:
                result["parse_status"] = "unsupported_unit"
            else:
                try:
                    value, relation, spread = _measurement(expression["candidates"][0]["witness"]["quote"],
                                                            _SCALES[raw_unit], "expression")
                    result["parsed_measurement"] = {"value": value, "relation": relation,
                                                     "reported_spread": spread, "unit": "nM"}
                    result["parse_status"] = "reported_unavailable" if relation == "unreported" else "parsed"
                except (ExperimentalContractError, OverflowError, ValueError) as error:
                    result["parse_status"] = "unsupported_expression"
                    result["error"] = _error(error, "expression")
        except Exception as error:
            result["parse_status"] = "source_unavailable"
            result["error"] = _error(error, "cell." + cell["cell_id"])
        cells.append(result)

    # Physical identity is exact original locator equality, never box overlap.
    groups = {}
    for cell in cells:
        if cell["physical_cell_key"] is not None:
            groups.setdefault(cell["physical_cell_key"], []).append(cell)
    physical_conflict = False
    for group in groups.values():
        signatures = {(cell["ligand"]["value"],
                       cell["expression"]["candidates"][0]["witness"]["quote"])
                      for cell in group if cell["expression"]["status"] == "exact"}
        if len(signatures) > 1 or any(cell["parse_status"] == "conflicting" for cell in group):
            physical_conflict = True
            for cell in group:
                cell.update(parse_status="conflicting", parsed_measurement=None,
                            error={"code": "conflicting_physical_cell_readings", "field": "cells"})
        elif len(group) > 1 and any(cell["parse_status"] in ("ambiguous", "unreadable") for cell in group):
            # A second uncertain reading of the same owner cannot be discarded.
            for cell in group:
                if cell["parsed_measurement"] is not None:
                    cell.update(parse_status="ambiguous", parsed_measurement=None,
                                error={"code": "unresolved_physical_cell_reading", "field": "cells"})
    overlaps = []
    for index, left in enumerate(cells):
        a = left["canonical_locator"]
        if a is None:
            continue
        for right in cells[index + 1:]:
            b = right["canonical_locator"]
            if (b is None or left["physical_cell_key"] == right["physical_cell_key"]
                    or any(a[name] != b[name] for name in ("original_source_ref", "original_artifact_ref"))):
                continue
            x, y = a["image_region"], b["image_region"]
            if max(x[0], y[0]) < min(x[2], y[2]) and max(x[1], y[1]) < min(x[3], y[3]):
                overlaps.append({"left_cell_id": left["cell_id"], "right_cell_id": right["cell_id"]})

    included = [cell for cell in cells if cell["parsed_measurement"] is not None]
    withheld = [cell["cell_id"] for cell in cells if cell["parsed_measurement"] is None]
    reasons = []
    if withheld:
        reasons.append("withheld_transcriptions")
    if physical_conflict:
        reasons.append("physical_cell_conflict")
    if any(cell["parse_status"] == "source_unavailable" for cell in cells) or qualification_errors:
        reasons.append("source_unavailable")
    if unit["status"] != "exact":
        reasons.append("unit_not_exact")
    if any(cell["parse_status"] == "unsupported_expression" for cell in cells):
        reasons.append("unsupported_expression")
    if not supported_unit:
        reasons.append("unsupported_unit")
    if not included:
        reasons.append("no_representable_cells")
    table = None
    if included and supported_unit and not qualification_errors and not shared_errors:
        table = {"version": "binding_parameter_table_v1", "table_id": arguments["table_id"],
                 "parameter_kind": parameter["value"], "unit": raw_unit,
                 "uncertainty_basis": basis["value"],
                 "minimum_experiment_count": count["value"] if count is not None else None,
                 "rows": [{**{name: cell[name]["value"] for name in ("subject", "state", "experiment", "ligand")},
                           "expression": cell["expression"]["candidates"][0]["witness"]["quote"],
                           "locator": deepcopy(cell["canonical_locator"])} for cell in included]}
    status = "unavailable" if table is None else "partial_requires_adapter" if withheld else "complete"
    return {"version": OUTPUT_VERSION, "table_id": arguments["table_id"], "context": context,
            "parameter_kind": parameter, "unit": unit, "uncertainty_basis": basis,
            "minimum_experiment_count": count, "images": images, "cells": cells,
            "source_refs": inputs.references, "geometry_overlaps": overlaps,
            "compatibility": {"status": status, "table": table,
                              "included_cell_ids": [cell["cell_id"] for cell in included] if table else [],
                              "withheld_cell_ids": withheld if table else [cell["cell_id"] for cell in cells],
                              "reasons": reasons}}


__all__ = ["VERSION", "OUTPUT_VERSION", "binding_visual_arguments_schema", "read_binding_visual_inputs"]
