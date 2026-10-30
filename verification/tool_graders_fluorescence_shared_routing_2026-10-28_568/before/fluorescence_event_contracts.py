"""Closed, pure data contracts shared by both supplied-fluorescence operations.

These validators check represented identities and relationships. They do not
authenticate artifact bytes, evaluate predicates, or recreate numerical answers.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata


SHEET_SCHEMA = "fluorescence_event_population_sheet_v1"
PARSE_SCHEMA = "fluorescence_event_parse_v1"
COMPONENTS_SCHEMA = "fluorescence_event_components_v1"
VIEW_SCHEMA = "fluorescence_event_result_view_v1"
TABLE_SCHEMA = "fluorescence_event_table_v1"

_ERROR_CODES = frozenset("""
invalid_source invalid_sample invalid_channel invalid_domain invalid_event
invalid_population invalid_gate invalid_control invalid_native_report
invalid_parse_result invalid_sheet invalid_parameters invalid_components
invalid_selection
""".split())
_ISSUE_CODES = frozenset("""
source_unavailable retained_artifact_mismatch native_format_mismatch
decoder_unavailable truncated_source invalid_event_row invalid_numeric_token
channel_missing ambiguous_channel measurement_domain_unavailable
measurement_domain_mismatch gate_parameter_invalid unknown_parent_membership
unknown_gate_membership empty_parent_population empty_evaluable_population
incomplete_population control_missing control_pair_incompatible
native_count_conflict native_population_unknown derived_numeric_overflow
calculation_sheet_mismatch calculation_parameters_mismatch
native_report_uninterpretable input_encoding_invalid
""".split())
_STAGES = frozenset("input parse domain gate calculation projection".split())
_LOCATORS = ("source_key", "sample_key", "domain_key", "channel_key",
             "event_ordinal", "gate_key", "control_key")
_CELL_IDENTITIES = ("gate_key", "domain_key", "channel_key", "control_key",
                    "native_report_key")
_POPULATION_METRICS = (
    "retained_event_count", "parent_event_count", "parent_unknown_count",
    "evaluable_event_count", "selected_event_count", "rejected_event_count",
    "unknown_gate_event_count",
)
_FRACTION_METRICS = ("selected_fraction", "selected_percent")
_INTENSITY_METRICS = (
    "selected_intensity_count", "selected_intensity_missing_count",
    "selected_intensity_sum", "selected_intensity_mean", "selected_intensity_median",
)
_CONTROL_METRICS = ("control_difference_fraction",
                    "control_difference_percentage_points",
                    "legacy_nonnegative_difference_percentage_points")
_NATIVE_METRICS = ("native_value", "native_minus_calculated")


class FluorescenceContractError(ValueError):
    """A malformed caller or saved-data contract, rather than bad native data."""

    def __init__(self, code: str):
        if type(code) is not str or code not in _ERROR_CODES:
            raise ValueError("unknown fluorescence contract error code")
        self.code = code
        super().__init__(code)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def finite(value) -> bool:
    """JSON numbers exclude booleans; Python's unbounded integers are finite."""
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _need(condition, code):
    if not condition:
        raise FluorescenceContractError(code)


def _keys(value, names, code):
    _need(type(value) is dict and set(value) == set(names.split()), code)


def _list(value, code):
    _need(type(value) is list, code)


def _key(value, code, *, nullable=False):
    if value is None and nullable:
        return
    _need(type(value) is str and bool(value)
          and not any(unicodedata.category(c) == "Cc" for c in value), code)


def _text(value, code, *, nullable=True):
    _need(type(value) is str or (nullable and value is None), code)


def _integer(value, code, *, nullable=False, minimum=0):
    _need((nullable and value is None)
          or (type(value) is int and value >= minimum), code)


def _enum(value, allowed, code):
    _need(type(value) is str and value in allowed, code)


def _unique(values, code):
    _need(len(values) == len(set(values)), code)


def _file(value, code):
    _keys(value, "artifact_ref sha256 size_bytes format", code)
    sha = value["sha256"]
    _need(type(sha) is str and re.fullmatch(r"[0-9a-f]{64}", sha) is not None, code)
    _need(value["artifact_ref"] == "artifact_" + sha, code)
    _integer(value["size_bytes"], code)
    _key(value["format"], code)


def _location(value, code, *, file=None):
    _keys(value, "record_ordinal line_start line_end byte_start byte_end", code)
    for key, item in value.items():
        _integer(item, code, nullable=True,
                 minimum=1 if key.startswith("line_") else 0)
    for start, end in (("line_start", "line_end"), ("byte_start", "byte_end")):
        if value[start] is not None and value[end] is not None:
            _need(value[start] <= value[end], code)
    if file is not None:
        for key in ("byte_start", "byte_end"):
            if value[key] is not None:
                _need(value[key] <= file["size_bytes"], code)


def _association(value, code, *, sources=None):
    _keys(value, "namespace identifier file source_key location", code)
    _key(value["namespace"], code)
    _key(value["identifier"], code)
    _file(value["file"], code)
    _key(value["source_key"], code, nullable=True)
    if sources is not None and value["source_key"] is not None:
        _need(value["source_key"] in sources, code)
    _location(value["location"], code, file=value["file"])


def _source(value):
    code = "invalid_source"
    _keys(value, "key file dataset_position format_profile extent native_event_count metadata", code)
    _key(value["key"], code)
    if value["file"] is not None:
        _file(value["file"], code)
    else:
        _need(value["extent"] == "unavailable", code)
    _integer(value["dataset_position"], code)
    _key(value["format_profile"], code)
    _enum(value["extent"], {"complete", "partial", "unavailable"}, code)
    _integer(value["native_event_count"], code, nullable=True)
    _list(value["metadata"], code)
    for item in value["metadata"]:
        _keys(item, "name value", code)
        _text(item["name"], code, nullable=False)
        _text(item["value"], code, nullable=False)


def _sample(value, *, sources=None):
    code = "invalid_sample"
    _keys(value, "key primary_domain_key label condition biological_replicate technical_replicate associations", code)
    _key(value["key"], code)
    _key(value["primary_domain_key"], code)
    for name in ("label", "condition", "biological_replicate", "technical_replicate"):
        _text(value[name], code)
    _list(value["associations"], code)
    for item in value["associations"]:
        _association(item, code, sources=sources)


def _channel(value, *, binding=False, sources=None):
    code = "invalid_channel"
    names = "key ordinal native_name label unit analyte"
    _keys(value, names + (" measurement_origin" if binding else " domain_key"), code)
    _key(value["key"], code)
    if not binding:
        _key(value["domain_key"], code)
    else:
        _enum(value["measurement_origin"], {"observed", "supplied_predicted"}, code)
    _integer(value["ordinal"], code)
    for name in ("native_name", "label", "unit"):
        _text(value[name], code)
    if value["analyte"] is not None:
        _association(value["analyte"], code, sources=sources)


def _basis(value, code, *, nullable=False):
    if value is None and nullable:
        return
    _keys(value, "key evidence_file", code)
    _key(value["key"], code)
    _file(value["evidence_file"], code)


def _preparation(value, code):
    _keys(value, "state method parameters_file", code)
    _enum(value["state"], {"not_applied", "applied", "unknown", "failed"}, code)
    _key(value["method"], code, nullable=True)
    if value["parameters_file"] is not None:
        _file(value["parameters_file"], code)
    if value["state"] == "applied":
        _need(value["method"] is not None and value["parameters_file"] is not None, code)


def _domain(value):
    code = "invalid_domain"
    _keys(value, "key sample_key source_key parent_domain_key state scale_kind compensation transformation correspondence comparison_basis", code)
    for name in ("key", "sample_key", "source_key"):
        _key(value[name], code)
    _key(value["parent_domain_key"], code, nullable=True)
    _need(value["parent_domain_key"] != value["key"], code)
    _enum(value["state"], {"available", "unavailable", "failed"}, code)
    _enum(value["scale_kind"], {"encoded", "scaled", "as_supplied"}, code)
    _preparation(value["compensation"], code)
    _preparation(value["transformation"], code)
    _basis(value["comparison_basis"], code, nullable=True)
    mapping = value["correspondence"]
    if value["parent_domain_key"] is None:
        _need(mapping is None, code)
    else:
        _list(mapping, code)
        for item in mapping:
            _keys(item, "source_ordinal event_ordinal", code)
            _integer(item["source_ordinal"], code)
            _integer(item["event_ordinal"], code)
        _unique([item["source_ordinal"] for item in mapping], code)
        _unique([item["event_ordinal"] for item in mapping], code)


def _measurement(value, code):
    _keys(value, "value state raw", code)
    _enum(value["state"], {"observed", "supplied_predicted", "missing", "invalid", "unavailable"}, code)
    _need(finite(value["value"]) if value["state"] in {"observed", "supplied_predicted"}
          else value["value"] is None, code)
    _text(value["raw"], code)


def _issue(value, code, *, indexes=None):
    _keys(value, "code stage " + " ".join(_LOCATORS), code)
    _enum(value["code"], _ISSUE_CODES, code)
    _enum(value["stage"], _STAGES, code)
    for name in _LOCATORS:
        if name == "event_ordinal":
            _integer(value[name], code, nullable=True)
        else:
            _key(value[name], code, nullable=True)
            if indexes is not None and name in indexes and value[name] is not None:
                _need(value[name] in indexes[name], code)


def _issues(values, code, *, indexes=None):
    _list(values, code)
    for item in values:
        _issue(item, code, indexes=indexes)


def issue(code: str, stage: str, *, source_key=None, sample_key=None,
          domain_key=None, channel_key=None, event_ordinal=None, gate_key=None,
          control_key=None) -> dict:
    value = dict(code=code, stage=stage, source_key=source_key,
                 sample_key=sample_key, domain_key=domain_key,
                 channel_key=channel_key, event_ordinal=event_ordinal,
                 gate_key=gate_key, control_key=control_key)
    _issue(value, "invalid_parameters")
    return value


def _parse_context(*, source, sample, channels, domain, binding=False):
    _source(source)
    _sample(sample)
    _domain(domain)
    _list(channels, "invalid_channel")
    for item in channels:
        _channel(item, binding=binding)
        if not binding:
            _need(item["domain_key"] == domain["key"], "invalid_channel")
    _unique([item["key"] for item in channels], "invalid_channel")
    _need([item["ordinal"] for item in channels] == list(range(len(channels))), "invalid_channel")
    _need(domain["source_key"] == source["key"]
          and domain["sample_key"] == sample["key"], "invalid_domain")
    _need((domain["key"] == sample["primary_domain_key"])
          == (domain["parent_domain_key"] is None), "invalid_domain")


def _event(value, *, source, sample, channels, domain):
    code = "invalid_event"
    _keys(value, "sample_key domain_key event_ordinal source_ordinal location values", code)
    _need(value["sample_key"] == sample["key"] and value["domain_key"] == domain["key"], code)
    _integer(value["event_ordinal"], code)
    _integer(value["source_ordinal"], code)
    _location(value["location"], code, file=source["file"])
    if value["location"]["record_ordinal"] is not None:
        _need(value["location"]["record_ordinal"] == value["source_ordinal"], code)
    if domain["parent_domain_key"] is None:
        _need(value["event_ordinal"] == value["source_ordinal"], code)
    else:
        mapping = {item["source_ordinal"]: item["event_ordinal"]
                   for item in domain["correspondence"]}
        _need(mapping.get(value["source_ordinal"]) == value["event_ordinal"], code)
    _list(value["values"], code)
    for cell in value["values"]:
        _keys(cell, "channel_key measurement", code)
        _key(cell["channel_key"], code)
        _measurement(cell["measurement"], code)
    _need([cell["channel_key"] for cell in value["values"]]
          == [item["key"] for item in channels], code)


def _domain_events(events, *, source, sample, channels, domain):
    _list(events, "invalid_event")
    for item in events:
        _event(item, source=source, sample=sample, channels=channels, domain=domain)
    ordinals = [item["source_ordinal"] for item in events]
    _need(ordinals == list(range(len(events))), "invalid_event")
    _unique([item["event_ordinal"] for item in events], "invalid_event")
    if source["extent"] == "unavailable" or domain["state"] != "available":
        _need(not events, "invalid_event")
    if (domain["parent_domain_key"] is not None and source["extent"] == "complete"
            and domain["state"] == "available"):
        _need(set(ordinals) == {item["source_ordinal"] for item in domain["correspondence"]}, "invalid_domain")


def validate_event_parse_result(value: dict) -> dict:
    code = "invalid_parse_result"
    _keys(value, "schema source sample channels domain events issues", code)
    _need(value["schema"] == PARSE_SCHEMA, code)
    context = {name: value[name] for name in ("source", "sample", "channels", "domain")}
    _parse_context(**context)
    _domain_events(value["events"], **context)
    # Cross-domain association sources and derived parents can be in other batches.
    indexes = {"source_key": {value["source"]["key"]},
               "sample_key": {value["sample"]["key"]},
               "domain_key": {value["domain"]["key"]},
               "channel_key": {x["key"] for x in value["channels"]}}
    _issues(value["issues"], code, indexes=indexes)
    if value["source"]["extent"] == "unavailable":
        _need(bool(value["issues"]), code)
    return value


def validate_csv_request(*, source: dict, format_spec: dict, sample: dict,
                         channels: list[dict], domain: dict) -> None:
    validate_snapshot_request(source=source, sample=sample, channels=channels, domain=domain)
    code = "invalid_parameters"
    _keys(format_spec, "encoding delimiter quotechar escapechar doublequote header missing_tokens", code)
    _enum(format_spec["encoding"], {"utf-8", "utf-8-sig"}, code)
    for name in ("delimiter", "quotechar", "escapechar"):
        item = format_spec[name]
        _need((name == "escapechar" and item is None)
              or (type(item) is str and len(item) == 1), code)
    _need(format_spec["delimiter"] != format_spec["quotechar"], code)
    for name in ("doublequote", "header"):
        _need(type(format_spec[name]) is bool, code)
    _list(format_spec["missing_tokens"], code)
    for token in format_spec["missing_tokens"]:
        _text(token, code, nullable=False)


def validate_snapshot_request(*, source: dict, sample: dict,
                              channels: list[dict], domain: dict) -> None:
    validate_event_input_request(source=source, sample=sample, channels=channels, domain=domain)


def validate_event_input_request(*, source: dict, sample: dict,
                                 channels: list[dict], domain: dict) -> None:
    _parse_context(source=source, sample=sample, channels=channels, domain=domain, binding=True)
    _need(source["file"] is not None, "invalid_source")


def _parent(value, code):
    _keys(value, "kind key", code)
    _enum(value["kind"], {"population", "gate"}, code)
    _key(value["key"], code)


def _population(value):
    code = "invalid_population"
    _keys(value, "key sample_key kind event_ordinals", code)
    _key(value["key"], code)
    _key(value["sample_key"], code)
    _enum(value["kind"], {"all", "subset"}, code)
    if value["kind"] == "all":
        _need(value["event_ordinals"] is None, code)
    else:
        _ordinals(value["event_ordinals"], code, ordered=False)


def _gate(value):
    code = "invalid_gate"
    _keys(value, "key sample_key parent kind domain_key channel_key lower upper", code)
    _key(value["key"], code)
    _key(value["sample_key"], code)
    _parent(value["parent"], code)
    _enum(value["kind"], {"threshold", "pass_all"}, code)
    for name in ("domain_key", "channel_key"):
        _key(value[name], code, nullable=True)
    for name in ("lower", "upper"):
        if value[name] is not None:
            _keys(value[name], "value inclusive", code)
            _need(finite(value[name]["value"]) and type(value[name]["inclusive"]) is bool, code)
    if value["kind"] == "pass_all":
        _need(all(value[name] is None for name in ("domain_key", "channel_key", "lower", "upper")), code)
    else:
        _need(value["domain_key"] is not None and value["channel_key"] is not None
              and (value["lower"] is not None or value["upper"] is not None), code)
        if value["lower"] is not None and value["upper"] is not None:
            _need(value["lower"]["value"] <= value["upper"]["value"], code)


def _control(value):
    code = "invalid_control"
    _keys(value, "key target_gate_key control_gate_key denominator comparison_basis", code)
    for name in ("key", "target_gate_key", "control_gate_key"):
        _key(value[name], code)
    _enum(value["denominator"], {"parent", "evaluable"}, code)
    _basis(value["comparison_basis"], code)


def _cell_request(value, code, *, indexes=None):
    _keys(value, "kind " + " ".join(_CELL_IDENTITIES) + " denominator metric", code)
    required, metrics = {
        "population": ({"gate_key"}, _POPULATION_METRICS),
        "fraction": ({"gate_key"}, _FRACTION_METRICS),
        "intensity": ({"gate_key", "domain_key", "channel_key"}, _INTENSITY_METRICS),
        "control": ({"control_key"}, _CONTROL_METRICS),
        "native_comparison": ({"native_report_key"}, _NATIVE_METRICS),
    }.get(value["kind"] if type(value["kind"]) is str else None, (None, ()))
    _need(required is not None, code)
    _enum(value["metric"], metrics, code)
    _enum(value["denominator"], {"parent", "evaluable"} if value["kind"] == "fraction" else {"none"}, code)
    for name in _CELL_IDENTITIES:
        if name in required:
            _key(value[name], code)
            if indexes is not None:
                _need(value[name] in indexes[name], code)
        else:
            _need(value[name] is None, code)
    if indexes is not None and value["kind"] == "intensity":
        gate, domain, channel = (indexes[name][value[name]]
                                 for name in ("gate_key", "domain_key", "channel_key"))
        _need(gate["sample_key"] == domain["sample_key"]
              and channel["domain_key"] == domain["key"], code)


def _native_report(value, *, indexes=None):
    code = "invalid_native_report"
    _keys(value, "key file source_key location label value raw unit component_request decimal_places", code)
    _key(value["key"], code)
    _file(value["file"], code)
    _key(value["source_key"], code, nullable=True)
    if indexes is not None and value["source_key"] is not None:
        _need(value["source_key"] in indexes["source_key"], code)
    _location(value["location"], code, file=value["file"])
    for name in ("label", "raw", "unit"):
        _text(value[name], code)
    _need(value["value"] is None or finite(value["value"]), code)
    _integer(value["decimal_places"], code, nullable=True)
    if value["component_request"] is not None:
        _cell_request(value["component_request"], code, indexes=indexes)
        _need(value["component_request"]["kind"] != "native_comparison", code)


def _ordinals(value, code, *, ordered=True):
    _list(value, code)
    for item in value:
        _integer(item, code)
    _unique(value, code)
    if ordered:
        _need(value == sorted(value), code)


def _collection(values, validator, code):
    _list(values, code)
    for item in values:
        validator(item)
    _unique([item["key"] for item in values], code)
    return {item["key"]: item for item in values}


def _sheet_indexes(sheet):
    return {name: {item["key"]: item for item in sheet[collection]}
            for name, collection in (
                ("source_key", "input_sources"), ("sample_key", "samples"),
                ("domain_key", "measurement_domains"), ("channel_key", "channels"),
                ("population_key", "population_definitions"), ("gate_key", "gate_definitions"),
                ("control_key", "control_pairs"), ("native_report_key", "native_reports"))}


def _root_population(gate, gates, populations):
    while gate["parent"]["kind"] == "gate":
        gate = gates[gate["parent"]["key"]]
    return populations[gate["parent"]["key"]]


def _validate_sheet(sheet):
    code = "invalid_sheet"
    _keys(sheet, "schema input_sources samples channels measurement_domains events population_definitions gate_definitions control_pairs native_reports issues", code)
    _need(sheet["schema"] == SHEET_SCHEMA, code)
    sources = _collection(sheet["input_sources"], _source, "invalid_source")
    samples = _collection(sheet["samples"], lambda v: _sample(v, sources=sources), "invalid_sample")
    channels = _collection(sheet["channels"], lambda v: _channel(v, sources=sources), "invalid_channel")
    domains = _collection(sheet["measurement_domains"], _domain, "invalid_domain")
    populations = _collection(sheet["population_definitions"], _population, "invalid_population")
    gates = _collection(sheet["gate_definitions"], _gate, "invalid_gate")
    controls = _collection(sheet["control_pairs"], _control, "invalid_control")
    _collection(sheet["native_reports"], _native_report, "invalid_native_report")
    indexes = _sheet_indexes(sheet)
    for sample in samples.values():
        primary = domains.get(sample["primary_domain_key"])
        _need(primary is not None and primary["sample_key"] == sample["key"]
              and primary["parent_domain_key"] is None, "invalid_sample")
    for domain in domains.values():
        _need(domain["source_key"] in sources and domain["sample_key"] in samples, "invalid_domain")
        current, seen = domain, set()
        while current["parent_domain_key"] is not None:
            _need(current["key"] not in seen, "invalid_domain")
            seen.add(current["key"])
            current = domains.get(current["parent_domain_key"])
            _need(current is not None and current["sample_key"] == domain["sample_key"], "invalid_domain")
        _need(current["key"] == samples[domain["sample_key"]]["primary_domain_key"], "invalid_domain")
    by_domain = {key: [] for key in domains}
    for channel in channels.values():
        _need(channel["domain_key"] in domains, "invalid_channel")
        by_domain[channel["domain_key"]].append(channel)
    for items in by_domain.values():
        _need([item["ordinal"] for item in items] == list(range(len(items))), "invalid_channel")
    _list(sheet["events"], "invalid_event")
    events_by_domain = {key: [] for key in domains}
    for event in sheet["events"]:
        _keys(event, "sample_key domain_key event_ordinal source_ordinal location values", "invalid_event")
        _key(event["domain_key"], "invalid_event")
        _need(event["domain_key"] in domains, "invalid_event")
        events_by_domain[event["domain_key"]].append(event)
    for domain in domains.values():
        _domain_events(events_by_domain[domain["key"]], source=sources[domain["source_key"]],
                       sample=samples[domain["sample_key"]], channels=by_domain[domain["key"]], domain=domain)
    primary_ordinals = {sample["key"]: {e["event_ordinal"] for e in events_by_domain[sample["primary_domain_key"]]}
                        for sample in samples.values()}
    for domain in domains.values():
        if domain["correspondence"] is not None:
            _need(all(item["event_ordinal"] in primary_ordinals[domain["sample_key"]]
                      for item in domain["correspondence"]), "invalid_domain")
    for population in populations.values():
        _need(population["sample_key"] in samples, "invalid_population")
        if population["kind"] == "subset":
            _need(set(population["event_ordinals"]) <= primary_ordinals[population["sample_key"]], "invalid_population")
    for gate in gates.values():
        _need(gate["sample_key"] in samples, "invalid_gate")
        parents = gates if gate["parent"]["kind"] == "gate" else populations
        parent = parents.get(gate["parent"]["key"])
        _need(parent is not None and parent["sample_key"] == gate["sample_key"], "invalid_gate")
        if gate["kind"] == "threshold":
            domain, channel = domains.get(gate["domain_key"]), channels.get(gate["channel_key"])
            _need(domain is not None and channel is not None
                  and domain["sample_key"] == gate["sample_key"]
                  and channel["domain_key"] == domain["key"], "invalid_gate")
    for gate in gates.values():
        current, seen = gate, set()
        while current["parent"]["kind"] == "gate":
            _need(current["key"] not in seen, "invalid_gate")
            seen.add(current["key"])
            current = gates[current["parent"]["key"]]
    for control in controls.values():
        _need(control["target_gate_key"] in gates and control["control_gate_key"] in gates, "invalid_control")
    for report in sheet["native_reports"]:
        _native_report(report, indexes=indexes)
    _issues(sheet["issues"], code, indexes=indexes)
    for source in sources.values():
        if source["extent"] == "unavailable":
            _need(any(item["source_key"] == source["key"] for item in sheet["issues"]), code)
    return sheet


def validate_calculation_parameters(value: dict, *, sheet: dict) -> dict:
    _validate_sheet(sheet)
    code = "invalid_parameters"
    _keys(value, "fraction_requests intensity_requests control_requests native_comparison_requests", code)
    indexes = _sheet_indexes(sheet)
    for requests in value.values():
        _list(requests, code)
    for request in value["fraction_requests"]:
        _keys(request, "gate_key denominator", code)
        _key(request["gate_key"], code)
        _need(request["gate_key"] in indexes["gate_key"], code)
        _enum(request["denominator"], {"parent", "evaluable"}, code)
    for request in value["intensity_requests"]:
        _keys(request, "gate_key domain_key channel_key", code)
        for name in ("gate_key", "domain_key", "channel_key"):
            _key(request[name], code)
            _need(request[name] in indexes[name], code)
        gate, domain, channel = (indexes[name][request[name]]
                                 for name in ("gate_key", "domain_key", "channel_key"))
        _need(gate["sample_key"] == domain["sample_key"]
              and channel["domain_key"] == domain["key"], code)
    for request in value["control_requests"]:
        _keys(request, "control_key include_legacy_clipping", code)
        _key(request["control_key"], code)
        _need(request["control_key"] in indexes["control_key"]
              and type(request["include_legacy_clipping"]) is bool, code)
    for key in value["native_comparison_requests"]:
        _key(key, code)
        _need(key in indexes["native_report_key"], code)
    for requests in value.values():
        _unique([canonical(request) for request in requests], code)
    _unique([request["control_key"] for request in value["control_requests"]], code)
    return value


def _request(kind, metric, *, denominator="none", **identities):
    return dict(kind=kind, **{name: identities.get(name) for name in _CELL_IDENTITIES},
                denominator=denominator, metric=metric)


def _expected_requests(sheet, parameters):
    """Expand declared output identities only; no membership or arithmetic."""
    requests = []
    for gate in sheet["gate_definitions"]:
        requests.extend(_request("population", metric, gate_key=gate["key"])
                        for metric in _POPULATION_METRICS)
    for item in parameters["fraction_requests"]:
        requests.extend(_request("fraction", metric, **item) for metric in _FRACTION_METRICS)
    for item in parameters["intensity_requests"]:
        requests.extend(_request("intensity", metric, **item) for metric in _INTENSITY_METRICS)
    controls = {item["key"]: item for item in sheet["control_pairs"]}
    for item in parameters["control_requests"]:
        pair = controls[item["control_key"]]
        for name in ("target_gate_key", "control_gate_key"):
            for metric in _FRACTION_METRICS:
                request = _request("fraction", metric, gate_key=pair[name], denominator=pair["denominator"])
                if request not in requests:
                    requests.append(request)
    for item in parameters["control_requests"]:
        metrics = _CONTROL_METRICS if item["include_legacy_clipping"] else _CONTROL_METRICS[:2]
        requests.extend(_request("control", metric, control_key=item["control_key"]) for metric in metrics)
    for key in parameters["native_comparison_requests"]:
        requests.extend(_request("native_comparison", metric, native_report_key=key) for metric in _NATIVE_METRICS)
    return requests


def _partition(parts, universe, code):
    union = set()
    for part in parts:
        _need(not union.intersection(part), code)
        union.update(part)
    _need(union == set(universe), code)


def _membership(value, *, indexes):
    code = "invalid_components"
    ordinal_fields = ("universe_event_ordinals", "parent_true", "parent_false",
                      "parent_unknown", "selected", "rejected", "unknown",
                      "parent_evaluable", "parent_nonevaluable")
    _keys(value, "gate_key sample_key parent " + " ".join(ordinal_fields)
          + " population_complete issues", code)
    for name in ("gate_key", "sample_key"):
        _key(value[name], code)
        _need(value[name] in indexes[name], code)
    gate = indexes["gate_key"][value["gate_key"]]
    _parent(value["parent"], code)
    _need(value["sample_key"] == gate["sample_key"] and value["parent"] == gate["parent"], code)
    for name in ordinal_fields:
        _ordinals(value[name], code)
    _need(type(value["population_complete"]) is bool, code)
    _partition([value[name] for name in ("selected", "rejected", "unknown")], value["universe_event_ordinals"], code)
    _partition([value[name] for name in ("parent_true", "parent_false", "parent_unknown")], value["universe_event_ordinals"], code)
    _partition([value[name] for name in ("parent_evaluable", "parent_nonevaluable")], value["parent_true"], code)
    _need(set(value["selected"]) <= set(value["parent_evaluable"]), code)
    _need(set(value["parent_false"]) <= set(value["rejected"]), code)
    _need(set(value["parent_nonevaluable"]) == set(value["parent_true"]).intersection(value["unknown"]), code)
    _issues(value["issues"], code, indexes=indexes)


def _cell_population(value, request, *, indexes, code):
    _keys(value, "sample_key gate_key domain_key channel_key denominator extent", code)
    for name in ("sample_key", "gate_key", "domain_key", "channel_key"):
        _key(value[name], code, nullable=True)
        if value[name] is not None and indexes is not None:
            _need(value[name] in indexes[name], code)
    _enum(value["denominator"], {"none", "parent", "evaluable", "selected_finite", "paired_controls"}, code)
    _enum(value["extent"], {"complete", "confirmed_subset", "incomplete", "unavailable"}, code)
    kind = request["kind"]
    if kind in {"population", "fraction", "intensity"}:
        _need(value["gate_key"] == request["gate_key"] and value["sample_key"] is not None, code)
        if indexes is not None:
            _need(value["sample_key"] == indexes["gate_key"][request["gate_key"]]["sample_key"], code)
        if kind == "intensity":
            _need(value["domain_key"] == request["domain_key"]
                  and value["channel_key"] == request["channel_key"]
                  and value["denominator"] == "selected_finite", code)
        else:
            _need(value["domain_key"] is None and value["channel_key"] is None
                  and value["denominator"] == request["denominator"], code)
    else:
        _need(all(value[name] is None for name in ("sample_key", "gate_key", "domain_key", "channel_key")), code)
        _need(value["denominator"] == ("paired_controls" if kind == "control" else "none"), code)


def _resolve_operand(reference, roots, code):
    """Resolve strict RFC 6901 pointers, including escaped object member names."""
    _need(type(reference) is str and ":" in reference, code)
    prefix, pointer = reference.split(":", 1)
    _need(prefix in roots and (pointer == "" or pointer.startswith("/")), code)
    current = roots[prefix]
    if pointer == "":
        return current
    for token in pointer[1:].split("/"):
        _need(re.search(r"~(?:[^01]|$)", token) is None, code)
        token = token.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            _need(token in current, code)
            current = current[token]
        elif type(current) is list:
            _need(re.fullmatch(r"0|[1-9][0-9]*", token) is not None, code)
            # Bound length first, so hostile huge index strings never reach int().
            _need(len(token) <= len(str(len(current))), code)
            index = int(token)
            _need(index < len(current), code)
            current = current[index]
        else:
            raise FluorescenceContractError(code)
    return current


def _cell(value, code, *, indexes=None, roots=None):
    _keys(value, "request value state unit population operands issues", code)
    _cell_request(value["request"], code, indexes=indexes)
    _enum(value["state"], {"present", "qualified", "unavailable"}, code)
    _need(value["value"] is None if value["state"] == "unavailable" else finite(value["value"]), code)
    _text(value["unit"], code)
    request, number = value["request"], value["value"]
    kind, metric = request["kind"], request["metric"]
    is_count = kind == "population" or metric in _INTENSITY_METRICS[:2]
    if number is not None:
        if is_count:
            _integer(number, code)
        elif kind == "fraction":
            _need(0 <= number <= (1 if metric == "selected_fraction" else 100), code)
    if is_count:
        _need(value["unit"] == "events", code)
    elif kind == "fraction":
        _need(value["unit"] == ("dimensionless" if metric == "selected_fraction" else "percent"), code)
    elif kind == "control":
        _need(value["unit"] == ("dimensionless" if metric == "control_difference_fraction" else "percentage_points"), code)
    elif indexes is not None and kind == "intensity":
        _need(value["unit"] == indexes["channel_key"][request["channel_key"]]["unit"], code)
    elif indexes is not None and kind == "native_comparison":
        _need(value["unit"] == indexes["native_report_key"][request["native_report_key"]]["unit"], code)
    _cell_population(value["population"], value["request"], indexes=indexes, code=code)
    _list(value["operands"], code)
    for operand in value["operands"]:
        _text(operand, code, nullable=False)
        if roots is not None:
            _resolve_operand(operand, roots, code)
    _issues(value["issues"], code, indexes=indexes)


def validate_components(value: dict, *, sheet: dict) -> dict:
    _validate_sheet(sheet)
    code = "invalid_components"
    _keys(value, "schema sheet_sha256 parameters memberships cells status issues", code)
    _need(value["schema"] == COMPONENTS_SCHEMA and value["sheet_sha256"] == digest(sheet), code)
    validate_calculation_parameters(value["parameters"], sheet=sheet)
    indexes = _sheet_indexes(sheet)
    _list(value["memberships"], code)
    for membership in value["memberships"]:
        _membership(membership, indexes=indexes)
    _unique([item["gate_key"] for item in value["memberships"]], code)
    memberships = {item["gate_key"]: item for item in value["memberships"]}
    _need(set(memberships) == set(indexes["gate_key"]), code)
    for key, membership in memberships.items():
        gate = indexes["gate_key"][key]
        root = _root_population(gate, indexes["gate_key"], indexes["population_key"])
        sample = indexes["sample_key"][gate["sample_key"]]
        domain = indexes["domain_key"][sample["primary_domain_key"]]
        source = indexes["source_key"][domain["source_key"]]
        retained = {e["event_ordinal"] for e in sheet["events"] if e["domain_key"] == domain["key"]}
        universe = retained if root["kind"] == "all" else set(root["event_ordinals"])
        _need(set(membership["universe_event_ordinals"]) == universe, code)
        complete = (source["extent"] != "unavailable" and domain["state"] == "available"
                    and (root["kind"] == "subset" or source["extent"] == "complete"))
        _need(membership["population_complete"] == complete, code)
        if gate["parent"]["kind"] == "gate":
            parent = memberships[gate["parent"]["key"]]
            for own, earlier in (("parent_true", "selected"), ("parent_false", "rejected"),
                                 ("parent_unknown", "unknown")):
                _need(membership[own] == parent[earlier], code)
        else:
            _need(membership["parent_true"] == membership["universe_event_ordinals"]
                  and not membership["parent_false"] and not membership["parent_unknown"], code)
    _list(value["cells"], code)
    roots = {"sheet": sheet, "parameters": value["parameters"], "components": value}
    for cell in value["cells"]:
        _cell(cell, code, indexes=indexes, roots=roots)
    requests = [item["request"] for item in value["cells"]]
    _unique([canonical(request) for request in requests], code)
    _need(requests == _expected_requests(sheet, value["parameters"]), code)
    _issues(value["issues"], code, indexes=indexes)
    _enum(value["status"], {"calculated", "partial", "unavailable"}, code)
    states = {item["state"] for item in value["cells"]}
    if not states.intersection({"present", "qualified"}):
        expected_status = "unavailable"
    elif (states.intersection({"qualified", "unavailable"}) or sheet["issues"]
          or value["issues"] or any(item["issues"] for item in value["memberships"])
          or any(item["issues"] for item in value["cells"])):
        expected_status = "partial"
    else:
        expected_status = "calculated"
    _need(value["status"] == expected_status, code)
    return value


def validate_selection(value: dict, *, components: dict) -> dict:
    code = "invalid_selection"
    _keys(value, "requests offset limit", code)
    _list(value["requests"], code)
    _integer(value["offset"], code)
    _integer(value["limit"], code, minimum=1)
    # Full component-to-sheet validation is the projection caller's responsibility;
    # this port has only the saved component bundle and must not invent a sheet.
    _keys(components, "schema sheet_sha256 parameters memberships cells status issues", code)
    _need(components["schema"] == COMPONENTS_SCHEMA, code)
    _list(components["cells"], code)
    for cell in components["cells"]:
        _cell(cell, code)
    available = [canonical(cell["request"]) for cell in components["cells"]]
    _unique(available, code)
    selected = []
    for request in value["requests"]:
        _cell_request(request, code)
        key = canonical(request)
        _need(key in available, code)
        selected.append(key)
    _unique(selected, code)
    return value
