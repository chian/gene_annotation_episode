"""Read reported intervention summaries from exact source spans.

Selections identify printed numbers and their statistical meanings. The
existing summary reader owns uncertainty calculations; this adapter supplies
no numerical predictions, missing measurements or assumed covariances.
"""
from copy import deepcopy
from decimal import Decimal
import re

from .domain import identity, obj, validate_schema
from .literature_assay_inputs import _fail, _witness_schema
from .literature_partner_source_fields import (
    number_selector_schema, read_source_number, _unit_contexts, _unit_continuation,
)


def source_measurements_schema():
    from .literature_perturbation_summary import (
        ROLES, SUMMARY_KINDS, SCALES, SPREAD_KINDS, UNIT_KINDS,
        INTERPRETATION_BASES, INTERPRETATION_BASIS_FIELDS, VARIANCE_STATUSES,
    )
    number = {"anyOf": [number_selector_schema(), {"type": "null"}]}
    entry = obj({
        "number": number_selector_schema(),
        "value_scale": {"enum": list(SCALES[:-1])},
        "summary_kind": {"enum": list(SUMMARY_KINDS)},
        "summary_scale": {"enum": list(SCALES)},
        "uncertainty": obj({"kind": {"enum": list(SPREAD_KINDS)},
            **{name: deepcopy(number) for name in ("value", "lower", "upper", "coverage")},
            "scale": {"enum": list(SCALES)}}),
        "count": obj({"number": deepcopy(number), "unit_kind": {"enum": list(UNIT_KINDS)},
            "independence": {"enum": ["independent", "not_independent", "unknown"]}}),
        "meaning_witnesses": {"type": "array", "minItems": 1, "items": _witness_schema()},
        "interpretation_basis": obj({name: {"enum": list(INTERPRETATION_BASES)}
            for name in INTERPRETATION_BASIS_FIELDS}),
    })
    schema = obj({"endpoint_unit": _witness_schema(),
        "exposure_unit": {"anyOf": [_witness_schema(), {"type": "null"}]},
        "measurements": obj({role: {"anyOf": [deepcopy(entry), {"type": "null"}]} for role in ROLES})})
    schema["properties"]["covariances"] = {"type": "array", "items": obj({
        "first": {"enum": ["W", "K", "R"]}, "second": {"enum": ["W", "K", "R"]},
        "kind": {"enum": ["mean_covariance", "uncorrelated", "unknown"]},
        "number": deepcopy(number),
        "unit": {"anyOf": [_witness_schema(), {"type": "null"}]},
        "variance_status": {"enum": list(VARIANCE_STATUSES)},
        "interpretation_basis": {"enum": list(INTERPRETATION_BASES)},
        "meaning_witnesses": {"type": "array", "minItems": 1, "items": _witness_schema()},
    })}
    return schema


def _unit(selection, sources, *, exposure=False, squared=False):
    """Read complete native unit labels, including separately printed headers."""
    witness = sources.witness(selection, "source_measurements.unit")
    prefix, suffix = _unit_contexts(sources, witness, 0, len(witness["quote"]))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in "_µμ/^")) or _unit_continuation(suffix):
        _fail("partial_source_unit", "source_measurements.unit")
    from .literature_perturbation_inputs import (
        ENDPOINT_UNITS, EXPOSURE_UNITS, HOURLY_RATE_UNITS, CFU_DENSITY_UNITS,
        endpoint_unit_token,
    )
    aliases = {unit: unit for unit in (EXPOSURE_UNITS if exposure else ENDPOINT_UNITS)}
    aliases.update({"mg/mL": "mg_per_mL"} if exposure else {
        "min": "minutes", "minute": "minutes", "CFU/mL": "CFU_per_mL", "min^-1": "per_min"})
    if squared:
        # For density, a bare exponent after the denominator does not square
        # the entire unit. The explicit shared density aliases below own these
        # spellings instead of generating CFU/mL^2 as a variance unit.
        aliases = {token: canonical for token, canonical in aliases.items()
            if canonical not in CFU_DENSITY_UNITS.values()}
        aliases = {spelling: canonical + "_squared" for token, canonical in aliases.items()
            for spelling in (token + "_squared", token + "^2", token + "²", "(" + token + ")^2")}
    if not exposure:
        aliases.update({token: canonical for token, canonical in HOURLY_RATE_UNITS.items()
            if canonical.endswith("_squared") == squared})
        aliases.update({token: canonical for token, canonical in CFU_DENSITY_UNITS.items()
            if canonical.endswith("_squared") == squared})
    token = endpoint_unit_token(witness["quote"])
    if token not in aliases:
        _fail("unsupported_perturbation_source_unit", "source_measurements.unit")
    return aliases[token], witness


def _number(selection, sources, trace, *, role="condition"):
    if selection is None:
        return None
    result = read_source_number(selection, sources=sources, role=role)
    if result["relation"] != "point":
        _fail("perturbation_summary_requires_point_number", "source_measurements.number")
    trace.append(result)
    return result["value"]


def _span(number):
    selection = number["selector"]
    witness = selection["witness"]
    return identity("physical_source_span", {"artifact_ref": witness["artifact_ref"],
        "start": witness["start"] + len(witness["quote"][:selection["number_start"]].encode()),
        "end": witness["start"] + len(witness["quote"][:selection["number_end"]].encode())})


def _covariances(selections, sources, endpoint):
    """Translate explicit joint-mean information to the existing calculator."""
    rows, traces = [], {}
    for index, selection in enumerate(selections):
        field = f"source_measurements.covariances[{index}]"
        trace, value = [], None
        witnesses = list(selection["meaning_witnesses"])
        if selection["kind"] == "mean_covariance":
            if selection["number"] is None or selection["unit"] is None:
                _fail("reported_covariance_number_and_unit_required", field)
            value = _number(selection["number"], sources, trace)
            unit, witness = _unit(selection["unit"], sources, squared=True)
            if unit != endpoint + "_squared":
                _fail("covariance_endpoint_unit_mismatch", field + ".unit")
            number_witness = trace[0]["selector"]["witness"]
            if any(witness[name] != number_witness[name]
                    for name in ("source_ref", "representation", "artifact_ref")):
                _fail("covariance_unit_from_different_source", field + ".unit")
            witnesses.extend([witness, number_witness])
        elif selection["number"] is not None or selection["unit"] is not None:
            _fail("covariance_number_not_applicable", field)
        rows.append({name: selection[name] for name in (
            "first", "second", "kind", "variance_status", "interpretation_basis")} | {
            "value": value, "witnesses": [
                {name: witness[name] for name in _witness_schema()["properties"]}
                for witness in witnesses]})
        if trace:
            pair = "_".join(sorted((selection["first"], selection["second"])))
            traces["covariance_" + pair] = trace
    return rows, traces


def read_source_measurements(selection, *, sources, reference, status, origin):
    """Populate the existing summary inputs without an intermediate JSON file."""
    from .literature_perturbation_summary import DATA_VERSION, ROLES, read_summary_measurements
    validate_schema(selection, source_measurements_schema())
    endpoint, endpoint_witness = _unit(selection["endpoint_unit"], sources)
    exposure, exposure_witness = ("unreported", None) if selection["exposure_unit"] is None else _unit(
        selection["exposure_unit"], sources, exposure=True)
    data = dict(version=DATA_VERSION, endpoint_unit=endpoint, exposure_unit=exposure,
        origin=origin, uncertainty_basis="per_measurement", measurements={}, covariances=[])
    traces = {}
    for role in ROLES:
        selected = selection["measurements"][role]
        empty = dict(value=None, measurement_id=None, value_scale="endpoint", summary_kind="unknown",
            summary_scale="unknown", uncertainty=dict(kind="unreported", value=None, lower=None,
                upper=None, coverage=None, scale="unknown", variance_status="unknown"),
            count=dict(n=None, unit_kind="unknown", independence="unknown"),
            raw_units=None, graph=None, digitization=None, meaning_witnesses=[])
        if selected is None:
            data["measurements"][role] = empty
            continue
        trace = []
        value = _number(selected["number"], sources, trace, role="rate")
        witness = trace[0]["selector"]["witness"]
        unit_witness = exposure_witness if role.startswith("A_") else endpoint_witness
        if unit_witness is None or any(witness[name] != unit_witness[name]
                for name in ("source_ref", "representation", "artifact_ref")):
            _fail("perturbation_unit_from_different_source", "source_measurements." + role)
        spread = selected["uncertainty"]
        uncertainty = {name: _number(spread[name], sources, trace,
            role="spread" if name == "value" else "condition") for name in ("value", "lower", "upper", "coverage")}
        for item in trace[1:]:
            if any(item["selector"]["witness"][name] != witness[name]
                    for name in ("source_ref", "representation", "artifact_ref")):
                _fail("perturbation_spread_from_different_source", "source_measurements." + role)
        count = _number(selected["count"]["number"], sources, trace)
        if count is not None:
            count = Decimal(trace[-1]["raw_number"].replace("−", "-"))
            if count != count.to_integral_value() or count < 1:
                _fail("positive_integer_repeat_count_required", "source_measurements." + role + ".count")
        # Retain every numeric witness in addition to the selected statistical
        # explanations. Unknown covariance remains unknown in the old calculator.
        data["measurements"][role] = {**empty, "value": value, "measurement_id": _span(trace[0]),
            **{name: selected[name] for name in ("value_scale", "summary_kind", "summary_scale", "interpretation_basis")},
            "uncertainty": {**uncertainty, "kind": spread["kind"], "scale": spread["scale"],
                "variance_status": "unknown" if spread["kind"] == "unreported" else "estimated"},
            "count": {"n": None if count is None else int(count),
                **{name: selected["count"][name] for name in ("unit_kind", "independence")}},
            "meaning_witnesses": [*selected["meaning_witnesses"],
                *[item["selector"]["witness"] for item in trace], unit_witness]}
        # Enriched witnesses carry artifact_ref; the existing reader accepts
        # original selector fields and authenticates those bytes itself.
        data["measurements"][role]["meaning_witnesses"] = [
            {name: item[name] for name in _witness_schema()["properties"]}
            for item in data["measurements"][role]["meaning_witnesses"]]
        traces[role] = trace
    data["covariances"], covariance_traces = _covariances(
        selection.get("covariances", []), sources, endpoint)
    source = sources.source(reference, "original")
    observations, summary = read_summary_measurements(data, sources=sources, reference=reference,
        artifact_ref=source["artifact_ref"], status=status,
        key_function=lambda _ref, _artifact, measurement_id: measurement_id)
    for role, trace in traces.items():
        witness = trace[0]["selector"]["witness"]
        observations[role].update(source_ref=witness["source_ref"], artifact_ref=witness["artifact_ref"])
    return observations, endpoint, exposure, origin, "per_measurement", summary, traces | covariance_traces
