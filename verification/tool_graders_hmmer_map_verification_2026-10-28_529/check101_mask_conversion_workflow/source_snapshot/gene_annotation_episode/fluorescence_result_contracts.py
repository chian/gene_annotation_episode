"""Closed execution/result projections for the shared fluorescence sheet.

Scientific shapes and cell meanings belong to fluorescence_event_contracts.
These stdlib-only checks validate selections and retained control relationships;
they do not decode source data, calculate cells, or grant artifact access.
"""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from . import fluorescence_event_contracts as core
from .fluorescence_execution_common import canonical, closed, digest, require, same, unique, validate_failure
from .native_fluorescence_contracts import (
    validate_fluorescence_job, validate_fluorescence_native_capture,
    validate_fluorescence_run_plan,
)

SELECTOR_VERSION = "fluorescence_result_selector_v1"
PLAN_VERSION = "fluorescence_worker_plan_v1"
RESULT_VERSION = "fluorescence_worker_result_v1"
CONTEXT_SCHEMA = "fluorescence_event_context_view_v1"
CONTEXT_FIELDS = ("sources", "samples", "channels", "domains", "populations",
                  "gates", "control_pairs", "native_reports")
OUTPUTS = (
    ("sheet", "sheet.json", core.SHEET_SCHEMA),
    ("calculations", "calculations.json", core.COMPONENTS_SCHEMA),
    ("projection", "projection.json", core.VIEW_SCHEMA),
    ("context", "context.json", CONTEXT_SCHEMA),
    ("diagnostics", "diagnostics.json", "fluorescence_execution_failures_v1"),
)
MODES = ("native_result", "saved_sheet_recalculation")


def obj(**fields):
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


def arr(items, **extra):
    return {"type": "array", "items": items, **extra}


def nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


KEY = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000-\\u001f\\u007f-\\u009f]+$"}
TEXT = {"type": "string"}
COUNT = {"type": "integer", "minimum": 0}
NUMBER = {"type": "number"}
BOOL = {"type": "boolean"}
SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
FILE_SCHEMA = obj(artifact_ref={"type": "string", "pattern": "^artifact_[0-9a-f]{64}$"},
                  sha256=SHA, size_bytes=COUNT, format=KEY)
SAVED_FILE_SCHEMA = deepcopy(FILE_SCHEMA)
SAVED_FILE_SCHEMA["properties"]["format"] = {"const": core.SHEET_SCHEMA}
LOCATION_SCHEMA = obj(record_ordinal=nullable(COUNT), line_start=nullable({"type": "integer", "minimum": 1}),
    line_end=nullable({"type": "integer", "minimum": 1}), byte_start=nullable(COUNT), byte_end=nullable(COUNT))
ASSOCIATION_SCHEMA = obj(namespace=KEY, identifier=KEY, file=FILE_SCHEMA,
                         source_key=nullable(KEY), location=LOCATION_SCHEMA)
SAMPLE_SCHEMA = obj(key=KEY, primary_domain_key=KEY, label=nullable(TEXT), condition=nullable(TEXT),
    biological_replicate=nullable(TEXT), technical_replicate=nullable(TEXT), associations=arr(ASSOCIATION_SCHEMA))
CHANNEL_SCHEMA = obj(key=KEY, domain_key=KEY, ordinal=COUNT, native_name=nullable(TEXT),
    label=nullable(TEXT), unit=nullable(TEXT), analyte=nullable(ASSOCIATION_SCHEMA))
PREPARATION_SCHEMA = obj(state={"enum": ["not_applied", "applied", "unknown", "failed"]},
    method=nullable(KEY), parameters_file=nullable(FILE_SCHEMA))
BASIS_SCHEMA = obj(key=KEY, evidence_file=FILE_SCHEMA)
SOURCE_CONTEXT_SCHEMA = obj(key=KEY, file=nullable(FILE_SCHEMA), dataset_position=COUNT, format_profile=KEY,
    extent={"enum": ["complete", "partial", "unavailable"]}, native_event_count=nullable(COUNT))
DOMAIN_CONTEXT_SCHEMA = obj(key=KEY, sample_key=KEY, source_key=KEY, parent_domain_key=nullable(KEY),
    state={"enum": ["available", "unavailable", "failed"]}, scale_kind={"enum": ["encoded", "scaled", "as_supplied"]},
    compensation=PREPARATION_SCHEMA, transformation=PREPARATION_SCHEMA, comparison_basis=nullable(BASIS_SCHEMA))
DOMAIN_CONTEXT_SCHEMA['properties']['scaling'] = deepcopy(PREPARATION_SCHEMA)
POPULATION_CONTEXT_SCHEMA = obj(key=KEY, sample_key=KEY, kind={"enum": ["all", "subset"]})
PARENT_SCHEMA = obj(kind={"enum": ["population", "gate"]}, key=KEY)
BOUND_SCHEMA = obj(value=NUMBER, inclusive=BOOL)
GATE_SCHEMA = obj(key=KEY, sample_key=KEY, parent=PARENT_SCHEMA, kind={"enum": ["threshold", "pass_all"]},
    domain_key=nullable(KEY), channel_key=nullable(KEY), lower=nullable(BOUND_SCHEMA), upper=nullable(BOUND_SCHEMA))
CONTROL_SCHEMA = obj(key=KEY, target_gate_key=KEY, control_gate_key=KEY,
    denominator={"enum": ["parent", "evaluable"]}, comparison_basis=BASIS_SCHEMA)


def cell_request_schema():
    definitions = (
        ("population", ("gate_key",), core._POPULATION_METRICS),
        ("fraction", ("gate_key",), core._FRACTION_METRICS),
        ("intensity", ("gate_key", "domain_key", "channel_key"), core._INTENSITY_METRICS),
        ("control", ("control_key",), core._CONTROL_METRICS),
        ("native_comparison", ("native_report_key",), core._NATIVE_METRICS),
    )
    return {"oneOf": [obj(kind={"const": kind},
        **{key: KEY if key in identities else {"type": "null"} for key in core._CELL_IDENTITIES},
        denominator={"enum": ["parent", "evaluable"] if kind == "fraction" else ["none"]},
        metric={"enum": list(metrics)}) for kind, identities, metrics in definitions]}


CELL_REQUEST_SCHEMA = cell_request_schema()
SELECTION_SCHEMA = obj(requests=arr(CELL_REQUEST_SCHEMA, uniqueItems=True), offset=COUNT,
                       limit={"type": "integer", "minimum": 1})
PARAMETERS_SCHEMA = obj(
    fraction_requests=arr(obj(gate_key=KEY, denominator={"enum": ["parent", "evaluable"]}), uniqueItems=True),
    intensity_requests=arr(obj(gate_key=KEY, domain_key=KEY, channel_key=KEY), uniqueItems=True),
    control_requests=arr(obj(control_key=KEY, include_legacy_clipping=BOOL), uniqueItems=True),
    native_comparison_requests=arr(KEY, uniqueItems=True))
ISSUE_SCHEMA = obj(code={"enum": sorted(core._ISSUE_CODES)}, stage={"enum": sorted(core._STAGES)},
    **{name: nullable(COUNT if name == "event_ordinal" else KEY) for name in core._LOCATORS})
CELL_SCHEMA = obj(request=CELL_REQUEST_SCHEMA, value=nullable(NUMBER),
    state={"enum": ["present", "qualified", "unavailable"]}, unit=nullable(TEXT),
    population=obj(**{name: nullable(KEY) for name in ("sample_key", "gate_key", "domain_key", "channel_key")},
        denominator={"enum": ["none", "parent", "evaluable", "selected_finite", "paired_controls"]},
        extent={"enum": ["complete", "confirmed_subset", "incomplete", "unavailable"]}),
    operands=arr({"type": "string", "pattern": "^(sheet|parameters|components):(/.*)?$"}), issues=arr(ISSUE_SCHEMA))
NATIVE_REPORT_SCHEMA = obj(key=KEY, file=FILE_SCHEMA, source_key=nullable(KEY), location=LOCATION_SCHEMA,
    label=nullable(TEXT), value=nullable(NUMBER), raw=nullable(TEXT), unit=nullable(TEXT),
    component_request=nullable(CELL_REQUEST_SCHEMA), decimal_places=nullable(COUNT))
CONTEXT_VIEW_SCHEMA = obj(schema={"const": CONTEXT_SCHEMA}, selection=SELECTION_SCHEMA,
    context_fields=arr({"enum": list(CONTEXT_FIELDS)}, uniqueItems=True), sources=arr(SOURCE_CONTEXT_SCHEMA),
    samples=arr(SAMPLE_SCHEMA), channels=arr(CHANNEL_SCHEMA), domains=arr(DOMAIN_CONTEXT_SCHEMA),
    populations=arr(POPULATION_CONTEXT_SCHEMA), gates=arr(GATE_SCHEMA), control_pairs=arr(CONTROL_SCHEMA),
    native_reports=arr(NATIVE_REPORT_SCHEMA))
PROJECTION_SCHEMA = obj(schema={"const": core.VIEW_SCHEMA}, selection=SELECTION_SCHEMA, rows=arr(CELL_SCHEMA),
    total_selected_rows=COUNT, returned_row_count=COUNT, has_more=BOOL,
    status={"enum": ["calculated", "partial", "unavailable"]}, issues=arr(ISSUE_SCHEMA))
FLUORESCENCE_RESULT_SELECTOR_SCHEMA = obj(version={"const": SELECTOR_VERSION}, mode={"enum": list(MODES)},
    selection=SELECTION_SCHEMA, context_fields=arr({"enum": list(CONTEXT_FIELDS)}, uniqueItems=True),
    saved_sheet_file=nullable(SAVED_FILE_SCHEMA), parameters=nullable(PARAMETERS_SCHEMA))
FAILURE_SCHEMA = obj(code={"enum": ["input_file_unavailable", "input_identity_mismatch",
    "capture_file_unavailable", "capture_file_digest_mismatch", "manifest_missing_or_malformed",
    "native_manifest_conflict", "parsed_batch_unavailable", "parsed_batch_invalid", "original_execution_mismatch",
    "native_software_mismatch", "worker_nonzero_exit", "worker_resource_failure", "worker_output_unavailable",
    "worker_output_malformed", "worker_execution_mismatch", "saved_sheet_incompatible", "projection_contract_invalid",
    "preparation_unavailable", "preparation_incompatible", "preparation_failed",
    "report_batch_unavailable", "report_batch_invalid"]},
    stage={"enum": ["input", "capture", "authority", "worker", "projection"]}, input_index=nullable(COUNT),
    role=nullable({"type": "string", "pattern": "^((event_input|support_input|event_batch|report_input|preparation_parameters|prepared_data|prepared_batch|report_batch):[0-9]+|manifest|sheet|calculations|projection|context|diagnostics|worker_result|worker_execution)$"}))


def validate_file(value, *, saved=False):
    core._file(value, "invalid_source")
    require(not saved or value["format"] == core.SHEET_SCHEMA, "saved_sheet_incompatible")
    return deepcopy(value)


def failure(code, stage, *, input_index=None, role=None):
    return validate_failure(dict(code=code, stage=stage, input_index=input_index, role=role))


def validate_path(value):
    require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"), "invalid_fluorescence_path")
    path = PurePosixPath(value)
    require(path.is_absolute() and str(path) == value and ".." not in path.parts and value != "/",
            "invalid_fluorescence_path")
    return value


def validate_retained(value, *, saved=False):
    closed(value, ("file", "path"))
    validate_path(value["path"])
    validate_file(value["file"], saved=saved)
    return deepcopy(value)


def validate_selection_shape(value):
    core._keys(value, "requests offset limit", "invalid_selection")
    core._list(value["requests"], "invalid_selection")
    core._integer(value["offset"], "invalid_selection")
    core._integer(value["limit"], "invalid_selection", minimum=1)
    for request in value["requests"]:
        core._cell_request(request, "invalid_selection")
    core._unique([core.canonical(row) for row in value["requests"]], "invalid_selection")
    return deepcopy(value)


def validate_context_fields(value):
    require(type(value) is list and all(type(row) is str and row in CONTEXT_FIELDS for row in value)
            and len(set(value)) == len(value), "projection_contract_invalid")
    return deepcopy(value)


def _parameters_shape(value):
    code = "invalid_parameters"
    core._keys(value, "fraction_requests intensity_requests control_requests native_comparison_requests", code)
    for name, rows in value.items():
        core._list(rows, code)
        for row in rows:
            if name == "native_comparison_requests":
                core._key(row, code)
                continue
            keys = {"fraction_requests": "gate_key denominator", "intensity_requests": "gate_key domain_key channel_key",
                    "control_requests": "control_key include_legacy_clipping"}[name]
            core._keys(row, keys, code)
            for key, item in row.items():
                if key == "denominator":
                    core._enum(item, {"parent", "evaluable"}, code)
                elif key == "include_legacy_clipping":
                    core._need(type(item) is bool, code)
                else:
                    core._key(item, code)
        core._unique([core.canonical(row) for row in rows], code)
    core._unique([row["control_key"] for row in value["control_requests"]], code)
    return value


def validate_fluorescence_selector(value, *, job=None):
    canonical(value)
    closed(value, ("version", "mode", "selection", "context_fields", "saved_sheet_file", "parameters"))
    require(value["version"] == SELECTOR_VERSION and value["mode"] in MODES, "invalid_fluorescence_selector")
    validate_selection_shape(value["selection"])
    validate_context_fields(value["context_fields"])
    if value["mode"] == "native_result":
        require(value["saved_sheet_file"] is None and value["parameters"] is None, "invalid_fluorescence_selector")
    else:
        validate_file(value["saved_sheet_file"], saved=True)
        _parameters_shape(value["parameters"])
    if job is not None:
        job = validate_fluorescence_job(job)
        if value["mode"] == "native_result":
            definitions = job["definitions"]
            expected = core._expected_requests({"gate_definitions": definitions["gates"],
                "control_pairs": definitions["control_pairs"]}, job["parameters"])
            require(all(row in expected for row in value["selection"]["requests"]), "invalid_selection")
    return deepcopy(value)


def validate_fluorescence_worker_plan(value):
    canonical(value)
    require(type(value) is dict and value.get("mode") in MODES, "invalid_fluorescence_worker_plan")
    closed(value, ("version", "mode", "directory", "selector", *(
        ("original_plan", "capture") if value["mode"] == "native_result" else ("sheet",))))
    require(value["version"] == PLAN_VERSION, "invalid_fluorescence_worker_plan")
    validate_path(value["directory"])
    if value["mode"] == "native_result":
        original = validate_fluorescence_run_plan(value["original_plan"])
        validate_fluorescence_native_capture(value["capture"], original_plan=original)
        selector = validate_fluorescence_selector(value["selector"], job=original["requested_job"]["native_fluorescence"])
    else:
        validate_retained(value["sheet"], saved=True)
        selector = validate_fluorescence_selector(value["selector"])
        require(same(value["sheet"]["file"], selector["saved_sheet_file"]), "saved_sheet_incompatible")
    require(selector["mode"] == value["mode"], "invalid_fluorescence_worker_plan")
    return deepcopy(value)


def validate_fluorescence_worker_result(value):
    canonical(value)
    closed(value, ("version", "mode", "plan_sha256", "selector", "outputs", "failures", "input_identities",
        "native_binding", "native_outcome", "original_events_acquired", "analysis_complete"))
    require(value["version"] == RESULT_VERSION and value["mode"] in MODES
        and type(value["plan_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["plan_sha256"]),
        "invalid_fluorescence_worker_result")
    selector = validate_fluorescence_selector(value["selector"])
    require(selector["mode"] == value["mode"], "invalid_fluorescence_worker_result")
    require(all(type(value[name]) is bool for name in ("native_binding", "original_events_acquired", "analysis_complete")),
            "invalid_fluorescence_worker_result")
    require(type(value["input_identities"]) is list and value["input_identities"], "invalid_fluorescence_worker_result")
    for file in value["input_identities"]:
        validate_file(file)
    saved = value["mode"] == "saved_sheet_recalculation"
    if saved:
        require(not value["native_binding"] and not value["original_events_acquired"]
            and value["native_outcome"] == "not_applicable" and same(value["input_identities"], [selector["saved_sheet_file"]]),
            "invalid_fluorescence_worker_result")
    else:
        require(value["native_outcome"] in ("complete", "partial", "unavailable")
            and (not value["original_events_acquired"] or value["native_binding"])
            and value["original_events_acquired"] == (value["native_outcome"] in ("complete", "partial")),
            "invalid_fluorescence_worker_result")
    require(type(value["outputs"]) is list and len(value["outputs"]) == len(OUTPUTS), "invalid_fluorescence_worker_outputs")
    declarations = {}
    for row, (role, path, format_) in zip(value["outputs"], OUTPUTS):
        closed(row, ("role", "declaration"))
        d = row["declaration"]
        closed(d, ("relative_path", "format", "state", "sha256", "size_bytes"))
        require(row["role"] == role and d["relative_path"] == path and d["format"] == format_
            and d["state"] in ("present", "absent"), "invalid_fluorescence_worker_outputs")
        if d["state"] == "present":
            validate_file(dict(artifact_ref="artifact_" + str(d["sha256"]),
                sha256=d["sha256"], size_bytes=d["size_bytes"], format=d["format"]))
        else:
            require(d["sha256"] is None and d["size_bytes"] is None, "invalid_fluorescence_worker_outputs")
        declarations[role] = d["state"] == "present"
    require(not declarations["projection"] or declarations["sheet"] and declarations["calculations"],
            "invalid_fluorescence_worker_outputs")
    require(not declarations["context"] or declarations["projection"] and bool(selector["context_fields"]),
            "invalid_fluorescence_worker_outputs")
    require(declarations["diagnostics"], "invalid_fluorescence_worker_outputs")
    require(not value["analysis_complete"] or all(declarations[k] for k in ("sheet", "calculations", "projection"))
        and (not selector["context_fields"] or declarations["context"])
        and (saved or value["native_binding"]) and not value["failures"], "invalid_fluorescence_worker_completion")
    require(type(value["failures"]) is list, "invalid_fluorescence_worker_result")
    for row in value["failures"]:
        validate_failure(row)
    require(same(value["failures"], unique(value["failures"])), "invalid_fluorescence_worker_result")
    return deepcopy(value)


def validate_fluorescence_projection(value):
    canonical(value)
    closed(value, ("schema", "selection", "rows", "total_selected_rows", "returned_row_count", "has_more", "status", "issues"))
    require(value["schema"] == core.VIEW_SCHEMA, "projection_contract_invalid")
    selection = validate_selection_shape(value["selection"])
    start, stop = selection["offset"], selection["offset"] + selection["limit"]
    require(type(value["rows"]) is list and type(value["total_selected_rows"]) is int
        and type(value["returned_row_count"]) is int and type(value["has_more"]) is bool,
        "projection_contract_invalid")
    for row in value["rows"]:
        core._cell(row, "invalid_components")
        for operand in row["operands"]:
            require(re.fullmatch(r"(?:sheet|parameters|components):(?:/.*)?", operand, re.DOTALL)
                and re.search(r"~(?:[^01]|$)", operand) is None, "projection_contract_invalid")
    require([row["request"] for row in value["rows"]] == selection["requests"][start:stop]
        and value["total_selected_rows"] == len(selection["requests"])
        and value["returned_row_count"] == len(value["rows"])
        and value["has_more"] is (stop < len(selection["requests"])), "projection_contract_invalid")
    core._issues(value["issues"], "invalid_components")
    require(same(value["issues"], unique(value["issues"])) and value["status"] in ("calculated", "partial", "unavailable"),
            "projection_contract_invalid")
    require(all(issue in value["issues"] for row in value["rows"] for issue in row["issues"]), "projection_contract_invalid")
    if start == 0 and stop >= len(selection["requests"]):
        expected = ("unavailable" if value["rows"] and all(row["state"] == "unavailable" for row in value["rows"])
            else "partial" if value["issues"] or any(row["state"] != "present" for row in value["rows"]) else "calculated")
        require(value["status"] == expected and same(value["issues"], unique([issue for row in value["rows"] for issue in row["issues"]])),
                "projection_contract_invalid")
    elif value["status"] == "calculated":
        require(not value["issues"] and all(row["state"] == "present" for row in value["rows"]), "projection_contract_invalid")
    elif value["status"] == "unavailable":
        require(bool(selection["requests"]) and all(row["state"] == "unavailable" for row in value["rows"]), "projection_contract_invalid")
    return deepcopy(value)


def validate_fluorescence_context(value):
    canonical(value)
    closed(value, ("schema", "selection", "context_fields", *CONTEXT_FIELDS))
    require(value["schema"] == CONTEXT_SCHEMA, "projection_contract_invalid")
    validate_selection_shape(value["selection"])
    fields = validate_context_fields(value["context_fields"])
    indexes = {}
    validators = dict(samples=core._sample, channels=core._channel, gates=core._gate,
                      control_pairs=core._control, native_reports=core._native_report)
    for name in CONTEXT_FIELDS:
        rows = value[name]
        require(type(rows) is list and (name in fields or not rows), "projection_contract_invalid")
        for row in rows:
            if name == "sources":
                closed(row, ("key", "file", "dataset_position", "format_profile", "extent", "native_event_count"))
                core._source({**row, "metadata": []})
            elif name == "domains":
                closed(row, ("key", "sample_key", "source_key", "parent_domain_key", "state", "scale_kind",
                    "compensation", "transformation", "comparison_basis") + (("scaling",) if "scaling" in row else ()))
                core._domain({**row, "correspondence": None if row["parent_domain_key"] is None else []})
            elif name == "populations":
                closed(row, ("key", "sample_key", "kind"))
                core._population({**row, "event_ordinals": None if row["kind"] == "all" else []})
            else:
                validators[name](row)
        require(len({row["key"] for row in rows}) == len(rows), "projection_contract_invalid")
        indexes[name] = {row["key"]: row for row in rows}

    def link(field, key):
        if key is None or field not in fields:
            return None
        require(key in indexes[field], "projection_contract_invalid")
        return indexes[field][key]

    for sample in value["samples"]:
        domain = link("domains", sample["primary_domain_key"])
        require(domain is None or domain["sample_key"] == sample["key"] and domain["parent_domain_key"] is None,
                "projection_contract_invalid")
        for association in sample["associations"]:
            link("sources", association["source_key"])
    for channel in value["channels"]:
        link("domains", channel["domain_key"])
        if channel["analyte"] is not None:
            link("sources", channel["analyte"]["source_key"])
    for domain in value["domains"]:
        link("samples", domain["sample_key"])
        link("sources", domain["source_key"])
        parent = link("domains", domain["parent_domain_key"])
        require(parent is None or parent["sample_key"] == domain["sample_key"], "projection_contract_invalid")
        current, seen = domain, set()
        while current is not None:
            require(current["key"] not in seen, "projection_contract_invalid")
            seen.add(current["key"])
            current = indexes["domains"].get(current["parent_domain_key"])
    for population in value["populations"]:
        link("samples", population["sample_key"])
    for gate in value["gates"]:
        link("samples", gate["sample_key"])
        parent = link("gates" if gate["parent"]["kind"] == "gate" else "populations", gate["parent"]["key"])
        require(parent is None or parent["sample_key"] == gate["sample_key"], "projection_contract_invalid")
        domain = link("domains", gate["domain_key"])
        channel = link("channels", gate["channel_key"])
        require(domain is None or domain["sample_key"] == gate["sample_key"], "projection_contract_invalid")
        require(channel is None or channel["domain_key"] == gate["domain_key"], "projection_contract_invalid")
        current, seen = gate, set()
        while current is not None:
            require(current["key"] not in seen, "projection_contract_invalid")
            seen.add(current["key"])
            current = indexes["gates"].get(current["parent"]["key"]) if current["parent"]["kind"] == "gate" else None
    for pair in value["control_pairs"]:
        link("gates", pair["target_gate_key"])
        link("gates", pair["control_gate_key"])
    for report in value["native_reports"]:
        link("sources", report["source_key"])
    selected = value["selection"]["requests"][value["selection"]["offset"]:][:value["selection"]["limit"]]
    for request in [*selected, *(r["component_request"] for r in value["native_reports"] if r["component_request"] is not None)]:
        for field, key in (("gates", "gate_key"), ("channels", "channel_key"), ("domains", "domain_key"),
                           ("control_pairs", "control_key"), ("native_reports", "native_report_key")):
            link(field, request[key])
    return deepcopy(value)


def projection_schema():
    return deepcopy(PROJECTION_SCHEMA)


def context_schema():
    return deepcopy(CONTEXT_VIEW_SCHEMA)
