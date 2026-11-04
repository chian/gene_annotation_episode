"""Read source-bound A105 assay operands without acquiring or judging a paper.

A caller interprets which experiment and numerical role a source passage has.
This reader verifies custody, literal numeric/unit selections and explicit
covariance ownership. Those checks are not proof of the interpretation's truth.
There is no model call, score, source fetch, state mutation or episode decision.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .domain import REF, identity, obj
from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_assay_inputs_v1"
PRIMITIVE_ORDER = ("q", "g", "k", "E", "u", "v")
ASSAY_LITERAL_FIELDS = ("molecule", "organism", "genotype", "construct", "preparation",
                        "condition", "intended_variable", "experimental_system", "expression_host",
                        "measured_entity", "asserted_input", "asserted_output")
ENDPOINTS = ("oxygen_consumption", "product_formation", "substrate_depletion", "ligand_binding",
             "transport_flux", "growth", "abundance", "other_measured_endpoint", "unknown", "conflicting")
ARRANGEMENTS = ("single_preparation", "replacement", "coexistence", "not_applicable", "unknown", "conflicting")
SOURCE_KINDS = ("primary_source", "retained_extraction", "graph_extraction", "synthetic_fixture")
VARIANCE_STATUSES = ("known", "estimated", "unknown")
OBSERVATION_MODELS = ("none", "known_normal_nonnegative_presence")
_NUMBER = re.compile(r"[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?\Z")
_ARGS = ("source_ref", "source_kind", "assay", "primitives", "covariance_source_ref",
         "distinct_residual_variance", "variance_status", "observation_model", "model_witnesses")
_MEASUREMENT_FIELDS = ("witness", "number_start", "number_end", "unit_start", "unit_end")
_WITNESS_FIELDS = ("source_ref", "representation", "start", "end", "quote")
_COVARIANCE_FIELDS = ("version", "primitive_order", "primitive_measurement_keys",
                      "primitive_units", "covariance", "origin")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _index(value, field):
    if type(value) is not int or value < 0:
        _fail("nonnegative_integer_offset_required", field)


def _finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _numeric(token, field):
    if not _NUMBER.fullmatch(token):
        _fail("literal_point_number_required", field)
    try:
        value = float(token.replace("−", "-"))
    except (OverflowError, ValueError):
        _fail("finite_number_required", field)
    _finite(value, field)
    if value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
        _fail("numerical_model_range", field)
    return value


def _unit(raw, role, field):
    compact = re.sub(r"\s+", "", raw).replace("µ", "u").replace("μ", "u")
    if role in ("q", "g", "u", "v"):
        units, canonical = {"uM/min": 1., "mM/min": 1000., "nM/min": .001}, "uM/min"
    elif role == "E":
        units, canonical = {"uM": 1., "mM": 1000., "nM": .001}, "uM"
    elif role == "k":
        units, canonical = {"": 1., "fraction": 1., "dimensionless": 1., "1": 1.}, "dimensionless"
    else:
        units, canonical = {"per_min_squared": 1., "min^-2": 1., "min−2": 1.}, "per_min_squared"
    if compact not in units:
        _fail("incompatible_primitive_unit", field)
    return canonical, units[compact]


def _witness_schema():
    return obj({"source_ref": REF, "representation": {"enum": ["original", "text"]},
        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
        "quote": {"type": "string", "minLength": 1}})


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def assay_arguments_schema():
    """Closed selected-operation operands; all numbers come from source spans."""
    witness = _witness_schema()
    measurement = obj({"witness": deepcopy(witness), **{field: {"type": "integer", "minimum": 0}
        for field in ("number_start", "number_end", "unit_start", "unit_end")}})
    def interpretation(values):
        return obj({"value": {"enum": list(values)},
                    "witnesses": {"type": "array", "items": deepcopy(witness)}})
    assay = obj({**{field: _nullable(deepcopy(witness)) for field in ASSAY_LITERAL_FIELDS},
                 "endpoint": interpretation(ENDPOINTS), "arrangement": interpretation(ARRANGEMENTS)})
    return obj({"source_ref": REF, "source_kind": {"enum": list(SOURCE_KINDS)}, "assay": assay,
        "primitives": obj({role: _nullable(deepcopy(measurement)) for role in PRIMITIVE_ORDER}),
        "covariance_source_ref": _nullable(deepcopy(REF)),
        "distinct_residual_variance": _nullable(deepcopy(measurement)),
        "variance_status": {"enum": list(VARIANCE_STATUSES)},
        "observation_model": {"enum": list(OBSERVATION_MODELS)},
        "model_witnesses": {"type": "array", "items": deepcopy(witness)}})


class _Sources:
    def __init__(self, read_source):
        if not callable(read_source):
            _fail("source_reader_required", "read_source")
        self.read_source = read_source
        self.cache = {}
        self.references = []

    def source(self, reference, representation):
        _text(reference, "source_ref")
        if representation not in ("original", "text"):
            _fail("unknown_source_representation", "representation")
        key = (reference, representation)
        if key not in self.cache:
            result = self.read_source(reference, representation)
            _keys(result, ("artifact_ref", "content"), "source_result")
            _text(result["artifact_ref"], "source_result.artifact_ref")
            if type(result["content"]) is not bytes:
                _fail("source_bytes_required", "source_result.content")
            self.cache[key] = dict(result)
            if reference not in self.references:
                self.references.append(reference)
        return self.cache[key]

    def witness(self, value, field):
        _keys(value, _WITNESS_FIELDS, field)
        _text(value["quote"], field + ".quote")
        for name in ("start", "end"):
            _index(value[name], field + "." + name)
        if value["end"] <= value["start"]:
            _fail("nonempty_source_span_required", field)
        source = self.source(value["source_ref"], value["representation"])
        if value["end"] > len(source["content"]):
            _fail("source_span_out_of_bounds", field)
        try:
            actual = source["content"][value["start"]:value["end"]].decode("utf-8")
        except UnicodeDecodeError as error:
            raise ExperimentalContractError("source_span_utf8_boundary_required", field) from error
        if actual != value["quote"]:
            actual_bytes = source["content"][value["start"]:value["end"]]
            try:
                nominated_bytes = value["quote"].encode("utf-8")
            except UnicodeEncodeError:
                nominated_bytes = None
            mismatch = (None if nominated_bytes is None else next(
                (index for index, (left, right) in enumerate(zip(actual_bytes, nominated_bytes))
                 if left != right), min(len(actual_bytes), len(nominated_bytes))))
            # A reversible observation of only the authorized selected bytes.
            # It nominates no replacement arguments or scientific interpretation.
            literal = (json.dumps(actual).replace("|", r"\u007c")
                       .replace("<", r"\u003c").replace(">", r"\u003e"))
            raise ExperimentalContractError("source_quote_mismatch", field, detail={
                "kind": "selected_source_span_observation",
                "source_ref": value["source_ref"], "artifact_ref": source["artifact_ref"],
                "representation": value["representation"],
                "start": value["start"], "end": value["end"],
                "actual_utf8_length": len(actual_bytes),
                "nominated_utf8_length": None if nominated_bytes is None else len(nominated_bytes),
                "first_mismatch_utf8_byte": mismatch,
                "selected_span_text": actual, "selected_span_text_json": literal})
        return {**deepcopy(value), "artifact_ref": source["artifact_ref"]}

    def measurement(self, value, role, field):
        _keys(value, _MEASUREMENT_FIELDS, field)
        witness = self.witness(value["witness"], field + ".witness")
        quote = witness["quote"]
        for name in ("number_start", "number_end", "unit_start", "unit_end"):
            _index(value[name], field + "." + name)
        ns, ne, us, ue = (value[name] for name in ("number_start", "number_end", "unit_start", "unit_end"))
        if not 0 <= ns < ne <= us <= ue <= len(quote):
            _fail("measurement_span_order_invalid", field)
        if quote[ne:us].strip():
            _fail("measurement_unit_not_adjacent", field)
        if us == ue and (role != "k" or us != ne):
            _fail("measurement_unit_required", field)
        token, raw_unit = quote[ns:ne], quote[us:ue]
        # Validate outside the selected quote too: cutting '<' or a leading digit
        # out of the witness must not turn a bound or partial token into a point.
        source = self.source(witness["source_ref"], witness["representation"])["content"]
        absolute_start = witness["start"] + len(quote[:ns].encode("utf-8"))
        absolute_end = witness["start"] + len(quote[:ne].encode("utf-8"))
        prefix = source[max(0, absolute_start - 120):absolute_start].decode("utf-8", errors="ignore")
        suffix = source[absolute_end:absolute_end + 40].decode("utf-8", errors="ignore")
        before = prefix[-1:] or " "
        after = suffix[:1] or " "
        numeric_edge = "0123456789.eE+−-"
        period_ends_sentence = (after == "." and "." in token
            and (len(suffix) == 1 or not (suffix[1].isdigit() or suffix[1] == ".")))
        if before in numeric_edge or after in numeric_edge and not period_ends_sentence:
            _fail("partial_numeric_token", field)
        # A terminal XML tag is markup, not a greater-than bound. Removing only
        # such terminal tags for this check also exposes an encoded comparator
        # immediately before inline markup. Retained source/witnesses stay exact.
        scientific_prefix = re.sub(r"(?:</?[A-Za-z_][^<>]*>\s*)+$", "", prefix)
        if (re.search(r"[<>≤≥~≈±]\s*$", scientific_prefix)
                or re.search(r"(?:&(?:lt|gt);|&#0*(?:60|62);|&#x0*(?:3c|3e);)\s*$",
                             scientific_prefix, re.IGNORECASE)
                or re.search(r"\b(?:less\s+than(?:\s+or\s+equal\s+to)?|"
                             r"greater\s+than(?:\s+or\s+equal\s+to)?|"
                             r"no\s+more\s+than|no\s+less\s+than|at\s+most|at\s+least|below|above|"
                             r"approximately|about|circa)\s*$", scientific_prefix, re.IGNORECASE)):
            _fail("censored_or_approximate_point", field)
        if not raw_unit and re.match(r"\s*(?:%|(?:[µμu]M|nM|mM|[µμu]mol|nmol|mmol|mol|mg|g|mL|L|s|min|percent|per\s+cent|per_min_squared)\b)", suffix):
            _fail("dimensional_unit_omitted", field)
        if raw_unit:
            absolute_unit_end = witness["start"] + len(quote[:ue].encode("utf-8"))
            after_unit = source[absolute_unit_end:absolute_unit_end + 8].decode("utf-8", errors="ignore")[:1]
            if after_unit and (after_unit.isalnum() or after_unit in "/_^−-⁻"):
                _fail("partial_unit_token", field)
        native = _numeric(token, field + ".number")
        canonical_unit, multiplier = _unit(raw_unit, role, field + ".unit")
        converted = native * multiplier
        if not math.isfinite(converted) or converted == 0 and native != 0:
            _fail("numerical_model_range", field)
        if role == "distinct_residual_variance" and converted < 0:
            _fail("nonnegative_residual_variance_required", field)
        measurement_key = identity("literature_measurement", {"source_ref": witness["source_ref"],
            "artifact_ref": witness["artifact_ref"],
            "number_start": absolute_start, "number_end": absolute_end})
        return {"role": role, "value": converted, "unit": canonical_unit, "multiplier": multiplier,
            "raw_number": token, "raw_unit": raw_unit, "witness": witness,
            **{name: value[name] for name in ("number_start", "number_end", "unit_start", "unit_end")},
            "measurement_key": measurement_key}


def _interpretation(value, allowed, sources, field):
    _keys(value, ("value", "witnesses"), field)
    if value["value"] not in allowed:
        _fail("unknown_interpretation_value", field + ".value")
    if not isinstance(value["witnesses"], list):
        _fail("witness_list_required", field + ".witnesses")
    witnesses = [sources.witness(item, f"{field}.witnesses[{i}]") for i, item in enumerate(value["witnesses"])]
    unique = {(item["source_ref"], item["artifact_ref"], item["representation"], item["start"], item["end"])
              for item in witnesses}
    required = 2 if value["value"] == "conflicting" else 0 if value["value"] == "unknown" else 1
    if len(unique) < required:
        _fail("interpretation_witness_required", field + ".witnesses")
    return {"kind": "source_interpretation", "value": value["value"], "witnesses": witnesses}


def _json_source(raw, field):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key", field)
            result[key] = value
        return result
    def constant(_value):
        _fail("finite_number_required", field)
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExperimentalContractError("covariance_json_required", field) from error


def _covariance(reference, observations, sources):
    if reference is None:
        return None, None
    _text(reference, "covariance_source_ref")
    if any(observations[role] is None for role in PRIMITIVE_ORDER):
        _fail("complete_covariance_owners_required", "covariance_source_ref")
    raw = sources.source(reference, "original")
    value = _json_source(raw["content"], "covariance_source_ref")
    _keys(value, _COVARIANCE_FIELDS, "covariance_source")
    if value["version"] != "a105_primitive_covariance_v1":
        _fail("covariance_version_mismatch", "covariance_source.version")
    if value["primitive_order"] != list(PRIMITIVE_ORDER):
        _fail("covariance_primitive_order_mismatch", "covariance_source.primitive_order")
    if value["primitive_measurement_keys"] != [observations[r]["measurement_key"] for r in PRIMITIVE_ORDER]:
        _fail("covariance_measurement_owner_mismatch", "covariance_source.primitive_measurement_keys")
    if value["primitive_units"] != [observations[r]["raw_unit"] for r in PRIMITIVE_ORDER]:
        _fail("covariance_primitive_unit_mismatch", "covariance_source.primitive_units")
    if value["origin"] not in ("reported", "derived", "synthetic"):
        _fail("unknown_covariance_origin", "covariance_source.origin")
    matrix = value["covariance"]
    if (not isinstance(matrix, list) or len(matrix) != 6
            or any(not isinstance(row, list) or len(row) != 6 for row in matrix)):
        _fail("six_by_six_covariance_required", "covariance_source.covariance")
    multipliers = [observations[role]["multiplier"] for role in PRIMITIVE_ORDER]
    converted = []
    for i, row in enumerate(matrix):
        values = []
        for j, operand in enumerate(row):
            _finite(operand, f"covariance_source.covariance[{i}][{j}]")
            try:
                number = float(operand) * multipliers[i] * multipliers[j]
            except OverflowError:
                _fail("numerical_model_range", "covariance_source.covariance")
            if not math.isfinite(number) or number == 0 and operand != 0:
                _fail("numerical_model_range", "covariance_source.covariance")
            values.append(number)
        converted.append(values)
    for i, role in enumerate(PRIMITIVE_ORDER):
        for j in range(i):
            other = PRIMITIVE_ORDER[j]
            if observations[role]["measurement_key"] == observations[other]["measurement_key"]:
                if converted[i] != converted[j] or any(row[i] != row[j] for row in converted):
                    _fail("shared_measurement_covariance_mismatch", "covariance_source.covariance")
    return converted, value["origin"]


def read_assay_inputs(arguments, *, read_source):
    """Read a finite source assay graph; unknown operands remain exact nulls.

    ``read_source`` authorizes actual received/scoped source references and returns
    their retained bytes. Source labels/roles/model assumptions are explicitly
    interpreted inputs. Matching quotes verifies neither biological attribution,
    comparison validity, independence nor the requested sampling model.
    """
    _keys(arguments, _ARGS, "arguments")
    if arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "source_kind")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    _keys(arguments["assay"], (*ASSAY_LITERAL_FIELDS, "endpoint", "arrangement"), "assay")
    assay = {}
    for field in ASSAY_LITERAL_FIELDS:
        item = arguments["assay"][field]
        witness = sources.witness(item, "assay." + field) if item is not None else None
        assay[field] = {"value": witness["quote"], "witness": witness} if witness else None
    assay["endpoint"] = _interpretation(arguments["assay"]["endpoint"], ENDPOINTS, sources, "assay.endpoint")
    assay["arrangement"] = _interpretation(arguments["assay"]["arrangement"], ARRANGEMENTS, sources, "assay.arrangement")
    _keys(arguments["primitives"], PRIMITIVE_ORDER, "primitives")
    observations = {role: sources.measurement(item, role, "primitives." + role) if item is not None else None
                    for role, item in arguments["primitives"].items()}
    residual = arguments["distinct_residual_variance"]
    residual = sources.measurement(residual, "distinct_residual_variance", "distinct_residual_variance") if residual is not None else None
    if residual is not None and any(item is not None and item["measurement_key"] == residual["measurement_key"]
                                    for item in observations.values()):
        _fail("residual_not_distinct_measurement", "distinct_residual_variance")
    if arguments["variance_status"] not in VARIANCE_STATUSES:
        _fail("unsupported_variance_status", "variance_status")
    if arguments["observation_model"] not in OBSERVATION_MODELS:
        _fail("unsupported_observation_model", "observation_model")
    if not isinstance(arguments["model_witnesses"], list):
        _fail("witness_list_required", "model_witnesses")
    model_witnesses = [sources.witness(item, f"model_witnesses[{i}]")
                       for i, item in enumerate(arguments["model_witnesses"])]
    if (arguments["variance_status"] != "unknown" or arguments["observation_model"] != "none") and not model_witnesses:
        _fail("model_witness_required", "model_witnesses")
    covariance, origin = _covariance(arguments["covariance_source_ref"], observations, sources)
    return {"version": VERSION, "source_ref": arguments["source_ref"], "source_kind": arguments["source_kind"],
        "assay": assay, "primitive_order": list(PRIMITIVE_ORDER),
        "values": {role: observations[role]["value"] if observations[role] else None for role in PRIMITIVE_ORDER},
        "primitive_observations": observations, "covariance": covariance, "covariance_origin": origin,
        "variance_status": arguments["variance_status"],
        "distinct_residual_variance": residual["value"] if residual else None,
        "distinct_residual_observation": residual, "observation_model": arguments["observation_model"],
        "model_witnesses": model_witnesses, "source_refs": list(sources.references)}


__all__ = ["VERSION", "PRIMITIVE_ORDER", "ASSAY_LITERAL_FIELDS", "ENDPOINTS", "ARRANGEMENTS",
           "SOURCE_KINDS", "assay_arguments_schema", "read_assay_inputs"]
