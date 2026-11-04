"""Source-bound four-arm inputs within A105; no scientific sheet calculation.

Selections assign scientific meanings. Exact bytes/geometry establish custody
only; original runtime authorization and outcome binding remain caller owned.
This first reader supports text/structured source covariance; graph nominations
are retained as explicit unimplemented capability, never made-up ordinates.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator
from .domain import REF, ContractError, identity
from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
from .literature_assay_inputs import _Sources
from .literature_rate_native_inputs import (
    _number as _native_number, _unit as _native_unit, _plain_unit,
    _scale as _native_scale, _check_explicit_unit, _field_contexts,
)
from .literature_partner_defined_units import defined_rate_unit_schema
from .literature_kinetic_inputs import _count_reading, _interval, _confidence
from .literature_binding_visual_inputs import _Inputs
from .literature_controlled_response_calculations import (
    INPUT_VERSION, PRIMITIVE_ORDER, validate_controlled_response_inputs,
)

VERSION = "controlled_response_source_extraction_v1"
SELECTION_VERSION = "controlled_response_source_selection_v1"
COVARIANCE_VERSION = "controlled_response_covariance_source_v1"
def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def enum(values):
    return {"enum": list(values)}


TEXT = {"type": "string", "minLength": 1}
OFFSET = {"type": "integer", "minimum": 0}
ROLES = ("protein_condition1", "empty_condition1", "protein_condition0", "empty_condition0")
WITNESS_FIELDS = {"source_ref": deepcopy(REF), "representation": enum(("original", "text")),
    "start": OFFSET, "end": {"type": "integer", "minimum": 1}, "quote": TEXT}
defs = {"NativeTextWitness": obj(WITNESS_FIELDS),
    "TextWitness": obj({"kind": {"const": "text"}, **WITNESS_FIELDS}),
    "Box": {"type": "array", "minItems": 4, "maxItems": 4, "items": OFFSET}}
defs["ImageWitness"] = obj({"kind": {"const": "image"}, "image_id": TEXT,
    "region": ref("Box"), "quote": TEXT})
defs["Witness"] = {"oneOf": [ref("TextWitness"), ref("ImageWitness")]}
defs["NumberSelector"] = obj({"witness": ref("NativeTextWitness"),
    "number_start": OFFSET, "number_end": {"type": "integer", "minimum": 1}})
defs["UnitSelection"] = {"anyOf": [ref("NativeTextWitness"), defined_rate_unit_schema()]}


def interpretation(values):
    return obj({"value": enum(values), "witnesses": array(ref("Witness"))})


defs["Correspondence"] = interpretation(("same", "unknown", "conflicting"))
defs["Meaning"] = obj({"status": enum(("known", "unknown", "conflicting")),
    "label": nullable(TEXT), "witnesses": array(ref("Witness")),
    "canonical_witness": nullable(ref("Witness")), "canonical_correspondence": ref("Correspondence")})
defs["Literal"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("NumberSelector")), "fragments": array(ref("Witness"))})
defs["AxisLiteral"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("Witness")), "fragments": array(ref("Witness"))})
defs["Image"] = obj({"image_id": TEXT, "source_ref": deepcopy(REF),
    "original_source_ref": deepcopy(REF), "mapping": nullable(obj({"original_region": ref("Box"),
        "colour_conversion": enum(("preserve", "rgb"))}))})
defs["TextMeasurement"] = obj({"kind": {"const": "source_literal"},
    "literal": ref("Literal"), "unit": nullable(ref("UnitSelection"))})
defs["BarSelection"] = obj({
    "roi": obj({name: OFFSET for name in ("left", "top", "right", "bottom")}),
    "rgb_min": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "rgb_max": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "minimum_row_fraction": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    "minimum_run_rows": {"type": "integer", "minimum": 1},
    "edge_tolerance_pixels": {"type": "number", "minimum": 0}})
defs["GraphMeasurement"] = obj({"kind": {"const": "linear_bar"}, "image_id": TEXT,
    "bar_selection": ref("BarSelection"), "axis": obj({
        "first": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "second": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "unit": ref("AxisLiteral")})})
defs["CISelector"] = obj({"witness": ref("NativeTextWitness"),
    **{name: OFFSET for name in ("lower_start", "lower_end", "upper_start", "upper_end")}})
defs["Uncertainty"] = obj({
    "statistic": interpretation(("sd", "sem", "ci", "unspecified", "unreported", "unknown", "conflicting")),
    "magnitude": nullable(ref("NumberSelector")), "interval": nullable(ref("CISelector")),
    "unit": nullable(ref("UnitSelection")),
    "unit_relationship": interpretation(("same_as_response", "explicit_unit", "unknown", "conflicting")),
    "confidence_level": nullable(ref("NativeTextWitness")), "count": nullable(ref("NumberSelector")),
    "repetition_basis": interpretation(("biological_preparations", "technical_measurements", "unspecified", "unknown", "conflicting")),
    "estimate_basis": interpretation(("fit_to_averaged_curve", "between_fitted_parameters", "unknown", "conflicting"))})
defs["Arm"] = obj({"source_kind": enum(("primary_source", "retained_extraction", "synthetic_fixture")),
    "context": obj({name: nullable(ref("Witness")) for name in
        ("subject", "organism", "genotype", "construct", "preparation", "experimental_system")}),
    "protein_arrangement": interpretation(("protein_present", "protein_free_control", "empty_vector_control", "other_specified", "unknown", "conflicting")),
    **{name: ref("Meaning") for name in ("subject_construct", "condition", "endpoint", "normalization", "physical_observation")},
    "intended_factor_level": nullable(ref("Witness")),
    "measurement": nullable({"oneOf": [ref("TextMeasurement"), ref("GraphMeasurement")]}),
    "reported_uncertainty": ref("Uncertainty")})
defs["Relationships"] = obj({"condition1_target": ref("Meaning"), "condition0_target": ref("Meaning"),
    "condition_levels_relation": interpretation(("same", "different", "unknown", "conflicting")),
    "subject_construct_across_conditions": interpretation(("same", "different", "unknown", "conflicting")),
    **{name: interpretation(("matched_condition_control", "shared_reference_assumption", "unknown", "conflicting"))
        for name in ("condition1_control_application", "condition0_control_application")},
    "control_reference_reuse": interpretation(("distinct_observations", "same_reference_with_stated_invariance", "unknown", "conflicting")),
    "nonintended_conditions": interpretation(("matched", "different", "unknown", "conflicting")),
    "intended_factor": nullable(ref("Witness"))})
defs["CovarianceBinding"] = obj({"variable_index": OFFSET, "label_witness": ref("NativeTextWitness"),
    "owner_witness": ref("Witness"), "correspondence": ref("Correspondence")})
selection = obj({"version": {"const": "controlled_response_source_selection_v1"},
    "source_ref": deepcopy(REF), "images": array(ref("Image")),
    "arms": obj({role: nullable(ref("Arm")) for role in ROLES}), "relationships": ref("Relationships"),
    "covariance": nullable(obj({"source_ref": deepcopy(REF),
        "bindings": obj({role: nullable(ref("CovarianceBinding")) for role in ROLES})})),
    "variance_status": interpretation(("known", "estimated", "unknown")),
    "model_kind": interpretation(("none", "known_joint_normal_source_means"))})
selection["$defs"] = defs
selection["$schema"] = "https://json-schema.org/draft/2020-12/schema"

_SELECTION_SCHEMA = selection
DEPENDENCIES = {'literature_assay_inputs.py': '52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e',
 'literature_rate_native_inputs.py': '55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500',
 'literature_partner_source_fields.py': '20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17',
 'literature_partner_defined_units.py': 'cc6733d763ba494e3c4016a9a3be98ea6b7b6076b97dc8ef1aad5f43a8f856ca',
 'literature_kinetic_inputs.py': '78e0c0094bbffa8306c26a6d134eec74f291c34177a87656ec09f925c2dd1960',
 'literature_binding_visual_inputs.py': '8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718',
 'literature_binding_reader.py': 'e117105486773280edf1dba796ab2be10c61feb6a9c0ad407ba876e2332714a1',
 'literature_controlled_response_calculations.py': 'a75b8f8ef4905d805be24e86236ef8303c97b5e4761acf0d849ca01aadaec023'}

_MEANINGS = ("endpoint", "normalization", "subject_construct", "condition", "physical_observation")
_UNKNOWN = ("unknown", "none", "unspecified", "unreported")
_NUMBER_PATTERN = re.compile(r"[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\Z")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _closed(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("closed_fields_required", field)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _rational(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _finite(value):
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) and (number != 0 or value == 0) else None


def _diag(code, field, domain, references=()):
    return {"code": code, "field": field, "domain": domain,
            "source_refs": sorted(set(references))}


def _all_diagnostics(value):
    if isinstance(value, dict):
        if set(value) == {"code", "field", "domain", "source_refs"}:
            yield value
        else:
            for key, item in value.items():
                if key != "selection":
                    yield from _all_diagnostics(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_diagnostics(item)


def _unique_diagnostics(value):
    return list({json.dumps(d, sort_keys=True): d for d in _all_diagnostics(value)}.values())


def controlled_response_arguments_schema():
    """Closed nominations only; numerical scientific operands are never inputs."""
    return deepcopy(_SELECTION_SCHEMA)


def _nomination_key(witness):
    if witness.get("kind") == "image":
        return ("image", witness["image_id"], tuple(witness["region"]))
    return ("text", witness["source_ref"], witness["representation"], witness["start"], witness["end"])


def validate_controlled_response_selection(arguments):
    """Validate the whole closed nomination before any callback or decoding."""
    try:
        Draft202012Validator(_SELECTION_SCHEMA).validate(arguments)
        json.dumps(arguments, allow_nan=False)
    except Exception as error:
        if not isinstance(error, (ValueError, TypeError)) and error.__class__.__module__.split(".")[0] != "jsonschema":
            raise
        raise ExperimentalContractError("controlled_selection_schema_invalid", "arguments") from error
    image_ids = set()
    for image in arguments["images"]:
        if image["image_id"] in image_ids:
            _fail("duplicate_image_id", "images")
        image_ids.add(image["image_id"])
        if image["mapping"] is None and image["source_ref"] != image["original_source_ref"]:
            _fail("unmapped_original_source_mismatch", "images")

    def walk(value, field):
        if isinstance(value, dict):
            if "image_id" in value and value["image_id"] not in image_ids:
                _fail("undeclared_image_id", field)
            if "region" in value or "original_region" in value:
                box = value.get("region", value.get("original_region"))
                if box[0] >= box[2] or box[1] >= box[3]:
                    _fail("nonempty_integer_image_region_required", field)
            if "start" in value and "end" in value and value["start"] >= value["end"]:
                _fail("nonempty_source_span_required", field)
            if "number_start" in value:
                if not 0 <= value["number_start"] < value["number_end"] <= len(value["witness"]["quote"]):
                    _fail("source_number_span_order_invalid", field)
            if set(value) == {"value", "witnesses"}:
                minimum = 2 if value["value"] == "conflicting" else 0 if value["value"] in _UNKNOWN else 1
                if len({_nomination_key(w) for w in value["witnesses"]}) < minimum:
                    _fail("interpretation_witness_required", field)
            if set(value) == {"status", "label", "witnesses", "canonical_witness", "canonical_correspondence"}:
                minimum = 2 if value["status"] == "conflicting" else 1 if value["status"] == "known" else 0
                if len({_nomination_key(w) for w in value["witnesses"]}) < minimum:
                    _fail("meaning_witness_required", field)
                if value["canonical_correspondence"]["value"] == "same" and value["canonical_witness"] is None:
                    _fail("canonical_witness_required", field)
            if set(value) == {"status", "candidates", "fragments"}:
                count = len(value["candidates"])
                status = value["status"]
                if status == "exact" and (count != 1 or value["fragments"]):
                    _fail("one_exact_candidate_required", field)
                if status == "unreadable" and (count or not value["fragments"]):
                    _fail("unreadable_fragments_required", field)
                if status in ("ambiguous", "conflicting") and len({json.dumps(w, sort_keys=True) for w in value["candidates"]}) < 2:
                    _fail("distinct_source_candidates_required", field)
            for key, item in value.items():
                walk(item, field + "." + key)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{field}[{i}]")
    walk(arguments, "arguments")
    return deepcopy(arguments)


class _Unavailable(Exception):
    pass


def _reference_closure(arguments):
    result = {(arguments["source_ref"], "original")}
    def walk(value):
        if isinstance(value, dict):
            if "source_ref" in value:
                result.add((value["source_ref"], value.get("representation", "original")))
            if "original_source_ref" in value:
                result.add((value["original_source_ref"], "original"))
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(arguments)
    return sorted(result)


class _Context:
    def __init__(self, arguments, callback):
        if not callable(callback):
            _fail("source_reader_required", "read_source")
        self.cache, self.roster = {}, []
        artifacts = {}
        # Complete authorization/source callback phase precedes any geometry
        # helper's broad catches. Scope failures are never data partials.
        for reference, representation in _reference_closure(arguments):
            record = {"source_ref": reference, "representation": representation,
                "artifact_ref": None, "byte_sha256": None, "state": "available", "diagnostics": []}
            try:
                loaded = callback(reference, representation)
            except PermissionError:
                raise
            except (OSError, EOFError):
                loaded = _Unavailable()
                record.update(state="unavailable", diagnostics=[_diag("source_dependency_unavailable",
                    "sources", "dependency", [reference])])
            if not isinstance(loaded, _Unavailable):
                _closed(loaded, ("artifact_ref", "content"), "source_result")
                if not isinstance(loaded["artifact_ref"], str) or not loaded["artifact_ref"].strip() or type(loaded["content"]) is not bytes:
                    _fail("malformed_source_result", "source_result")
                digest = _hash(loaded["content"])
                if loaded["artifact_ref"] in artifacts and artifacts[loaded["artifact_ref"]] != digest:
                    _fail("artifact_content_conflict", "source_result")
                artifacts[loaded["artifact_ref"]] = digest
                record.update(artifact_ref=loaded["artifact_ref"], byte_sha256=digest)
            self.cache[(reference, representation)] = loaded
            self.roster.append(record)
        self.native = _Sources(self.source)
        self.visual = _Inputs(self.source)
        self.images = []
        for spec in arguments["images"]:
            image = self.visual.image(spec)
            if image["error"] and image["error"]["code"] in ("image_mapping_pixels_mismatch", "image_region_out_of_bounds"):
                _fail(image["error"]["code"], image["error"]["field"])
            self.images.append(image)

    def source(self, reference, representation):
        key = (reference, representation)
        if key not in self.cache:
            _fail("unselected_source_read", "source_ref")
        value = self.cache[key]
        if isinstance(value, _Unavailable):
            raise value
        return value

    def witness(self, nominated, field):
        if nominated is None:
            return None
        selected = deepcopy(nominated)
        if "kind" not in selected:
            selected = {"kind": "text", **selected}
        record = {"selection": selected, "artifact_ref": None, "byte_sha256": None,
            "canonical_locator": None, "authentication": "unavailable",
            "attribution": "literal_source_record" if selected["kind"] == "text" else "investigating_episode_interpretation",
            "diagnostics": []}
        if selected["kind"] == "text":
            reference = selected["source_ref"]
            try:
                loaded = self.source(reference, selected["representation"])
            except _Unavailable:
                record["diagnostics"] = [_diag("source_dependency_unavailable", field, "dependency", [reference])]
                return record
            try:
                loaded["content"].decode("utf-8")
            except UnicodeDecodeError:
                record["diagnostics"] = [_diag("source_text_encoding_unsupported", field, "reader_capability", [reference])]
                return record
            actual = self.native.witness({k:v for k,v in selected.items() if k != "kind"}, field)
            digest = _hash(loaded["content"])
            record.update(artifact_ref=actual["artifact_ref"], byte_sha256=digest,
                canonical_locator={"kind": "text", "source_ref": reference, "artifact_ref": actual["artifact_ref"],
                    "byte_sha256": digest, "start": actual["start"], "end": actual["end"]},
                authentication="exact_utf8_byte_span")
        else:
            actual = self.visual.witness(selected)
            if actual["error"]:
                code = actual["error"]["code"]
                if code == "image_region_out_of_bounds":
                    _fail(code, field)
                record["diagnostics"] = [_diag("source_image_format_unsupported" if code in
                    ("unsupported_image_format", "unsupported_image_mode", "single_frame_required") else
                    "source_image_decode_failed", field, "reader_capability")]
            else:
                image = self.visual.images[selected["image_id"]]
                locator = actual["canonical_locator"]
                record.update(artifact_ref=actual["artifact_ref"], byte_sha256=image["byte_sha256"],
                    canonical_locator={"kind": "image", "original_source_ref": locator["original_source_ref"],
                        "original_artifact_ref": locator["original_artifact_ref"],
                        "original_byte_sha256": image["original_byte_sha256"], "region": locator["image_region"]},
                    authentication="image_bytes_and_geometry_only")
        return record


def _interpretation(context, selected, field):
    witnesses = [context.witness(w, field) for w in selected["witnesses"]]
    valid = [w for w in witnesses if w["canonical_locator"] is not None]
    unique = {json.dumps(w["canonical_locator"], sort_keys=True) for w in valid}
    minimum = 2 if selected["value"] == "conflicting" else 0 if selected["value"] in _UNKNOWN else 1
    if len(valid) == len(witnesses) and len(unique) < minimum:
        _fail("distinct_interpretation_witness_required", field)
    effective = selected["value"] if len(valid) == len(witnesses) else "unknown"
    return {"selection": deepcopy(selected), "witnesses": witnesses,
            "effective_value": effective, "diagnostics": _unique_diagnostics(witnesses)}


def _meaning(context, selected, category, field):
    witnesses = [context.witness(w, field) for w in selected["witnesses"]]
    canonical = context.witness(selected["canonical_witness"], field + ".canonical_witness")
    correspondence = _interpretation(context, selected["canonical_correspondence"], field + ".canonical_correspondence")
    good = all(w["canonical_locator"] is not None for w in witnesses)
    unique = {json.dumps(w["canonical_locator"], sort_keys=True) for w in witnesses if w["canonical_locator"] is not None}
    required = 2 if selected["status"] == "conflicting" else 1 if selected["status"] == "known" else 0
    if good and len(unique) < required:
        _fail("distinct_meaning_witness_required", field)
    state = "conflicting" if selected["status"] == "conflicting" or correspondence["effective_value"] == "conflicting" else "unknown"
    canonical_id = None
    if (selected["status"] == "known" and good and canonical and canonical["canonical_locator"] is not None
            and correspondence["effective_value"] == "same"):
        state = "known"
        canonical_id = identity("controlled_" + category, canonical["canonical_locator"])
    return {"selection": deepcopy(selected), "witnesses": witnesses, "canonical_witness": canonical,
        "canonical_correspondence": correspondence, "resolved_state": state, "canonical_id": canonical_id,
        "diagnostics": _unique_diagnostics([witnesses, canonical, correspondence])}


def _number(context, selected, field, role="rate", *, count_unit_guard=True):
    witness = context.witness(selected["witness"], field)
    record = {"selection": deepcopy(selected), "witness": witness, "raw_expression": None,
        "native_value": None, "relation": "unresolved", "approximate": None,
        "source_locator": None, "status": "dependency_unavailable", "diagnostics": deepcopy(witness["diagnostics"])}
    if witness["canonical_locator"] is None:
        return record
    start, end = selected["number_start"], selected["number_end"]
    quote = selected["witness"]["quote"]
    expression = quote[start:end]
    location = deepcopy(witness["canonical_locator"])
    location["start"] += len(quote[:start].encode())
    location["end"] = location["start"] + len(expression.encode())
    record.update(raw_expression=expression, source_locator=location, status="unsupported")
    try:
        native = _native_number(selected, context.native, role, count_unit_guard=count_unit_guard)
    except ExperimentalContractError as error:
        if error.code.startswith("partial_") or error.code in ("source_number_span_order_invalid", "source_arithmetic_expression_unsupported", "nonliteral_scientific_expression"):
            raise
        if not _NUMBER_PATTERN.fullmatch(expression):
            before, after = _field_contexts(context.native, {**selected["witness"], "artifact_ref": witness["artifact_ref"]}, start, end)
            if (before[-1:] and (before[-1:].isalnum() or before[-1:] in ".eE+−-_")
                    or after[:1] and (after[:1].isalnum() or after[:1] in "^×*/")):
                _fail("partial_source_expression", field)
        code = "source_numeric_range" if error.code == "numerical_model_range" else "unsupported_complete_source_expression"
        record.update(status="numeric_range" if code == "source_numeric_range" else "unsupported",
            diagnostics=[_diag(code, field, "reader_capability", [selected["witness"]["source_ref"]])])
        return record
    record.update(native_value=native["value"], relation=native["relation"], approximate=native["approximate"], status="parsed")
    return record


def _unit(context, selected, endpoint, field):
    record = {"selection": deepcopy(selected), "witness": None, "raw_unit": None,
        "canonical_unit": None, "exact_scale": None, "native_registry_unit": None,
        "definition_witnesses": None, "status": "unknown", "diagnostics": []}
    if selected is None:
        record["diagnostics"] = [_diag("source_rate_unit_unknown", field, "source_interpretation")]
        return record
    defined = selected.get("kind") == "source_defined_rate_unit"
    unit_witness = selected["witness"] if defined else selected
    record["witness"] = context.witness(unit_witness, field)
    if record["witness"]["canonical_locator"] is None:
        record.update(status="dependency_unavailable", diagnostics=deepcopy(record["witness"]["diagnostics"]))
        return record
    record["raw_unit"] = unit_witness["quote"]
    endpoint_witness = None
    if defined:
        definitions = {key: _number(context, value, field + ".definition.amount", "condition", count_unit_guard=False) if key == "amount"
            else context.witness(value, field + ".definition." + key) for key,value in selected["definition"].items()}
        record["definition_witnesses"] = definitions
        if any(w["witness"]["canonical_locator"] is None if key == "amount" else w["canonical_locator"] is None
               for key,w in definitions.items()):
            record.update(status="dependency_unavailable", diagnostics=_unique_diagnostics(definitions))
            return record
        nominated = {"kind": "text", **selected["definition"]["endpoint"]}
        available = [w["selection"] for w in endpoint["witnesses"]] + ([endpoint["canonical_witness"]["selection"]] if endpoint["canonical_witness"] else []) if endpoint else []
        if endpoint is None or endpoint["resolved_state"] != "known" or nominated not in available:
            record.update(status="endpoint_correspondence_unknown", diagnostics=[_diag(
                "unit_endpoint_correspondence_unknown", field, "source_binding", [unit_witness["source_ref"]])])
            return record
        endpoint_witness = selected["definition"]["endpoint"]
    try:
        parsed = _native_unit(selected, context.native, endpoint_witness)
        if parsed["canonical_unit"] is None:
            record.update(status="unsupported", diagnostics=[_diag("source_defined_unit_definition_not_selected" if
                parsed["unavailable_reason"] == "source_defined_unit_definition_required" else "source_rate_unit_unsupported",
                field, "reader_capability", [unit_witness["source_ref"]])])
            return record
        scale = _native_scale(parsed)
    except ExperimentalContractError as error:
        if error.code.startswith("partial_") or "mismatch" in error.code or "containment" in error.code or "boundary" in error.code:
            raise
        record.update(status="numeric_range" if error.code == "numerical_model_range" else "unsupported",
            diagnostics=[_diag("custom_unit_projection_unrepresentable" if error.code == "numerical_model_range" else
                "source_rate_unit_unsupported", field, "reader_capability", [unit_witness["source_ref"]])])
        return record
    native_key = next((key for key in RATE_UNITS if _plain_unit(key) == (parsed["canonical_unit"], scale)), None)
    record.update(canonical_unit=parsed["canonical_unit"], exact_scale=_rational(scale),
                  native_registry_unit=native_key, status="supported")
    return record


def _display(number, unit):
    result = {"value": None, "threshold": None, "unit": unit["canonical_unit"] if unit else None,
        "relation": "none", "approximate": bool(number and number["approximate"]), "diagnostics": []}
    if number and number["status"] == "parsed" and unit and unit["status"] == "supported":
        exact = Fraction(number["raw_expression"].replace("−", "-")) * _fraction(unit["exact_scale"])
        value = _finite(exact)
        if value is None:
            result["diagnostics"] = [_diag("source_numeric_range", "canonical_display", "reader_capability")]
        else:
            result["relation"] = "eq" if number["relation"] == "point" else number["relation"]
            result["value" if number["relation"] == "point" else "threshold"] = value
    return result


def _measurement(context, selected, endpoint, field):
    result = {"selection": deepcopy(selected), "candidates": [], "fragments": [], "unit": None,
        "graph_witnesses": [], "reading_status": "not_selected", "source_observation_id": None,
        "canonical_display": _display(None, None), "pixel_result": None, "diagnostics": []}
    if selected is None:
        result["diagnostics"] = [_diag("measurement_not_selected", field, "source_interpretation")]
        return result
    if selected["kind"] == "linear_bar":
        for part in ("first", "second", "unit"):
            literal = selected["axis"][part]["tick"] if part != "unit" else selected["axis"][part]
            result["graph_witnesses"].extend(context.witness(w, field + ".axis") for w in literal["candidates"] + literal["fragments"])
        # Authenticate the nominated actual bar geometry even without an ordinate.
        image = context.visual.images[selected["image_id"]]
        roi = selected["bar_selection"]["roi"]
        if not image["error"]:
            context.visual.location(selected["image_id"], [roi[k] for k in ("left", "top", "right", "bottom")])
            result["source_observation_id"] = identity("controlled_graph_nomination", {
                "artifact_ref": image["artifact_ref"], "byte_sha256": image["byte_sha256"], "nomination": selected})
        result.update(reading_status="graph_unimplemented", diagnostics=[_diag("graph_rate_reader_unimplemented", field, "reader_capability")])
        return result
    literal = selected["literal"]
    result["candidates"] = [_number(context, item, field + ".candidates") for item in literal["candidates"]]
    result["fragments"] = [context.witness(w, field + ".fragments") for w in literal["fragments"]]
    result["unit"] = _unit(context, selected["unit"], endpoint, field + ".unit")
    state = literal["status"]
    if any(n["status"] == "dependency_unavailable" for n in result["candidates"]) or any(w["canonical_locator"] is None for w in result["fragments"]):
        state = "dependency_unavailable"
    elif state == "exact" and result["candidates"][0]["status"] != "parsed":
        state = "unsupported"
    result["reading_status"] = state
    authenticated = [n["source_locator"] for n in result["candidates"] if n["source_locator"] is not None]
    authenticated += [w["canonical_locator"] for w in result["fragments"] if w["canonical_locator"] is not None]
    if state != "dependency_unavailable" and authenticated:
        result["source_observation_id"] = identity("controlled_source_token", authenticated[0] if len(authenticated) == 1 else authenticated)
    if state == "exact":
        item = result["candidates"][0]
        unit = result["unit"]
        if unit["status"] == "supported":
            parsed_number = _native_number(item["selection"], context.native, "rate")
            parsed_unit = _native_unit(unit["selection"], context.native,
                unit["selection"]["definition"]["endpoint"] if unit["definition_witnesses"] else None)
            _check_explicit_unit(parsed_number, parsed_unit, context.native)
        result["canonical_display"] = _display(item, unit)
    if state in ("ambiguous", "unreadable", "conflicting"):
        result["diagnostics"].append(_diag("source_literal_" + state, field, "source_interpretation"))
    result["diagnostics"].extend(_unique_diagnostics([result["candidates"], result["fragments"], result["unit"], result["canonical_display"]]))
    return result


def _uncertainty_piece(context, selected, field, kind):
    if selected is None:
        return None
    nominal = selected["witness"] if kind in ("interval", "count") else selected
    witness = context.witness(nominal, field)
    if kind == "count":
        result = {"selection": deepcopy(selected), "witness": witness, "reading": None, "diagnostics": deepcopy(witness["diagnostics"])}
    else:
        result = {"selection": deepcopy(selected), "witness": witness,
            **({"raw_values": None, "values": None} if kind == "interval" else {"value": None}),
            "status": "dependency_unavailable", "diagnostics": deepcopy(witness["diagnostics"])}
    if witness["canonical_locator"] is None:
        return result
    try:
        reading = {"interval": _interval, "confidence": _confidence, "count": _count_reading}[kind](selected, context.native)
    except ExperimentalContractError as error:
        sentence_stop = False
        if kind == "confidence" and error.code == "partial_source_confidence_level":
            raw = selected["quote"]
            _, after = _field_contexts(context.native, {**selected, "artifact_ref": witness["artifact_ref"]}, 0, len(raw))
            sentence_stop = bool(re.fullmatch(r"\s*[0-9]+(?:\.[0-9]*)?\s*%\s*", raw)
                                 and re.match(r"\.(?:\s|$)", after))
        if error.code.startswith("partial_") and not sentence_stop or "selector_mismatch" in error.code or error.code == "source_number_span_order_invalid":
            raise
        code = ("source_confidence_sentence_stop_unsupported" if sentence_stop else
                "qualified_confidence_unsupported" if error.code == "qualified_source_confidence_unsupported" else
                "source_numeric_range" if error.code == "numerical_model_range" else "source_uncertainty_piece_unsupported")
        result["diagnostics"] = [_diag(code, field, "reader_capability", [nominal["source_ref"]])]
        if kind != "count":
            result["status"] = "numeric_range" if code == "source_numeric_range" else "unsupported"
        return result
    if kind == "count":
        result["reading"] = reading
    elif kind == "interval":
        result.update(raw_values=reading["raw_values"], values=reading["values"], status="parsed")
    else:
        result.update(value=reading["value"], status="parsed")
    return result


def _uncertainty(context, selected, response_unit, endpoint, field):
    meanings = {key: _interpretation(context, selected[key], field + "." + key) for key in
        ("statistic", "unit_relationship", "repetition_basis", "estimate_basis")}
    magnitude = _number(context, selected["magnitude"], field + ".magnitude", "spread") if selected["magnitude"] else None
    interval = _uncertainty_piece(context, selected["interval"], field + ".interval", "interval")
    confidence = _uncertainty_piece(context, selected["confidence_level"], field + ".confidence_level", "confidence")
    count = _uncertainty_piece(context, selected["count"], field + ".count", "count")
    unit = _unit(context, selected["unit"], endpoint, field + ".unit") if selected["unit"] else None
    relationship = meanings["unit_relationship"]["effective_value"]
    effective_unit = response_unit if relationship == "same_as_response" else unit if relationship == "explicit_unit" else None
    diagnostics = []
    if relationship == "conflicting":
        effective_unit = None
        diagnostics.append(_diag("source_uncertainty_unit_conflicting", field, "source_interpretation"))
    if relationship == "same_as_response" and unit and response_unit and (unit["canonical_unit"], unit["exact_scale"]) != (response_unit["canonical_unit"], response_unit["exact_scale"]):
        effective_unit = None
        diagnostics.append(_diag("source_uncertainty_unit_conflicting", field, "source_interpretation"))
    statistic = meanings["statistic"]["effective_value"]
    if (statistic == "unreported" and any(item is not None for item in (magnitude, interval, confidence))
            or statistic == "ci" and magnitude is not None
            or statistic in ("sd", "sem") and any(item is not None for item in (interval, confidence))):
        statistic = "conflicting"
        diagnostics.append(_diag("source_uncertainty_meaning_conflict", field, "source_interpretation"))
    spread = _display(magnitude, effective_unit)["value"]
    bounds = None
    if interval and interval["status"] == "parsed" and effective_unit and effective_unit["status"] == "supported":
        values = [_finite(Fraction(v.replace("−", "-")) * _fraction(effective_unit["exact_scale"])) for v in interval["raw_values"]]
        if all(v is not None for v in values):
            bounds = values
        else:
            diagnostics.append(_diag("source_numeric_range", field + ".interval", "reader_capability"))
    if (magnitude or interval) and (effective_unit is None or effective_unit["status"] != "supported"):
        diagnostics.append(_diag("source_uncertainty_unit_unknown", field, "source_interpretation"))
    exact_count = count["reading"]["value"] if count and count["reading"] and count["reading"]["status"] == "exact" else None
    result = {"selection": deepcopy(selected), "meanings": meanings, "magnitude": magnitude,
        "interval": interval, "unit": unit, "effective_unit": deepcopy(effective_unit),
        "confidence_level": confidence, "count": count,
        "canonical": {"statistic": statistic, "magnitude": spread, "interval": bounds,
            "confidence_level": confidence["value"] if confidence else None, "count": exact_count,
            "repetition_basis": meanings["repetition_basis"]["effective_value"],
            "estimate_basis": meanings["estimate_basis"]["effective_value"]}, "diagnostics": diagnostics}
    result["diagnostics"].extend(_unique_diagnostics([meanings, magnitude, interval, unit, confidence, count]))
    return result


def _operand_from_arm(arm):
    measurement = arm["measurement"]
    if measurement["reading_status"] == "dependency_unavailable" or (measurement["reading_status"] == "graph_unimplemented" and measurement["source_observation_id"] is None):
        return None
    state = measurement["reading_status"]
    item = measurement["candidates"][0] if state == "exact" else None
    unit = measurement["unit"]
    native_value = threshold = None
    relation, approximate = "none", False
    pure_unit = unit["native_registry_unit"] if unit and unit["status"] == "supported" else None
    status = {"not_selected": "missing", "exact": "point", "ambiguous": "ambiguous", "conflicting": "conflicting"}.get(state, "unsupported")
    if item:
        number = item["native_value"]
        approximate = bool(item["approximate"])
        exact_native = Fraction(item["raw_expression"].replace("−", "-"))
        if Fraction(str(number)) != exact_native:
            approximate = True
        if unit and unit["status"] == "supported":
            pure_unit = unit["native_registry_unit"]
            if pure_unit is None:
                number = _finite(exact_native * _fraction(unit["exact_scale"]))
                pure_unit = unit["canonical_unit"] if number is not None else None
                if number is not None and Fraction(str(number)) != exact_native * _fraction(unit["exact_scale"]):
                    approximate = True
        if number is None:
            status, pure_unit = "unsupported", None
        else:
            if item["relation"] == "point":
                native_value, relation = number, "eq"
            else:
                threshold, relation, status = number, item["relation"], "bound"
    result = {"value": native_value, "threshold": threshold, "relation": relation,
        "approximate": approximate, "unit": pure_unit, "status": status,
        **{name + "_id": arm["meanings"][name]["canonical_id"] for name in _MEANINGS},
        "source_observation_id": measurement["source_observation_id"],
        "origin": "synthetic" if arm["selection"]["source_kind"] == "synthetic_fixture" else
                  "graph_derived" if state == "graph_unimplemented" else "reported",
        "digitization_interval": None, "protein_arrangement": arm["protein_arrangement"]["effective_value"],
        "meaning_statuses": {name: arm["meanings"][name]["resolved_state"] for name in _MEANINGS}}
    return result


def _arm(context, selected, field):
    if selected is None:
        return None
    meanings = {name: _meaning(context, selected[name], name, field + "." + name) for name in _MEANINGS}
    measurement = _measurement(context, selected["measurement"], meanings["endpoint"], field + ".measurement")
    result = {"selection": deepcopy(selected),
        "context": {name: context.witness(w, field + ".context." + name) if w is not None else None for name,w in selected["context"].items()},
        "protein_arrangement": _interpretation(context, selected["protein_arrangement"], field + ".protein_arrangement"),
        "meanings": meanings, "intended_factor_level": context.witness(selected["intended_factor_level"], field + ".intended_factor_level"),
        "measurement": measurement,
        "reported_uncertainty": _uncertainty(context, selected["reported_uncertainty"], measurement["unit"], meanings["endpoint"], field + ".reported_uncertainty"),
        "calculation_operand": None, "diagnostics": []}
    result["calculation_operand"] = _operand_from_arm(result)
    operand = result["calculation_operand"]
    if operand and measurement["reading_status"] == "exact":
        item = measurement["candidates"][0]
        if operand["approximate"] and not item["approximate"]:
            result["diagnostics"].append(_diag("numeric_projection_rounding", field, "reader_capability"))
        if operand["status"] == "unsupported":
            result["diagnostics"].append(_diag("custom_unit_projection_unrepresentable", field, "reader_capability"))
    result["diagnostics"].extend(_unique_diagnostics([result["context"], meanings, result["protein_arrangement"], measurement, result["reported_uncertainty"]]))
    return result


class _CovarianceError(Exception):
    def __init__(self, code):
        self.code = code


class _JSON:
    """Strict structural JSON with exact decimal numbers and original spans."""
    _number = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+−-]?[0-9]+)?")

    def __init__(self, text):
        self.text, self.at, self.spans, self.tokens = text, 0, {}, {}

    def skip(self):
        while self.at < len(self.text) and self.text[self.at] in " \t\r\n":
            self.at += 1

    def parse(self, path=()):
        self.skip()
        start = self.at
        char = self.text[self.at:self.at + 1]
        if char == '"':
            try:
                value, end = json.JSONDecoder().raw_decode(self.text, self.at)
            except (ValueError, RecursionError) as error:
                raise _CovarianceError("unsupported_covariance_representation") from error
            self.at = end
        elif char == "{":
            self.at += 1
            value = {}
            self.skip()
            while self.text[self.at:self.at + 1] != "}":
                self.skip()
                if self.text[self.at:self.at + 1] != '"':
                    raise _CovarianceError("unsupported_covariance_representation")
                key = self.parse((*path, "__key__"))
                if key in value:
                    raise _CovarianceError("source_json_duplicate_key")
                self.skip()
                if self.text[self.at:self.at + 1] != ":":
                    raise _CovarianceError("unsupported_covariance_representation")
                self.at += 1
                value[key] = self.parse((*path, key))
                self.skip()
                separator = self.text[self.at:self.at + 1]
                if separator == "}":
                    break
                if separator != ",":
                    raise _CovarianceError("unsupported_covariance_representation")
                self.at += 1
                self.skip()
                if self.text[self.at:self.at + 1] == "}":
                    raise _CovarianceError("unsupported_covariance_representation")
            self.at += 1
        elif char == "[":
            self.at += 1
            value = []
            self.skip()
            while self.text[self.at:self.at + 1] != "]":
                value.append(self.parse((*path, len(value))))
                self.skip()
                separator = self.text[self.at:self.at + 1]
                if separator == "]":
                    break
                if separator != ",":
                    raise _CovarianceError("unsupported_covariance_representation")
                self.at += 1
                self.skip()
                if self.text[self.at:self.at + 1] == "]":
                    raise _CovarianceError("unsupported_covariance_representation")
            self.at += 1
        elif self.text.startswith(("NaN", "Infinity", "-Infinity"), self.at):
            raise _CovarianceError("source_json_nonfinite")
        elif self.text.startswith("true", self.at):
            value, self.at = True, self.at + 4
        elif self.text.startswith("false", self.at):
            value, self.at = False, self.at + 5
        elif self.text.startswith("null", self.at):
            value, self.at = None, self.at + 4
        else:
            number = self._number.match(self.text, self.at)
            if number is None:
                raise _CovarianceError("unsupported_covariance_representation")
            token = number.group()
            try:
                value = Fraction(token)
            except (ValueError, OverflowError) as error:
                raise _CovarianceError("unsupported_covariance_representation") from error
            self.tokens[path] = token
            self.at = number.end()
        self.spans[path] = start, self.at
        return value

    def load(self):
        try:
            result = self.parse()
            self.skip()
            if self.at != len(self.text):
                raise _CovarianceError("unsupported_covariance_representation")
            return result
        except (IndexError, RecursionError) as error:
            raise _CovarianceError("unsupported_covariance_representation") from error


def _psd(matrix):
    """Exact symmetric elimination; zero PSD pivots require a zero row."""
    work = [row[:] for row in matrix]
    for i in range(len(work)):
        pivot = work[i][i]
        if pivot < 0:
            return False
        if pivot == 0:
            if any(work[i][j] != 0 for j in range(i + 1, len(work))):
                return False
            continue
        for j in range(i + 1, len(work)):
            for k in range(j, len(work)):
                value = work[j][k] - work[j][i] * work[i][k] / pivot
                work[j][k] = work[k][j] = value
    return True


def _json_witness(reference, parser, path):
    start, end = parser.spans[path]
    return {"source_ref": reference, "representation": "original",
        "start": len(parser.text[:start].encode()), "end": len(parser.text[:end].encode()),
        "quote": parser.text[start:end]}


def _source_model_shape(document):
    fields = ("version", "variables", "covariance", "origin", "variance_status", "model_kind")
    if not isinstance(document, dict) or set(document) != set(fields) or document["version"] != COVARIANCE_VERSION:
        raise _CovarianceError("unsupported_covariance_representation")
    variables = document["variables"]
    if not isinstance(variables, list) or not variables:
        raise _CovarianceError("source_covariance_shape_invalid")
    for variable in variables:
        if not isinstance(variable, dict) or set(variable) != {"label", "unit", "description"} or any(
                not isinstance(v, str) or not v.strip() for v in variable.values()):
            raise _CovarianceError("unsupported_covariance_representation")
    if document["origin"] not in ("reported", "derived", "synthetic"):
        raise _CovarianceError("source_covariance_origin_invalid")
    if document["variance_status"] not in ("known", "estimated", "unknown") or document["model_kind"] not in ("none", "known_joint_normal_source_means"):
        raise _CovarianceError("unsupported_covariance_representation")
    n, matrix = len(variables), document["covariance"]
    if not isinstance(matrix, list) or len(matrix) != n or any(not isinstance(row, list) or len(row) != n for row in matrix):
        raise _CovarianceError("source_covariance_shape_invalid")
    if any(type(v) is not Fraction for row in matrix for v in row):
        raise _CovarianceError("source_covariance_shape_invalid")


def _empty_covariance(selected):
    return {"selection": deepcopy(selected), "source_ref": selected["source_ref"],
        "artifact_ref": None, "byte_sha256": None, "raw_text": None, "variables": [],
        "matrix_tokens": None, "exact_matrix": None, "source_model": None,
        "bindings": {role: {"selection": deepcopy(selected["bindings"][role]), "label_witness": None,
            "owner_witness": None, "correspondence": None, "source_variable_index": None,
            "resolved_owner_id": None, "state": "unknown", "diagnostics": []} for role in PRIMITIVE_ORDER},
        "projection_indices": None, "projected_exact_matrix": None, "calculation_covariance": None,
        "source_validation": "unassessed", "projection_state": "unavailable", "diagnostics": []}


def _covariance(context, selected, arms, relationships):
    if selected is None:
        return None
    result = _empty_covariance(selected)
    reference = selected["source_ref"]
    try:
        loaded = context.source(reference, "original")
    except _Unavailable:
        result["diagnostics"] = [_diag("source_dependency_unavailable", "covariance", "dependency", [reference])]
        return result
    result.update(artifact_ref=loaded["artifact_ref"], byte_sha256=_hash(loaded["content"]))
    try:
        text = loaded["content"].decode("utf-8")
    except UnicodeDecodeError:
        result.update(projection_state="unsupported_format", diagnostics=[_diag(
            "unsupported_covariance_representation", "covariance", "reader_capability", [reference])])
        return result
    result["raw_text"] = text
    parser = _JSON(text)
    try:
        document = parser.load()
        _source_model_shape(document)
    except _CovarianceError as error:
        result.update(source_validation="unassessed" if error.code == "unsupported_covariance_representation" else "invalid", projection_state="unsupported_format" if
            error.code == "unsupported_covariance_representation" else "source_invalid",
            diagnostics=[_diag(error.code, "covariance", "reader_capability" if error.code == "unsupported_covariance_representation" else "source_representation", [reference])])
        return result
    matrix = document["covariance"]
    result["source_model"] = {key: document[key] for key in ("origin", "variance_status", "model_kind")}
    result["matrix_tokens"] = [[parser.tokens[("covariance", i, j)] for j in range(len(matrix))] for i in range(len(matrix))]
    result["exact_matrix"] = [[_rational(v) for v in row] for row in matrix]
    for i, variable in enumerate(document["variables"]):
        parsed = _plain_unit(variable["unit"])
        native = next((key for key in RATE_UNITS if _plain_unit(key) == parsed), None) if parsed else None
        result["variables"].append({"index": i, **variable,
            **{field + "_witness": context.witness(_json_witness(reference, parser, ("variables", i, field)),
                "covariance.variables." + field) for field in ("label", "unit", "description")},
            "native_registry_unit": native, "exact_scale": _rational(parsed[1]) if parsed else None,
            "diagnostics": [] if native else [_diag("source_covariance_unit_unsupported", f"covariance.variables[{i}]", "reader_capability", [reference])]})
    if any(matrix[i][j] != matrix[j][i] for i in range(len(matrix)) for j in range(len(matrix))):
        result.update(source_validation="invalid", projection_state="source_invalid", diagnostics=[_diag(
            "source_covariance_asymmetric", "covariance", "source_representation", [reference])])
    elif not _psd(matrix):
        result.update(source_validation="invalid", projection_state="source_invalid", diagnostics=[_diag(
            "source_covariance_not_psd", "covariance", "source_representation", [reference])])
    else:
        result["source_validation"] = "valid"
    # Bind actual source label positions, not only decoded label equality.
    for role in PRIMITIVE_ORDER:
        nominated = selected["bindings"][role]
        binding = result["bindings"][role]
        if nominated is None:
            continue
        index = nominated["variable_index"]
        if index >= len(matrix):
            _fail("source_variable_index_out_of_bounds", "covariance.bindings." + role)
        label = context.witness(nominated["label_witness"], "covariance.bindings." + role + ".label")
        actual = result["variables"][index]["label_witness"]
        if label["canonical_locator"] is not None and label["canonical_locator"] != actual["canonical_locator"]:
            _fail("source_label_token_binding_mismatch", "covariance.bindings." + role)
        owner = context.witness(nominated["owner_witness"], "covariance.bindings." + role + ".owner")
        correspondence = _interpretation(context, nominated["correspondence"], "covariance.bindings." + role + ".correspondence")
        arm = arms[role]
        physical = arm["meanings"]["physical_observation"] if arm else None
        declared = [w["selection"] for w in physical["witnesses"]] + ([physical["canonical_witness"]["selection"]] if physical["canonical_witness"] else []) if physical else []
        if arm and nominated["owner_witness"] not in declared:
            _fail("owner_witness_not_in_role", "covariance.bindings." + role)
        state = "conflicting" if correspondence["effective_value"] == "conflicting" else "unknown"
        if (physical and physical["resolved_state"] == "known" and label["canonical_locator"] is not None
                and owner["canonical_locator"] is not None and correspondence["effective_value"] == "same"):
            state = "known"
        binding.update(label_witness=label, owner_witness=owner, correspondence=correspondence,
            source_variable_index=index, resolved_owner_id=physical["canonical_id"] if state == "known" else None,
            state=state, diagnostics=_unique_diagnostics([label, owner, correspondence]))
    if result["source_validation"] != "valid":
        return result
    states = [result["bindings"][role]["state"] for role in PRIMITIVE_ORDER]
    if any(state != "known" for state in states):
        conflicting = "conflicting" in states
        result.update(projection_state="binding_conflicting" if conflicting else "binding_unresolved",
            diagnostics=[_diag("covariance_owner_conflicting" if conflicting else "covariance_owner_unresolved",
                "covariance.bindings", "source_binding", [reference])])
        return result
    indices = [result["bindings"][role]["source_variable_index"] for role in PRIMITIVE_ORDER]
    result["projection_indices"] = indices
    projected = [[matrix[i][j] for j in indices] for i in indices]
    result["projected_exact_matrix"] = [[_rational(v) for v in row] for row in projected]
    if _cross_control_alias_conflict(arms):
        result.update(projection_state="binding_conflicting", diagnostics=[_diag(
            "covariance_shared_values_conflicting", "covariance.bindings.empty_condition1|empty_condition0",
            "source_binding", [reference])])
        return result
    variables = [result["variables"][i] for i in indices]
    if any(v["native_registry_unit"] is None for v in variables):
        result.update(projection_state="unavailable", diagnostics=[_diag(
            "source_covariance_unit_unsupported", "covariance.projection", "reader_capability", [reference])])
        return result
    operands = [arms[role]["calculation_operand"] for role in PRIMITIVE_ORDER]
    if any(arm is None or arm["unit"] is None for arm in operands):
        result.update(projection_state="unavailable", diagnostics=[_diag(
            "source_dependency_unavailable", "covariance.projection.operands", "dependency", [reference])])
        return result
    owners = [b["physical_observation_id"] for b in operands]
    scales = [_fraction(v["exact_scale"]) for v in variables]
    for i in range(4):
        for j in range(i):
            if indices[i] == indices[j] and owners[i] != owners[j]:
                result.update(projection_state="binding_conflicting", diagnostics=[_diag(
                    "covariance_owner_conflicting", "covariance.projection", "source_binding", [reference])])
                return result
            if owners[i] != owners[j]:
                continue
            a, b = indices[i], indices[j]
            if any(scales[i] * matrix[a][k] != scales[j] * matrix[b][k] for k in range(len(matrix))):
                result.update(projection_state="binding_conflicting", diagnostics=[_diag(
                    "covariance_shared_rows_conflicting", "covariance.projection", "source_binding", [reference])])
                return result
    finite_matrix = [[_finite(v) for v in row] for row in projected]
    if any(v is None for row in finite_matrix for v in row):
        result.update(projection_state="numeric_range", diagnostics=[_diag(
            "covariance_projection_numeric_range", "covariance.projection", "reader_capability", [reference])])
        return result
    finite_exact = [[Fraction(str(v)) for v in row] for row in finite_matrix]
    if not _psd(finite_exact):
        result.update(projection_state="precision_invalid", diagnostics=[_diag(
            "covariance_projection_precision_invalid", "covariance.projection", "reader_capability", [reference])])
        return result
    covariance = {"primitive_order": list(PRIMITIVE_ORDER), "physical_observation_ids": owners,
        "units": [v["native_registry_unit"] for v in variables], "matrix": finite_matrix}
    # Frozen API validation checks normalized alias values/context/rows and unit
    # dimensions without computing e, V or any sheet. Errors stay source partials.
    trial = {"version": INPUT_VERSION, "arms": {r:arms[r]["calculation_operand"] for r in PRIMITIVE_ORDER},
        "relationships": _relationships_inputs(relationships), "covariance": covariance,
        "variance_status": "known", "model_kind": "none"}
    try:
        validate_controlled_response_inputs(trial)
    except ExperimentalContractError as error:
        if error.code == "shared_measurement_covariance_mismatch":
            result.update(projection_state="precision_invalid", diagnostics=[_diag(
                "covariance_projection_precision_invalid", "covariance.projection", "reader_capability", [reference])])
            return result
        result.update(projection_state="binding_conflicting", diagnostics=[_diag(
            "covariance_shared_values_conflicting" if error.code == "shared_measurement_context_mismatch" else
            "source_covariance_unit_unsupported", "covariance.projection", "source_binding", [reference])])
        return result
    result.update(calculation_covariance=covariance, projection_state="available")
    if finite_exact != projected:
        result["diagnostics"].append(_diag("numeric_projection_rounding", "covariance.projection", "reader_capability", [reference]))
    return result


def _relationships(context, selected):
    return {key: _meaning(context, value, "condition", "relationships." + key)
            if key.endswith("_target") else context.witness(value, "relationships.intended_factor")
            if key == "intended_factor" else _interpretation(context, value, "relationships." + key)
            for key,value in selected.items()}


def _cross_control_alias_conflict(arms):
    left, right = (arms[role] for role in ("empty_condition1", "empty_condition0"))
    if left is None or right is None:
        return False
    owner = left["meanings"]["physical_observation"]["canonical_id"]
    if owner is None or owner != right["meanings"]["physical_observation"]["canonical_id"]:
        return False
    values = []
    for arm in (left, right):
        measurement = arm["measurement"]
        unit = measurement["unit"]
        if measurement["reading_status"] != "exact" or unit is None or unit["status"] != "supported":
            return False
        candidate = measurement["candidates"][0]
        exact = Fraction(candidate["raw_expression"].replace("−", "-")) * _fraction(unit["exact_scale"])
        values.append((exact, candidate["relation"], candidate["approximate"], unit["canonical_unit"]))
    return values[0] != values[1]


def _resolve_control_alias(arms, relationships):
    if not _cross_control_alias_conflict(arms):
        return
    refs = [arms[role]["measurement"]["candidates"][0]["source_locator"]["source_ref"]
            for role in ("empty_condition1", "empty_condition0")]
    record = relationships["control_reference_reuse"]
    record["effective_value"] = "conflicting"
    record["diagnostics"].append(_diag("source_literal_conflicting",
        "arms.empty_condition1|arms.empty_condition0", "source_binding", refs))


def _relationships_inputs(relationships):
    result = {}
    for key, value in relationships.items():
        if key.endswith("_target"):
            result[key] = {"status": value["resolved_state"], "canonical_id": value["canonical_id"]}
        elif key == "intended_factor":
            result[key] = identity("controlled_intended_factor", value["canonical_locator"]) if value and value["canonical_locator"] else None
        else:
            result[key] = value["effective_value"]
    return result


def _effective_model(requested, covariance, arms):
    result = {"variance_status": "unknown", "model_kind": "none", "diagnostics": []}
    if covariance is None or covariance["calculation_covariance"] is None:
        return result
    actual = covariance["source_model"]
    requested_status = requested["variance_status"]["effective_value"]
    if actual["variance_status"] == "unknown":
        result["diagnostics"].append(_diag("source_variance_status_unknown", "model", "source_interpretation"))
        return result
    if requested_status == "unknown":
        result["diagnostics"].append(_diag("variance_status_not_selected", "model", "source_interpretation"))
        return result
    if requested_status != actual["variance_status"]:
        result["diagnostics"].append(_diag("requested_source_variance_status_conflict", "model", "source_interpretation"))
        return result
    if actual["origin"] == "synthetic" and any(arm and arm["selection"]["source_kind"] != "synthetic_fixture" for arm in arms.values()):
        result["diagnostics"].append(_diag("synthetic_covariance_with_reported_operands", "model", "source_binding"))
        return result
    result["variance_status"] = actual["variance_status"]
    selected_model = requested["model_kind"]["effective_value"]
    if selected_model == "none":
        result["diagnostics"].append(_diag("normal_model_not_selected", "model", "source_interpretation"))
    elif selected_model != "known_joint_normal_source_means":
        result["diagnostics"].append(_diag("source_model_witness_unavailable", "model", "dependency"))
    elif actual["model_kind"] != "known_joint_normal_source_means":
        result["diagnostics"].append(_diag("source_normal_model_unsupported", "model", "source_interpretation"))
    elif any(d["code"] == "numeric_projection_rounding" for d in covariance["diagnostics"]):
        result["diagnostics"].append(_diag("source_model_projection_rounding", "model", "reader_capability"))
    else:
        result["model_kind"] = "known_joint_normal_source_means"
    return result


def _calculation_inputs(arms, relationships, covariance, effective):
    return {"version": INPUT_VERSION,
        "arms": {role: deepcopy(arms[role]["calculation_operand"]) if arms[role] else None for role in PRIMITIVE_ORDER},
        "relationships": _relationships_inputs(relationships),
        "covariance": deepcopy(covariance["calculation_covariance"]) if covariance and effective["variance_status"] != "unknown" else None,
        "variance_status": effective["variance_status"], "model_kind": effective["model_kind"]}


def read_controlled_response_inputs(arguments, *, read_source):
    """Read selected authorized bytes into the frozen parsed-input contract.

    ``read_source`` must authorize actual received/scope/ancestry references. Its
    ContractError or malformed success is never swallowed by image helper catches.
    Only actual OSError/EOFError availability failures become local partials.
    This function never calls a sheet calculator or makes an episode observation.
    """
    selected = validate_controlled_response_selection(arguments)
    context = _Context(selected, read_source)
    # Authenticate every nominated witness even when an independent data format
    # will later be unsupported. A malformed covariance cannot hide a forged
    # label/model nomination. Unavailable bytes remain explicitly unavailable.
    def authenticate(value, field):
        if isinstance(value, dict):
            if "quote" in value and ("source_ref" in value or value.get("kind") == "image"):
                context.witness(value, field)
            for key, item in value.items():
                authenticate(item, field + "." + key)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                authenticate(item, f"{field}[{i}]")
    authenticate(selected, "arguments")
    relationships = _relationships(context, selected["relationships"])
    arms = {role: _arm(context, selected["arms"][role], "arms." + role) for role in PRIMITIVE_ORDER}
    _resolve_control_alias(arms, relationships)
    requested = {name: _interpretation(context, selected[name], name) for name in ("variance_status", "model_kind")}
    covariance = _covariance(context, selected["covariance"], arms, relationships)
    effective = _effective_model(requested, covariance, arms)
    parsed = _calculation_inputs(arms, relationships, covariance, effective)
    validate_controlled_response_inputs(parsed)
    result = {"version": VERSION, "selection": selected, "sources": context.roster,
        "images": context.images, "arms": arms, "relationships": relationships,
        "covariance": covariance, "requested_model": requested, "effective_model": effective,
        "calculation_inputs": parsed, "diagnostics": [],
        "implementation_dependencies": {"reader_contract_version": VERSION,
            "calculator_contract_version": INPUT_VERSION, "expected_module_fingerprints": deepcopy(DEPENDENCIES)}}
    result["diagnostics"] = _unique_diagnostics(result)
    json.dumps(result, allow_nan=False)
    return deepcopy(result)


_RESULT_FIELDS = {'Diagnostic': ('code', 'field', 'domain', 'source_refs'),
 'SourceRecord': ('source_ref',
                  'representation',
                  'artifact_ref',
                  'byte_sha256',
                  'state',
                  'diagnostics'),
 'WitnessRecord': ('selection',
                   'artifact_ref',
                   'byte_sha256',
                   'canonical_locator',
                   'authentication',
                   'attribution',
                   'diagnostics'),
 'TextLocator': ('kind', 'source_ref', 'artifact_ref', 'byte_sha256', 'start', 'end'),
 'ImageLocator': ('kind',
                  'original_source_ref',
                  'original_artifact_ref',
                  'original_byte_sha256',
                  'region'),
 'InterpretationExtraction': ('selection', 'witnesses', 'effective_value', 'diagnostics'),
 'MeaningExtraction': ('selection',
                       'witnesses',
                       'canonical_witness',
                       'canonical_correspondence',
                       'resolved_state',
                       'canonical_id',
                       'diagnostics'),
 'NumberCandidate': ('selection',
                     'witness',
                     'raw_expression',
                     'native_value',
                     'relation',
                     'approximate',
                     'source_locator',
                     'status',
                     'diagnostics'),
 'UnitRecord': ('selection',
                'witness',
                'raw_unit',
                'canonical_unit',
                'exact_scale',
                'native_registry_unit',
                'definition_witnesses',
                'status',
                'diagnostics'),
 'Rational': ('numerator', 'denominator'),
 'CanonicalDisplay': ('value', 'threshold', 'unit', 'relation', 'approximate', 'diagnostics'),
 'MeasurementExtraction': ('selection',
                           'candidates',
                           'fragments',
                           'unit',
                           'graph_witnesses',
                           'reading_status',
                           'source_observation_id',
                           'canonical_display',
                           'pixel_result',
                           'diagnostics'),
 'UncertaintyExtraction': ('selection',
                           'meanings',
                           'magnitude',
                           'interval',
                           'unit',
                           'effective_unit',
                           'confidence_level',
                           'count',
                           'canonical',
                           'diagnostics'),
 'IntervalRecord': ('selection', 'witness', 'raw_values', 'values', 'status', 'diagnostics'),
 'ConfidenceRecord': ('selection', 'witness', 'value', 'status', 'diagnostics'),
 'CountRecord': ('selection', 'witness', 'reading', 'diagnostics'),
 'UncertaintyCanonical': ('statistic',
                          'magnitude',
                          'interval',
                          'confidence_level',
                          'count',
                          'repetition_basis',
                          'estimate_basis'),
 'ArmExtraction': ('selection',
                   'context',
                   'protein_arrangement',
                   'meanings',
                   'intended_factor_level',
                   'measurement',
                   'reported_uncertainty',
                   'calculation_operand',
                   'diagnostics'),
 'RelationshipExtraction': ('condition1_target',
                            'condition0_target',
                            'condition_levels_relation',
                            'subject_construct_across_conditions',
                            'condition1_control_application',
                            'condition0_control_application',
                            'control_reference_reuse',
                            'nonintended_conditions',
                            'intended_factor'),
 'CovarianceBindingExtraction': ('selection',
                                 'label_witness',
                                 'owner_witness',
                                 'correspondence',
                                 'source_variable_index',
                                 'resolved_owner_id',
                                 'state',
                                 'diagnostics'),
 'CovarianceSourceVariable': ('index',
                              'label',
                              'label_witness',
                              'unit',
                              'unit_witness',
                              'description',
                              'description_witness',
                              'native_registry_unit',
                              'exact_scale',
                              'diagnostics'),
 'CovarianceExtraction': ('selection',
                          'source_ref',
                          'artifact_ref',
                          'byte_sha256',
                          'raw_text',
                          'variables',
                          'matrix_tokens',
                          'exact_matrix',
                          'source_model',
                          'bindings',
                          'projection_indices',
                          'projected_exact_matrix',
                          'calculation_covariance',
                          'source_validation',
                          'projection_state',
                          'diagnostics'),
 'RequestedModel': ('variance_status', 'model_kind'),
 'EffectiveModel': ('variance_status', 'model_kind', 'diagnostics'),
 'DependencyRecord': ('reader_contract_version',
                      'calculator_contract_version',
                      'expected_module_fingerprints')}
_ROOT_FIELDS = ('version', 'selection', 'sources', 'images', 'arms', 'relationships', 'covariance', 'requested_model', 'effective_model', 'calculation_inputs', 'diagnostics', 'implementation_dependencies')


def _saved_witness(record, selected, sources, field):
    if selected is None:
        if record is not None:
            _fail("saved_selection_mismatch", field)
        return
    _closed(record, _RESULT_FIELDS["WitnessRecord"], field)
    expected = selected if "kind" in selected else {"kind": "text", **selected}
    if record["selection"] != expected:
        _fail("saved_selection_mismatch", field)
    locator = record["canonical_locator"]
    if record["authentication"] == "unavailable":
        if locator is not None or record["artifact_ref"] is not None or record["byte_sha256"] is not None:
            _fail("unavailable_witness_identity_mismatch", field)
        return
    if expected["kind"] == "text":
        source = sources.get((expected["source_ref"], expected["representation"]))
        if source is None or source["state"] != "available":
            _fail("saved_source_identity_mismatch", field)
        wanted = {"kind": "text", "source_ref": expected["source_ref"], "artifact_ref": source["artifact_ref"],
            "byte_sha256": source["byte_sha256"], "start": expected["start"], "end": expected["end"]}
        if (record["authentication"] != "exact_utf8_byte_span" or locator != wanted
                or record["artifact_ref"] != source["artifact_ref"] or record["byte_sha256"] != source["byte_sha256"]
                or expected["end"] - expected["start"] != len(expected["quote"].encode())):
            _fail("saved_witness_identity_mismatch", field)
    else:
        _closed(locator, _RESULT_FIELDS["ImageLocator"], field + ".canonical_locator")
        if record["authentication"] != "image_bytes_and_geometry_only" or record["attribution"] != "investigating_episode_interpretation":
            _fail("saved_image_authentication_mismatch", field)


def _saved_interpretation(record, selected, sources, field, *, control_alias=False):
    _closed(record, _RESULT_FIELDS["InterpretationExtraction"], field)
    if record["selection"] != selected or len(record["witnesses"]) != len(selected["witnesses"]):
        _fail("saved_selection_mismatch", field)
    for w, nominated in zip(record["witnesses"], selected["witnesses"]):
        _saved_witness(w, nominated, sources, field)
    effective = selected["value"] if all(w["canonical_locator"] is not None for w in record["witnesses"]) else "unknown"
    if control_alias:
        effective = "conflicting"
    if record["effective_value"] != effective:
        _fail("saved_interpretation_mismatch", field)


def _saved_meaning(record, selected, sources, category, field):
    _closed(record, _RESULT_FIELDS["MeaningExtraction"], field)
    if record["selection"] != selected or len(record["witnesses"]) != len(selected["witnesses"]):
        _fail("saved_selection_mismatch", field)
    for w, nominated in zip(record["witnesses"], selected["witnesses"]):
        _saved_witness(w, nominated, sources, field)
    _saved_witness(record["canonical_witness"], selected["canonical_witness"], sources, field)
    _saved_interpretation(record["canonical_correspondence"], selected["canonical_correspondence"], sources, field)
    state = "conflicting" if selected["status"] == "conflicting" or record["canonical_correspondence"]["effective_value"] == "conflicting" else "unknown"
    key = None
    if (selected["status"] == "known" and all(w["canonical_locator"] is not None for w in record["witnesses"])
            and record["canonical_witness"] and record["canonical_witness"]["canonical_locator"] is not None
            and record["canonical_correspondence"]["effective_value"] == "same"):
        state = "known"
        key = identity("controlled_" + category, record["canonical_witness"]["canonical_locator"])
    if (record["resolved_state"], record["canonical_id"]) != (state, key):
        _fail("saved_meaning_identity_mismatch", field)


def _saved_number(record, selected, sources, field):
    _closed(record, _RESULT_FIELDS["NumberCandidate"], field)
    if record["selection"] != selected:
        _fail("saved_selection_mismatch", field)
    _saved_witness(record["witness"], selected["witness"], sources, field)
    locator = record["witness"]["canonical_locator"]
    if locator is None:
        if any(record[k] is not None for k in ("raw_expression", "native_value", "source_locator")) or record["status"] != "dependency_unavailable":
            _fail("saved_unavailable_number_mismatch", field)
        return
    text = selected["witness"]["quote"]
    raw = text[selected["number_start"]:selected["number_end"]]
    expected = deepcopy(locator)
    expected["start"] += len(text[:selected["number_start"]].encode())
    expected["end"] = expected["start"] + len(raw.encode())
    if record["raw_expression"] != raw or record["source_locator"] != expected:
        _fail("saved_numeric_location_mismatch", field)
    if record["status"] == "parsed":
        try:
            number = float(raw.replace("−", "-"))
        except ValueError:
            _fail("saved_numeric_literal_mismatch", field)
        if (not math.isfinite(number) or number == 0 and Fraction(raw.replace("−", "-")) != 0
                or record["native_value"] != number or record["relation"] not in ("point", "lt", "le", "gt", "ge")
                or type(record["approximate"]) is not bool):
            _fail("saved_numeric_literal_mismatch", field)
    elif record["status"] not in ("unsupported", "numeric_range") or record["native_value"] is not None:
        _fail("saved_numeric_state_mismatch", field)


def _saved_unit(record, selected, sources, field):
    if record is None:
        if selected is not None:
            _fail("saved_selection_mismatch", field)
        return
    _closed(record, _RESULT_FIELDS["UnitRecord"], field)
    if record["selection"] != selected:
        _fail("saved_selection_mismatch", field)
    if selected is None:
        if record["status"] != "unknown" or any(record[k] is not None for k in ("witness", "raw_unit", "canonical_unit", "exact_scale", "native_registry_unit", "definition_witnesses")):
            _fail("saved_unknown_unit_mismatch", field)
        return
    defined = selected.get("kind") == "source_defined_rate_unit"
    nominated = selected["witness"] if defined else selected
    _saved_witness(record["witness"], nominated, sources, field)
    if record["witness"]["canonical_locator"] is not None and record["raw_unit"] != nominated["quote"]:
        _fail("saved_unit_literal_mismatch", field)
    if defined:
        definitions = record["definition_witnesses"]
        _closed(definitions, selected["definition"], field + ".definition")
        for key, nomination in selected["definition"].items():
            if key == "amount":
                _saved_number(definitions[key], nomination, sources, field + ".definition.amount")
            else:
                _saved_witness(definitions[key], nomination, sources, field + ".definition." + key)
    elif record["status"] == "supported":
        actual = _plain_unit(record["raw_unit"])
        if actual is None or actual != (record["canonical_unit"], _fraction(record["exact_scale"])):
            _fail("saved_unit_scale_mismatch", field)
    if record["status"] == "supported":
        expected = next((key for key in RATE_UNITS if _plain_unit(key) == (record["canonical_unit"], _fraction(record["exact_scale"]))), None)
        if record["native_registry_unit"] != expected:
            _fail("saved_unit_registry_mismatch", field)


def validate_controlled_response_extraction(arguments, extraction):
    """Check detached saved consistency, never grant custody or source access.

    No callback, acquisition, image decoder or source literal reader is invoked.
    Original runtime request/source/operation/outcome binding is still required:
    self-consistent hashes/quotes are not independent authentication of evidence.
    """
    selected = validate_controlled_response_selection(arguments)
    _closed(extraction, _ROOT_FIELDS, "extraction")
    if extraction["version"] != VERSION or extraction["selection"] != selected:
        _fail("saved_selection_mismatch", "extraction")
    expected_dependencies = {"reader_contract_version": VERSION, "calculator_contract_version": INPUT_VERSION,
                             "expected_module_fingerprints": DEPENDENCIES}
    if extraction["implementation_dependencies"] != expected_dependencies:
        _fail("saved_dependency_contract_mismatch", "implementation_dependencies")
    source_map = {}
    for source in extraction["sources"]:
        _closed(source, _RESULT_FIELDS["SourceRecord"], "sources")
        key = source["source_ref"], source["representation"]
        if key in source_map:
            _fail("saved_duplicate_source", "sources")
        source_map[key] = source
        if source["state"] == "available":
            if not isinstance(source["artifact_ref"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["byte_sha256"] or ""):
                _fail("saved_source_identity_mismatch", "sources")
        elif source["state"] != "unavailable" or source["artifact_ref"] is not None or source["byte_sha256"] is not None:
            _fail("saved_source_state_mismatch", "sources")
    if set(source_map) != set(_reference_closure(selected)):
        _fail("saved_source_roster_mismatch", "sources")
    _closed(extraction["arms"], PRIMITIVE_ORDER, "arms")
    for role, arm in extraction["arms"].items():
        nomination = selected["arms"][role]
        if nomination is None:
            if arm is not None:
                _fail("saved_selection_mismatch", role)
            continue
        _closed(arm, _RESULT_FIELDS["ArmExtraction"], role)
        if arm["selection"] != nomination:
            _fail("saved_selection_mismatch", role)
        for name in _MEANINGS:
            _saved_meaning(arm["meanings"][name], nomination[name], source_map, name, role + "." + name)
        _saved_interpretation(arm["protein_arrangement"], nomination["protein_arrangement"], source_map, role)
        _closed(arm["context"], nomination["context"], role + ".context")
        for key, record in arm["context"].items():
            _saved_witness(record, nomination["context"][key], source_map, role + ".context." + key)
        _saved_witness(arm["intended_factor_level"], nomination["intended_factor_level"], source_map, role)
        measurement = arm["measurement"]
        _closed(measurement, _RESULT_FIELDS["MeasurementExtraction"], role + ".measurement")
        nominated = nomination["measurement"]
        if measurement["selection"] != nominated:
            _fail("saved_selection_mismatch", role + ".measurement")
        if nominated and nominated["kind"] == "source_literal":
            literal = nominated["literal"]
            if len(measurement["candidates"]) != len(literal["candidates"]) or len(measurement["fragments"]) != len(literal["fragments"]):
                _fail("saved_selection_mismatch", role + ".measurement")
            for record, selector in zip(measurement["candidates"], literal["candidates"]):
                _saved_number(record, selector, source_map, role)
            for record, selector in zip(measurement["fragments"], literal["fragments"]):
                _saved_witness(record, selector, source_map, role)
            _saved_unit(measurement["unit"], nominated["unit"], source_map, role)
            candidate = measurement["candidates"][0] if measurement["reading_status"] == "exact" else None
            if measurement["canonical_display"] != _display(candidate, measurement["unit"]):
                _fail("saved_canonical_display_mismatch", role)
        if arm["calculation_operand"] != _operand_from_arm(arm):
            _fail("saved_operand_projection_mismatch", role)
        uncertainty = arm["reported_uncertainty"]
        _closed(uncertainty, _RESULT_FIELDS["UncertaintyExtraction"], role + ".reported_uncertainty")
        if uncertainty["selection"] != nomination["reported_uncertainty"]:
            _fail("saved_selection_mismatch", role + ".reported_uncertainty")
    relationships = extraction["relationships"]
    _closed(relationships, selected["relationships"], "relationships")
    conflict = _cross_control_alias_conflict(extraction["arms"])
    for key, record in relationships.items():
        if key.endswith("_target"):
            _saved_meaning(record, selected["relationships"][key], source_map, "condition", key)
        elif key == "intended_factor":
            _saved_witness(record, selected["relationships"][key], source_map, key)
        else:
            _saved_interpretation(record, selected["relationships"][key], source_map, key,
                                  control_alias=key == "control_reference_reuse" and conflict)
    covariance = extraction["covariance"]
    if covariance is None:
        if selected["covariance"] is not None:
            _fail("saved_selection_mismatch", "covariance")
    else:
        _closed(covariance, _RESULT_FIELDS["CovarianceExtraction"], "covariance")
        if covariance["selection"] != selected["covariance"]:
            _fail("saved_selection_mismatch", "covariance")
        if covariance["raw_text"] is not None:
            actual_hash = _hash(covariance["raw_text"].encode())
            source = source_map[(covariance["source_ref"], "original")]
            if actual_hash != covariance["byte_sha256"] or actual_hash != source["byte_sha256"] or covariance["artifact_ref"] != source["artifact_ref"]:
                _fail("saved_covariance_source_mismatch", "covariance")
            parser = _JSON(covariance["raw_text"])
            try:
                document = parser.load()
                _source_model_shape(document)
            except _CovarianceError as error:
                expected = "unassessed" if error.code == "unsupported_covariance_representation" else "invalid"
                if covariance["source_validation"] != expected or covariance["calculation_covariance"] is not None:
                    _fail("saved_covariance_invalid_state_mismatch", "covariance")
            else:
                matrix = document["covariance"]
                expected_model = {key: document[key] for key in ("origin", "variance_status", "model_kind")}
                if covariance["source_model"] != expected_model or len(covariance["variables"]) != len(document["variables"]):
                    _fail("saved_covariance_model_mismatch", "covariance")
                tokens = [[parser.tokens[("covariance", i, j)] for j in range(len(matrix))] for i in range(len(matrix))]
                if covariance["matrix_tokens"] != tokens:
                    _fail("saved_covariance_lexeme_mismatch", "covariance")
                if covariance["exact_matrix"] != [[_rational(v) for v in row] for row in matrix]:
                    _fail("saved_covariance_matrix_mismatch", "covariance")
                valid = all(matrix[i][j] == matrix[j][i] for i in range(len(matrix)) for j in range(len(matrix))) and _psd(matrix)
                if covariance["source_validation"] != ("valid" if valid else "invalid"):
                    _fail("saved_covariance_validation_mismatch", "covariance")
                for i, variable in enumerate(covariance["variables"]):
                    _closed(variable, _RESULT_FIELDS["CovarianceSourceVariable"], "covariance.variables")
                    for name in ("label", "unit", "description"):
                        if variable[name] != document["variables"][i][name]:
                            _fail("saved_covariance_variable_mismatch", "covariance.variables")
                        _saved_witness(variable[name + "_witness"], _json_witness(covariance["source_ref"], parser, ("variables", i, name)), source_map, "covariance.variables")
                _closed(covariance["bindings"], PRIMITIVE_ORDER, "covariance.bindings")
                for role, binding in covariance["bindings"].items():
                    nomination = selected["covariance"]["bindings"][role]
                    _closed(binding, _RESULT_FIELDS["CovarianceBindingExtraction"], "covariance.bindings." + role)
                    if binding["selection"] != nomination:
                        _fail("saved_selection_mismatch", "covariance.bindings." + role)
                    if nomination is None:
                        if binding["state"] != "unknown" or binding["resolved_owner_id"] is not None:
                            _fail("saved_owner_binding_mismatch", "covariance.bindings." + role)
                        continue
                    index = nomination["variable_index"]
                    if index >= len(matrix) or binding["source_variable_index"] != index:
                        _fail("saved_label_index_mismatch", "covariance.bindings." + role)
                    _saved_witness(binding["label_witness"], nomination["label_witness"], source_map, role)
                    _saved_witness(binding["owner_witness"], nomination["owner_witness"], source_map, role)
                    _saved_interpretation(binding["correspondence"], nomination["correspondence"], source_map, role)
                    if binding["label_witness"]["canonical_locator"] is not None and binding["label_witness"]["canonical_locator"] != covariance["variables"][index]["label_witness"]["canonical_locator"]:
                        _fail("saved_label_token_mismatch", "covariance.bindings." + role)
                    arm = extraction["arms"][role]
                    physical = arm["meanings"]["physical_observation"] if arm else None
                    known = (physical and physical["resolved_state"] == "known"
                        and binding["label_witness"]["canonical_locator"] is not None
                        and binding["owner_witness"]["canonical_locator"] is not None
                        and binding["correspondence"]["effective_value"] == "same")
                    state = "known" if known else "conflicting" if binding["correspondence"]["effective_value"] == "conflicting" else "unknown"
                    if (binding["state"], binding["resolved_owner_id"]) != (state, physical["canonical_id"] if known else None):
                        _fail("saved_owner_binding_mismatch", "covariance.bindings." + role)
                indices = covariance["projection_indices"]
                if indices is not None:
                    expected_indices = [covariance["bindings"][role]["source_variable_index"] for role in PRIMITIVE_ORDER]
                    if indices != expected_indices or covariance["projected_exact_matrix"] != [[_rational(matrix[i][j]) for j in indices] for i in indices]:
                        _fail("saved_covariance_projection_mismatch", "covariance")
                finite_covariance = covariance["calculation_covariance"]
                if finite_covariance is not None:
                    if indices is None or covariance["projection_state"] != "available":
                        _fail("saved_covariance_projection_mismatch", "covariance")
                    expected_covariance = {"primitive_order": list(PRIMITIVE_ORDER),
                        "physical_observation_ids": [covariance["bindings"][role]["resolved_owner_id"] for role in PRIMITIVE_ORDER],
                        "units": [covariance["variables"][i]["native_registry_unit"] for i in indices],
                        "matrix": [[_finite(matrix[i][j]) for j in indices] for i in indices]}
                    if finite_covariance != expected_covariance:
                        _fail("saved_covariance_finite_projection_mismatch", "covariance")
    for key, record in extraction["requested_model"].items():
        _saved_interpretation(record, selected[key], source_map, key)
    effective = _effective_model(extraction["requested_model"], covariance, extraction["arms"])
    if extraction["effective_model"] != effective:
        _fail("saved_effective_model_mismatch", "effective_model")
    parsed = _calculation_inputs(extraction["arms"], relationships, covariance, effective)
    if extraction["calculation_inputs"] != parsed:
        _fail("saved_calculation_projection_mismatch", "calculation_inputs")
    validate_controlled_response_inputs(parsed)
    json.dumps(extraction, allow_nan=False)
    return deepcopy(extraction)


__all__ = ["VERSION", "SELECTION_VERSION", "COVARIANCE_VERSION", "DEPENDENCIES",
    "controlled_response_arguments_schema", "validate_controlled_response_selection",
    "read_controlled_response_inputs", "validate_controlled_response_extraction"]
