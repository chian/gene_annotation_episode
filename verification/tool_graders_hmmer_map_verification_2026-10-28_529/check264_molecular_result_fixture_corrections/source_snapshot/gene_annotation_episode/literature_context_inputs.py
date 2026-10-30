"""Read retained A108 context operands and exact source witnesses.

This finite JSON boundary does not understand arbitrary paper prose or native
instrument files. Source custody does not establish biological attribution,
joint-domain support, independence, calibration or an exhaustive sample frame.
No acquisition, numerical component calculation, model call or mutation occurs.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .domain import REF, obj
from .literature_assay_inputs import (
    SOURCE_KINDS, _Sources, _fail, _finite, _keys, _nullable, _numeric,
    _text, _witness_schema,
)
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a108_context_inputs_v1"
DATA_VERSION = "a108_source_context_measurements_v1"
LITERAL_FIELDS = ("molecule", "organism", "strain", "experiment", "function",
                  "biological_context", "sample_frame", "endpoint", "condition")
QUESTION_KINDS = ("organism_capability", "sample_context_coverage", "unreported")
ORIGINS = ("reported", "graph_derived", "synthetic")
SCOPE_STATUSES = ("defined", "unreported")
FRAME_STATUSES = ("defined", "unreported")
PAIRINGS = ("paired", "unpaired_marginals", "unknown")
WEIGHT_BASES = ("equal_units", "measured_duration", "measured_volume", "inclusion_weight")
SAMPLING_DESIGNS = ("census", "independent_equal_weight", "unknown")
NATIVE_UNITS = ("ppbv_H2_gas", "ppmv_H2_gas", "uM_H2_solution", "percent_O2_gas",
                "percent_O2_saturation_solution", "mM", "uM", "nm", "minutes", "state")
JOINT_SUPPORT = ("established", "unresolved", "conflicting")
SCOPE_MATCHES = ("matched", "unresolved", "conflicting")
RELATIONS = ("numeric", "supported", "incompatible", "unresolved")
COUNT_RELATIONS = ("exact", "at_least", "at_most", "unknown")
REPLICATE_KINDS = ("biological", "technical", "timepoint", "unknown")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "interpretation_witnesses")
_INPUT_FIELDS = ("question_kind", "origin", "scope_status", "frame_status", "pairing",
                 "weight_basis", "sampling_design", "alpha", "permitted_remainder",
                 "requirements", "routes", "contexts", "marginals")
_OBSERVATION_FIELDS = ("requirement_key", "measurement_key", "unit", "interval", "relation",
                       "reported_sd", "reported_sem", "reported_plusminus", "reported_count",
                       "count_relation", "replicate_kind")


def context_population_schema():
    """Closed selected arguments; numerical operands reside in retained bytes."""
    witness = _witness_schema()
    return obj({"source_ref": deepcopy(REF), "data_source_ref": _nullable(deepcopy(REF)),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({name: _nullable(deepcopy(witness)) for name in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)}})


def _json_measurements(raw):
    field = "data_source_ref"

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key", field)
            result[key] = value
        return result

    def constant(_token):
        _fail("finite_number_required", field)

    def integer(token):
        value = int(token)
        _finite(value, field)
        return value

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_int=integer,
                          parse_float=lambda token: _numeric(token, field))
    except ExperimentalContractError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_context_measurements_source", field) from error


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_" + field.rsplit(".", 1)[-1], field)


def _list(value, field, *, nonempty=False):
    if not isinstance(value, list):
        _fail("array_required", field)
    if nonempty and not value:
        _fail("nonempty_array_required", field)


def _boolean(value, field):
    if type(value) is not bool:
        _fail("boolean_required", field)


def _unique_key(value, seen, field):
    _text(value, field)
    if value in seen:
        _fail("duplicate_physical_or_model_key", field)
    seen.add(value)


def _number(value, field, *, nonnegative=False, positive=False):
    if value is None:
        return
    _finite(value, field)
    if nonnegative and value < 0:
        _fail("nonnegative_value_required", field)
    if positive and value <= 0:
        _fail("positive_value_required", field)


def _interval(value, field):
    _keys(value, ("lower", "upper", "lower_closed", "upper_closed"), field)
    for name in ("lower", "upper"):
        _number(value[name], field + "." + name)
        _boolean(value[name + "_closed"], field + "." + name + "_closed")
        if value[name] is None and value[name + "_closed"]:
            _fail("unbounded_endpoint_must_be_open", field + "." + name)
    lower, upper = value["lower"], value["upper"]
    if lower is not None and upper is not None:
        if lower > upper:
            _fail("ordered_bounds_required", field)
        if lower == upper and not (value["lower_closed"] and value["upper_closed"]):
            _fail("nonempty_interval_required", field)


def _requirements(value):
    _list(value, "data_source.inputs.requirements")
    seen = set()
    for index, item in enumerate(value):
        field = f"data_source.inputs.requirements[{index}]"
        _keys(item, ("key", "unit", "supported", "incompatible"), field)
        _unique_key(item["key"], seen, field + ".key")
        _enum(item["unit"], NATIVE_UNITS, field + ".unit")
        for name in ("supported", "incompatible"):
            _list(item[name], field + "." + name)
            if item["unit"] == "state" and item[name]:
                _fail("state_domain_regions_must_be_empty", field + "." + name)
            for i, interval in enumerate(item[name]):
                _interval(interval, f"{field}.{name}[{i}]")
    return seen


def _routes(value, requirement_keys):
    if value is None:
        return
    _list(value, "data_source.inputs.routes", nonempty=True)
    seen = set()
    for index, item in enumerate(value):
        field = f"data_source.inputs.routes[{index}]"
        _keys(item, ("key", "requirements", "requirements_complete", "joint_support"), field)
        _unique_key(item["key"], seen, field + ".key")
        _boolean(item["requirements_complete"], field + ".requirements_complete")
        _enum(item["joint_support"], JOINT_SUPPORT, field + ".joint_support")
        _list(item["requirements"], field + ".requirements")
        members = set()
        for index, key in enumerate(item["requirements"]):
            path = f"{field}.requirements[{index}]"
            _unique_key(key, members, path)
            if key not in requirement_keys:
                _fail("unknown_requirement_reference", path)


def _observation(item, requirement_keys, field):
    _keys(item, _OBSERVATION_FIELDS, field)
    _text(item["requirement_key"], field + ".requirement_key")
    if item["requirement_key"] not in requirement_keys:
        _fail("unknown_requirement_reference", field + ".requirement_key")
    _text(item["measurement_key"], field + ".measurement_key")
    _enum(item["unit"], NATIVE_UNITS, field + ".unit")
    _enum(item["relation"], RELATIONS, field + ".relation")
    if item["unit"] == "state":
        if item["interval"] is not None or item["relation"] == "numeric":
            _fail("state_relation_requires_null_interval", field)
    else:
        if item["relation"] != "numeric":
            _fail("numeric_unit_requires_numeric_relation", field + ".relation")
        if item["interval"] is not None:
            _interval(item["interval"], field + ".interval")
    for name in ("reported_sd", "reported_sem", "reported_plusminus"):
        _number(item[name], field + "." + name, nonnegative=True)
        if item["unit"] == "state" and item[name] is not None:
            _fail("state_uncertainty_requires_numeric_unit", field + "." + name)
    count = item["reported_count"]
    if count is not None and (type(count) is not int or count < 0):
        _fail("nonnegative_integer_count_required", field + ".reported_count")
    _enum(item["count_relation"], COUNT_RELATIONS, field + ".count_relation")
    if count is None and item["count_relation"] != "unknown":
        _fail("missing_count_requires_unknown_relation", field + ".count_relation")
    _enum(item["replicate_kind"], REPLICATE_KINDS, field + ".replicate_kind")


def _contexts(value, requirement_keys, weight_basis):
    _list(value, "data_source.inputs.contexts")
    contexts, measurements, unique = {}, {}, []
    for index, item in enumerate(value):
        field = f"data_source.inputs.contexts[{index}]"
        _keys(item, ("key", "weight", "cluster_key", "scope_match", "observations"), field)
        _text(item["key"], field + ".key")
        if item["key"] in contexts and contexts[item["key"]] != item:
            _fail("duplicate_context_conflict", field + ".key")
        _number(item["weight"], field + ".weight", positive=True)
        if weight_basis == "equal_units" and item["weight"] not in (None, 1):
            _fail("equal_units_weight_must_be_one", field + ".weight")
        if item["cluster_key"] is not None:
            _text(item["cluster_key"], field + ".cluster_key")
        _enum(item["scope_match"], SCOPE_MATCHES, field + ".scope_match")
        _list(item["observations"], field + ".observations")
        seen = set()
        for i, observation in enumerate(item["observations"]):
            path = f"{field}.observations[{i}]"
            _observation(observation, requirement_keys, path)
            _unique_key(observation["requirement_key"], seen, path + ".requirement_key")
            meaning = {key: value for key, value in observation.items() if key != "requirement_key"}
            key = observation["measurement_key"]
            if key in measurements and measurements[key] != meaning:
                _fail("shared_measurement_meaning_conflict", path + ".measurement_key")
            measurements[key] = meaning
        key = item["key"]
        if key not in contexts:
            contexts[key] = item
            unique.append(item)
    return unique


def _marginals(value, requirement_keys):
    _list(value, "data_source.inputs.marginals")
    seen = set()
    for index, item in enumerate(value):
        field = f"data_source.inputs.marginals[{index}]"
        _keys(item, ("requirement_key", "lower", "upper"), field)
        _unique_key(item["requirement_key"], seen, field + ".requirement_key")
        if item["requirement_key"] not in requirement_keys:
            _fail("unknown_requirement_reference", field + ".requirement_key")
        for name in ("lower", "upper"):
            _finite(item[name], field + "." + name)
            if not 0 <= item[name] <= 1:
                _fail("unit_interval_required", field + "." + name)
        if item["lower"] > item["upper"]:
            _fail("ordered_bounds_required", field)


def _validate_inputs(value):
    field = "data_source.inputs"
    _keys(value, _INPUT_FIELDS, field)
    for name, allowed in (("question_kind", QUESTION_KINDS), ("origin", ORIGINS),
        ("scope_status", SCOPE_STATUSES), ("frame_status", FRAME_STATUSES),
        ("pairing", PAIRINGS), ("weight_basis", WEIGHT_BASES),
        ("sampling_design", SAMPLING_DESIGNS)):
        _enum(value[name], allowed, field + "." + name)
    _number(value["alpha"], field + ".alpha")
    if value["alpha"] is not None and not 0 < value["alpha"] < 1:
        _fail("open_unit_interval_required", field + ".alpha")
    if value["permitted_remainder"] is not None:
        _boolean(value["permitted_remainder"], field + ".permitted_remainder")
    requirements = _requirements(value["requirements"])
    _routes(value["routes"], requirements)
    contexts = _contexts(value["contexts"], requirements, value["weight_basis"])
    _marginals(value["marginals"], requirements)
    if value["pairing"] == "paired" and value["marginals"]:
        _fail("paired_marginals_must_be_empty", field + ".marginals")
    if value["pairing"] == "unpaired_marginals" and value["contexts"]:
        _fail("unpaired_contexts_must_be_empty", field + ".contexts")
    return contexts


def _physical_key(kind, reference, artifact_ref, local_id):
    owner = {"source_ref": reference, "artifact_ref": artifact_ref, "raw_id": local_id}
    raw = json.dumps(owner, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "literature_" + kind + "_" + hashlib.sha256(raw).hexdigest()


def _measurements(reference, sources):
    if reference is None:
        return None, None, None
    source = sources.source(reference, "original")
    data = _json_measurements(source["content"])
    from .literature_context_native_inputs import DATA_VERSION as NATIVE_DATA_VERSION, read_native_selection
    native = None
    if isinstance(data, dict) and data.get("version") == NATIVE_DATA_VERSION:
        data, native = read_native_selection(data, sources=sources,
            reference=reference, artifact_ref=source["artifact_ref"])
    from .literature_context_meanings import DATA_VERSION as MEANINGS_DATA_VERSION
    version = data.get("version") if isinstance(data, dict) else None
    _keys(data, ("version", "inputs", "meanings") if version == MEANINGS_DATA_VERSION
          else ("version", "inputs"), "data_source")
    if version not in (DATA_VERSION, MEANINGS_DATA_VERSION):
        _fail("unsupported_context_measurements_version", "data_source.version")
    contexts = _validate_inputs(data["inputs"])
    inputs = deepcopy(data["inputs"])
    inputs["contexts"] = deepcopy(contexts)
    for context in inputs["contexts"]:
        context["key"] = _physical_key("context", reference, source["artifact_ref"], context["key"])
        if context["cluster_key"] is not None:
            context["cluster_key"] = _physical_key("cluster", reference, source["artifact_ref"], context["cluster_key"])
        for observation in context["observations"]:
            observation["measurement_key"] = _physical_key(
                "measurement", reference, source["artifact_ref"], observation["measurement_key"])
    if native is not None:
        for context in native["contexts"]:
            context["key"] = _physical_key("context", reference, source["artifact_ref"], context["key"])
            for observation in context["observations"]:
                observation["measurement_key"] = _physical_key(
                    "measurement", reference, source["artifact_ref"], observation["measurement_key"])
    return data, inputs, native


def read_context_inputs(arguments, *, read_source):
    """Read authorized retained sources; preserve raw records and unknowns.

    ``read_source(ref, representation)`` returns ``{artifact_ref, content:bytes}``
    after authorizing the actual received/scoped reference. Failures propagate.
    Context aliases coalesce only for calculation inputs; raw rows remain intact.
    Native domains and reported uncertainty remain separate, without conversion.
    """
    _keys(arguments, _ARGS, "arguments")
    _enum(arguments["source_kind"], SOURCE_KINDS, "source_kind")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    literals = {}
    for name in LITERAL_FIELDS:
        value = arguments["literals"][name]
        witness = sources.witness(value, "literals." + name) if value is not None else None
        literals[name] = {"value": witness["quote"], "witness": witness} if witness else None
    _list(arguments["interpretation_witnesses"], "interpretation_witnesses")
    interpretations = [sources.witness(value, f"interpretation_witnesses[{i}]")
                       for i, value in enumerate(arguments["interpretation_witnesses"])]
    observations, inputs, native = _measurements(arguments["data_source_ref"], sources)
    from .literature_context_meanings import (
        DATA_VERSION as MEANINGS_DATA_VERSION, INPUT_VERSION as MEANINGS_INPUT_VERSION,
        read_meanings,
    )
    meanings = (read_meanings(observations["meanings"], inputs, sources)
                if observations is not None and observations["version"] == MEANINGS_DATA_VERSION else None)
    return {"version": VERSION if meanings is None else MEANINGS_INPUT_VERSION,
            "arguments": deepcopy(arguments),
            "sources": list(sources.references), "literals": literals,
            "interpretations": interpretations, "observations": observations,
            "calculation_inputs": inputs,
            **({"meanings": meanings} if meanings is not None else {}),
            **({"native_evidence": native} if native is not None else {})}


__all__ = ["VERSION", "DATA_VERSION", "LITERAL_FIELDS", "SOURCE_KINDS", "QUESTION_KINDS",
           "ORIGINS", "SCOPE_STATUSES", "FRAME_STATUSES", "PAIRINGS", "WEIGHT_BASES",
           "SAMPLING_DESIGNS", "NATIVE_UNITS", "JOINT_SUPPORT", "SCOPE_MATCHES", "RELATIONS",
           "COUNT_RELATIONS", "REPLICATE_KINDS", "context_population_schema", "read_context_inputs"]
