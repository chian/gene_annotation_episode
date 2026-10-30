"""Closed data ports for three source-defined fluorescence report formats.

These declarations never authenticate a historical execution or calculate a
scientific component. Association support refers to exact selected identities;
display labels are not join keys.
"""

from __future__ import annotations

from copy import deepcopy
import re

from . import fluorescence_event_contracts as core
from .native_fluorescence_contracts import _input, path_value


BINDING_VERSION = "fluorescence_report_parse_binding_v1"
PARSE_VERSION = "fluorescence_native_report_parse_v1"
ASSOCIATION_VERSION = "fluorescence_report_association_v1"
FACS_PROFILE = "biomni_facs_log_548_v1"
CYTOKINE_LOG_PROFILE = "biomni_cytokine_log_548_v1"
CYTOKINE_CSV_PROFILE = "biomni_cytokine_csv_548_v1"
PROFILE_SOURCES = {
    FACS_PROFILE: dict(
        operation="perform_facs_cell_sorting",
        source_file_sha256="45f8edb43c079cab4727211ae6cecbf603577b4d886cd05295fabdd561a763af",
        function_sha256="c400891a22aa723c1fb8d42cce9f2c7b9a8241f9a8c16467780c7c2b6e138fb7"),
    CYTOKINE_LOG_PROFILE: dict(
        operation="analyze_cytokine_production_in_cd4_tcells",
        source_file_sha256="ef97b6bfdd52a935078e0ea4cdd8641edb2d4c1ff7f77f206b551a293fb6bdb4",
        function_sha256="9d4f5b14cdd5337b4b807dfbe04790a164501ad6bad6fb270bdb6937c0a7a6ba"),
}
PROFILE_SOURCES[CYTOKINE_CSV_PROFILE] = deepcopy(PROFILE_SOURCES[CYTOKINE_LOG_PROFILE])
CSV_COLUMNS = {"IFN-γ", "IL-17", "IFN-γ (background-subtracted)",
               "IL-17 (background-subtracted)"}
_CODE = "invalid_native_report"
_FLOAT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def _need(condition):
    core._need(condition, _CODE)


def _keys(value, names):
    core._keys(value, names, _CODE)


def _unique(values):
    core._unique(values, _CODE)


def _domain_identity(domain):
    return {name: domain[name] for name in ("key", "source_key", "sample_key")}


def _context(*, definitions, event_inputs, preparations):
    """Validate selected relationships without inventing an event universe."""
    _keys(definitions, "populations gates control_pairs native_reports")
    _need(type(definitions["native_reports"]) is list and not definitions["native_reports"])
    core._list(event_inputs, _CODE)
    core._list(preparations, _CODE)
    sources, samples, domains, channels, by_domain = {}, {}, {}, {}, {}
    originals, declared = [], []
    for item in event_inputs:
        _input(item)
        for name, index in (("source", sources), ("sample", samples)):
            row = item[name]
            _need(row["key"] not in index or core.canonical(index[row["key"]]) == core.canonical(row))
            index[row["key"]] = row
        domain = item["domain"]
        _need(domain["key"] not in domains)
        domains[domain["key"]] = domain
        originals.append(_domain_identity(domain))
        by_domain[domain["key"]] = []
        for original in item["channels"]:
            channel = {k: v for k, v in original.items() if k != "measurement_origin"}
            channel["domain_key"] = domain["key"]
            _need(channel["key"] not in channels)
            channels[channel["key"]] = channel
            by_domain[domain["key"]].append(channel)
    if preparations:
        from .fluorescence_preparation_contracts import SCALE_METHOD, validate_preparation_request
    preparation_keys = []
    for item in preparations:
        # P validates the closed request; the caller selects the per-kind list.
        _need(type(item) is dict and type(item.get("input")) is dict)
        selected = originals if item["input"].get("kind") == "event_input" else declared
        validate_preparation_request(item, input_domains=selected)
        preparation_keys.append(item["key"])
        parent = selected[item["input"]["index"]]
        output = item["output"]
        _need(output["key"] not in domains and output["source_key"] not in sources)
        _need(output["sample_key"] in samples)
        previous = by_domain[parent["key"]]
        _need(len(output["channels"]) == len(previous))
        for old, new in zip(previous, output["channels"]):
            _need(all(new[k] == old[k] for k in ("ordinal", "native_name", "label", "analyte")))
            prospective_time = (item["recipe"]["method"] == SCALE_METHOD
                                and old["native_name"] is not None
                                and old["native_name"].lower() == "time")
            #017 permits this selection before metadata exists. P's actual
            #resolution/outcome validator owns TIMESTEP and resulting units.
            if not prospective_time:
                _need(new["unit"] == old["unit"])
        declared.append(_domain_identity(output))
        # This is an internal identity graph, not a prepared Domain or outcome.
        domains[output["key"]] = dict(_domain_identity(output), parent_domain_key=parent["key"])
        sources[output["source_key"]] = None  # no generated artifact identity exists yet
        by_domain[output["key"]] = []
        for original in output["channels"]:
            channel = dict(original, domain_key=output["key"])
            _need(channel["key"] not in channels)
            channels[channel["key"]] = channel
            by_domain[output["key"]].append(channel)
    _unique(preparation_keys)
    populations = core._collection(definitions["populations"], core._population, "invalid_population")
    gates = core._collection(definitions["gates"], core._gate, "invalid_gate")
    controls = core._collection(definitions["control_pairs"], core._control, "invalid_control")
    for sample in samples.values():
        core._sample(sample, sources=sources)
        primary = domains.get(sample["primary_domain_key"])
        _need(primary is not None and primary["sample_key"] == sample["key"]
              and primary["parent_domain_key"] is None)
    for channel in channels.values():
        core._channel(channel, sources=sources)
    for domain in domains.values():
        current, seen = domain, set()
        while current["parent_domain_key"] is not None:
            _need(current["key"] not in seen)
            seen.add(current["key"])
            current = domains.get(current["parent_domain_key"])
            _need(current is not None and current["sample_key"] == domain["sample_key"])
        _need(current["key"] == samples[domain["sample_key"]]["primary_domain_key"])
    for population in populations.values():
        _need(population["sample_key"] in samples)
    for gate in gates.values():
        parents = gates if gate["parent"]["kind"] == "gate" else populations
        parent = parents.get(gate["parent"]["key"])
        _need(gate["sample_key"] in samples and parent is not None
              and parent["sample_key"] == gate["sample_key"])
        if gate["kind"] == "threshold":
            domain, channel = domains.get(gate["domain_key"]), channels.get(gate["channel_key"])
            _need(domain is not None and channel is not None
                  and domain["sample_key"] == gate["sample_key"]
                  and channel["domain_key"] == domain["key"])
        current, seen = gate, set()
        while current["parent"]["kind"] == "gate":
            _need(current["key"] not in seen and current["parent"]["key"] in gates)
            seen.add(current["key"])
            current = gates[current["parent"]["key"]]
    for control in controls.values():
        _need(control["target_gate_key"] in gates and control["control_gate_key"] in gates)
    return dict(source_key=sources, sample_key=samples, domain_key=domains,
                channel_key=channels, population_key=populations, gate_key=gates,
                control_key=controls, native_report_key={}, by_domain=by_domain)


def _locator(value, profile):
    if profile == FACS_PROFILE:
        _keys(value, "kind metric occurrence")
        _need(value["kind"] == "facs_metric")
        core._enum(value["metric"], {"original_count", "selected_count", "selected_percent",
            "selected_mean", "selected_median", "lower_remaining_count", "upper_remaining_count"}, _CODE)
        core._integer(value["occurrence"], _CODE)
    elif profile == CYTOKINE_LOG_PROFILE:
        _keys(value, "kind condition_ordinal metric marker_occurrence")
        _need(value["kind"] == "cytokine_log_metric")
        core._integer(value["condition_ordinal"], _CODE)
        core._enum(value["metric"], {"parent_count", "original_count", "marker_percent"}, _CODE)
        if value["metric"] == "marker_percent":
            core._integer(value["marker_occurrence"], _CODE)
        else:
            _need(value["marker_occurrence"] is None)
    else:
        _keys(value, "kind row_ordinal column_ordinal condition_label column_label")
        _need(value["kind"] == "cytokine_csv_cell")
        core._integer(value["row_ordinal"], _CODE)
        core._integer(value["column_ordinal"], _CODE, minimum=1)
        core._text(value["condition_label"], _CODE, nullable=False)
        core._enum(value["column_label"], CSV_COLUMNS, _CODE)


def _metric_link(field, profile):
    request, locator = field["component_request"], field["locator"]
    if request is None:
        return
    if profile == FACS_PROFILE:
        kind, metrics = {
            "original_count": ("population", {"parent_event_count"}),
            "selected_count": ("population", {"selected_event_count"}),
            "selected_percent": ("fraction", {"selected_percent"}),
            "selected_mean": ("intensity", {"selected_intensity_mean"}),
            "selected_median": ("intensity", {"selected_intensity_median"}),
            "lower_remaining_count": ("population", {"selected_event_count"}),
            "upper_remaining_count": ("population", {"selected_event_count"}),
        }[locator["metric"]]
    elif profile == CYTOKINE_LOG_PROFILE and locator["metric"] != "marker_percent":
        kind = "population"
        metrics = {"parent_event_count", "selected_event_count"}
    elif profile == CYTOKINE_CSV_PROFILE and locator["column_label"].endswith(" (background-subtracted)"):
        kind, metrics = "control", {"legacy_nonnegative_difference_percentage_points"}
    else:
        kind, metrics = "fraction", {"selected_percent"}
    _need(request["kind"] == kind and request["metric"] in metrics)
    if kind == "fraction":
        _need(request["denominator"] == "parent")


def validate_report_input(value: dict, *, definitions: dict, event_inputs: list[dict],
                          preparations: list[dict]) -> dict:
    """Validate selection only. Association bytes are separate fallible data."""
    context = _context(definitions=definitions, event_inputs=event_inputs, preparations=preparations)
    _keys(value, "file path source_key profile fields association_file")
    core._file(value["file"], _CODE)
    path_value(value["path"], absolute=True)
    core._key(value["source_key"], _CODE)
    core._enum(value["profile"], PROFILE_SOURCES, _CODE)
    if value["association_file"] is not None:
        core._file(value["association_file"], _CODE)
    core._list(value["fields"], _CODE)
    for field in value["fields"]:
        _keys(field, "key locator component_request")
        core._key(field["key"], _CODE)
        _locator(field["locator"], value["profile"])
        if field["component_request"] is not None:
            core._cell_request(field["component_request"], _CODE, indexes=context)
            _metric_link(field, value["profile"])
    keys = [value["source_key"], *(field["key"] for field in value["fields"])]
    _unique(keys)
    _need(not set(keys).intersection(context["source_key"]))
    _unique([core.canonical(field["locator"]) for field in value["fields"]])
    return deepcopy(value)


def make_fluorescence_report_binding(report_input: dict, *, definitions: dict,
                                    event_inputs: list[dict], preparations: list[dict]) -> dict:
    report_input = validate_report_input(report_input, definitions=definitions,
        event_inputs=event_inputs, preparations=preparations)
    return deepcopy(dict(version=BINDING_VERSION, report_input=report_input,
                         definitions=definitions, event_inputs=event_inputs, preparations=preparations))


def _binding(value):
    _keys(value, "version report_input definitions event_inputs preparations")
    _need(value["version"] == BINDING_VERSION)
    validate_report_input(value["report_input"], definitions=value["definitions"],
                          event_inputs=value["event_inputs"], preparations=value["preparations"])
    return _context(definitions=value["definitions"], event_inputs=value["event_inputs"],
                    preparations=value["preparations"])


def _dependencies(request, context, event_inputs):
    """Exact scientific dependency closure, not a join by display labels."""
    gate_keys, domain_keys, sample_keys = set(), set(), set()
    control = context["control_key"][request["control_key"]] if request["kind"] == "control" else None
    pending = [control["target_gate_key"], control["control_gate_key"]] if control else [request["gate_key"]]
    while pending:
        key = pending.pop()
        if key in gate_keys:
            continue
        gate_keys.add(key)
        gate = context["gate_key"][key]
        sample_keys.add(gate["sample_key"])
        if gate["domain_key"] is not None:
            domain_keys.add(gate["domain_key"])
        if gate["parent"]["kind"] == "gate":
            pending.append(gate["parent"]["key"])
    if request["kind"] == "intensity":
        domain_keys.add(request["domain_key"])
    domain_keys.update(context["sample_key"][key]["primary_domain_key"] for key in sample_keys)
    pending = list(domain_keys)
    while pending:
        parent = context["domain_key"][pending.pop()]["parent_domain_key"]
        if parent is not None and parent not in domain_keys:
            domain_keys.add(parent)
            pending.append(parent)
    event_sources = [dict(file=item["source"]["file"], dataset_position=item["source"]["dataset_position"])
                     for item in event_inputs if item["domain"]["key"] in domain_keys]
    return dict(sample_keys=sample_keys, domain_keys=domain_keys, gate_keys=gate_keys,
                event_sources={core.canonical(item) for item in event_sources}, control=control)


def _association(value, *, binding, context):
    """Validate supplied support; caller converts failures to a saved Issue."""
    _keys(value, "version report_file fields")
    _need(value["version"] == ASSOCIATION_VERSION)
    core._file(value["report_file"], _CODE)
    selected = binding["report_input"]
    _need(value["report_file"] == selected["file"])
    core._list(value["fields"], _CODE)
    linked = {row["key"]: row for row in selected["fields"] if row["component_request"] is not None}
    keys = []
    for field in value["fields"]:
        _keys(field, "report_key component_request event_sources sample_keys domain_keys gates control_pair")
        core._key(field["report_key"], _CODE)
        keys.append(field["report_key"])
        _need(field["report_key"] in linked)
        request = linked[field["report_key"]]["component_request"]
        _need(core.canonical(field["component_request"]) == core.canonical(request))
        needed = _dependencies(request, context, binding["event_inputs"])
        for name in ("sample_keys", "domain_keys"):
            core._list(field[name], _CODE)
            for key in field[name]:
                core._key(key, _CODE)
            _unique(field[name])
            _need(set(field[name]) == needed[name])
        core._list(field["event_sources"], _CODE)
        for source in field["event_sources"]:
            _keys(source, "file dataset_position")
            core._file(source["file"], _CODE)
            core._integer(source["dataset_position"], _CODE)
        tokens = [core.canonical(source) for source in field["event_sources"]]
        _unique(tokens)
        _need(set(tokens) == needed["event_sources"])
        gates = core._collection(field["gates"], core._gate, "invalid_gate")
        _need(set(gates) == needed["gate_keys"])
        _need(all(core.canonical(gate) == core.canonical(context["gate_key"][key])
                  for key, gate in gates.items()))
        _need(core.canonical(field["control_pair"]) == core.canonical(needed["control"]))
    _unique(keys)
    _need(set(keys) == set(linked))
    return value


def _number(raw, *, count=False, fixed=False):
    """Decode a lexical scalar only; no scientific calculation occurs here."""
    if type(raw) is not str:
        return None
    grammar = r"[0-9]+\Z" if count else (r"[+-]?[0-9]+\.[0-9]{2}\Z" if fixed else _FLOAT)
    if re.fullmatch(grammar, raw) is None:
        return None
    try:
        value = int(raw) if count else float(raw)
    except (ValueError, OverflowError):
        return None
    return value if core.finite(value) else None


def _field_shape(field, profile, context):
    locator, request = field["locator"], field["component_request"]
    metric = locator.get("metric")
    count = metric is not None and metric.endswith("count")
    if count:
        unit = "events"
    elif profile == CYTOKINE_CSV_PROFILE:
        unit = "percentage_points" if locator["column_label"].endswith(" (background-subtracted)") else "percent"
    elif metric in {"selected_percent", "marker_percent"}:
        unit = "percent"
    else:
        unit = context["channel_key"][request["channel_key"]]["unit"] if request else None
    precision = None if profile == CYTOKINE_CSV_PROFILE else (0 if count else 2)
    return unit, precision, count


def _csv_unit(column_label):
    return "percentage_points" if column_label.endswith(" (background-subtracted)") else "percent"


def validate_report_parse_result(value: dict, *, binding: dict) -> dict:
    """Validate retained relationships, tokens and shapes, without source I/O.

    Byte authentication/extraction belongs to the parser and caller's retained
    artifact boundary. This validator cannot prove a span against absent bytes.
    """
    context = _binding(binding)
    selected = binding["report_input"]
    _keys(value, "version source reports issues provenance")
    _need(value["version"] == PARSE_VERSION)
    core._source(value["source"])
    source = value["source"]
    _need(source["key"] == selected["source_key"] and source["file"] == selected["file"]
          and source["format_profile"] == selected["profile"] and source["dataset_position"] == 0
          and source["native_event_count"] is None and source["metadata"] == [])
    _need(value["provenance"] == dict(artifact_origin="received_supplied", producer_execution="unverified",
        profile=selected["profile"], profile_source=PROFILE_SOURCES[selected["profile"]]))
    core._list(value["reports"], _CODE)
    _need(len(value["reports"]) == len(selected["fields"]))
    core._issues(value["issues"], _CODE)
    for report, field in zip(value["reports"], selected["fields"]):
        core._native_report(report)
        unit, precision, count = _field_shape(field, selected["profile"], context)
        _need(report["key"] == field["key"] and report["file"] == selected["file"]
              and report["source_key"] == selected["source_key"]
              and core.canonical(report["component_request"]) == core.canonical(field["component_request"])
              and report["decimal_places"] == precision)
        if report["unit"] != unit:
            # A requested CSV position can contain another native column. Keep
            # its actual unit and the failed requested relationship separately.
            _need(selected["profile"] == CYTOKINE_CSV_PROFILE and type(report["label"]) is str)
            actual_columns = [column for column in CSV_COLUMNS if report["label"].endswith(": " + column)]
            _need(len(actual_columns) == 1 and report["unit"] == _csv_unit(actual_columns[0]))
            _need(core.issue("native_format_mismatch", "parse", source_key=source["key"]) in value["issues"])
            if field["component_request"] is not None:
                _need(core.issue("native_population_unknown", "input", source_key=source["key"]) in value["issues"])
        if report["value"] is not None:
            _need(core.canonical(_number(report["raw"], count=count, fixed=precision == 2)) == core.canonical(report["value"]))
        if report["raw"] is None:
            _need(report["value"] is None and all(x is None for x in report["location"].values()))
        else:
            _need(type(report["label"]) is str
                  and all(location is not None for location in report["location"].values()))
    for problem in value["issues"]:
        _need(problem["source_key"] == selected["source_key"])
        _need(all(problem[name] is None for name in core._LOCATORS if name != "source_key"))
    _unique([core.canonical(problem) for problem in value["issues"]])
    if source["extent"] != "complete" or any(row["value"] is None for row in value["reports"]):
        _need(bool(value["issues"]))
    if source["extent"] == "unavailable":
        _need(all(row["value"] is None and row["raw"] is None for row in value["reports"]))
    return deepcopy(value)
