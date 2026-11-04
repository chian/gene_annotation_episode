"""Source-bound inputs for the four-cell A105 binding interaction.

This pure reader authenticates selected bytes/image geometry and parses literal
operands. Scientific labels, canonical correspondences and experimental meanings
are attributed to the investigating episode. It does not establish their truth,
acquire evidence, invoke a model, populate a sheet, select work or award credit.

The request is closed. All fields are required; unknown selections are explicit:
 {version, source_ref, source_kind, images, parameter_kind, comparison_scope,
  roles:{role:null|Role for role in ROLES}, relationships:{name:Relationship}}
 Image uses frozen049's actual original/crop contract. Witness is its tagged
 exact UTF-8 text span or image region. Literal={status,candidates,fragments};
 status is exact|ambiguous|unreadable|conflicting. Parameter expressions are image
 literals; unit/uncertainty/count literals may also use exact source text.
 EnumMeaning={value,witnesses}. Meaning={status,label,witnesses,canonical_witness},
 status known|unknown|conflicting. SourceIdentity={canonical_witness,witnesses}.
 Role={parameter_kind,definitions:{field:Meaning for field in ID_FIELDS},
       physical_fit:null|SourceIdentity, measurement:null|Measurement,
       uncertainty:null|UncertaintySelection}.
 Measurement={image_id,cell_region,expression:Literal,unit:null|Literal}.
 UncertaintySelection={statistic,basis,repetition_basis,interval,
                      confidence_level,exact_count,minimum_count}.
 Interval={lower:null|Literal,upper:null|Literal,unit_relationship:EnumMeaning,
           unit:null|Literal}, or null. Confidence level/counts are null|Literal.

The interval's two separate literal selections allow independently missing source
endpoints without pretending that a partial CI was unreported. A nullable whole
uncertainty projection means unresolved/not supplied, not source-unreported.
No scientific numbers or covariance are accepted as direct request fields.

Output retains the full selection, authenticated raw witnesses/candidates,
native-versus-canonical values, finite per-field statuses, canonical048 inputs
or an explicit common-kind failure, source roster and dependency fingerprints.
Source-cell identity is separate from actual physical-fit identity. Unknown
context never creates a known identity or suppresses a valid raw parameter.

Caller read_source(ref, representation) must authorize receipt/scope/ancestry.
It returns exactly {artifact_ref,content:bytes}; authorization failures raise
domain.ContractError and propagate before source parsing. Other authorized read
failures become local source-failure partials. No replay/reconstruction API is
provided here: a repository must retain this result rather than reread sources.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re

from .domain import ContractError
from .literature_binding_reader import _measurement, _SCALES
from .literature_binding_visual_inputs import (
    _Inputs, _box, _inside, _witness_shape, ATTRIBUTION, PILLOW_VERSION,
)
from .literature_binding_interaction_calculations import (
    INPUT_VERSION as CALC_INPUT_VERSION, ROLES, ID_FIELDS, CONTEXT_FIELDS,
    RELATIONS, validate_binding_interaction_inputs,
)
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "binding_interaction_source_inputs_v1"
OUTPUT_VERSION = "binding_interaction_source_extraction_v1"
KINDS = ("ic50", "reported_hill_kd", "unknown", "conflicting")
STATES = ("exact", "ambiguous", "unreadable", "conflicting")
STATISTICS = ("sd", "sem", "confidence_interval", "unspecified", "unreported", "unknown", "conflicting")
BASES = ("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown", "conflicting")
REPETITIONS = ("biological_preparations", "technical_measurements", "assay_occasions", "unspecified", "unknown", "conflicting")
UNIT_RELATIONS = ("same_as_parameter", "explicit_unit", "unknown", "conflicting")
_FROZEN = {
    "literature_binding_visual_inputs.py": "8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718",
    "literature_binding_reader.py": None,
    "literature_experimental_contracts.py": "0d7d4cb57f63c66ae36912e369fbcea557a6b9646c727ed1c60eac229ca3bccc",
}
# Filled only after the separately owned053 correction is actually released.
CALCULATOR_SHA256 = None
_DECIMAL = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_SCALAR = re.compile(rf"\s*(?P<approx>about\s+|approximately\s+|[~≈∼]\s*)?"
    rf"(?P<relation>>=|<=|≥|≤|>|<|at\s+least\s+|at\s+most\s+)?"
    rf"(?P<number>{_DECIMAL})\s*(?P<percent>%)?\s*", re.IGNORECASE)
_RELATIONS = {None: "eq", ">": "gt", ">=": "ge", "≥": "ge", "<": "lt", "<=": "le", "≤": "le"}


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, keys, field):
    if type(value) is not dict or set(value) != set(keys):
        _fail("closed_fields_required", field)


def _text(value, field, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value.strip():
        _fail("nonempty_source_token_required", field)


def _enum(value, choices, field):
    if type(value) is not str or value not in choices:
        _fail("unsupported_value", field)


def _witnesses(value, field):
    if type(value) is not list:
        _fail("witness_list_required", field)
    for index, witness in enumerate(value):
        _witness_shape(witness, f"{field}[{index}]")


def _enum_shape(value, choices, field):
    _keys(value, ("value", "witnesses"), field)
    _enum(value["value"], choices, field + ".value")
    _witnesses(value["witnesses"], field + ".witnesses")
    minimum = 2 if value["value"] == "conflicting" else 0 if value["value"] in ("unknown", "unspecified") else 1
    if len(value["witnesses"]) < minimum:
        _fail("interpretation_witness_required", field)


def _meaning_shape(value, field):
    _keys(value, ("status", "label", "witnesses", "canonical_witness"), field)
    _enum(value["status"], ("known", "unknown", "conflicting"), field + ".status")
    _text(value["label"], field + ".label", True)
    _witnesses(value["witnesses"], field + ".witnesses")
    if value["status"] == "known":
        _text(value["label"], field + ".label")
        if not value["witnesses"] or value["canonical_witness"] is None:
            _fail("known_meaning_witness_required", field)
        _witness_shape(value["canonical_witness"], field + ".canonical_witness")
    elif value["canonical_witness"] is not None:
        _fail("unresolved_canonical_witness_must_be_null", field)
    elif value["status"] == "conflicting" and len(value["witnesses"]) < 2:
        _fail("conflicting_witnesses_required", field)


def _literal_shape(value, field, image_only=False, nullable=False):
    if value is None and nullable:
        return
    _keys(value, ("status", "candidates", "fragments"), field)
    _enum(value["status"], STATES, field + ".status")
    for name in ("candidates", "fragments"):
        if type(value[name]) is not list:
            _fail("witness_list_required", field + "." + name)
        for index, witness in enumerate(value[name]):
            _witness_shape(witness, f"{field}.{name}[{index}]", image_only=image_only)
    if value["status"] == "exact" and (len(value["candidates"]) != 1 or value["fragments"]):
        _fail("one_exact_candidate_required", field)
    if value["status"] == "unreadable" and value["candidates"]:
        _fail("unreadable_has_no_candidate", field)
    if value["status"] in ("ambiguous", "conflicting") and len({w["quote"] for w in value["candidates"]}) < 2:
        _fail("distinct_transcription_candidates_required", field)


def _validate(arguments):
    _keys(arguments, ("version", "source_ref", "source_kind", "images", "parameter_kind",
        "comparison_scope", "roles", "relationships"), "arguments")
    _enum(arguments["version"], (VERSION,), "arguments.version")
    _text(arguments["source_ref"], "arguments.source_ref")
    _enum(arguments["source_kind"], ("primary_source", "synthetic_fixture"), "arguments.source_kind")
    _enum(arguments["comparison_scope"], ("reported_protocols", "common_conditions"), "arguments.comparison_scope")
    _enum_shape(arguments["parameter_kind"], KINDS, "parameter_kind")
    if type(arguments["images"]) is not list:
        _fail("image_list_required", "images")
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
            _enum(image["mapping"]["colour_conversion"], ("preserve", "rgb"), field + ".mapping.colour_conversion")
    _keys(arguments["roles"], ROLES, "roles")
    for role, value in arguments["roles"].items():
        if value is None:
            continue
        field = "roles." + role
        _keys(value, ("parameter_kind", "definitions", "physical_fit", "measurement", "uncertainty"), field)
        _enum_shape(value["parameter_kind"], KINDS, field + ".parameter_kind")
        _keys(value["definitions"], ID_FIELDS, field + ".definitions")
        for name, meaning in value["definitions"].items():
            _meaning_shape(meaning, field + ".definitions." + name)
        physical = value["physical_fit"]
        if physical is not None:
            _keys(physical, ("canonical_witness", "witnesses"), field + ".physical_fit")
            _witness_shape(physical["canonical_witness"], field + ".physical_fit.canonical_witness")
            _witnesses(physical["witnesses"], field + ".physical_fit.witnesses")
            if not physical["witnesses"]:
                _fail("physical_identity_witness_required", field + ".physical_fit")
        measurement = value["measurement"]
        if measurement is not None:
            _keys(measurement, ("image_id", "cell_region", "expression", "unit"), field + ".measurement")
            _text(measurement["image_id"], field + ".measurement.image_id")
            _box(measurement["cell_region"], field + ".measurement.cell_region")
            _literal_shape(measurement["expression"], field + ".measurement.expression", image_only=True)
            _literal_shape(measurement["unit"], field + ".measurement.unit", nullable=True)
        uncertainty = value["uncertainty"]
        if uncertainty is not None:
            _keys(uncertainty, ("statistic", "basis", "repetition_basis", "interval", "confidence_level",
                "exact_count", "minimum_count"), field + ".uncertainty")
            for name, choices in (("statistic", STATISTICS), ("basis", BASES), ("repetition_basis", REPETITIONS)):
                _enum_shape(uncertainty[name], choices, field + ".uncertainty." + name)
            interval = uncertainty["interval"]
            if interval is not None:
                _keys(interval, ("lower", "upper", "unit_relationship", "unit"), field + ".uncertainty.interval")
                _enum_shape(interval["unit_relationship"], UNIT_RELATIONS, field + ".uncertainty.interval.unit_relationship")
                for name in ("lower", "upper", "unit"):
                    _literal_shape(interval[name], field + ".uncertainty.interval." + name, nullable=True)
            for name in ("confidence_level", "exact_count", "minimum_count"):
                _literal_shape(uncertainty[name], field + ".uncertainty." + name, nullable=True)
    _keys(arguments["relationships"], RELATIONS, "relationships")
    for name, value in arguments["relationships"].items():
        _keys(value, ("status", "witnesses"), "relationships." + name)
        statuses = ("matched", "not_matched", "unknown", "conflicting") if name == "common_conditions" else ("supported", "unknown", "conflicting")
        _enum_shape({"value": value["status"], "witnesses": value["witnesses"]}, statuses, "relationships." + name)
    def check_images(value):
        if type(value) is dict:
            if "image_id" in value and value["image_id"] not in image_ids:
                _fail("undeclared_image_id", "image_id")
            for child in value.values():
                check_images(child)
        elif type(value) is list:
            for child in value:
                check_images(child)
    check_images(arguments)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _dependencies():
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in _FROZEN}
    if any(expected is None or hashes[name] != expected for name, expected in _FROZEN.items()):
        _fail("binding_interaction_frozen_dependency_mismatch", "implementation")
    calculator = hashlib.sha256(Path(__file__).with_name("literature_binding_interaction_calculations.py").read_bytes()).hexdigest()
    if CALCULATOR_SHA256 is None:
        _fail("binding_interaction_calculator_dependency_pending", "implementation")
    if calculator != CALCULATOR_SHA256:
        _fail("binding_interaction_frozen_dependency_mismatch", "implementation.calculator")
    return {"sha256": {**hashes, "literature_binding_interaction_calculations.py": calculator},
        "reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "pillow_version": PILLOW_VERSION}


def _source_requests(arguments):
    result = [(arguments["source_ref"], "original")]
    for image in arguments["images"]:
        result.extend(((image["source_ref"], "original"), (image["original_source_ref"], "original")))
    def visit(value):
        if type(value) is dict:
            if value.get("kind") == "text" and "quote" in value:
                result.append((value["source_ref"], value["representation"]))
            else:
                for key in sorted(value):
                    visit(value[key])
        elif type(value) is list:
            for item in value:
                visit(item)
    visit(arguments)
    return list(dict.fromkeys(result))


def _locator(witness):
    if witness is None or witness["error"]:
        return None
    original = witness["witness"]
    if original["kind"] == "image":
        located = witness["canonical_locator"]
        return {"source_ref": located["original_source_ref"], "artifact_ref": located["original_artifact_ref"],
            "kind": "image_region", "region": deepcopy(located["image_region"])}
    return {"source_ref": original["source_ref"], "artifact_ref": witness["artifact_ref"],
        "kind": "utf8_span", "start": original["start"], "end": original["end"]}


def _resolved_enum(selection, inputs):
    result = inputs.interpretation(selection)
    locations = [_locator(w) for w in result["witnesses"]]
    error = any(location is None for location in locations)
    if selection["value"] == "conflicting" and len({_digest(v) for v in locations if v is not None}) < 2:
        error = True
    result["status"] = "source_unavailable" if error else "interpreted"
    return result


def _resolved_meaning(selection, dimension, inputs):
    witnesses = [inputs.witness(w) for w in selection["witnesses"]]
    canonical = inputs.witness(selection["canonical_witness"]) if selection["canonical_witness"] else None
    failed = any(w["error"] for w in witnesses) or bool(canonical and canonical["error"])
    status = "source_unavailable" if failed else selection["status"]
    if status == "conflicting" and len({_digest(_locator(w)) for w in witnesses}) < 2:
        status = "source_unavailable"
    canonical_id = ("binding_meaning_" + _digest({"dimension": dimension, "source": _locator(canonical)})) if status == "known" else None
    return {"status": status, "label": selection["label"], "witnesses": witnesses,
        "canonical_witness": canonical, "canonical_id": canonical_id, "interpretation_attribution": ATTRIBUTION}


def _resolved_literal(selection, inputs):
    if selection is None:
        return {"status": "not_selected", "declared_status": None, "candidates": [], "fragments": [],
            "interpretation_attribution": ATTRIBUTION}
    result = inputs.transcription(selection)
    result["declared_status"] = selection["status"]
    if any(w["error"] for part in ("candidates", "fragments") for w in result[part]):
        result["status"] = "source_unavailable"
    return result


def _quote(literal):
    return literal["candidates"][0]["witness"]["quote"] if literal["status"] == "exact" else None


def _point(expression, scale):
    try:
        value, relation, spread = _measurement(expression, scale, "measurement.expression")
        return {"value": value, "relation": relation, "reported_spread": spread}, None
    except (ExperimentalContractError, ValueError, OverflowError) as error:
        return None, {"code": getattr(error, "code", "numerical_model_range"), "field": "measurement.expression"}


def _measurement_result(selection, inputs):
    if selection is None:
        return {"parse_status": "not_selected", "canonical_locator": None, "source_cell_id": None,
            "expression": _resolved_literal(None, inputs), "unit": _resolved_literal(None, inputs),
            "native_measurement": None, "canonical_measurement": None, "candidate_measurements": [], "error": None}
    expression, unit = (_resolved_literal(selection[k], inputs) for k in ("expression", "unit"))
    result = {"parse_status": expression["status"], "canonical_locator": None, "source_cell_id": None,
        "expression": expression, "unit": unit, "native_measurement": None, "canonical_measurement": None,
        "candidate_measurements": [], "error": None}
    try:
        locator = inputs.location(selection["image_id"], selection["cell_region"])
        result["canonical_locator"] = locator
        result["source_cell_id"] = "binding_source_cell_" + _digest(locator)
        for part in ("candidates", "fragments"):
            for witness in expression[part]:
                mapped = witness["canonical_locator"]
                if witness["error"] or mapped is None:
                    continue
                if (any(mapped[k] != locator[k] for k in ("original_source_ref", "original_artifact_ref"))
                        or not _inside(mapped["image_region"], locator["image_region"])):
                    _fail("expression_outside_canonical_cell", "measurement.expression")
        raw_unit = _quote(unit)
        scale = _SCALES.get(raw_unit)
        for index, witness in enumerate(expression["candidates"]):
            native, error = (None, {"code": "source_unavailable", "field": "measurement.expression"}) if witness["error"] else _point(witness["witness"]["quote"], 1.0)
            canonical, canonical_error = (None, None) if native is None or scale is None else _point(witness["witness"]["quote"], scale)
            result["candidate_measurements"].append({"candidate_index": index, "witness": deepcopy(witness),
                "native": native, "canonical": canonical, "canonical_unit": "nM" if canonical is not None else None,
                "error": error or canonical_error})
        if expression["status"] != "exact":
            return result
        candidate = result["candidate_measurements"][0]
        result["native_measurement"] = candidate["native"]
        if candidate["native"] is None:
            result.update(parse_status="unsupported_expression", error=candidate["error"])
        elif unit["status"] != "exact":
            result.update(parse_status="unit_" + unit["status"])
        elif scale is None:
            result.update(parse_status="unsupported_unit")
        elif candidate["canonical"] is None:
            result.update(parse_status="numerical_range", error=candidate["error"])
        else:
            result["canonical_measurement"] = candidate["canonical"]
            result["parse_status"] = "reported_unavailable" if candidate["canonical"]["relation"] == "unreported" else "parsed"
    except ExperimentalContractError as error:
        result.update(parse_status="source_unavailable", error={"code": error.code, "field": error.field})
    return result


def _text_context(witness, inputs):
    """Mechanical token/qualification context; no scientific interpretation."""
    selected = witness["witness"]
    if selected["kind"] != "text" or witness["error"]:
        return "", ""
    content = inputs.source(selected["source_ref"], selected["representation"])["content"]
    before = content[max(0, selected["start"] - 96):selected["start"]].decode("utf-8", errors="ignore")
    after = content[selected["end"]:selected["end"] + 24].decode("utf-8", errors="ignore")
    # A closing source-markup angle bracket is not a printed greater-than sign.
    before = re.sub(r"<[^<>]*>\s*$", " ", before)
    after = re.sub(r"^\s*<[^<>]*>", " ", after)
    return before, after


def _scalar(literal, inputs, purpose):
    result = {"literal": literal, "status": literal["status"], "value": None,
        "relation": None, "approximate": False, "percent": False, "raw_number": None,
        "qualification_origin": None, "error": None}
    quote = _quote(literal)
    if quote is None:
        return result
    match = _SCALAR.fullmatch(quote)
    if match is None:
        result["status"] = "unsupported_literal"
        return result
    relation = match["relation"]
    relation = ("ge" if relation and relation.lower().strip() == "at least" else
        "le" if relation and relation.lower().strip() == "at most" else _RELATIONS.get(relation))
    approximate = match["approx"] is not None
    before, after = _text_context(literal["candidates"][0], inputs)
    raw = match["number"]
    if (before and re.search(r"[\w.+−-]$", before)
            or after and re.match(r"[\w+−-]|\.\d", after)):
        result.update(status="source_token_incomplete", raw_number=raw)
        return result
    prefix = re.search(r"(?P<approx>about|approximately|[~≈∼])\s*$|(?P<relation>>=|<=|≥|≤|>|<|at\s+least|at\s+most)\s*$", before, re.IGNORECASE)
    if prefix:
        if prefix["approx"]:
            approximate = True
        else:
            outside = prefix["relation"].lower()
            outside = "ge" if re.fullmatch(r"at\s+least", outside) else "le" if re.fullmatch(r"at\s+most", outside) else _RELATIONS[outside]
            if relation != "eq" and relation != outside:
                result.update(status="conflicting_qualification", raw_number=raw)
                return result
            relation = outside
        result["qualification_origin"] = "retained_text_context"
    elif approximate or relation != "eq":
        result["qualification_origin"] = "selected_literal"
    try:
        exact = Decimal(raw)
        value = float(exact)
        if not math.isfinite(value) or value == 0 and exact != 0:
            raise ValueError("unrepresentable")
    except (InvalidOperation, ValueError, OverflowError):
        result.update(status="numerical_range", raw_number=raw)
        return result
    if purpose in ("exact_count", "minimum_count") and (
            not re.fullmatch(r"[0-9]+", raw) or exact < 1 or match["percent"]):
        result.update(status="unsupported_count_literal", raw_number=raw)
        return result
    result.update(value=int(raw) if purpose in ("exact_count", "minimum_count") else value,
        relation=relation, approximate=approximate, percent=match["percent"] is not None,
        raw_number=raw, status="qualified" if approximate or relation != "eq" else "parsed")
    # A percent omitted immediately outside the selected token is incomplete,
    # rather than a source probability on the unit interval.
    if purpose == "confidence_level" and not match["percent"] and re.match(r"\s*%", after):
        result["status"] = "source_token_incomplete"
    return result


def _empty_uncertainty(inputs):
    return {"selection_status": "not_selected", "meanings": None, "interval": None,
        "confidence_level": _scalar(_resolved_literal(None, inputs), inputs, "confidence_level"),
        "exact_count": _scalar(_resolved_literal(None, inputs), inputs, "exact_count"),
        "minimum_count": _scalar(_resolved_literal(None, inputs), inputs, "minimum_count"),
        "reported_spread_status": "unresolved", "canonical": None,
        "unavailable_reasons": ["uncertainty_description_not_selected"]}


def _uncertainty_result(selection, measurement, inputs):
    if selection is None:
        return _empty_uncertainty(inputs)
    meanings = {name: _resolved_enum(selection[name], inputs) for name in ("statistic", "basis", "repetition_basis")}
    exact_count = _scalar(_resolved_literal(selection["exact_count"], inputs), inputs, "exact_count")
    minimum_count = _scalar(_resolved_literal(selection["minimum_count"], inputs), inputs, "minimum_count")
    level = _scalar(_resolved_literal(selection["confidence_level"], inputs), inputs, "confidence_level")
    interval = None
    interval_values = None
    reasons = []
    if selection["interval"] is not None:
        selected = selection["interval"]
        relationship = _resolved_enum(selected["unit_relationship"], inputs)
        unit = _resolved_literal(selected["unit"], inputs)
        lower = _scalar(_resolved_literal(selected["lower"], inputs), inputs, "interval")
        upper = _scalar(_resolved_literal(selected["upper"], inputs), inputs, "interval")
        raw_unit = (_quote(measurement["unit"]) if relationship["value"] == "same_as_parameter" else
                    _quote(unit) if relationship["value"] == "explicit_unit" else None)
        scale = _SCALES.get(raw_unit) if relationship["status"] == "interpreted" else None
        converted = []
        for endpoint in (lower, upper):
            value = None
            if endpoint["status"] == "parsed" and not endpoint["percent"] and scale is not None:
                value = endpoint["value"] * scale
                if not math.isfinite(value) or value == 0 and endpoint["value"] != 0:
                    value = None
                    endpoint["status"] = "numerical_range"
            converted.append(value)
        interval_values = converted if any(value is not None for value in converted) else None
        interval = {"lower": lower, "upper": upper, "unit_relationship": relationship,
            "unit": unit, "canonical_values": interval_values, "canonical_unit": "nM" if scale is not None else None}
        if scale is None:
            reasons.append("uncertainty_interval_unit_unavailable")
        if all(value is not None for value in converted) and converted[0] > converted[1]:
            reasons.append("conflicting_interval_order")
    probability = None
    if level["status"] == "parsed":
        probability = level["value"] / 100 if level["percent"] else level["value"]
        if not 0 < probability < 1:
            probability = None
            reasons.append("confidence_level_out_of_range")
    exact_value = exact_count["value"] if exact_count["status"] == "parsed" else None
    minimum_value = (minimum_count["value"] if minimum_count["status"] in ("parsed", "qualified")
        and not minimum_count["approximate"] and minimum_count["relation"] in ("eq", "ge", "gt") else None)
    if exact_value is not None and minimum_value is not None and exact_value < minimum_value:
        reasons.append("conflicting_exact_minimum_count")
    canonical_measurement = measurement["canonical_measurement"]
    spread = canonical_measurement["reported_spread"] if canonical_measurement else None
    statistic = meanings["statistic"]["value"]
    if any(v["status"] != "interpreted" for v in meanings.values()):
        reasons.append("uncertainty_meaning_source_unavailable")
    if statistic in ("unknown", "conflicting"):
        reasons.append("uncertainty_statistic_" + statistic)
    if meanings["basis"]["value"] == "conflicting" or meanings["repetition_basis"]["value"] == "conflicting":
        reasons.append("uncertainty_basis_conflicting")
    if statistic in ("unreported", "confidence_interval") and spread is not None:
        reasons.append("reported_spread_uncertainty_meaning_conflict")
    if statistic != "confidence_interval" and (selection["interval"] is not None or selection["confidence_level"] is not None):
        reasons.append("interval_uncertainty_meaning_conflict")
    if canonical_measurement and canonical_measurement["relation"] == "unreported" and statistic != "unreported":
        reasons.append("uncertainty_on_unreported_parameter")
    blocking = any(reason.startswith("conflicting_") or reason.endswith("conflict") or
        reason in ("uncertainty_meaning_source_unavailable", "uncertainty_statistic_unknown",
            "uncertainty_statistic_conflicting", "uncertainty_basis_conflicting",
            "uncertainty_on_unreported_parameter") for reason in reasons)
    canonical = None
    if not blocking:
        canonical = {"statistic": statistic,
            "basis": meanings["basis"]["value"],
            "interval": interval_values if statistic == "confidence_interval" else None,
            "confidence_level": probability if statistic == "confidence_interval" else None,
            "exact_count": exact_value, "minimum_count": minimum_value,
            "repetition_basis": "unspecified" if meanings["repetition_basis"]["value"] == "unknown" else meanings["repetition_basis"]["value"]}
    return {"selection_status": "selected", "meanings": meanings, "interval": interval,
        "confidence_level": level, "exact_count": exact_count, "minimum_count": minimum_count,
        "reported_spread_status": "reported" if spread is not None else "not_in_selected_expression",
        "canonical": canonical, "unavailable_reasons": reasons}


def _physical_identity(selection, inputs):
    if selection is None:
        return {"status": "unknown", "canonical_witness": None, "witnesses": [], "physical_fit_id": None,
            "interpretation_attribution": ATTRIBUTION}
    canonical = inputs.witness(selection["canonical_witness"])
    witnesses = [inputs.witness(w) for w in selection["witnesses"]]
    status = "source_unavailable" if canonical["error"] or any(w["error"] for w in witnesses) else "known"
    return {"status": status, "canonical_witness": canonical, "witnesses": witnesses,
        "physical_fit_id": "binding_physical_fit_" + _digest(_locator(canonical)) if status == "known" else None,
        "interpretation_attribution": ATTRIBUTION}


def _role_result(selection, inputs):
    if selection is None:
        return {"selection_status": "not_selected", "parameter_kind": None, "definitions": None,
            "physical_fit": _physical_identity(None, inputs), "measurement": _measurement_result(None, inputs),
            "uncertainty": _empty_uncertainty(inputs), "calculation_operand": None,
            "unavailable_reasons": ["role_not_selected"]}
    measurement = _measurement_result(selection["measurement"], inputs)
    return {"selection_status": "selected", "parameter_kind": _resolved_enum(selection["parameter_kind"], inputs),
        "definitions": {name: _resolved_meaning(selection["definitions"][name], name, inputs) for name in ID_FIELDS},
        "physical_fit": _physical_identity(selection["physical_fit"], inputs), "measurement": measurement,
        "uncertainty": _uncertainty_result(selection["uncertainty"], measurement, inputs),
        "calculation_operand": None, "unavailable_reasons": []}


def _joint_cells(roles):
    groups = {}
    for role, row in roles.items():
        key = row["measurement"]["source_cell_id"]
        if key is not None:
            groups.setdefault(key, []).append((role, row))
    for group in groups.values():
        readings = {_quote(row["measurement"]["expression"]) for _, row in group
            if row["measurement"]["expression"]["status"] == "exact"}
        units = {_quote(row["measurement"]["unit"]) for _, row in group
            if row["measurement"]["unit"]["status"] == "exact"}
        semantic_conflict = False
        for name in ID_FIELDS:
            known = {row["definitions"][name]["canonical_id"] for _, row in group
                if row["definitions"] and row["definitions"][name]["canonical_id"] is not None}
            semantic_conflict |= len(known) > 1
        kinds = {row["parameter_kind"]["value"] for _, row in group if row["parameter_kind"] and
            row["parameter_kind"]["status"] == "interpreted" and row["parameter_kind"]["value"] not in ("unknown", "conflicting")}
        conflicting = len(readings) > 1 or len(units) > 1 or len(kinds) > 1 or semantic_conflict or any(
            row["measurement"]["parse_status"] == "conflicting" for _, row in group)
        unresolved = len(group) > 1 and any(row["measurement"]["parse_status"] in ("ambiguous", "unreadable") for _, row in group)
        if conflicting or unresolved:
            for _, row in group:
                row["measurement"].update(parse_status="conflicting" if conflicting else "ambiguous",
                    native_measurement=None, canonical_measurement=None,
                    error={"code": "conflicting_source_cell" if conflicting else "unresolved_source_cell_rereading", "field": "roles"})
                row["unavailable_reasons"].append("conflicting_source_cell" if conflicting else "unresolved_source_cell_rereading")


def _overlaps(roles):
    result = []
    for index, left_role in enumerate(ROLES):
        left = roles[left_role]["measurement"]["canonical_locator"]
        if left is None:
            continue
        for right_role in ROLES[index + 1:]:
            right = roles[right_role]["measurement"]["canonical_locator"]
            if right is None or left == right or any(left[k] != right[k] for k in ("original_source_ref", "original_artifact_ref")):
                continue
            a, b = left["image_region"], right["image_region"]
            if max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
                result.append({"left_role": left_role, "right_role": right_role})
    return result


def _operand(row, common_kind, origin):
    if row["selection_status"] != "selected":
        return None
    kind = row["parameter_kind"]
    if kind["status"] != "interpreted" or kind["value"] != common_kind:
        row["unavailable_reasons"].append("parameter_kind_" + (kind["value"] if kind["value"] in ("unknown", "conflicting") else "mismatch"))
        return None
    measurement = row["measurement"]
    numeric = measurement["canonical_measurement"]
    if numeric is None:
        row["unavailable_reasons"].append("measurement_" + measurement["parse_status"])
        return None
    located = measurement["canonical_locator"]
    source = {"source_ref": located["original_source_ref"], "artifact_ref": located["original_artifact_ref"],
        "kind": "image_region", "region": deepcopy(located["image_region"])}
    return {"value": numeric["value"], "relation": numeric["relation"], "reported_spread": numeric["reported_spread"],
        "origin": origin, "context": {name: row["definitions"][name]["label"] for name in CONTEXT_FIELDS},
        "canonical_ids": {name: row["definitions"][name]["canonical_id"] for name in ID_FIELDS},
        "physical_fit_id": row["physical_fit"]["physical_fit_id"],
        "uncertainty": deepcopy(row["uncertainty"]["canonical"]), "source": source,
        "expression": _quote(measurement["expression"])}


def read_binding_interaction_inputs(arguments, *, read_source):
    """Return exact source partials and validated common-definition048 operands.

    No048 calculator is invoked. Validation uses the separately frozen053
    uncertainty contract; a missing/mismatched implementation raises an explicit
    implementation error, never a scientific unknown. Raw source means and
    uncertainty remain distinct from a missing scientific interpretation.
    """
    _validate(arguments)
    if not callable(read_source):
        _fail("source_reader_required", "read_source")
    dependencies = _dependencies()
    selection = deepcopy(arguments)
    acquired, roster = {}, []
    # Authorization errors cross the action boundary before _Inputs' local
    # failure retention. Ordinary authorized read errors stay per dependency.
    for reference, representation in _source_requests(selection):
        try:
            source = read_source(reference, representation)
        except ContractError:
            raise
        except Exception as error:
            source = error
        acquired[(reference, representation)] = source
        roster.append({"source_ref": reference, "representation": representation,
            "artifact_ref": source.get("artifact_ref") if type(source) is dict else None,
            "sha256": hashlib.sha256(source["content"]).hexdigest() if type(source) is dict and type(source.get("content")) is bytes else None,
            "error": {"code": getattr(source, "code", "source_read_failed"), "field": reference} if isinstance(source, Exception) else None})
    def cached(reference, representation):
        value = acquired[(reference, representation)]
        if isinstance(value, Exception):
            raise value
        return value
    inputs = _Inputs(cached)
    images = [inputs.image(spec) for spec in selection["images"]]
    common_kind = _resolved_enum(selection["parameter_kind"], inputs)
    roles = {role: _role_result(selection["roles"][role], inputs) for role in ROLES}
    _joint_cells(roles)
    relationships, calculation_relationships = {}, {}
    for name in RELATIONS:
        selected = selection["relationships"][name]
        interpreted = _resolved_enum({"value": selected["status"], "witnesses": selected["witnesses"]}, inputs)
        relationships[name] = interpreted
        sources = [_locator(w) for w in interpreted["witnesses"]]
        calculation_relationships[name] = {"status": interpreted["value"] if interpreted["status"] == "interpreted" else "unknown",
            "sources": [source for source in sources if source is not None]}
    status = ("common_parameter_kind_source_unavailable" if common_kind["status"] != "interpreted" else
              "common_parameter_kind_" + common_kind["value"] if common_kind["value"] in ("unknown", "conflicting") else "ready")
    calculation_inputs = None
    if status == "ready":
        origin = "synthetic" if selection["source_kind"] == "synthetic_fixture" else "visual_transcription"
        for role, row in roles.items():
            row["calculation_operand"] = _operand(row, common_kind["value"], origin)
        calculation_inputs = {"version": CALC_INPUT_VERSION, "parameter_kind": common_kind["value"], "unit": "nM",
            "comparison_scope": selection["comparison_scope"],
            "operands": {role: deepcopy(row["calculation_operand"]) for role, row in roles.items()},
            "relationships": calculation_relationships}
        validate_binding_interaction_inputs(calculation_inputs)
    return {"version": OUTPUT_VERSION, "source_ref": selection["source_ref"], "source_kind": selection["source_kind"],
        "selection": selection, "parameter_kind": common_kind, "images": images, "roles": roles,
        "relationships": relationships, "geometry_overlaps": _overlaps(roles),
        "calculation_input_status": status, "calculation_inputs": calculation_inputs,
        "source_refs": list(dict.fromkeys(row["source_ref"] for row in roster)),
        "source_representations": roster, "implementation_dependencies": dependencies,
        "interpretation_attribution": ATTRIBUTION}
