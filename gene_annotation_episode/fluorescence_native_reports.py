"""Pure extraction of retained fluorescence report bytes.

Only the three pinned source-format profiles are understood. This module never
opens a path, launches software, evaluates event gates, or calculates summaries.
The source hash describes a format, not authenticated upstream execution.
"""

from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import io
import json
import re

from . import fluorescence_event_contracts as core
from .fluorescence_native_report_contracts import (
    CYTOKINE_CSV_PROFILE, CYTOKINE_LOG_PROFILE, FACS_PROFILE, CSV_COLUMNS,
    PARSE_VERSION, PROFILE_SOURCES, _association, _binding, _csv_unit, _field_shape, _number,
    validate_report_parse_result,
)


_FACS_HEADER = "# FACS-based Cell Sorting and Enrichment Research Log"
_CYTOKINE_HEADER = "# Cytokine Production Analysis by Flow Cytometry"


def _empty_location():
    return dict(record_ordinal=None, line_start=None, line_end=None, byte_start=None, byte_end=None)


def _lines(text):
    """Physical CR/LF lines with offsets in the original UTF-8 byte stream."""
    offset = 0
    for ordinal, match in enumerate(re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", text)):
        full = match.group()
        if not full:
            break
        body = full.rstrip("\r\n")
        yield dict(text=body, full=full, ordinal=ordinal, byte_start=offset)
        offset += len(full.encode("utf-8"))


def _candidate(line, start, end, *, label, metadata=None, broken=False):
    body = line["text"]
    first = line["byte_start"] + len(body[:start].encode("utf-8"))
    last = line["byte_start"] + len(body[:end].encode("utf-8"))
    return dict(raw=body[start:end], label=label, metadata=deepcopy(metadata or {}), broken=broken,
                location=dict(record_ordinal=line["ordinal"], line_start=line["ordinal"] + 1,
                    line_end=line["ordinal"] + 1, byte_start=first, byte_end=last))


def _ending(line, prefix, suffix, *, label, metadata):
    text = line["text"]
    if not text.startswith(prefix):
        return None
    complete = text.endswith(suffix) if suffix else len(line["full"]) > len(text)
    end = len(text) - len(suffix) if suffix and complete else len(text)
    return _candidate(line, len(prefix), end, label=label, metadata=metadata, broken=not complete)


def _facs(text):
    records, state, metadata = {}, None, {}
    for line in _lines(text):
        body = line["text"]
        if body == _FACS_HEADER:
            state, metadata = "loading", dict(parameter=None, bounds=[])
            continue
        if state is None or state == "terminal":
            continue
        if body in {"## Error", "## Output"}:
            state = "terminal"
            continue
        header = re.fullmatch(r"## Applying Gating Strategy for (.*)", body)
        if header:
            state = "gating"
            metadata = dict(parameter=header.group(1), bounds=[])
            continue
        if body == "## Enrichment Results":
            state = "results"
            continue
        if state == "gating":
            threshold = re.match(r"Applied (minimum|maximum) threshold of (.*?): ", body)
            if threshold:
                kind = "lower" if threshold.group(1) == "minimum" else "upper"
                metadata["bounds"].append(dict(kind=kind, raw=threshold.group(2),
                    value=_number(threshold.group(2)), inclusive=True))
                candidate = _ending(line, threshold.group(), " cells remaining",
                    label=threshold.group().rstrip(), metadata=metadata)
                records.setdefault(kind + "_remaining_count", []).append(candidate)
            continue
        if state != "results":
            continue
        for metric, prefix, suffix in (
            ("original_count", "Original population: ", " cells"),
            ("selected_count", "Sorted population: ", " cells"),
            ("selected_percent", "Enrichment percentage: ", "%"),
        ):
            candidate = _ending(line, prefix, suffix, label=prefix[:-2], metadata=metadata)
            if candidate is not None:
                records.setdefault(metric, []).append(candidate)
                break
        else:
            statistic = re.match(r"(Mean|Median) (.*): ", body)
            if statistic:
                metric = "selected_mean" if statistic.group(1) == "Mean" else "selected_median"
                extra = dict(metadata, statistic_parameter=statistic.group(2))
                records.setdefault(metric, []).append(_ending(line, statistic.group(), "",
                    label=statistic.group()[:-2], metadata=extra))
    return records


def _cytokine_log(text):
    records, current, ordinal, marker, active = {}, None, -1, 0, False
    for line in _lines(text):
        body = line["text"]
        if body == _CYTOKINE_HEADER:
            active = True
            current = None
            continue
        if body.startswith("## Results Summary") or body.startswith("No valid results were generated"):
            active, current = False, None
        if not active:
            continue
        processing = re.fullmatch(r"Processing (.*) condition from file: (.*)", body)
        if processing:
            ordinal += 1
            marker = 0
            current = dict(condition=processing.group(1), basename=processing.group(2),
                           cd4=None, cytokines=[])
            continue
        if current is None:
            continue
        if body.startswith("ERROR"):
            current = None
            continue
        channels = re.fullmatch(r"- Identified channels: CD4=(.*), Cytokines=(.*)", body)
        if channels:
            current.update(cd4=channels.group(1), cytokines=channels.group(2).split(", "))
            continue
        gate = re.match(r"- Applied CD4\+ gating: (.*?) cells \(from ", body)
        if gate:
            start, end = gate.span(1)
            records[(ordinal, "parent_count", None)] = _candidate(line, start, end,
                label="Applied CD4+ gating", metadata=current)
            prefix = gate.group()
            records[(ordinal, "original_count", None)] = _ending(line, prefix, " total)",
                label="Original cells before CD4+ gating", metadata=current)
            continue
        frequency = re.match(r"- (IFN-γ|IL-17)\+ frequency: ", body)
        if frequency:
            extra = dict(current, alias=frequency.group(1), marker_occurrence=marker)
            records[(ordinal, "marker_percent", marker)] = _ending(line, frequency.group(),
                "% of CD4+ T cells", label=frequency.group()[:-2], metadata=extra)
            marker += 1
    return records


def _csv_spans(record):
    """Locate fields of a record already parsed by the stdlib CSV decoder."""
    spans, start, quoted, position = [], 0, False, 0
    while position < len(record):
        character = record[position]
        if character == '"':
            if quoted and position + 1 < len(record) and record[position + 1] == '"':
                position += 2
                continue
            if quoted or position == start:
                quoted = not quoted
        elif character == "," and not quoted:
            spans.append((start, position))
            start = position + 1
        elif character in "\r\n" and not quoted:
            break
        position += 1
    spans.append((start, position))
    return spans


def _cytokine_csv(text):
    physical = list(_lines(text))
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=",", quotechar='"',
                        doublequote=True, strict=True)
    records, header, problems, previous = {}, None, [], 0
    try:
        for record_index, row in enumerate(reader):
            first, last = previous, reader.line_num
            previous = last
            segment = "".join(line["full"] for line in physical[first:last])
            if record_index == 0:
                if not row or row[0] != "" or any(name not in CSV_COLUMNS for name in row[1:]) or len(set(row)) != len(row):
                    return {}, ["native_format_mismatch"], False
                header = row
                continue
            if not row:
                problems.append("native_format_mismatch")
                continue
            if len(row) != len(header):
                problems.append("truncated_source" if len(row) < len(header) else "native_format_mismatch")
            spans = _csv_spans(segment)
            base = physical[first]["byte_start"]
            for column in range(1, min(len(row), len(header))):
                start, end = spans[column]
                # CSV quoting is syntax; the scalar token remains inside it.
                if segment[start:end].startswith('"') and segment[start:end].endswith('"'):
                    start, end = start + 1, end - 1
                before = segment[:start]
                through = segment[:end]
                line_start = first + 1 + len(re.findall(r"\r\n|\r|\n", before))
                line_end = first + 1 + len(re.findall(r"\r\n|\r|\n", through))
                broken = column == len(row) - 1 and not segment.endswith(("\n", "\r"))
                if broken:
                    problems.append("truncated_source")
                records[(record_index - 1, column)] = dict(raw=row[column],
                    label=row[0] + ": " + header[column], broken=broken,
                    metadata=dict(condition=row[0], column=header[column]),
                    location=dict(record_ordinal=record_index - 1, line_start=line_start,
                        line_end=line_end, byte_start=base + len(before.encode("utf-8")),
                        byte_end=base + len(through.encode("utf-8"))))
    except csv.Error:
        problems.append("truncated_source")
    return records, problems, header is not None


def _chain(gate_key, context):
    chain = []
    gate = context["gate_key"][gate_key]
    while True:
        chain.append(gate)
        parent = gate["parent"]
        if parent["kind"] == "population":
            return chain, context["population_key"][parent["key"]]
        gate = context["gate_key"][parent["key"]]


def _facs_meaning(field, candidate, context):
    request, meta = field["component_request"], candidate["metadata"]
    if type(meta.get("parameter")) is not str:
        return False
    chain, population = _chain(request["gate_key"], context)
    if population["kind"] != "all":
        return False
    metric = field["locator"]["metric"]
    if metric == "original_count":
        return all(gate["kind"] == "pass_all" for gate in chain[1:])
    if metric == "selected_percent" and any(gate["kind"] != "pass_all" for gate in chain[1:]):
        return False
    thresholds = [gate for gate in chain if gate["kind"] == "threshold"]
    channels = {gate["channel_key"] for gate in thresholds}
    domains = {gate["domain_key"] for gate in thresholds}
    if request["kind"] == "intensity":
        channels.add(request["channel_key"])
        domains.add(request["domain_key"])
        if meta.get("statistic_parameter") != meta.get("parameter"):
            return False
    if len(channels) > 1 or len(domains) > 1:
        return False
    if channels and context["channel_key"][next(iter(channels))]["native_name"] != meta.get("parameter"):
        return False
    actual = [dict(kind=kind, value=gate[kind]["value"], inclusive=gate[kind]["inclusive"])
              for gate in thresholds for kind in ("lower", "upper") if gate[kind] is not None]
    expected = [{key: bound[key] for key in ("kind", "value", "inclusive")} for bound in meta.get("bounds", [])]
    if any(bound["value"] is None for bound in expected):
        return False
    return sorted((row["kind"], row["value"], row["inclusive"]) for row in actual) == sorted(
        (row["kind"], row["value"], row["inclusive"]) for row in expected)


def _alias(native_name):
    # These are the inspected producer's literal alias rules. No channel is
    # selected by this function; exact gate/channel identities are supplied.
    if type(native_name) is not str:
        return None
    return "IFN-γ" if "IFN" in native_name else ("IL-17" if "IL-17" in native_name else None)


def _cd4(gate, context, *, native_name=None):
    if gate["kind"] != "threshold" or gate["lower"] != dict(value=1000, inclusive=False) or gate["upper"] is not None:
        return False
    if gate["parent"]["kind"] != "population" or context["population_key"][gate["parent"]["key"]]["kind"] != "all":
        return False
    channels = context["by_domain"][gate["domain_key"]]
    first = next((row for row in channels if type(row["native_name"]) is str and "CD4" in row["native_name"]), None)
    return first is not None and first["key"] == gate["channel_key"] and (
        native_name is None or first["native_name"] == native_name)


def _marker(gate, context, *, native_name=None, alias=None, last_alias=False, cd4_name=None):
    if gate["kind"] != "threshold" or gate["lower"] != dict(value=500, inclusive=False) or gate["upper"] is not None:
        return False
    if gate["parent"]["kind"] != "gate":
        return False
    parent = context["gate_key"][gate["parent"]["key"]]
    if parent["domain_key"] != gate["domain_key"] or not _cd4(parent, context, native_name=cd4_name):
        return False
    channel = context["channel_key"][gate["channel_key"]]
    if native_name is not None and channel["native_name"] != native_name:
        return False
    native_alias = _alias(channel["native_name"])
    if native_alias is None or (alias is not None and native_alias != alias):
        return False
    if last_alias:
        matches = [row for row in context["by_domain"][gate["domain_key"]] if _alias(row["native_name"]) == native_alias]
        if not matches or matches[-1]["key"] != channel["key"]:
            return False
    return True


def _sample_matches(gate, meta, context):
    sample = context["sample_key"][gate["sample_key"]]
    # File/dataset identity was checked in the explicit association. A current
    # retained path can differ from the historical log's display basename.
    return sample["condition"] == meta["condition"]


def _cytokine_meaning(field, candidate, context, binding):
    request, meta = field["component_request"], candidate["metadata"]
    profile = binding["report_input"]["profile"]
    if request["kind"] == "control":
        pair = context["control_key"][request["control_key"]]
        target = context["gate_key"][pair["target_gate_key"]]
        control = context["gate_key"][pair["control_gate_key"]]
        alias = meta["column"].removesuffix(" (background-subtracted)")
        return (pair["denominator"] == "parent" and target["sample_key"] != control["sample_key"]
            and _sample_matches(target, meta, context)
            and context["sample_key"][target["sample_key"]]["condition"] != "unstimulated"
            and context["sample_key"][control["sample_key"]]["condition"] == "unstimulated"
            and _marker(target, context, alias=alias, last_alias=True)
            and _marker(control, context, alias=alias, last_alias=True))
    gate = context["gate_key"][request["gate_key"]]
    if not _sample_matches(gate, meta, context):
        return False
    if profile == CYTOKINE_CSV_PROFILE:
        return _marker(gate, context, alias=meta["column"], last_alias=True)
    metric = field["locator"]["metric"]
    if meta["cd4"] is None:
        return False
    if metric == "original_count":
        if request["metric"] == "parent_event_count":
            return _cd4(gate, context, native_name=meta["cd4"])
        chain, population = _chain(gate["key"], context)
        return population["kind"] == "all" and all(row["kind"] == "pass_all" for row in chain)
    if metric == "parent_count":
        if request["metric"] == "selected_event_count":
            return _cd4(gate, context, native_name=meta["cd4"])
        channel = context["channel_key"].get(gate["channel_key"])
        return (channel is not None and channel["native_name"] in meta["cytokines"]
                and _marker(gate, context, cd4_name=meta["cd4"]))
    occurrence = meta["marker_occurrence"]
    if occurrence >= len(meta["cytokines"]) or meta["cd4"] is None:
        return False
    native_name = meta["cytokines"][occurrence]
    return _marker(gate, context, native_name=native_name, alias=meta["alias"], cd4_name=meta["cd4"])


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate association key")
        result[key] = value
    return result


def _reject_constant(token):
    raise ValueError("nonfinite association number")


def _supported(raw, binding, context):
    selected = binding["report_input"]
    if not any(field["component_request"] is not None for field in selected["fields"]):
        return True
    identity = selected["association_file"]
    if raw is None or identity is None or len(raw) != identity["size_bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
        return False
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object, parse_constant=_reject_constant)
        _association(value, binding=binding, context=context)
    except (UnicodeDecodeError, ValueError, TypeError, KeyError, RecursionError):
        return False
    return True


def parse_fluorescence_native_reports(raw: bytes, *, binding: dict,
                                      association_raw: bytes | None) -> dict:
    """Extract requested native scalars; all scientific arithmetic stays shared."""
    context = _binding(binding)
    if type(raw) is not bytes or (association_raw is not None and type(association_raw) is not bytes):
        raise core.FluorescenceContractError("invalid_source")
    selected = binding["report_input"]
    profile, identity = selected["profile"], selected["file"]
    result = dict(version=PARSE_VERSION, source=dict(key=selected["source_key"], file=deepcopy(identity),
        dataset_position=0, format_profile=profile, extent="complete", native_event_count=None, metadata=[]),
        reports=[], issues=[], provenance=dict(artifact_origin="received_supplied", producer_execution="unverified",
            profile=profile, profile_source=deepcopy(PROFILE_SOURCES[profile])))

    def problem(code, stage="parse"):
        value = core.issue(code, stage, source_key=selected["source_key"])
        if value not in result["issues"]:
            result["issues"].append(value)

    for field in selected["fields"]:
        unit, precision, _ = _field_shape(field, profile, context)
        result["reports"].append(dict(key=field["key"], file=deepcopy(identity), source_key=selected["source_key"],
            location=_empty_location(), label=None, value=None, raw=None, unit=unit,
            component_request=deepcopy(field["component_request"]), decimal_places=precision))
    support = _supported(association_raw, binding, context)
    if not support:
        problem("native_population_unknown", "input")
    if len(raw) != identity["size_bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
        result["source"]["extent"] = "unavailable"
        problem("retained_artifact_mismatch", "input")
        return validate_report_parse_result(result, binding=binding)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        text = raw[:error.start].decode("utf-8")
        result["source"]["extent"] = "partial"
        problem("input_encoding_invalid")
    records, recognized = {}, True
    if profile == CYTOKINE_CSV_PROFILE:
        records, errors, recognized = _cytokine_csv(text)
        for code in errors:
            problem(code)
            result["source"]["extent"] = "partial"
    else:
        header = _FACS_HEADER if profile == FACS_PROFILE else _CYTOKINE_HEADER
        recognized = bool(text) and next(_lines(text))["text"] == header
        if recognized:
            records = _facs(text) if profile == FACS_PROFILE else _cytokine_log(text)
    if not recognized:
        result["source"]["extent"] = "unavailable"
        problem("native_format_mismatch")
        return validate_report_parse_result(result, binding=binding)
    for field, report in zip(selected["fields"], result["reports"]):
        locator = field["locator"]
        if profile == FACS_PROFILE:
            items = records.get(locator["metric"], [])
            candidate = items[locator["occurrence"]] if locator["occurrence"] < len(items) else None
        elif profile == CYTOKINE_LOG_PROFILE:
            candidate = records.get((locator["condition_ordinal"], locator["metric"], locator["marker_occurrence"]))
        else:
            candidate = records.get((locator["row_ordinal"], locator["column_ordinal"]))
        if candidate is None:
            problem("native_report_uninterpretable")
            result["source"]["extent"] = "partial"
            continue
        report.update(raw=candidate["raw"], label=candidate["label"], location=candidate["location"])
        if profile == CYTOKINE_CSV_PROFILE:
            report["unit"] = _csv_unit(candidate["metadata"]["column"])
        _, precision, count = _field_shape(field, profile, context)
        if candidate["broken"]:
            problem("truncated_source")
        else:
            report["value"] = _number(report["raw"], count=count, fixed=precision == 2)
        if report["value"] is None:
            problem("native_report_uninterpretable" if not report["raw"] else "invalid_numeric_token")
            result["source"]["extent"] = "partial"
        labels_match = (profile != CYTOKINE_CSV_PROFILE or (
            candidate["metadata"]["condition"] == locator["condition_label"]
            and candidate["metadata"]["column"] == locator["column_label"]))
        if not labels_match:
            problem("native_format_mismatch")
            result["source"]["extent"] = "partial"
        if field["component_request"] is not None:
            meaning = (_facs_meaning(field, candidate, context) if profile == FACS_PROFILE
                       else _cytokine_meaning(field, candidate, context, binding))
            if not labels_match or not meaning:
                problem("native_population_unknown", "input")
    return validate_report_parse_result(result, binding=binding)
