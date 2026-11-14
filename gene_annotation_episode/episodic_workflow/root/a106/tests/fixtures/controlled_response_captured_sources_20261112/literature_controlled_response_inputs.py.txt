"""Source-bound four-arm inputs within A105; no scientific sheet calculation.

Selections assign scientific meanings. Exact bytes/geometry establish custody
only; original runtime authorization and outcome binding remain caller owned.
The v1 profile retains its original text/structured covariance semantics and
unimplemented graph nominations. Explicit HOST stages also serve full v2, whose
graph facade supplies actual063 measurements before shared science assembly.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import errno
import hashlib
import json
import math
import re
from types import MappingProxyType

from jsonschema import Draft202012Validator
from .domain import REF, ContractError, identity
from .literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
from .literature_assay_inputs import _Sources
from .literature_rate_native_inputs import (
    _number as _native_number, _unit as _native_unit, _plain_unit,
    _scale as _native_scale, _check_explicit_unit, _field_contexts,
)
from .literature_partner_defined_units import defined_rate_unit_schema, _definition_scale
from .literature_kinetic_inputs import _count_reading, _interval, _confidence, _cardinal_count
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


def _unique_diagnostics(value, *, stable=False):
    records = {json.dumps(d, sort_keys=True): d for d in _all_diagnostics(value)}
    return [records[key] for key in sorted(records)] if stable else list(records.values())


def controlled_response_arguments_schema():
    """Closed nominations only; numerical scientific operands are never inputs."""
    return deepcopy(_SELECTION_SCHEMA)


def _nomination_key(witness):
    if witness.get("kind") == "image":
        return ("image", witness["image_id"], tuple(witness["region"]))
    return ("text", witness["source_ref"], witness["representation"], witness["start"], witness["end"])


def validate_controlled_response_selection(arguments):
    """Validate the whole closed nomination before any callback or decoding."""
    return _validate_selection(arguments, _SELECTION_SCHEMA)


def _validate_selection(arguments, schema):
    try:
        Draft202012Validator(schema).validate(arguments)
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
            if set(value) == {"left", "top", "right", "bottom"} and (value["left"] >= value["right"] or value["top"] >= value["bottom"]):
                _fail("nonempty_integer_image_region_required", field)
            if "rgb_min" in value and any(a > b for a,b in zip(value["rgb_min"], value["rgb_max"])):
                _fail("invalid_rgb_range", field)
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
        self.unavailable_errors = {}
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
            except OSError as error:
                if error.errno not in (errno.ENOENT, errno.EIO, errno.ETIMEDOUT):
                    raise
                self.unavailable_errors[(reference, representation)] = error
                loaded = _Unavailable()
                record.update(state="unavailable", diagnostics=[_diag("source_dependency_unavailable",
                    "sources", "dependency", [reference])])
            except EOFError as error:
                self.unavailable_errors[(reference, representation)] = error
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
            self.cache[(reference, representation)] = loaded if isinstance(loaded, _Unavailable) else dict(loaded)
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
            # The retained selection contains the authenticated literal even
            # when its admitted input supplied only source coordinates.
            selected["quote"] = actual["quote"]
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
                image = self.visual.images[selected["image_id"]]
                missing = [ref for ref in (image["source_ref"], image["original_source_ref"])
                           if isinstance(self.cache[(ref, "original")], _Unavailable)]
                record["diagnostics"] = ([_diag("source_dependency_unavailable", field, "dependency", missing)] if missing else
                    [_diag("source_image_format_unsupported" if code in
                    ("unsupported_image_format", "unsupported_image_mode", "single_frame_required") else
                    "source_image_decode_failed", field, "reader_capability")])
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
        parse_selection = _ci_literal_subselection(selected) if kind == "interval" and getattr(context,"profile","v1") in ("v2", "v3") else selected
        reading = {"interval": _interval, "confidence": _confidence, "count": _count_reading}[kind](parse_selection, context.native)
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
    if hasattr(context, "saved_uncertainty"):
        saved = context.saved_uncertainty
        if saved["selection"] != selected: _fail("saved_selection_mismatch", field)
        return deepcopy(saved["value"])
    tagged = getattr(context, "profile", "v1") in ("v2", "v3")
    response_carrier = response_unit
    response_unit = response_unit["record"] if tagged and response_unit is not None else response_unit
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
    if magnitude and magnitude["status"] == "parsed" and effective_unit and effective_unit["status"] == "supported":
        try:
            actual_number = _native_number(magnitude["selection"], context.native, "spread")
            actual_unit = (_native_unit(effective_unit["selection"], context.native,
                effective_unit["selection"]["definition"]["endpoint"] if effective_unit["definition_witnesses"] else None)
                if not tagged or relationship == "explicit_unit" else
                {"canonical_unit": effective_unit["canonical_unit"], "raw_unit": effective_unit["raw_unit"],
                 "source_defined_unit": None})
            _check_explicit_unit(actual_number, actual_unit, context.native)
        except ExperimentalContractError as error:
            if error.code == "source_spread_unit_mismatch":
                effective_unit = None
                diagnostics.append(_diag("source_uncertainty_unit_conflicting", field, "source_interpretation"))
            else:
                raise
    if tagged and interval and interval["status"] == "parsed" and effective_unit and effective_unit["status"] == "supported":
        narrowed = _ci_literal_subselection(interval["selection"])
        witness = {**narrowed["witness"], "artifact_ref": interval["witness"]["artifact_ref"]}
        _, suffix = _field_contexts(context.native, witness, 0, len(witness["quote"]))
        if _retained_printed_unit_conflict(suffix, effective_unit):
            effective_unit = None
            diagnostics.append(_diag("source_uncertainty_unit_conflicting", field, "source_interpretation"))
    result = _assemble_uncertainty(selected, meanings=meanings, magnitude=magnitude,
        interval=interval, confidence=confidence, count=count, unit=unit,
        effective_unit=effective_unit, diagnostics=diagnostics, field=field, stable=tagged)
    if tagged and result["effective_unit"] is not None:
        result["effective_unit"] = (deepcopy(response_carrier) if relationship == "same_as_response"
            else {"kind": "text", "record": result["effective_unit"]})
    return result


def _assemble_uncertainty(selected, *, meanings, magnitude, interval, confidence,
                          count, unit, effective_unit, diagnostics, field, stable=False):
    """Arithmetic on retained readings shared by live and detached science."""
    statistic = meanings["statistic"]["effective_value"]
    if (statistic == "unreported" and any(item is not None for item in (magnitude, interval, confidence))
            or statistic == "ci" and magnitude is not None
            or statistic in ("sd", "sem") and any(item is not None for item in (interval, confidence))):
        statistic = "conflicting"
        diagnostics.append(_diag("source_uncertainty_meaning_conflict", field, "source_interpretation"))
    spread = _display(magnitude, effective_unit)["value"]
    bounds = None
    if interval and interval["status"] == "parsed" and effective_unit and effective_unit["status"] == "supported":
        exact_bounds = [Fraction(v.replace("−", "-")) * _fraction(effective_unit["exact_scale"]) for v in interval["raw_values"]]
        values = [_finite(v) for v in exact_bounds]
        if all(v is not None for v in values) and not (values[0] == values[1] and exact_bounds[0] != exact_bounds[1]):
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
    result["diagnostics"].extend(_unique_diagnostics([meanings, magnitude, interval, unit, confidence, count], stable=stable))
    if stable:
        result["diagnostics"] = _unique_diagnostics(result["diagnostics"], stable=True)
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


def _covariance_document_facts(context, selected):
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
        if isinstance(document, dict) and document.get("version") == COVARIANCE_VERSION:
            model = {key: document.get(key) for key in ("origin", "variance_status", "model_kind")}
            if (model["origin"] in ("reported", "derived", "synthetic")
                    and model["variance_status"] in ("known", "estimated", "unknown")
                    and model["model_kind"] in ("none", "known_joint_normal_source_means")):
                result["source_model"] = model
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
    return result


def _covariance(context, selected, arms, relationships, *, owner_profile=False):
    result = _covariance_document_facts(context, selected)
    if result is None or result["exact_matrix"] is None:
        return result
    reference = selected["source_ref"]
    matrix = [[_fraction(v) for v in row] for row in result["exact_matrix"]]
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
    if owner_profile:
        return _project_owner_covariance(result, matrix, arms, relationships)
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
    Only explicit ENOENT/EIO/ETIMEDOUT OSError, or the callback's explicit EOFError
    signal for unavailable/truncated retained bytes, become availability partials.
    Other exceptions (including OSError with no errno) propagate as callback
    failures, not source findings.
    This function never calls a sheet calculator or makes an episode observation.
    """
    selected = validate_controlled_response_selection(arguments)
    with SourceContext(selected, read_source) as context:
        arms = {}
        for role in PRIMITIVE_ORDER:
            nominated = context.arguments["arms"][role]
            if nominated is None:
                arms[role] = None
            else:
                # The legacy ordering (meaning, measurement, context) is retained.
                arms[role] = _arm(context, nominated, "arms." + role)
        return finish_controlled_response_inputs(context, arms=arms)


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
        if definitions is None:
            if (record["status"] != "dependency_unavailable" or record["witness"]["canonical_locator"] is not None
                    or any(record[key] is not None for key in ("raw_unit", "canonical_unit", "exact_scale", "native_registry_unit"))):
                _fail("saved_unavailable_definition_mismatch", field)
            return
        _closed(definitions, selected["definition"], field + ".definition")
        for key, nomination in selected["definition"].items():
            if key == "amount":
                _saved_number(definitions[key], nomination, sources, field + ".definition.amount")
            else:
                _saved_witness(definitions[key], nomination, sources, field + ".definition." + key)
        if record["status"] == "supported":
            legacy = {}
            for key, saved in definitions.items():
                if key == "amount":
                    witness = saved["witness"]
                    original = {k:v for k,v in witness["selection"].items() if k != "kind"}
                    original["artifact_ref"] = witness["artifact_ref"]
                    legacy[key] = {"selector": {**saved["selection"], "witness": original},
                        "raw_number": saved["raw_expression"], "value": saved["native_value"], "relation": saved["relation"]}
                else:
                    legacy[key] = {**{k:v for k,v in saved["selection"].items() if k != "kind"}, "artifact_ref": saved["artifact_ref"]}
            if record["canonical_unit"] != "umol/min/mg" or _fraction(record["exact_scale"]) != _definition_scale(legacy) / 1000000:
                _fail("saved_unit_scale_mismatch", field)
    elif record["status"] == "supported":
        actual = _plain_unit(record["raw_unit"])
        if actual is None or actual != (record["canonical_unit"], _fraction(record["exact_scale"])):
            _fail("saved_unit_scale_mismatch", field)
    if record["status"] == "supported":
        expected = next((key for key in RATE_UNITS if _plain_unit(key) == (record["canonical_unit"], _fraction(record["exact_scale"]))), None)
        if record["native_registry_unit"] != expected:
            _fail("saved_unit_registry_mismatch", field)


def _validate_v1_saved_science(arguments, extraction):
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
    if len(extraction["images"]) != len(selected["images"]):
        _fail("saved_image_roster_mismatch", "images")
    image_fields = ("image_id", "source_ref", "artifact_ref", "byte_sha256", "original_source_ref",
        "original_artifact_ref", "original_byte_sha256", "actual_format", "actual_mode", "width", "height",
        "frame_count", "mapping", "pillow_version", "error")
    for image, nominated in zip(extraction["images"], selected["images"]):
        _closed(image, image_fields, "images")
        if any(image[k] != nominated[k] for k in ("image_id", "source_ref", "original_source_ref", "mapping")):
            _fail("saved_image_selection_mismatch", "images")
        for prefix, reference in (("", image["source_ref"]), ("original_", image["original_source_ref"])):
            source = source_map[(reference, "original")]
            if image[prefix + "artifact_ref"] is not None and (image[prefix + "artifact_ref"] != source["artifact_ref"] or image[prefix + "byte_sha256"] != source["byte_sha256"]):
                _fail("saved_image_source_mismatch", "images")
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
        _closed(arm["meanings"], _MEANINGS, role + ".meanings")
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
        unc_nom = nomination["reported_uncertainty"]
        _closed(uncertainty["meanings"], ("statistic", "unit_relationship", "repetition_basis", "estimate_basis"), role + ".uncertainty.meanings")
        for key, record in uncertainty["meanings"].items():
            _saved_interpretation(record, unc_nom[key], source_map, role + ".uncertainty." + key)
        if unc_nom["magnitude"] is not None:
            _saved_number(uncertainty["magnitude"], unc_nom["magnitude"], source_map, role + ".uncertainty.magnitude")
        elif uncertainty["magnitude"] is not None:
            _fail("saved_selection_mismatch", role + ".uncertainty.magnitude")
        _saved_unit(uncertainty["unit"], unc_nom["unit"], source_map, role + ".uncertainty.unit")
        _closed(uncertainty["canonical"], _RESULT_FIELDS["UncertaintyCanonical"], role + ".uncertainty.canonical")
        for key, type_name in (("interval", "IntervalRecord"), ("confidence_level", "ConfidenceRecord"), ("count", "CountRecord")):
            record, selected_piece = uncertainty[key], unc_nom[key]
            if selected_piece is None:
                if record is not None: _fail("saved_selection_mismatch", role + ".uncertainty." + key)
                continue
            _closed(record, _RESULT_FIELDS[type_name], role + ".uncertainty." + key)
            if record["selection"] != selected_piece:
                _fail("saved_selection_mismatch", role + ".uncertainty." + key)
            _saved_witness(record["witness"], selected_piece if key == "confidence_level" else selected_piece["witness"], source_map, role + ".uncertainty." + key)
            if key == "count" and record["reading"] is not None:
                reading = record["reading"]
                _closed(reading, ("selector", "raw_number", "value", "notation", "relation", "approximate", "status", "unavailable_reason"), role + ".uncertainty.count.reading")
                raw = selected_piece["witness"]["quote"][selected_piece["number_start"]:selected_piece["number_end"]]
                if reading["raw_number"] != raw:
                    _fail("saved_count_literal_mismatch", role)
        expected_count = (uncertainty["count"]["reading"]["value"] if uncertainty["count"] and uncertainty["count"]["reading"]
                          and uncertainty["count"]["reading"]["status"] == "exact" else None)
        if uncertainty["canonical"]["count"] != expected_count:
            _fail("saved_count_projection_mismatch", role)
        if uncertainty["count"] and uncertainty["count"]["reading"]:
            reading = uncertainty["count"]["reading"]
            raw = reading["raw_number"]
            value = int(raw.replace("−", "-")) if re.fullmatch(r"[-−]?[0-9]+", raw) else _cardinal_count(raw)
            if reading["status"] in ("exact", "qualified", "not_positive") and reading["value"] != value:
                _fail("saved_count_literal_mismatch", role)
        confidence = uncertainty["confidence_level"]
        if confidence and confidence["status"] == "parsed":
            raw = confidence["selection"]["quote"].strip()
            try:
                value = _finite(Fraction(raw[:-1].strip().replace("−", "-")) / 100) if raw.endswith("%") else None
            except ValueError:
                value = None
            if confidence["value"] != value or value is None or not 0 < value < 1:
                _fail("saved_confidence_literal_mismatch", role)
        effective_unit = uncertainty["effective_unit"]
        expected_spread = _display(uncertainty["magnitude"], effective_unit)["value"]
        if uncertainty["canonical"]["magnitude"] != expected_spread:
            _fail("saved_uncertainty_projection_mismatch", role)
        expected_interval = None
        interval = uncertainty["interval"]
        if interval and interval["status"] == "parsed":
            selection = interval["selection"]
            quote = selection["witness"]["quote"]
            raw_values = [quote[selection[side + "_start"]:selection[side + "_end"]] for side in ("lower", "upper")]
            if interval["raw_values"] != raw_values or interval["values"] != [float(raw.replace("−", "-")) for raw in raw_values]:
                _fail("saved_interval_literal_mismatch", role)
            if effective_unit and effective_unit["status"] == "supported":
                exact = [Fraction(v.replace("−", "-")) * _fraction(effective_unit["exact_scale"]) for v in raw_values]
                values = [_finite(v) for v in exact]
                if all(v is not None for v in values) and not (values[0] == values[1] and exact[0] != exact[1]):
                    expected_interval = values
        if uncertainty["canonical"]["interval"] != expected_interval or uncertainty["canonical"]["confidence_level"] != (confidence["value"] if confidence else None):
            _fail("saved_uncertainty_projection_mismatch", role)
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
        if covariance["selection"] != selected["covariance"] or covariance["source_ref"] != selected["covariance"]["source_ref"]:
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


def validate_controlled_response_extraction(arguments, extraction):
    selected = validate_controlled_response_selection(arguments)
    return validate_controlled_response_saved_science(selected, extraction,
        measurement_checks=None)


__all__ = ["VERSION", "SELECTION_VERSION", "COVARIANCE_VERSION", "DEPENDENCIES",
    "controlled_response_arguments_schema", "validate_controlled_response_selection",
    "read_controlled_response_inputs", "validate_controlled_response_extraction"]

# HOST stages are deliberately explicit imports, outside the original __all__.
class _StageValue(dict):
    def __init__(self, context, value):
        super().__init__(deepcopy(value))
        self._context = context


class SourceContext(_Context):
    """One validated, prefetched source closure; no provider survives close."""
    def __init__(self, arguments, callback):
        self.arguments = deepcopy(arguments)
        self._profile = {SELECTION_VERSION: "v1", "controlled_response_source_selection_v2": "v2",
            "controlled_response_source_selection_v3": "v3"}.get(arguments["version"])
        if self._profile is None:
            _fail("controlled_selection_schema_invalid", "arguments")
        self.closed = False
        self._endpoints = {}
        self.visual = None
        if self.profile == "v3":
            _initialize_v3_registries(self)
        try:
            super().__init__(self.arguments, callback)
            _authenticate_request(self, self.arguments, "arguments")
            self.relationships = _relationships(self, self.arguments["relationships"])
            if self.profile == "v3":
                self._v3_relationships = _frozen_json(self.relationships)
                self.cache = MappingProxyType({key: value if isinstance(value, _Unavailable)
                    else MappingProxyType(value) for key, value in self.cache.items()})
        except BaseException:
            self.close()
            raise

    @property
    def profile(self):
        return self._profile

    def read_source(self, source_ref, representation):
        self._active()
        value = self.source(source_ref, representation)
        return dict(value)

    def source(self, reference, representation):
        value = super().source(reference, representation)
        # Native helpers receive their ordinary dictionary interface, while v3's
        # original authorized cache remains immutable and cannot be rebound.
        return dict(value) if self.profile == "v3" else value

    def _active(self):
        if self.closed:
            _fail("source_context_closed", "context")
        if hasattr(self, "_original_v3_request") and (
                self._profile != "v3" or _frozen_json(self.arguments) != self._original_v3_request):
            _fail("source_context_nomination_mismatch", "arguments")
        if hasattr(self, "_v3_relationships") and _frozen_json(self.relationships) != self._v3_relationships:
            _fail("source_context_science_mismatch", "relationships")

    def close(self):
        if self.closed:
            return
        if self.visual is not None:
            for decoded in self.visual.decoded.values():
                if isinstance(decoded, tuple) and len(decoded) > 1:
                    decoded[1].close()
            self.visual.decoded.clear()
            self.visual.images.clear()
        if hasattr(self, "cache"):
            if isinstance(self.cache, MappingProxyType):
                self.cache = MappingProxyType({})
            else:
                self.cache.clear()
        if hasattr(self, "native"):
            self.native.cache.clear()
            self.native.references.clear()
        if self.visual is not None:
            self.visual.sources.clear()
        if hasattr(self, "unavailable_errors"):
            self.unavailable_errors.clear()
        self._endpoints.clear()
        for name in ("_stage_records", "_document_records", "_covariance_facts"):
            value = getattr(self, name, None)
            if value is not None:
                value.clear()
        for name in ("_reading_registry", "_scope_registry"):
            if hasattr(self, name):
                setattr(self, name, MappingProxyType({}))
        self.closed = True

    def __enter__(self):
        self._active()
        return self

    def __exit__(self, *exception):
        self.close()


def _authenticate_request(context, value, field):
    if isinstance(value, dict):
        if "quote" in value and ("source_ref" in value or value.get("kind") == "image"):
            context.witness(value, field)
        for key, item in value.items():
            _authenticate_request(context, item, field + "." + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _authenticate_request(context, item, f"{field}[{i}]")


def open_controlled_response_sources(arguments, *, read_source):
    if isinstance(arguments, dict) and arguments.get("version") == "controlled_response_source_selection_v3":
        from .literature_controlled_response_v3_inputs import validate_controlled_response_v3_selection
        selected = validate_controlled_response_v3_selection(arguments)
    elif isinstance(arguments, dict) and arguments.get("version") == "controlled_response_source_selection_v2":
        from .literature_controlled_response_v2_inputs import validate_controlled_response_v2_selection
        selected = validate_controlled_response_v2_selection(arguments)
    else:
        selected = validate_controlled_response_selection(arguments)
    return SourceContext(selected, read_source)


def _owned(context, value, field):
    context._active()
    if not isinstance(value, _StageValue) or value._context is not context:
        _fail("source_stage_context_mismatch", field)


def _selected_arm_field(context, selected):
    context._active()
    for role, nominated in context.arguments["arms"].items():
        if nominated is not None and nominated is selected:
            return "arms." + role
    for role, nominated in context.arguments["arms"].items():
        if nominated is not None and nominated == selected:
            return "arms." + role
    _fail("unselected_arm_science", "selected_arm")


def read_controlled_response_arm_science(context, selected_arm, *, reading_selector=None):
    field = _reading_field(context, selected_arm, reading_selector)
    meanings = {name: _meaning(context, selected_arm[name], name, field + "." + name) for name in _MEANINGS}
    science = _StageValue(context, {"selection": selected_arm,
        "context": {name: context.witness(w, field + ".context." + name) for name,w in selected_arm["context"].items()},
        "protein_arrangement": _interpretation(context, selected_arm["protein_arrangement"], field + ".protein_arrangement"),
        "meanings": meanings, "intended_factor_level": context.witness(selected_arm["intended_factor_level"], field + ".intended_factor_level")})
    context._endpoints[id(science["meanings"]["endpoint"])] = (science["meanings"]["endpoint"], field)
    if context.profile == "v3":
        _mark_reading_stage(context, science, reading_selector, kind="science")
        context._endpoints[id(science["meanings"]["endpoint"])] = (
            science["meanings"]["endpoint"], field, _selector_key(reading_selector), science)
    return science


def _exact_response(measurement, *, graph=False):
    unit = measurement["unit"]
    if unit is None or unit["status"] != "supported":
        return None
    scale = _fraction(unit["exact_scale"])
    if graph:
        pixels = measurement["pixel_result"]
        if pixels["status"] != "measured":
            return None
        point = _fraction(pixels["native_ordinate"]) * scale
        lower, upper = (_fraction(pixels["native_bounds"][s]) * scale for s in ("lower", "upper"))
        return {"point": _rational(point), "lower": _rational(lower), "upper": _rational(upper),
            "relation": "interval", "approximate": True, "unit": unit["canonical_unit"]}
    if measurement["reading_status"] != "exact":
        return None
    number = measurement["candidates"][0]
    q = Fraction(number["raw_expression"].replace("−", "-")) * scale
    relation = "eq" if number["relation"] == "point" else number["relation"]
    return {"point": _rational(q) if relation == "eq" else None,
        "lower": _rational(q) if relation in ("eq", "gt", "ge") else None,
        "upper": _rational(q) if relation in ("eq", "lt", "le") else None,
        "relation": relation, "approximate": bool(number["approximate"]), "unit": unit["canonical_unit"]}


def _reading_from_text(context, selected, extraction):
    stub = {"selection": {"source_kind": "primary_source"}, "measurement": extraction,
        "meanings": {name: {"canonical_id": None, "resolved_state": "unknown"} for name in _MEANINGS},
        "protein_arrangement": {"effective_value": "unknown"}}
    operand = _operand_from_arm(stub)
    if operand is None:
        operand = {"value": None, "threshold": None, "relation": "none", "approximate": False,
            "unit": extraction["unit"]["native_registry_unit"] if extraction["unit"] else None,
            "status": "missing", "origin": "reported", "digitization_interval": None}
    return _StageValue(context, {"selection": selected, "extraction": extraction,
        "operand_projection": {k:operand[k] for k in ("value", "threshold", "relation", "approximate", "unit", "status", "origin", "digitization_interval")},
        "unit_semantics": {"kind": "text", "record": extraction["unit"]} if extraction["unit"] is not None else None,
        "exact_response": _exact_response(extraction), "source_observation_id": extraction["source_observation_id"],
        "graph_details": None})


def read_controlled_response_text_measurement(context, selected, *, endpoint, reading_selector=None):
    context._active()
    if context.profile == "v3":
        entry, field = _measurement_entry(context, reading_selector, selected, endpoint)
        if selected is not None and selected.get("kind") != "source_literal":
            _fail("source_text_measurement_required", "selected")
        reading = _reading_from_text(context, selected, _measurement(context, selected, endpoint, field + ".measurement"))
        return _mark_reading_stage(context, reading, reading_selector, kind="measurement",
            endpoint_science=context._endpoints[id(endpoint)][3])
    if reading_selector is not None:
        _fail("unsupported_stage_selector", "reading_selector")
    if selected is not None and selected.get("kind") != "source_literal":
        _fail("source_text_measurement_required", "selected")
    matching = [(role, arm) for role,arm in context.arguments["arms"].items()
                if arm is not None and arm["measurement"] == selected]
    if not matching:
        _fail("unselected_measurement", "selected")
    endpoint_binding = context._endpoints.get(id(endpoint))
    if endpoint_binding is None or endpoint_binding[0] is not endpoint:
        _fail("source_stage_context_mismatch", "endpoint")
    field = endpoint_binding[1]
    role = field.split(".",1)[1]
    arm = context.arguments["arms"][role]
    if arm["measurement"] != selected or endpoint["selection"] != arm["endpoint"]:
        _fail("source_stage_endpoint_mismatch", "endpoint")
    extraction = _measurement(context, selected, endpoint, "arms." + role + ".measurement")
    return _reading_from_text(context, selected, extraction)


def finish_controlled_response_arm(context, arm_science, *, measurement, reading_selector=None):
    _owned(context, arm_science, "arm_science")
    _owned(context, measurement, "measurement")
    selected = arm_science["selection"]
    field = _reading_field(context, selected, reading_selector)
    if context.profile == "v3":
        _owned_reading(context, arm_science, reading_selector, "arm_science", kind="science")
        _owned_reading(context, measurement, reading_selector, "measurement", kind="measurement")
        if context._stage_records[id(measurement)][4] is not arm_science:
            _fail("source_stage_endpoint_mismatch", "measurement")
    if selected["measurement"] != measurement["selection"]:
        _fail("source_stage_measurement_mismatch", field)
    result = deepcopy(dict(arm_science))
    result["measurement"] = deepcopy(measurement["extraction"])
    carrier = measurement["unit_semantics"]
    response_unit = carrier if context.profile in ("v2", "v3") else (carrier["record"] if carrier else None)
    result["reported_uncertainty"] = _uncertainty(context, selected["reported_uncertainty"], response_unit,
        result["meanings"]["endpoint"], field + ".reported_uncertainty")
    if context.profile == "v1":
        result["calculation_operand"] = _operand_from_arm(result)
    else:
        operand = deepcopy(measurement["operand_projection"])
        operand.update({name + "_id": result["meanings"][name]["canonical_id"] for name in _MEANINGS})
        operand.update(source_observation_id=measurement["source_observation_id"],
            protein_arrangement=result["protein_arrangement"]["effective_value"],
            meaning_statuses={name:result["meanings"][name]["resolved_state"] for name in _MEANINGS})
        if selected["source_kind"] == "synthetic_fixture":
            operand["origin"] = "synthetic"
        # Retain a real nomination identity for authenticated failed graph attempts.
        if operand["status"] != "missing" and operand["source_observation_id"] is None:
            candidates = [w["canonical_locator"] for w in result["measurement"]["graph_witnesses"] if w["canonical_locator"]]
            image = next((i for i in context.images if selected["measurement"] and i["image_id"] == selected["measurement"].get("image_id")), None)
            if image and image["artifact_ref"] and candidates:
                operand["source_observation_id"] = identity("controlled_graph_nomination", {
                    "artifact_ref": image["artifact_ref"], "byte_sha256": image["byte_sha256"], "nomination": selected["measurement"]})
            else:
                operand.update(status="missing", value=None, threshold=None, relation="none", digitization_interval=None)
        result["calculation_operand"] = operand
        result["graph_details"] = deepcopy(measurement["graph_details"])
    result["diagnostics"] = _unique_diagnostics([result["context"], result["meanings"], result["protein_arrangement"],
        result["measurement"], result["reported_uncertainty"]], stable=context.profile in ("v2", "v3"))
    stage = _StageValue(context, result)
    return _mark_reading_stage(context, stage, reading_selector, kind="arm") if context.profile == "v3" else stage


def _project_owner_covariance(result, matrix, arms, relationships):
    """Validate all supplied owners/full rows before taking any marginal."""
    from .literature_controlled_response_owner_calculations import validate_controlled_response_owner_inputs
    result.pop("projection_indices")
    result["provided_owner_projection"] = []
    if result["source_validation"] != "valid":
        return result
    reference = result["source_ref"]
    def partial(code, state="binding_conflicting", domain="source_binding"):
        result.update(projection_state=state, diagnostics=[_diag(code, "covariance.projection", domain, [reference])])
        return result
    bindings = [(role, b) for role,b in result["bindings"].items() if b["state"] == "known"]
    if any(b["state"] == "conflicting" for b in result["bindings"].values()):
        return partial("covariance_owner_conflicting")
    by_owner, by_index = {}, {}
    for role,binding in bindings:
        owner, index = binding["resolved_owner_id"], binding["source_variable_index"]
        if index in by_index and by_index[index] != owner:
            return partial("covariance_owner_conflicting")
        by_index[index] = owner
        by_owner.setdefault(owner, []).append((role, index))
        variable = result["variables"][index]
        if variable["native_registry_unit"] is None:
            return partial("source_covariance_unit_unsupported", "unavailable", "reader_capability")
        operand = arms[role]["calculation_operand"]
        if operand["unit"] and RATE_UNITS[operand["unit"]][0] != RATE_UNITS[variable["native_registry_unit"]][0]:
            return partial("covariance_owner_dimension_conflict")
    for owner, rows in by_owner.items():
        for role, i in rows:
            for other_role, j in rows:
                a,b = result["variables"][i], result["variables"][j]
                if RATE_UNITS[a["native_registry_unit"]][0] != RATE_UNITS[b["native_registry_unit"]][0]:
                    return partial("covariance_owner_dimension_conflict")
                sa,sb = _fraction(a["exact_scale"]), _fraction(b["exact_scale"])
                if any(sa * matrix[i][k] != sb * matrix[j][k] for k in range(len(matrix))):
                    return partial("covariance_shared_rows_conflicting")
    for owner, rows in sorted(by_owner.items(), key=lambda item:min(i for _,i in item[1])):
        index = min(i for _,i in rows)
        result["provided_owner_projection"].append({"physical_observation_id": owner,
            "source_variable_index": index, "roles": [r for r in PRIMITIVE_ORDER if any(r == role for role,_ in rows)],
            "native_registry_unit": result["variables"][index]["native_registry_unit"]})
    rows = result["provided_owner_projection"]
    if not rows:
        return partial("covariance_owner_unresolved", "binding_unresolved")
    indices = [row["source_variable_index"] for row in rows]
    projected = [[matrix[i][j] for j in indices] for i in indices]
    result["projected_exact_matrix"] = [[_rational(v) for v in row] for row in projected]
    finite = [[_finite(v) for v in row] for row in projected]
    if any(v is None for row in finite for v in row):
        return partial("covariance_projection_numeric_range", "numeric_range", "reader_capability")
    finite_exact = [[Fraction(str(v)) for v in row] for row in finite]
    if not _psd(finite_exact):
        return partial("covariance_projection_precision_invalid", "precision_invalid", "reader_capability")
    covariance = {"physical_observation_ids": [r["physical_observation_id"] for r in rows],
        "units": [r["native_registry_unit"] for r in rows], "matrix": finite}
    trial = {"version": "controlled_response_owner_inputs_v2", "arms": {r:arms[r]["calculation_operand"] if arms[r] else None for r in PRIMITIVE_ORDER},
        "relationships": _relationships_inputs(relationships), "covariance": covariance,
        "variance_status": "known", "model_kind": "none"}
    try:
        validate_controlled_response_owner_inputs(trial)
    except ExperimentalContractError:
        return partial("covariance_owner_dimension_conflict")
    result.update(calculation_covariance=covariance, projection_state="available")
    if finite_exact != projected:
        result["diagnostics"].append(_diag("numeric_projection_rounding", "covariance.projection", "reader_capability", [reference]))
    return result


def _representations(arms):
    from .literature_controlled_response_owner_calculations import _groups
    groups = _groups([arms[role]["calculation_operand"] if arms[role] else None for role in PRIMITIVE_ORDER])
    result = []
    for group in groups:
        roles = group["roles"]
        domains = [_exact_response(arms[r]["measurement"], graph=bool(arms[r].get("graph_details"))) if arms[r] else None for r in roles]
        readings = [{"role": r, "source_reading_id": arms[r]["calculation_operand"]["source_observation_id"] if arms[r] else None,
            "exact_domain": d} for r,d in zip(roles, domains)]
        canceled = group["known_owner"] and group["coefficient"] == 0
        science = all(arms[r] and all(v["resolved_state"] == "known" for v in arms[r]["meanings"].values()) for r in roles)
        equal = all(d is not None and d == domains[0] for d in domains)
        disjoint = any(_response_domains_disjoint(a,b) for i,a in enumerate(domains) for b in domains[:i] if a and b)
        if not science:
            method,state = "unresolved", "unresolved_science"
        elif canceled:
            method,state = "owner_cancellation", "canceled_readings_retained"
        elif len(roles) == 1:
            method,state = "single_reading", "single"
        elif equal:
            method,state = "exact_equivalence", "exact_equivalent"
        else:
            method,state = "unresolved", "conflicting_active_domains" if disjoint else "unresolved_active_model"
        qualifications = []
        if any(arms[r] and arms[r].get("graph_details") for r in roles):
            qualifications.append("conditional_digitization_not_sampling")
        if canceled:
            if any(d is None for d in domains): qualifications.append("canceled_numeric_unavailable")
            if any(arms[r]["calculation_operand"]["unit"] is None for r in roles): qualifications.append("canceled_unit_unknown")
            if disjoint: qualifications.append("canceled_numeric_conflict")
        elif state == "unresolved_active_model":
            qualifications.append("active_reconciliation_unimplemented")
        result.append({"physical_observation_id": group["physical_observation_id"], "roles": roles,
            "readings": readings, "net_coefficient": group["coefficient"], "method": method, "state": state,
            "canonical_source_reading_id": readings[0]["source_reading_id"] if method in ("single_reading", "exact_equivalence") else None,
            "qualifications": qualifications, "diagnostics": []})
    return result


def finish_controlled_response_inputs(context, *, arms, companion_arms=None, covariance_scopes=None):
    context._active()
    if context.profile == "v3":
        _validate_v3_finish_stages(context, arms, companion_arms, covariance_scopes)
        from .literature_controlled_response_v3_inputs import _finish_v3
        return _finish_v3(context, arms=arms, companion_arms=companion_arms, covariance_scopes=covariance_scopes)
    if companion_arms is not None or covariance_scopes is not None:
        _fail("unsupported_stage_selector", "finish")
    _closed(arms, PRIMITIVE_ORDER, "arms")
    relationships = deepcopy(context.relationships)
    for role, arm in arms.items():
        if (arm is None) != (context.arguments["arms"][role] is None) or arm is not None and arm["selection"] != context.arguments["arms"][role]:
            _fail("source_stage_arm_mismatch", "arms." + role)
        if context.profile == "v2" and arm is not None:
            _owned(context, arm, "arms." + role)
    if context.profile == "v1":
        _resolve_control_alias(arms, relationships)
    requested = {name:_interpretation(context, context.arguments[name], name) for name in ("variance_status", "model_kind")}
    covariance = _covariance(context, context.arguments["covariance"], arms, relationships, owner_profile=context.profile == "v2")
    if context.profile == "v2" and covariance is not None and "projection_indices" in covariance:
        covariance.pop("projection_indices")
        covariance["provided_owner_projection"] = []
    effective = _effective_model(requested, covariance, arms)
    parsed = _calculation_inputs(arms, relationships, covariance, effective)
    version, input_version, dependencies = VERSION, INPUT_VERSION, DEPENDENCIES
    if context.profile == "v2":
        from .literature_controlled_response_owner_calculations import validate_controlled_response_owner_inputs
        from .literature_controlled_response_v2_inputs import _dependencies
        version, input_version = "controlled_response_source_extraction_v2", "controlled_response_owner_inputs_v2"
        parsed["version"] = input_version
        validate_controlled_response_owner_inputs(parsed)
        dependencies = _dependencies()
    else:
        validate_controlled_response_inputs(parsed)
    result = {"version": version, "selection": deepcopy(context.arguments), "sources": deepcopy(context.roster),
        "images": deepcopy(context.images), "arms": {r:deepcopy(dict(a)) if a is not None else None for r,a in arms.items()},
        "relationships": relationships, "covariance": covariance, "requested_model": requested, "effective_model": effective,
        "calculation_inputs": parsed, "diagnostics": [], "implementation_dependencies": {
            "reader_contract_version": version, "calculator_contract_version": input_version, "expected_module_fingerprints": deepcopy(dependencies)}}
    if context.profile == "v2":
        result["representation_reconciliations"] = _representations(arms)
    result["diagnostics"] = _unique_diagnostics(result, stable=context.profile == "v2")
    json.dumps(result, allow_nan=False)
    return deepcopy(result)


def validate_controlled_response_saved_science(arguments, extraction, *, measurement_checks):
    """Single detached-science entrance; profiles retain their original contracts."""
    if isinstance(arguments, dict) and arguments.get("version") == "controlled_response_source_selection_v3":
        return _validate_v3_saved_science(arguments, extraction, measurement_checks=measurement_checks)
    if isinstance(arguments, dict) and arguments.get("version") == SELECTION_VERSION:
        return _validate_v1_saved_science(arguments, extraction)
    return _validate_v2_saved_science(arguments, extraction, measurement_checks=measurement_checks)


class _SavedSourceContext:
    """Retained witness algebra only. Never holds a provider or decoded frame."""
    profile = "v2"
    def __init__(self, arguments, extraction):
        self.arguments = arguments
        self.images = extraction["images"]
        self.roster = extraction["sources"]
        self.sources = {(s["source_ref"],s["representation"]):s for s in self.roster}
        self.witnesses = {}
        self.closed = False
        self._endpoints = {}
        def walk(value):
            if isinstance(value, dict):
                if set(value) == set(_RESULT_FIELDS["WitnessRecord"]):
                    self.witnesses.setdefault(json.dumps(value["selection"],sort_keys=True), value)
                else:
                    for key,item in value.items():
                        if key != "selection": walk(item)
            elif isinstance(value,list):
                for item in value: walk(item)
        walk(extraction)
        self.covariance = extraction["covariance"]

    def _active(self):
        if self.closed: _fail("source_context_closed", "context")

    def witness(self, selected, field):
        if selected is None: return None
        nomination = selected if "kind" in selected else {"kind":"text", **selected}
        key = json.dumps(nomination,sort_keys=True)
        record = self.witnesses.get(key)
        if record is None:
            _fail("saved_witness_missing", field)
        _saved_witness(record, selected, self.sources, field)
        result = deepcopy(record)
        # The same retained unavailable source span can serve several named
        # roles. Each shared witness call owns its diagnostic field, as live
        # reading does; JSON object traversal never chooses that field.
        for diagnostic in result["diagnostics"]:
            diagnostic["field"] = field
        return result

    def source(self, reference, representation):
        # Only the ORIGINAL full structured covariance text is retained for
        # strict source-N validation; this is not source acquisition/reparsing.
        if self.covariance is None or (reference,representation) != (self.covariance["source_ref"],"original"):
            _fail("unselected_source_read", "source_ref")
        source = self.sources[(reference,representation)]
        if source["state"] == "unavailable":
            raise _Unavailable()
        if self.covariance["raw_text"] is None:
            # The original source had unsupported UTF8 bytes. No invented bytes.
            raise _SavedUnsupportedCovariance()
        raw = self.covariance["raw_text"].encode()
        if _hash(raw) != source["byte_sha256"] or self.covariance["byte_sha256"] != source["byte_sha256"] or self.covariance["artifact_ref"] != source["artifact_ref"]:
            _fail("saved_covariance_source_mismatch", "covariance")
        return {"artifact_ref":source["artifact_ref"], "content":raw}


class _SavedUnsupportedCovariance(Exception):
    pass


def _saved_uncertainty_v2(selected, record, measurement_reading, sources, field):
    """Validate original spread facts, then use the same arithmetic assembly."""
    if record["selection"] != selected:
        _fail("saved_selection_mismatch", field)
    for key,item in record["meanings"].items():
        _saved_interpretation(item, selected[key], sources, field+"."+key)
    for key in ("magnitude",):
        if selected[key] is None:
            if record[key] is not None: _fail("saved_selection_mismatch", field+"."+key)
        else:
            _saved_number(record[key],selected[key],sources,field+"."+key)
    _saved_unit(record["unit"],selected["unit"],sources,field+".unit")
    for key in ("interval","confidence_level","count"):
        item,nomination = record[key],selected[key]
        if nomination is None:
            if item is not None: _fail("saved_selection_mismatch",field+"."+key)
            continue
        if item["selection"] != nomination:
            _fail("saved_selection_mismatch",field+"."+key)
        witness = nomination if key=="confidence_level" else nomination["witness"]
        _saved_witness(item["witness"],witness,sources,field+"."+key)
        if key=="interval" and item["status"]=="parsed":
            _ci_literal_subselection(nomination)
            quote=nomination["witness"]["quote"]
            raw=[quote[nomination[s+"_start"]:nomination[s+"_end"]] for s in ("lower","upper")]
            if item["raw_values"]!=raw or item["values"]!=[float(v.replace("−","-")) for v in raw] or Fraction(raw[0].replace("−","-"))>Fraction(raw[1].replace("−","-")):
                _fail("saved_interval_literal_mismatch",field)
        if key=="confidence_level" and item["status"]=="parsed":
            quote=nomination["quote"].strip()
            try: value=_finite(Fraction(quote[:-1].strip().replace("−","-"))/100) if quote.endswith("%") else None
            except ValueError: value=None
            if item["value"]!=value or value is None or not 0<value<1:
                _fail("saved_confidence_literal_mismatch",field)
        if key=="count" and item["reading"]:
            reading=item["reading"]
            raw=nomination["witness"]["quote"][nomination["number_start"]:nomination["number_end"]]
            enriched={**nomination,"witness":{**nomination["witness"],"artifact_ref":item["witness"]["artifact_ref"]}}
            if reading["raw_number"]!=raw or reading["selector"]!=enriched:
                _fail("saved_count_literal_mismatch",field)
            count=int(raw.replace("−","-")) if re.fullmatch(r"[-−]?[0-9]+",raw) else _cardinal_count(raw)
            if reading["status"] in ("exact","qualified","not_positive") and reading["value"]!=count:
                _fail("saved_count_literal_mismatch",field)
    meanings=record["meanings"]
    relationship=meanings["unit_relationship"]["effective_value"]
    carrier=measurement_reading["unit_semantics"]
    response_unit=carrier["record"] if carrier else None
    unit=record["unit"]
    effective=response_unit if relationship=="same_as_response" else unit if relationship=="explicit_unit" else None
    diagnostics=[]
    if relationship=="conflicting":
        diagnostics.append(_diag("source_uncertainty_unit_conflicting",field,"source_interpretation"))
    if relationship=="same_as_response" and unit and response_unit and (unit["canonical_unit"],unit["exact_scale"])!=(response_unit["canonical_unit"],response_unit["exact_scale"]):
        effective=None
        diagnostics.append(_diag("source_uncertainty_unit_conflicting",field,"source_interpretation"))
    # Native explicit-unit detection uses the retained full selected quote where
    # available. If adjacent source context was outside the saved quote, the
    # original typed conflict is retained (custody remains the native caller's).
    magnitude=record["magnitude"]
    if magnitude and magnitude["status"]=="parsed" and effective and effective["status"]=="supported":
        from .literature_rate_native_inputs import _PRINTED_UNIT
        suffix=selected["magnitude"]["witness"]["quote"][selected["magnitude"]["number_end"]:].lstrip()
        match=_PRINTED_UNIT.match(suffix)
        mismatch=bool(match and _plain_unit(match.group())!=(effective["canonical_unit"],_fraction(effective["exact_scale"])) and match.group().replace(" ","")!="U/mg")
        retained_conflict=any(d["code"]=="source_uncertainty_unit_conflicting" for d in record["diagnostics"])
        if mismatch or retained_conflict:
            effective=None
            if not diagnostics: diagnostics.append(_diag("source_uncertainty_unit_conflicting",field,"source_interpretation"))
    if record["interval"] and record["interval"]["status"]=="parsed" and effective and effective["status"]=="supported":
        interval_selection=selected["interval"]
        narrowed=_ci_literal_subselection(interval_selection)
        end=narrowed["witness"]["end"]-interval_selection["witness"]["start"]
        quote=interval_selection["witness"]["quote"].encode()
        suffix=quote[end:].decode()
        retained_conflict=any(d["code"]=="source_uncertainty_unit_conflicting" for d in record["diagnostics"])
        if _retained_printed_unit_conflict(suffix,effective) or retained_conflict:
            effective=None
            if not diagnostics: diagnostics.append(_diag("source_uncertainty_unit_conflicting",field,"source_interpretation"))
    expected=_assemble_uncertainty(selected,meanings=meanings,magnitude=magnitude,interval=record["interval"],
        confidence=record["confidence_level"],count=record["count"],unit=unit,effective_unit=effective,diagnostics=diagnostics,field=field,stable=True)
    if expected["effective_unit"] is not None:
        expected["effective_unit"]=deepcopy(carrier) if relationship=="same_as_response" else {"kind":"text","record":expected["effective_unit"]}
    if record!=expected:
        _fail("saved_uncertainty_projection_mismatch",field)
    return deepcopy(record)


def _validate_v2_saved_science(arguments, extraction, *, measurement_checks):
    from . import literature_controlled_response_v2_inputs as facade
    selected=facade.validate_controlled_response_v2_selection(arguments)
    try:
        Draft202012Validator(facade._extraction_schema()).validate(extraction)
        json.dumps(extraction,allow_nan=False)
    except (ValueError,TypeError) as error:
        raise ExperimentalContractError("saved_extraction_schema_invalid","extraction") from error
    except Exception as error:
        if error.__class__.__module__.split(".")[0]!="jsonschema": raise
        raise ExperimentalContractError("saved_extraction_schema_invalid","extraction") from error
    if extraction["selection"]!=selected:
        _fail("saved_selection_mismatch","extraction")
    dependencies={"reader_contract_version":"controlled_response_source_extraction_v2", "calculator_contract_version":"controlled_response_owner_inputs_v2",
        "expected_module_fingerprints":facade._dependencies()}
    if extraction["implementation_dependencies"]!=dependencies:
        _fail("saved_dependency_contract_mismatch","implementation_dependencies")
    sources=facade._saved_roster(selected,extraction)
    def retained_witnesses(value):
        if isinstance(value,dict):
            if set(value)==set(_RESULT_FIELDS["WitnessRecord"]):
                facade._check_witness(value,value["selection"],sources,extraction["images"],"saved_witness")
            else:
                for key,item in value.items():
                    if key!="selection": retained_witnesses(item)
        elif isinstance(value,list):
            for item in value: retained_witnesses(item)
    retained_witnesses(extraction)
    context=_SavedSourceContext(selected,extraction)
    arms={}
    for role,arm in extraction["arms"].items():
        nomination=selected["arms"][role]
        if nomination is None:
            if arm is not None: _fail("saved_selection_mismatch",role)
            arms[role]=None
            continue
        if arm is None or arm["selection"]!=nomination:
            _fail("saved_selection_mismatch",role)
        for name in _MEANINGS:
            _saved_meaning(arm["meanings"][name],nomination[name],sources,name,"arms."+role+"."+name)
        _saved_interpretation(arm["protein_arrangement"],nomination["protein_arrangement"],sources,"arms."+role)
        for key,record in arm["context"].items():
            facade._check_witness(record,nomination["context"][key],sources,extraction["images"],"arms."+role+".context."+key)
        facade._check_witness(arm["intended_factor_level"],nomination["intended_factor_level"],sources,extraction["images"],"arms."+role)
        measurement=nomination["measurement"]
        if not callable(measurement_checks): _fail("saved_measurement_checks_required","measurement_checks")
        reading=measurement_checks(measurement,arm["measurement"],source_records=extraction["sources"],image_records=extraction["images"])
        if reading["graph_details"]!=arm["graph_details"]:
            _fail("saved_graph_measurement_mismatch",role)
        reading=_StageValue(context,dict(reading))
        # Rebuild projected operand with the same finish function, using only
        # validated retained spread facts rather than a native literal reader.
        context.saved_uncertainty={"selection":nomination["reported_uncertainty"],"value":_saved_uncertainty_v2(
            nomination["reported_uncertainty"],arm["reported_uncertainty"],reading,sources,"arms."+role+".reported_uncertainty")}
        science=read_controlled_response_arm_science(context,nomination)
        expected=finish_controlled_response_arm(context,science,measurement=reading)
        if dict(expected)!=arm:
            _fail("saved_operand_projection_mismatch",role)
        arms[role]=expected
    relationships=_relationships(context,selected["relationships"])
    if relationships!=extraction["relationships"]:
        _fail("saved_relationships_mismatch","relationships")
    requested={name:_interpretation(context,selected[name],name) for name in ("variance_status","model_kind")}
    if requested!=extraction["requested_model"]:
        _fail("saved_requested_model_mismatch","requested_model")
    try:
        covariance=_covariance(context,selected["covariance"],arms,relationships,owner_profile=True)
    except _SavedUnsupportedCovariance:
        covariance=deepcopy(extraction["covariance"])
        empty=_empty_covariance(selected["covariance"])
        empty.pop("projection_indices");empty["provided_owner_projection"]=[]
        for key in ("variables","matrix_tokens","exact_matrix","bindings","projected_exact_matrix","calculation_covariance","source_model","source_validation"):
            if covariance[key]!=empty[key]: _fail("saved_covariance_invalid_state_mismatch","covariance")
        if covariance["projection_state"]!="unsupported_format": _fail("saved_covariance_invalid_state_mismatch","covariance")
    if covariance is not None and "projection_indices" in covariance:
        covariance.pop("projection_indices");covariance["provided_owner_projection"]=[]
    if covariance!=extraction["covariance"]:
        _fail("saved_covariance_projection_mismatch","covariance")
    effective=_effective_model(requested,covariance,arms)
    if effective!=extraction["effective_model"]:
        _fail("saved_effective_model_mismatch","effective_model")
    parsed=_calculation_inputs(arms,relationships,covariance,effective)
    parsed["version"]="controlled_response_owner_inputs_v2"
    if parsed!=extraction["calculation_inputs"]:
        _fail("saved_calculation_projection_mismatch","calculation_inputs")
    from .literature_controlled_response_owner_calculations import validate_controlled_response_owner_inputs
    validate_controlled_response_owner_inputs(parsed)
    if _representations(arms)!=extraction["representation_reconciliations"]:
        _fail("saved_representation_projection_mismatch","representation_reconciliations")
    expected=deepcopy(extraction);expected["diagnostics"]=[]
    if _unique_diagnostics(expected,stable=True)!=extraction["diagnostics"]:
        _fail("saved_diagnostics_mismatch","diagnostics")
    return deepcopy(extraction)


def _response_domains_disjoint(a,b):
    for left,right in ((a,b),(b,a)):
        if left["upper"] is not None and right["lower"] is not None:
            upper,lower=_fraction(left["upper"]),_fraction(right["lower"])
            if upper<lower or upper==lower and (left["relation"]=="lt" or right["relation"]=="gt"):
                return True
    return False


def _ci_literal_subselection(selected):
    """Read an explicitly positioned CI inside a full selected source field.

    The saved selection/witness stays original. The unchanged literal parser
    receives only the containing bracket pair, with exact original offsets.
    """
    quote=selected["witness"]["quote"]
    pattern=r"[\[(]\s*(?P<lower>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)\s*,\s*(?P<upper>[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?)\s*[\])]"
    for match in re.finditer(pattern,quote):
        if (quote[match.start()],quote[match.end()-1]) not in (("[","]"),("(",")")):
            continue
        if all((selected[side+"_start"],selected[side+"_end"])==match.span(side) for side in ("lower","upper")):
            witness=deepcopy(selected["witness"])
            witness["start"]+=len(quote[:match.start()].encode())
            witness["end"]=witness["start"]+len(match.group().encode())
            witness["quote"]=match.group()
            return {"witness":witness,**{side+suffix:selected[side+suffix]-match.start() for side in ("lower","upper") for suffix in ("_start","_end")}}
    _fail("ci_interval_selector_mismatch","uncertainty.interval")


def _retained_printed_unit_conflict(suffix,unit):
    from .literature_rate_native_inputs import _PRINTED_UNIT
    from .literature_partner_source_fields import _unit_continuation
    visible=suffix.lstrip()
    match=_PRINTED_UNIT.match(visible)
    if match is None: return False
    if _unit_continuation(visible[match.end():]) or re.match(r"\s+per\b",visible[match.end():]):
        _fail("partial_source_rate_unit","uncertainty.interval")
    token=match.group()
    if re.fullmatch(r"U\s*/\s*mg",token):
        if unit["definition_witnesses"] is None:
            _fail("source_defined_unit_definition_required","uncertainty.interval")
        return False
    return _plain_unit(token)!=(unit["canonical_unit"],_fraction(unit["exact_scale"]))

# Additive v3 HOST stages. Tokens and immutable nomination bytes never enter JSON.
def _selector_key(selector):
    if (not isinstance(selector, dict) or set(selector) != {"role", "reading_key"}
            or selector["role"] not in PRIMITIVE_ORDER
            or selector["reading_key"] is not None and
            (not isinstance(selector["reading_key"], str) or not selector["reading_key"])):
        _fail("source_reading_selector_invalid", "reading_selector")
    return selector["role"], selector["reading_key"]


def _scope_key(scope):
    if not isinstance(scope, dict) or set(scope) != {"kind", "index"}:
        _fail("source_covariance_scope_invalid", "scope_key")
    kind, index = scope["kind"], scope["index"]
    if not (kind == "base" and index is None or kind in ("joint", "local")
            and type(index) is int and index >= 0):
        _fail("source_covariance_scope_invalid", "scope_key")
    return kind, index


def _frozen_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _initialize_v3_registries(context):
    arguments = context.arguments
    context._original_v3_request = _frozen_json(arguments)
    context._reading_registry = {}
    for role in PRIMITIVE_ORDER:
        context._reading_registry[(role, None)] = (_frozen_json(arguments["arms"][role]), "arms." + role, object())
    for i, row in enumerate(arguments["companion_readings"]):
        key = row["primary_role"], row["reading_key"]
        if key in context._reading_registry:
            _fail("duplicate_reading_selector", "companion_readings")
        context._reading_registry[key] = (_frozen_json(row["reading"]), f"companion_readings[{i}].reading", object())
    context._scope_registry = {}
    primary = [{"role": r, "reading_key": None} for r in PRIMITIVE_ORDER]
    context._scope_registry[("base", None)] = (_frozen_json(arguments["covariance"]), _frozen_json(primary))
    scopes = {row["assignment_index"]: row for row in arguments["joint_scopes"]}
    if len(scopes) != len(arguments["joint_scopes"]) or set(scopes) != set(range(len(arguments["joint_reading_assignments"]))):
        _fail("source_joint_scope_roster_mismatch", "joint_scopes")
    for i, joint in enumerate(arguments["joint_reading_assignments"]):
        selectors = [{"role": r, "reading_key": joint["assignment"][r]} for r in PRIMITIVE_ORDER]
        for selector in selectors:
            if _selector_key(selector) not in context._reading_registry:
                _fail("source_reading_selector_unresolved", "joint_reading_assignments")
        context._scope_registry[("joint", i)] = (_frozen_json(scopes[i]["covariance_selection"]), _frozen_json(selectors))
    for i, pair in enumerate(arguments["local_pair_assignments"]):
        selectors = [pair["protein"], pair["control"]]
        for selector in selectors:
            if _selector_key(selector) not in context._reading_registry:
                _fail("source_reading_selector_unresolved", "local_pair_assignments")
        context._scope_registry[("local", i)] = (_frozen_json(pair["covariance_selection"]), _frozen_json(selectors))
    context._reading_registry = MappingProxyType(context._reading_registry)
    context._scope_registry = MappingProxyType(context._scope_registry)
    context._stage_records, context._document_records, context._covariance_facts = {}, {}, {}


def _reading_entry(context, selector):
    context._active()
    if context.profile != "v3":
        _fail("unsupported_stage_selector", "reading_selector")
    key = _selector_key(selector)
    entry = context._reading_registry.get(key)
    if entry is None:
        _fail("source_reading_selector_unresolved", "reading_selector")
    return entry


def _reading_field(context, selected, selector):
    if context.profile != "v3":
        if selector is not None:
            _fail("unsupported_stage_selector", "reading_selector")
        return _selected_arm_field(context, selected)
    entry = _reading_entry(context, selector)
    if selected is None or _frozen_json(selected) != entry[0]:
        _fail("source_stage_arm_mismatch", "selected_arm")
    return entry[1]


def _mark_reading_stage(context, stage, selector, *, kind, endpoint_science=None):
    entry = _reading_entry(context, selector)
    context._stage_records[id(stage)] = (stage, entry[2], _frozen_json(dict(stage)), kind, endpoint_science)
    return stage


def _owned_reading(context, stage, selector, field, *, kind=None):
    _owned(context, stage, field)
    entry = _reading_entry(context, selector)
    record = context._stage_records.get(id(stage))
    if (record is None or record[0] is not stage or record[1] is not entry[2]
            or record[2] != _frozen_json(dict(stage)) or kind is not None and record[3] != kind):
        _fail("source_stage_selector_mismatch", field)


def _measurement_entry(context, selector, selected, endpoint):
    entry = _reading_entry(context, selector)
    arm = json.loads(entry[0])
    if arm is None or arm["measurement"] != selected:
        _fail("source_stage_measurement_mismatch", "selected")
    binding = context._endpoints.get(id(endpoint))
    if binding is None or binding[0] is not endpoint:
        _fail("source_stage_context_mismatch", "endpoint")
    if len(binding) != 4 or binding[2] != _selector_key(selector):
        _fail("source_stage_endpoint_mismatch", "endpoint")
    _owned_reading(context, binding[3], selector, "endpoint", kind="science")
    return arm, entry[1]


def read_controlled_response_graph_measurement(context, reading_selector, *, endpoint):
    """Read the exact registered graph through063 and this prefetched closure."""
    entry = _reading_entry(context, reading_selector)
    arm = json.loads(entry[0])
    selected = arm["measurement"] if arm else None
    _measurement_entry(context, reading_selector, selected, endpoint)
    if selected is None or selected["kind"] != "linear_bar":
        _fail("source_graph_measurement_required", "selected")
    from .literature_controlled_response_v2_inputs import _read_graph
    return _mark_reading_stage(context, _read_graph(context, selected), reading_selector,
        kind="measurement", endpoint_science=context._endpoints[id(endpoint)][3])


def _scope_entry(context, scope):
    context._active()
    if context.profile != "v3":
        _fail("unsupported_stage_selector", "scope_key")
    key = _scope_key(scope)
    entry = context._scope_registry.get(key)
    if entry is None:
        _fail("source_covariance_scope_unresolved", "scope_key")
    return json.loads(entry[0]), json.loads(entry[1])


_DOCUMENT_FIELDS = ("source_ref", "artifact_ref", "byte_sha256", "raw_text", "variables", "matrix_tokens",
    "exact_matrix", "source_model", "source_validation", "diagnostics")


def _check_document_nominations(context, selected, document):
    if document["exact_matrix"] is None:
        return
    for role in PRIMITIVE_ORDER:
        nomination = selected["bindings"][role]
        if nomination is None:
            continue
        field = "covariance.bindings." + role
        index = nomination["variable_index"]
        if index >= len(document["variables"]):
            _fail("source_variable_index_out_of_bounds", field)
        label = context.witness(nomination["label_witness"], field + ".label")
        actual = document["variables"][index]["label_witness"]
        if label["canonical_locator"] is not None and label["canonical_locator"] != actual["canonical_locator"]:
            _fail("source_label_token_binding_mismatch", field)


def read_controlled_response_covariance_document(context, scope_key):
    """Validate original full-N source facts before any owner projection."""
    selected, selectors = _scope_entry(context, scope_key)
    if selected is None:
        return None
    source_key = selected["source_ref"], "original"
    facts = context._covariance_facts.get(source_key)
    if facts is None:
        try:
            facts = _covariance_document_facts(context, selected)
        except _SavedUnsupportedCovariance:
            saved = context.documents[source_key]
            source = context.sources[source_key]
            facts = _empty_covariance(selected)
            facts.update(artifact_ref=source["artifact_ref"], byte_sha256=source["byte_sha256"],
                projection_state="unsupported_format", diagnostics=[_diag("unsupported_covariance_representation",
                    "covariance", "reader_capability", [selected["source_ref"]])])
            if saved["document_state"] != "unsupported_format":
                _fail("saved_covariance_invalid_state_mismatch", "covariance")
        context._covariance_facts[source_key] = facts
    document = {key: deepcopy(facts[key]) for key in _DOCUMENT_FIELDS}
    document["document_state"] = ("unavailable" if facts["artifact_ref"] is None else
        "unsupported_format" if facts["projection_state"] == "unsupported_format" else "available")
    _check_document_nominations(context, selected, document)
    stage = _StageValue(context, document)
    context._document_records[id(stage)] = (stage, _scope_key(scope_key), _frozen_json(dict(stage)))
    return stage


def _scope_binding(context, nomination, arm, document, field):
    binding = {"selection": deepcopy(nomination), "label_witness": None, "owner_witness": None,
        "correspondence": None, "source_variable_index": None, "resolved_owner_id": None,
        "state": "unknown", "diagnostics": []}
    if nomination is None or document["exact_matrix"] is None:
        return binding
    index = nomination["variable_index"]
    label = context.witness(nomination["label_witness"], field + ".label")
    owner = context.witness(nomination["owner_witness"], field + ".owner")
    correspondence = _interpretation(context, nomination["correspondence"], field + ".correspondence")
    physical = arm["meanings"]["physical_observation"] if arm else None
    declared = ([w["selection"] for w in physical["witnesses"]] +
        ([physical["canonical_witness"]["selection"]] if physical["canonical_witness"] else [])) if physical else []
    if arm and nomination["owner_witness"] not in declared:
        _fail("owner_witness_not_in_role", field)
    state = "conflicting" if correspondence["effective_value"] == "conflicting" else "unknown"
    if (physical and physical["resolved_state"] == "known" and label["canonical_locator"] is not None
            and owner["canonical_locator"] is not None and correspondence["effective_value"] == "same"):
        state = "known"
    binding.update(label_witness=label, owner_witness=owner, correspondence=correspondence,
        source_variable_index=index, resolved_owner_id=physical["canonical_id"] if state == "known" else None,
        state=state, diagnostics=_unique_diagnostics([label, owner, correspondence]))
    return binding


def _check_local_owner_rows(bindings, readings, document):
    """Retain pair binding conflicts without consulting unrelated role bindings."""
    if document is None or document["exact_matrix"] is None:
        return
    known = [(row["binding"], arm) for row, (_, arm) in zip(bindings, readings)
        if row["binding"]["state"] == "known"]
    matrix = [[_fraction(v) for v in row] for row in document["exact_matrix"]]
    problem = None
    for binding, arm in known:
        variable = document["variables"][binding["source_variable_index"]]
        operand_unit = arm["calculation_operand"]["unit"]
        source_unit = variable["native_registry_unit"]
        if (source_unit is not None and operand_unit is not None
                and RATE_UNITS[source_unit][0] != RATE_UNITS[operand_unit][0]):
            problem = "covariance_owner_dimension_conflict"
    for i, (left, _) in enumerate(known):
        for right, _ in known[:i]:
            a, b = left["source_variable_index"], right["source_variable_index"]
            if a == b and left["resolved_owner_id"] != right["resolved_owner_id"]:
                problem = "covariance_owner_conflicting"
            if left["resolved_owner_id"] != right["resolved_owner_id"]:
                continue
            va, vb = document["variables"][a], document["variables"][b]
            if va["native_registry_unit"] is None or vb["native_registry_unit"] is None:
                continue
            if RATE_UNITS[va["native_registry_unit"]][0] != RATE_UNITS[vb["native_registry_unit"]][0]:
                problem = "covariance_owner_dimension_conflict"
            elif any(_fraction(va["exact_scale"]) * matrix[a][k] !=
                    _fraction(vb["exact_scale"]) * matrix[b][k] for k in range(len(matrix))):
                problem = "covariance_shared_rows_conflicting"
    if problem is not None:
        for binding, _ in known:
            binding.update(state="conflicting", resolved_owner_id=None)
            binding["diagnostics"].append(_diag(problem, "covariance.bindings", "source_binding", [document["source_ref"]]))


def bind_controlled_response_covariance_scope(context, scope_key, document, *, readings):
    """Bind only this scope's actual original-order readings; local needs two."""
    selected, expected = _scope_entry(context, scope_key)
    if not isinstance(readings, (tuple, list)) or len(readings) != len(expected):
        _fail("source_covariance_reading_roster_mismatch", "readings")
    for pair, selector in zip(readings, expected):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2 or pair[0] != selector:
            _fail("source_covariance_reading_roster_mismatch", "readings")
        arm = pair[1]
        entry = _reading_entry(context, selector)
        if json.loads(entry[0]) is None:
            if arm is not None:
                _fail("source_stage_arm_mismatch", "readings")
        else:
            _owned_reading(context, arm, selector, "readings", kind="arm")
    if selected is None:
        if document is not None:
            _fail("source_covariance_document_mismatch", "document")
    else:
        _owned(context, document, "document")
        record = context._document_records.get(id(document))
        if (record is None or record[0] is not document or record[1] != _scope_key(scope_key)
                or record[2] != _frozen_json(dict(document))):
            _fail("source_covariance_document_mismatch", "document")
    bindings = []
    for selector, arm in readings:
        role = selector["role"]
        bindings.append({"reading": deepcopy(selector), "binding": _scope_binding(context,
            selected["bindings"][role] if selected is not None else None,
            arm, document, "covariance.bindings." + role)})
    if scope_key["kind"] == "local":
        _check_local_owner_rows(bindings, readings, document)
    whole = None
    if scope_key["kind"] != "local" and document is not None:
        whole = _empty_covariance(selected)
        whole.update({key: deepcopy(document[key]) for key in _DOCUMENT_FIELDS})
        whole["projection_state"] = ("source_invalid" if document["source_validation"] == "invalid" else
            "unsupported_format" if document["document_state"] == "unsupported_format" else "unavailable")
        whole["bindings"] = {row["reading"]["role"]: deepcopy(row["binding"]) for row in bindings}
        if document["exact_matrix"] is not None:
            matrix = [[_fraction(v) for v in row] for row in document["exact_matrix"]]
            whole = _project_owner_covariance(whole, matrix, {s["role"]: a for s,a in readings}, context.relationships)
        else:
            whole.pop("projection_indices")
            whole["provided_owner_projection"] = []
    result = _StageValue(context, {"scope": deepcopy(scope_key), "document": deepcopy(dict(document)) if document is not None else None,
        "bindings": bindings, "whole_projection": whole})
    context._document_records[id(result)] = (result, _scope_key(scope_key), _frozen_json(dict(result)))
    return result


def _validate_v3_finish_stages(context, arms, companions, scopes):
    _closed(arms, PRIMITIVE_ORDER, "arms")
    for role in PRIMITIVE_ORDER:
        selector = {"role": role, "reading_key": None}
        selected = json.loads(_reading_entry(context, selector)[0])
        if selected is None:
            if arms[role] is not None:
                _fail("source_stage_arm_mismatch", "arms." + role)
        else:
            _owned_reading(context, arms[role], selector, "arms." + role, kind="arm")
    expected = [dict(role=row["primary_role"], reading_key=row["reading_key"]) for row in context.arguments["companion_readings"]]
    if not isinstance(companions, (tuple, list)) or len(companions) != len(expected):
        _fail("source_companion_roster_mismatch", "companion_arms")
    for pair, selector in zip(companions, expected):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2 or pair[0] != selector:
            _fail("source_companion_roster_mismatch", "companion_arms")
        _owned_reading(context, pair[1], selector, "companion_arms", kind="arm")
    if not isinstance(scopes, (tuple, list)) or len(scopes) != len(context._scope_registry):
        _fail("source_covariance_scope_roster_mismatch", "covariance_scopes")
    for scope, key in zip(scopes, context._scope_registry):
        _owned(context, scope, "covariance_scopes")
        record = context._document_records.get(id(scope))
        if (record is None or record[0] is not scope or record[1] != key
                or record[2] != _frozen_json(dict(scope))):
            _fail("source_covariance_scope_roster_mismatch", "covariance_scopes")

class _SavedV3SourceContext(_SavedSourceContext):
    profile = "v3"

    def __init__(self, arguments, extraction):
        super().__init__(arguments, extraction)
        _initialize_v3_registries(self)
        self.documents = {}
        rows = extraction["covariance_document_scopes"]
        if [(_scope_key(row["scope"])) for row in rows] != list(self._scope_registry):
            _fail("saved_covariance_scope_roster_mismatch", "covariance_document_scopes")
        for row in rows:
            selected, _ = _scope_entry(self, row["scope"])
            document = row["document"]
            if (selected is None) != (document is None):
                _fail("saved_selection_mismatch", "covariance_document_scopes")
            if document is not None:
                if document["source_ref"] != selected["source_ref"]:
                    _fail("saved_covariance_source_mismatch", "covariance_document_scopes")
                key = (document["source_ref"], "original")
                previous = self.documents.get(key)
                if previous is not None and previous != document:
                    _fail("saved_covariance_document_conflict", "covariance_document_scopes")
                self.documents[key] = document

    def _active(self):
        super()._active()
        if self.profile != "v3" or _frozen_json(self.arguments) != self._original_v3_request:
            _fail("source_context_nomination_mismatch", "arguments")

    def close(self):
        if self.closed:
            return
        for name in ("_endpoints", "_stage_records", "_document_records", "_covariance_facts",
                "documents", "witnesses", "sources"):
            getattr(self, name).clear()
        self._reading_registry = MappingProxyType({})
        self._scope_registry = MappingProxyType({})
        self.closed = True

    def source(self, reference, representation):
        key = reference, representation
        document = self.documents.get(key)
        if document is None:
            _fail("unselected_source_read", "source_ref")
        source = self.sources[key]
        if source["state"] == "unavailable":
            raise _Unavailable()
        if document["raw_text"] is None:
            raise _SavedUnsupportedCovariance()
        raw = document["raw_text"].encode()
        if (_hash(raw) != source["byte_sha256"] or document["byte_sha256"] != source["byte_sha256"]
                or document["artifact_ref"] != source["artifact_ref"]):
            _fail("saved_covariance_source_mismatch", "covariance")
        return {"artifact_ref": source["artifact_ref"], "content": raw}


def _validate_v3_saved_science(arguments, extraction, *, measurement_checks):
    """Rebuild all source science from retained facts, with no native readers."""
    from . import literature_controlled_response_v3_inputs as facade
    from . import literature_controlled_response_v2_inputs as old_facade
    selected = facade.validate_controlled_response_v3_selection(arguments)
    try:
        Draft202012Validator(facade._extraction_schema()).validate(extraction)
        json.dumps(extraction, allow_nan=False)
    except Exception as error:
        if not isinstance(error, (ValueError, TypeError)) and error.__class__.__module__.split(".")[0] != "jsonschema":
            raise
        raise ExperimentalContractError("saved_extraction_schema_invalid", "extraction") from error
    if extraction["selection"] != selected:
        _fail("saved_selection_mismatch", "extraction")
    expected_dependencies = {"reader_contract_version": "controlled_response_source_extraction_v3",
        "calculator_contract_version": "controlled_response_owner_inputs_v2", "expected_module_fingerprints": facade._dependencies()}
    if extraction["implementation_dependencies"] != expected_dependencies:
        _fail("saved_dependency_contract_mismatch", "implementation_dependencies")
    sources = old_facade._saved_roster(selected, extraction)
    def check_witnesses(value):
        if isinstance(value, dict):
            if set(value) == set(_RESULT_FIELDS["WitnessRecord"]):
                old_facade._check_witness(value, value["selection"], sources, extraction["images"], "saved_witness")
            else:
                for key, item in value.items():
                    if key != "selection":
                        check_witnesses(item)
        elif isinstance(value, list):
            for item in value:
                check_witnesses(item)
    check_witnesses(extraction)
    context = _SavedV3SourceContext(selected, extraction)
    try:
        arms, companions, readings = {}, [], {}
        retained_companions = extraction["companion_extractions"]
        if len(retained_companions) != len(selected["companion_readings"]):
            _fail("saved_companion_roster_mismatch", "companion_extractions")
        for i, row in enumerate(retained_companions):
            nominated = selected["companion_readings"][i]
            if (row["reading_key"], row["primary_role"]) != (nominated["reading_key"], nominated["primary_role"]):
                _fail("saved_companion_roster_mismatch", "companion_extractions")
        for key, entry in context._reading_registry.items():
            selector = {"role": key[0], "reading_key": key[1]}
            nomination = json.loads(entry[0])
            field = entry[1]
            arm = (extraction["arms"][key[0]] if key[1] is None else
                next(row["reading"] for row in retained_companions if row["reading_key"] == key[1] and row["primary_role"] == key[0]))
            if nomination is None:
                if arm is not None:
                    _fail("saved_selection_mismatch", field)
                rebuilt = None
            else:
                if arm is None or arm["selection"] != nomination:
                    _fail("saved_selection_mismatch", field)
                for name in _MEANINGS:
                    _saved_meaning(arm["meanings"][name], nomination[name], sources, name, field + "." + name)
                _saved_interpretation(arm["protein_arrangement"], nomination["protein_arrangement"], sources, field)
                if not callable(measurement_checks):
                    _fail("saved_measurement_checks_required", "measurement_checks")
                reading = measurement_checks(selector, nomination["measurement"], arm["measurement"],
                    source_records=extraction["sources"], image_records=extraction["images"])
                if reading["graph_details"] != arm["graph_details"]:
                    _fail("saved_graph_measurement_mismatch", field)
                science = read_controlled_response_arm_science(context, nomination, reading_selector=selector)
                reading = _mark_reading_stage(context, _StageValue(context, dict(reading)), selector,
                    kind="measurement", endpoint_science=science)
                context.saved_uncertainty = {"selection": nomination["reported_uncertainty"],
                    "value": _saved_uncertainty_v2(nomination["reported_uncertainty"], arm["reported_uncertainty"],
                        reading, sources, field + ".reported_uncertainty")}
                rebuilt = finish_controlled_response_arm(context, science, measurement=reading, reading_selector=selector)
                if dict(rebuilt) != arm:
                    _fail("saved_operand_projection_mismatch", field)
            readings[key] = rebuilt
            if key[1] is None:
                arms[key[0]] = rebuilt
            else:
                companions.append((selector, rebuilt))
        context.relationships = _relationships(context, selected["relationships"])
        scopes = []
        for key in context._scope_registry:
            scope = {"kind": key[0], "index": key[1]}
            document = read_controlled_response_covariance_document(context, scope)
            expected_document = next(row["document"] for row in extraction["covariance_document_scopes"] if row["scope"] == scope)
            if document != expected_document:
                _fail("saved_covariance_document_mismatch", "covariance_document_scopes")
            _, selectors = _scope_entry(context, scope)
            scopes.append(bind_controlled_response_covariance_scope(context, scope, document,
                readings=[(s, readings[_selector_key(s)]) for s in selectors]))
        expected = finish_controlled_response_inputs(context, arms=arms, companion_arms=companions, covariance_scopes=scopes)
        if "local_pair_extractions" not in extraction:
            # Legacy saved shape: reconstruction above still requires every
            # witness to exist in the original retained records. Never invent
            # missing local facts or reopen a source to fill this older shape.
            expected.pop("local_pair_extractions")
            expected["diagnostics"] = []
            expected["diagnostics"] = _unique_diagnostics(expected, stable=True)
        if expected != extraction:
            _fail("saved_source_projection_mismatch", "extraction")
        return deepcopy(extraction)
    finally:
        context.close()
