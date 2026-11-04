"""Read retained reaction measurements and source-bound experimental context.

This finite JSON boundary is not a native NMR/PDF/plot reader. Source custody
and literal matching do not establish scientific attribution, calibration,
independence, resource usability or the truth of a model prediction. No source
acquisition, calculation, model call or state mutation occurs here.
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


VERSION = "a110_reaction_inputs_v1"
DATA_VERSION = "a110_source_reaction_measurements_v1"
LITERAL_FIELDS = ("molecule", "construct", "experiment", "numerator", "denominator",
                  "endpoint", "condition", "resource_context")
RATIO_MODES = ("independent_units", "source_summary")
RATIO_KINDS = ("product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio")
RATIO_UNITS = ("mol_per_mol", "signal_per_signal")
ORIGINS = ("reported", "graph_derived", "synthetic")
BUDGET_BASES = ("supplied_reagent_batch", "usable_batch", "usable_rate")
BATCH_UNITS = ("umol", "uM")
RATE_UNITS = ("umol_per_min", "uM_per_min")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "interpretation_witnesses")
_RATIO_FIELDS = ("mode", "ratio_kind", "unit", "origin", "observations", "mean",
                 "sample_sd", "independent_n", "claim", "alternatives")
_BUDGET_FIELDS = ("basis", "unit", "origin", "resources_complete", "resources", "demand")


def reaction_population_schema():
    """Closed operation arguments; numerical operands are in retained bytes."""
    witness = _witness_schema()
    return obj({
        "source_ref": deepcopy(REF),
        "data_source_ref": _nullable(deepcopy(REF)),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)},
    })


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
        raise ExperimentalContractError("malformed_reaction_measurements_source", field) from error


def _number(value, field, *, nonnegative=False, positive=False):
    if value is None:
        return
    _finite(value, field)
    if nonnegative and value < 0:
        _fail("nonnegative_value_required", field)
    if positive and value <= 0:
        _fail("positive_value_required", field)


def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail("unsupported_" + field.rsplit(".", 1)[-1], field)


def _list(value, field, *, nonempty=False):
    if not isinstance(value, list):
        _fail("array_required", field)
    if nonempty and not value:
        _fail("nonempty_array_required", field)


def _unique_key(value, seen, field):
    _text(value, field)
    if value in seen:
        _fail("duplicate_physical_or_model_key", field)
    seen.add(value)


def _validate_ratio(ratio):
    if ratio is None:
        return
    field = "data_source.ratio"
    _keys(ratio, _RATIO_FIELDS, field)
    for name, allowed in (("mode", RATIO_MODES), ("ratio_kind", RATIO_KINDS),
                          ("unit", RATIO_UNITS), ("origin", ORIGINS)):
        _enum(ratio[name], allowed, field + "." + name)
    expected_unit = "signal_per_signal" if ratio["ratio_kind"] == "signal_ratio" else "mol_per_mol"
    if ratio["unit"] != expected_unit:
        _fail("ratio_kind_unit_mismatch", field + ".unit")
    for name in ("mean", "sample_sd", "claim"):
        _number(ratio[name], field + "." + name, nonnegative=name == "sample_sd")
    count = ratio["independent_n"]
    if count is not None and (type(count) is not int or count < 1):
        _fail("positive_integer_count_required", field + ".independent_n")
    if count == 1 and ratio["sample_sd"] is not None:
        _fail("sample_sd_requires_multiple_units", field + ".sample_sd")
    observations = ratio["observations"]
    _list(observations, field + ".observations", nonempty=ratio["mode"] == "independent_units")
    if ratio["mode"] == "independent_units":
        if any(ratio[name] is not None for name in ("mean", "sample_sd", "independent_n")):
            _fail("independent_unit_summary_fields_must_be_null", field)
    elif observations:
        _fail("source_summary_observations_must_be_empty", field + ".observations")
    seen = set()
    for i, item in enumerate(observations):
        path = f"{field}.observations[{i}]"
        _keys(item, ("measurement_key", "value"), path)
        _unique_key(item["measurement_key"], seen, path + ".measurement_key")
        # Independent units are actual observed points, never null placeholders.
        _finite(item["value"], path + ".value")
    _list(ratio["alternatives"], field + ".alternatives")
    seen = set()
    for i, item in enumerate(ratio["alternatives"]):
        path = f"{field}.alternatives[{i}]"
        _keys(item, ("key", "prediction"), path)
        _unique_key(item["key"], seen, path + ".key")
        _number(item["prediction"], path + ".prediction")


def _validate_budget(budget):
    if budget is None:
        return
    field = "data_source.budget"
    _keys(budget, _BUDGET_FIELDS, field)
    _enum(budget["basis"], BUDGET_BASES, field + ".basis")
    _enum(budget["unit"], (*BATCH_UNITS, *RATE_UNITS), field + ".unit")
    _enum(budget["origin"], ORIGINS, field + ".origin")
    expected_units = RATE_UNITS if budget["basis"] == "usable_rate" else BATCH_UNITS
    if budget["unit"] not in expected_units:
        _fail("budget_basis_unit_mismatch", field + ".unit")
    if type(budget["resources_complete"]) is not bool:
        _fail("boolean_required", field + ".resources_complete")
    _number(budget["demand"], field + ".demand", positive=True)
    _list(budget["resources"], field + ".resources", nonempty=True)
    seen = set()
    for i, item in enumerate(budget["resources"]):
        path = f"{field}.resources[{i}]"
        _keys(item, ("resource_key", "value", "lower", "upper", "coefficient"), path)
        _unique_key(item["resource_key"], seen, path + ".resource_key")
        for name in ("value", "lower", "upper"):
            _number(item[name], path + "." + name, nonnegative=True)
        _finite(item["coefficient"], path + ".coefficient")
        if item["coefficient"] <= 0:
            _fail("positive_value_required", path + ".coefficient")
        lower, upper, value = item["lower"], item["upper"], item["value"]
        if lower is not None and upper is not None and lower > upper:
            _fail("ordered_bounds_required", path)
        if value is not None and (lower is not None and value < lower or upper is not None and value > upper):
            _fail("nominal_value_outside_bounds", path + ".value")


def _physical_key(reference, artifact_ref, local_id):
    owner = {"source_ref": reference, "artifact_ref": artifact_ref, "measurement_id": local_id}
    raw = json.dumps(owner, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "literature_measurement_" + hashlib.sha256(raw).hexdigest()


def _measurements(reference, sources, *, source_kind=None):
    if reference is None:
        return None, {"ratio": None, "budget": None}, None
    source = sources.source(reference, "original")
    data = _json_measurements(source["content"])
    from .literature_reaction_meanings import DATA_VERSION as MEANINGS_DATA_VERSION
    version = data.get("version") if isinstance(data, dict) else None
    from .literature_reaction_native_inputs import VERSION as NATIVE_VERSION, read_native_reaction_selection
    native = None
    if version == NATIVE_VERSION:
        selection = deepcopy(data)
        data, native = read_native_reaction_selection(data, sources=sources,
            origin="synthetic" if source_kind == "synthetic_fixture" else "reported")
        native["selection"] = selection
        version = data["version"]
    _keys(data, ("version", "ratio", "budget", "meanings") if version == MEANINGS_DATA_VERSION
          else ("version", "ratio", "budget"), "data_source")
    if version not in (DATA_VERSION, MEANINGS_DATA_VERSION):
        _fail("unsupported_reaction_measurements_version", "data_source.version")
    _validate_ratio(data["ratio"])
    _validate_budget(data["budget"])
    inputs = deepcopy({name: data[name] for name in ("ratio", "budget")})
    if inputs["ratio"] is not None:
        for observation in inputs["ratio"]["observations"]:
            observation["measurement_key"] = _physical_key(
                reference, source["artifact_ref"], observation["measurement_key"])
    if inputs["budget"] is not None:
        for resource in inputs["budget"]["resources"]:
            resource["resource_key"] = _physical_key(
                reference, source["artifact_ref"], resource["resource_key"])
    return data, inputs, native


def read_reaction_inputs(arguments, *, read_source):
    """Read only authorized retained bytes; preserve raw and namespaced records.

    ``read_source(ref, representation)`` must authorize actual received/scoped
    sources and return ``{artifact_ref, content: bytes}``. Callback failures
    propagate without fallback. Mean/SD/count and explicit resource bounds keep
    their declared meanings; this reader never computes intervals or fills
    missing controls, capacities, or independent repetitions.
    """
    _keys(arguments, _ARGS, "arguments")
    _enum(arguments["source_kind"], SOURCE_KINDS, "source_kind")
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    _keys(arguments["literals"], LITERAL_FIELDS, "literals")
    literals = {}
    for field in LITERAL_FIELDS:
        value = arguments["literals"][field]
        witness = sources.witness(value, "literals." + field) if value is not None else None
        literals[field] = {"value": witness["quote"], "witness": witness} if witness else None
    _list(arguments["interpretation_witnesses"], "interpretation_witnesses")
    interpretations = [sources.witness(value, f"interpretation_witnesses[{i}]")
                       for i, value in enumerate(arguments["interpretation_witnesses"])]
    observations, inputs, native = _measurements(arguments["data_source_ref"], sources, source_kind=arguments["source_kind"])
    from .literature_reaction_meanings import (
        DATA_VERSION as MEANINGS_DATA_VERSION, INPUT_VERSION as MEANINGS_INPUT_VERSION, read_meanings,
    )
    meanings = (read_meanings(observations["meanings"], observations, sources)
        if observations is not None and observations["version"] == MEANINGS_DATA_VERSION else None)
    return {"version": VERSION if meanings is None else MEANINGS_INPUT_VERSION,
            "arguments": deepcopy(arguments),
            "sources": list(sources.references), "literals": literals,
            "interpretations": interpretations, "observations": observations,
            "calculation_inputs": inputs,
            **({"meanings": meanings} if meanings is not None else {}),
            **({"native_evidence": native} if native is not None else {})}


__all__ = ["VERSION", "DATA_VERSION", "LITERAL_FIELDS", "SOURCE_KINDS", "RATIO_MODES",
           "RATIO_KINDS", "RATIO_UNITS", "ORIGINS", "BUDGET_BASES", "BATCH_UNITS", "RATE_UNITS",
           "reaction_population_schema", "read_reaction_inputs"]
