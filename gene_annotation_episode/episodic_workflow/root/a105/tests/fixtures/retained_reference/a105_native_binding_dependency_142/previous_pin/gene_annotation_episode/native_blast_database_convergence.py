"""Pure native database PSI/DELTA convergence binding (accepted 325).

Fresh binding selects actual captured bytes and a unique actual operand before
calling 316. Saved validation checks retained structure and identities only:
it does not import that extractor, lex native output, parse FASTA, populate a
sheet or calculate a score. Artifact identities here are expected identities;
the worker and publication boundary must retain and authenticate those bytes.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from . import native_blast_database_contracts as _producer


_PREFIX = "native_blast_database_convergence_"
_NATIVE_PREFIX = "blast_native_iteration_"
_NATIVE_CODES = tuple(_NATIVE_PREFIX + name for name in """bundle_contract_rejected
report_artifact_missing report_identity_conflict collection_artifact_conflict
report_format_unsupported report_program_conflict report_version_missing
report_version_unsupported report_encoding_invalid query_identity_conflict
query_format_unsupported query_input_invalid query_input_partial
query_scope_unavailable query_operand_conflict marker_absent marker_partial
marker_duplicate source_partial native_failed""".split())
_BINDING_CODES = tuple(_PREFIX + name for name in """report_capture_missing
report_bytes_unavailable report_identity_conflict query_capture_missing
query_bytes_unavailable query_identity_conflict query_operand_zero
query_operand_multiple query_operand_conflicting""".split())
_DETAILS = """capture_absent bytes_absent catalog_identity_conflict
byte_identity_conflict no_query_operand multiple_query_operands
missing_operand_identity operand_artifact_conflict conflicting_operand_values""".split()


def _object(**fields):
    return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)


def _array(item):
    return dict(type="array", items=item)


def _nullable(value):
    return dict(anyOf=[value, {"type": "null"}])


def _enum(*values):
    return dict(enum=list(values))


_TOKEN = dict(type="string", minLength=1, maxLength=512, pattern=r"^[^\x00\r\n]+$")
_REF = _TOKEN
_TEXT = dict(type="string")
_I0 = dict(type="integer", minimum=0)
_I1 = dict(type="integer", minimum=1)
_SHA = dict(type="string", pattern=r"^[0-9a-f]{64}$")
_POINTER = dict(type="string", pattern=r"^(?:/(?:[^~]|~[01])*)?$")
_INTERVAL = dict(type="array", prefixItems=[_I0, _I1], minItems=2, maxItems=2)
_IDENTITY = _object(namespace=_TOKEN, value=_TOKEN, version=_nullable(_TOKEN))
_OPERAND = _object(role=_enum("query", "subject", "database", "profile", "msa", "checkpoint"),
    artifact_key=_nullable(_TOKEN), record_ordinal=_nullable(_I0), native_id=_nullable(_TEXT),
    native_title=_nullable(_TEXT), subject_ref=_nullable(_REF), molecule=_enum("dna", "rna", "protein", "unknown"),
    length=_nullable(_I1), selected_interval=_nullable(_INTERVAL), identity=_nullable(_IDENTITY))
_BYTE_ID = _object(sha256=_SHA, size_bytes=_I0)
_ARTIFACT_ID = _object(artifact_ref=_REF, sha256=_SHA, size_bytes=_I0)
_CATALOG_ID = _object(artifact_ref=_REF, source_ref=_REF, sha256=_SHA, size_bytes=_I0)
_CONTEXT = _object(original_job=_producer.NATIVE_BLAST_DATABASE_JOB_SCHEMA,
    bundle=_producer.NATIVE_BLAST_DATABASE_BUNDLE_SCHEMA,
    attempt_identity=_object(identity=_producer.IDENTITY_SCHEMA, attempt_directory=_TEXT, plan_sha256=_SHA))
_INPUT_STATE = _object(status=_enum("missing_capture", "bytes_unavailable", "identity_conflict", "available"),
    artifact_key=_nullable(_TOKEN), capture=_nullable(_BYTE_ID), catalog=_nullable(_CATALOG_ID), supplied_bytes=_nullable(_BYTE_ID))
_ISSUE = _object(code=_enum(*_BINDING_CODES), pointer=_POINTER, artifact_key=_nullable(_TOKEN),
    input_key=_nullable(_TOKEN), operand_indices=_array(_I0), detail_code=_enum(*_DETAILS))
_NATIVE_ISSUE = _object(code=_enum(*_NATIVE_CODES), marker_index=_nullable(_I0),
    source_pointer=_nullable(_POINTER), details=dict(type="object"))
_MARKER = _object(record_key=_TEXT, byte_span=_INTERVAL, line_number=_I1, exact_text=_TEXT,
    scope=_enum("query", "unbound"), issue_codes=_array(_enum(*_NATIVE_CODES)))
_RECORD = _object(record_key=_TEXT, search_key={"type": "null"}, query_operand=_nullable(_OPERAND),
    native_converged={"type": "boolean", "const": True}, evidence=_object(
        origin={"const": "native_extractor_output"}, source=_object(source_ref=_REF, pointer={"const": ""}),
        source_format={"const": "ncbi_blastplus_2.17.0_tabular7"}, original_record=_TEXT,
        extractor=_object(module={"const": "gene_annotation_episode.blast_native_iteration_records"},
            function={"const": "extract_blast_tabular7_convergence"}, version={"const": "1"})))
_EXTRACTION = _object(schema={"const": "blast_native_convergence_extraction_v1"},
    status=_enum("complete", "partial", "unavailable", "incompatible"),
    report=_object(artifact_key=_TOKEN, source_ref=_REF, sha256=_SHA, size_bytes=_I0,
        format=_nullable(_TEXT), fields=_nullable(_array(_TEXT)), delimiter=_nullable(_TEXT),
        native_programs=_array(_TEXT), native_versions=_array(_TEXT), native_text=_nullable(_TEXT), native_bytes_base64=_TEXT),
    query=_object(input_key=_nullable(_TEXT), artifact_key=_nullable(_TEXT), sha256=_SHA, size_bytes=_I0,
        native_text=_nullable(_TEXT), native_bytes_base64=_TEXT, record_count=_nullable(_I0), query_operand=_nullable(_OPERAND)),
    source_context=_CONTEXT, markers=_array(_MARKER), convergence_records=_array(_RECORD), issues=_array(_NATIVE_ISSUE))
_BINDING = _object(schema={"const": "native_blast_database_convergence_binding_v1"},
    invocation=_enum("invoked", "not_invoked"), source_context=_CONTEXT,
    selected=_object(report_output_key=_TOKEN, query_input_key=_TOKEN, report=_INPUT_STATE, query=_INPUT_STATE),
    query_binding=_object(status=_enum("zero", "unique", "multiple", "conflicting"),
        candidates=_array(_object(operand_index=_I0, operand=_OPERAND)), selected_operand_index=_nullable(_I0)),
    issues=_array(_ISSUE), extraction=_nullable(_EXTRACTION), extraction_artifact=_nullable(_ARTIFACT_ID))
_CAPTURE_FIELDS = {k: v for k, v in _producer.NATIVE_BLAST_DATABASE_BUNDLE_SCHEMA["properties"]["artifacts"]["items"]["properties"].items()
                   if k != "content_assessment"}
_CATALOG = _object(bundle_source_ref=_REF, bundle_artifact_ref=_REF, bundle_sha256=_SHA,
    entries=_array(_object(**_CAPTURE_FIELDS, artifact_ref=_REF, source_ref=_REF, path=_TEXT)),
    retained_sources=_array(_object(source_ref=_REF, artifact_ref=_REF, sha256=_SHA, size_bytes=_I0, path=_TEXT)))
_INVOCATION = _object(execution_program=_TOKEN, scientific_mode=_TOKEN, resource_kind=_enum("api", "local", "hpc"),
    query_kind=_TOKEN, reference_kind=_TOKEN, request=dict(type="object"), effective_options=dict(type="object"),
    operands=_array(_OPERAND), completion=_object(native_returncode=_nullable(dict(type="integer")), producer_complete=_nullable(dict(type="boolean"))))
_COLLECTION_ARTIFACT = _object(artifact_key=_TOKEN, role=_TOKEN, format=_TOKEN, fields=_nullable(_array(_TEXT)),
    delimiter=_nullable(_TEXT), sha256=_SHA, size_bytes=_I0)
_COLLECTION_ARTIFACT["properties"]["members"] = _array(_object(member_ordinal=_I0, name=_TEXT, size_bytes=_I0, sha256=_nullable(_SHA)))
_SEARCH_KEY = _object(artifact_key=_TOKEN, member_ordinal=_nullable(_I0), report_index=_I0, search_pointer=_POINTER)
_SEARCH = _object(search_key=_SEARCH_KEY, program_context=_object(execution_program=_TOKEN, reported_program=_nullable(_TEXT),
    scientific_mode=_TOKEN, query_kind=_TOKEN, reference_kind=_TOKEN, native_version=_nullable(_TEXT), geometry_program=_nullable(_TEXT)),
    stage=_nullable(_TEXT), iteration=_nullable(_I1), normalized=dict(type="object"), row_map=_array(dict(type="object")),
    operand_binding=_nullable(_OPERAND), reporting=_object(native_hit_array_present=dict(type="boolean"), native_hit_count=_nullable(_I0),
        requested_hit_limit=_nullable(_I0), requested_hsp_limit=_nullable(_I0), native_returncode=_nullable(dict(type="integer")),
        producer_complete=_nullable(dict(type="boolean"))), native=dict(type="object"), issues=_array(dict(type="object")))
_COLLECTION = _object(schema={"const": "blast_report_collection_v1"}, invocation=_INVOCATION,
    artifacts=_array(_COLLECTION_ARTIFACT), searches=_array(_SEARCH), issues=_array(dict(type="object")))
_Validator = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) is int or type(value) is float and math.isfinite(value)}))


def _fail(kind, pointer):
    raise ValueError(_PREFIX + kind + "_invalid", pointer)


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _copy(value, kind, path, active=None):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or type(value) is dict and all(type(k) is str for k in value):
        active = set() if active is None else active
        if id(value) in active:
            _fail(kind, path)
        active.add(id(value))
        try:
            if type(value) is list:
                return [_copy(v, kind, path + "/" + str(i), active) for i, v in enumerate(value)]
            return {k: _copy(v, kind, path + "/" + _escape(k), active) for k, v in value.items()}
        finally:
            active.remove(id(value))
    _fail(kind, path)


def _shape(value, schema, kind, path):
    error = next(_Validator(schema).iter_errors(value), None)
    if error is not None:
        # Nullable wrappers should not hide the exact invalid retained field.
        while error.validator in ("anyOf", "oneOf") and error.context:
            candidates = [e for e in error.context if e.schema.get("type") != "null"]
            error = (candidates or error.context)[0]
        pointer = path + "".join("/" + _escape(p) for p in error.absolute_path)
        if error.validator == "required":
            pointer += "/" + _escape(next(k for k in error.validator_value if k not in error.instance))
        elif error.validator == "additionalProperties" and error.validator_value is False:
            pointer += "/" + _escape(next(k for k in error.instance if k not in error.schema.get("properties", {})))
        _fail(kind, pointer)


def _require(condition, kind, path):
    if not condition:
        _fail(kind, path)


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _byte_identity(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _artifact_identity(extraction):
    result = _byte_identity(_json_bytes(extraction))
    return dict(artifact_ref="artifact_" + result["sha256"], **result)


def _operand_relations(operand, kind, path):
    interval = operand["selected_interval"]
    _require(interval is None or interval[0] < interval[1] and
        (operand["length"] is None or interval[1] <= operand["length"]), kind, path + "/selected_interval")


def _context_collection(context, collection, kind):
    _shape(collection, _COLLECTION, kind, "/collection")
    inv, job, bundle = collection["invocation"], context["original_job"], context["bundle"]
    _require(job["program"] in ("psiblast", "deltablast"), kind, "/source_context/original_job/program")
    for name, expected in (("execution_program", job["program"]), ("scientific_mode", job["mode"]),
            ("query_kind", job["query"]["kind"]), ("reference_kind", "sequence"), ("request", bundle["requested_job"])):
        _require(inv[name] == expected, kind, "/collection/invocation/" + name)
    _require(inv["completion"]["native_returncode"] in (None, bundle["process"]["returncode"]),
        kind, "/collection/invocation/completion/native_returncode")
    for i, operand in enumerate(inv["operands"]):
        _operand_relations(operand, kind, f"/collection/invocation/operands/{i}")
    for name, key in (("artifacts", "artifact_key"), ("searches", "search_key")):
        ids = [_json_bytes(row[key]) for row in collection[name]]
        _require(len(ids) == len(set(ids)), kind, "/collection/" + name)


def _selections(context):
    job, bundle = context["original_job"], context["bundle"]
    report = next(r for r in job["outputs"] if r["role"] == "primary_report")
    query = next(r for r in job["inputs"] if r["input_key"] == job["query"]["input_key"])
    output = next(r for r in bundle["output_manifest"] if r["output_key"] == report["output_key"])
    input_ = next((r for r in bundle["input_manifest"] if r["input_key"] == query["input_key"]), None)
    keys = dict(report=output["artifact_keys"][0] if output["artifact_keys"] else None,
                query=input_["artifact_key"] if input_ is not None else None)
    captures = {r["artifact_key"]: r for r in bundle["artifacts"]}
    return report, query, {name: captures.get(key) for name, key in keys.items()}


def _issue(name, detail, *, artifact_key=None, input_key=None, indices=(), pointer=None):
    return dict(code=_PREFIX + name, pointer=pointer or "/query_binding", artifact_key=artifact_key,
        input_key=input_key, operand_indices=list(indices), detail_code=detail)


def _classify(collection, query_key, capture_key):
    candidates = [dict(operand_index=i, operand=o) for i, o in enumerate(collection["invocation"]["operands"]) if o["role"] == "query"]
    issues, addresses = [], {}
    for candidate_index, candidate in enumerate(candidates):
        index, operand = candidate["operand_index"], candidate["operand"]
        def add(detail, indices=(index,)):
            issues.append(_issue("query_operand_conflicting", detail, artifact_key=operand["artifact_key"],
                input_key=query_key, indices=indices, pointer=f"/query_binding/candidates/{candidate_index}/operand"))
        if operand["artifact_key"] is None or operand["record_ordinal"] is None:
            add("missing_operand_identity")
        if capture_key is not None and operand["artifact_key"] is not None and operand["artifact_key"] != capture_key:
            add("operand_artifact_conflict")
        address = _json_bytes([operand[k] for k in ("artifact_key", "record_ordinal", "selected_interval")])
        previous = addresses.setdefault(address, [])
        conflicting = [p["operand_index"] for p in previous if p["operand"] != operand]
        if conflicting:
            add("conflicting_operand_values", (*conflicting, index))
        previous.append(candidate)
    status = "zero" if not candidates else "conflicting" if issues else "unique" if len(candidates) == 1 else "multiple"
    if status in ("zero", "multiple"):
        issues.append(_issue("query_operand_" + status, "no_query_operand" if status == "zero" else "multiple_query_operands",
            artifact_key=capture_key, input_key=query_key, indices=[c["operand_index"] for c in candidates]))
    return dict(status=status, candidates=candidates, selected_operand_index=candidates[0]["operand_index"] if status == "unique" else None), issues


def _state(name, capture, selected, entries, contents):
    if capture is None:
        return dict(status="missing_capture", artifact_key=None, capture=None, catalog=None, supplied_bytes=None), [
            _issue(name + "_capture_missing", "capture_absent", input_key=selected.get("input_key"), pointer="/selected/" + name)]
    key = capture["artifact_key"]
    entry, raw = entries.get(key), contents.get(key)
    state = dict(status="available", artifact_key=key, capture={k: capture[k] for k in ("sha256", "size_bytes")},
        catalog={k: entry[k] for k in ("artifact_ref", "source_ref", "sha256", "size_bytes")} if entry is not None else None,
        supplied_bytes=_byte_identity(raw) if raw is not None else None)
    details = []
    if (entry is not None and any(entry[k] != capture[k] for k in _CAPTURE_FIELDS)
            or name == "query" and any(capture[k] != selected[k] for k in ("sha256", "size_bytes"))):
        details.append("catalog_identity_conflict")
    if raw is not None and (state["supplied_bytes"] != state["capture"] or entry is not None and
            any(state["supplied_bytes"][k] != entry[k] for k in ("sha256", "size_bytes"))):
        details.append("byte_identity_conflict")
    if details:
        state["status"] = "identity_conflict"
    elif entry is None or raw is None:
        state["status"] = "bytes_unavailable"
        details.append("bytes_absent")
    issues = [_issue(name + "_" + state["status"], detail, artifact_key=key, input_key=selected.get("input_key"),
        pointer="/selected/" + name) for detail in details]
    return state, issues


def bind_native_blast_database_convergence(*, original_job, bundle, attempt_identity,
        collection, artifact_catalog, artifact_contents):
    """Bind retained actual inputs, invoking 316 once only on the unique route."""
    context = {name: _copy(value, "input", "/" + name) for name, value in
        (("original_job", original_job), ("bundle", bundle), ("attempt_identity", attempt_identity))}
    # Preserve the existing producer validator's exact rejection and independent
    # attempt argument. This is qualification, never external authentication.
    _producer.validate_native_blast_database_bundle(context["bundle"], original_job=context["original_job"],
        attempt_identity=context["attempt_identity"])
    collection = _copy(collection, "input", "/collection")
    _context_collection(context, collection, "input")
    catalog = _copy(artifact_catalog, "input", "/artifact_catalog")
    _shape(catalog, _CATALOG, "input", "/artifact_catalog")
    entries = {}
    for i, entry in enumerate(catalog["entries"]):
        _require(entry["artifact_key"] not in entries, "input", f"/artifact_catalog/entries/{i}/artifact_key")
        _require(any(r["artifact_key"] == entry["artifact_key"] for r in context["bundle"]["artifacts"]),
            "input", f"/artifact_catalog/entries/{i}/artifact_key")
        _require(entry["path"].startswith("/") and "\x00" not in entry["path"], "input", f"/artifact_catalog/entries/{i}/path")
        entries[entry["artifact_key"]] = entry
    _require(type(artifact_contents) is dict, "input", "/artifact_contents")
    contents = {}
    for key, raw in artifact_contents.items():
        _require(type(key) is str and key in entries and type(raw) is bytes, "input", "/artifact_contents/" + _escape(key))
        contents[key] = raw
    report, query, captures = _selections(context)
    selected = dict(report_output_key=report["output_key"], query_input_key=query["input_key"])
    issues = []
    for name, descriptor in (("report", report), ("query", query)):
        selected[name], found = _state(name, captures[name], descriptor, entries, contents)
        issues.extend(found)
    binding, found = _classify(collection, query["input_key"], selected["query"]["artifact_key"])
    issues.extend(found)
    result = dict(schema="native_blast_database_convergence_binding_v1", invocation="not_invoked",
        source_context=context, selected=selected, query_binding=binding, issues=issues, extraction=None, extraction_artifact=None)
    if binding["status"] == "unique" and all(selected[k]["status"] == "available" for k in ("report", "query")):
        from .blast_native_iteration_records import extract_blast_tabular7_convergence
        rkey, qkey = (selected[k]["artifact_key"] for k in ("report", "query"))
        extraction = extract_blast_tabular7_convergence(contents[rkey], artifact_key=rkey, source_ref=entries[rkey]["source_ref"],
            original_job=context["original_job"], bundle=context["bundle"], attempt_identity=context["attempt_identity"],
            query_contents=contents[qkey], query_operand=collection["invocation"]["operands"][binding["selected_operand_index"]], collection=collection)
        result.update(invocation="invoked", extraction=extraction, extraction_artifact=_artifact_identity(extraction))
    return validate_native_blast_database_convergence_binding(result, collection=collection)


def _saved_input(state, *, name, capture, descriptor, issues):
    path = "/selected/" + name
    rows = [i for i in issues if i["pointer"] == path]
    expected_identity = {k: capture[k] for k in ("sha256", "size_bytes")} if capture is not None else None
    _require(state["artifact_key"] == (capture["artifact_key"] if capture is not None else None), "binding", path + "/artifact_key")
    _require(state["capture"] == expected_identity, "binding", path + "/capture")
    if capture is None:
        _require(state == dict(status="missing_capture", artifact_key=None, capture=None, catalog=None, supplied_bytes=None), "binding", path)
        expected = [_issue(name + "_capture_missing", "capture_absent", input_key=descriptor.get("input_key"), pointer=path)]
        _require(rows == expected, "binding", "/issues")
        return
    supplied, catalog = state["supplied_bytes"], state["catalog"]
    _require(supplied is None or catalog is not None, "binding", path + "/supplied_bytes")
    catalog_conflict = (catalog is not None and any(catalog[k] != expected_identity[k] for k in expected_identity)
        or name == "query" and any(descriptor[k] != expected_identity[k] for k in expected_identity))
    bytes_conflict = supplied is not None and (supplied != expected_identity or catalog is not None and
        any(supplied[k] != catalog[k] for k in supplied))
    details = [i["detail_code"] for i in rows]
    if state["status"] == "identity_conflict":
        # Owner differences in a catalog are diagnosed at fresh binding. Its
        # saved identity projection intentionally contains only byte/ref fields;
        # external frozen-artifact custody authenticates that retained diagnosis.
        _require(details in (["catalog_identity_conflict"], ["byte_identity_conflict"],
            ["catalog_identity_conflict", "byte_identity_conflict"]), "binding", "/issues")
        _require((not catalog_conflict or "catalog_identity_conflict" in details)
            and ("byte_identity_conflict" in details) == bytes_conflict, "binding", "/issues")
        _require(catalog is not None or catalog_conflict, "binding", path + "/catalog")
    else:
        _require(not catalog_conflict and not bytes_conflict, "binding", path)
        expected_status = "available" if catalog is not None and supplied is not None else "bytes_unavailable"
        _require(state["status"] == expected_status, "binding", path + "/status")
        details = [] if expected_status == "available" else ["bytes_absent"]
    expected = [_issue(name + "_" + state["status"], d, artifact_key=state["artifact_key"],
        input_key=descriptor.get("input_key"), pointer=path) for d in details]
    _require(rows == expected, "binding", "/issues")


def _saved_bytes(value, path, expected):
    try:
        raw = base64.b64decode(value["native_bytes_base64"], validate=True)
    except (ValueError, binascii.Error):
        _fail("binding", path + "/native_bytes_base64")
    _require(base64.b64encode(raw).decode("ascii") == value["native_bytes_base64"], "binding", path + "/native_bytes_base64")
    _require(_byte_identity(raw) == expected == {k: value[k] for k in ("sha256", "size_bytes")}, "binding", path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    _require(text == value["native_text"], "binding", path + "/native_text")
    return raw


def _saved_extraction(binding, collection, report_descriptor):
    extraction, context, selected = (binding[k] for k in ("extraction", "source_context", "selected"))
    _require(extraction["source_context"] == context, "binding", "/extraction/source_context")
    _require(binding["extraction_artifact"] == _artifact_identity(extraction), "binding", "/extraction_artifact")
    for name in ("report", "query"):
        _require(extraction[name]["artifact_key"] == selected[name]["artifact_key"], "binding", "/extraction/" + name + "/artifact_key")
    _require(extraction["query"]["input_key"] == selected["query_input_key"], "binding", "/extraction/query/input_key")
    _require(extraction["report"]["source_ref"] == selected["report"]["catalog"]["source_ref"], "binding", "/extraction/report/source_ref")
    for name in ("format", "fields", "delimiter"):
        _require(extraction["report"][name] == report_descriptor[name], "binding", "/extraction/report/" + name)
    raw = _saved_bytes(extraction["report"], "/extraction/report", selected["report"]["supplied_bytes"])
    _saved_bytes(extraction["query"], "/extraction/query", selected["query"]["supplied_bytes"])
    operand = collection["invocation"]["operands"][binding["query_binding"]["selected_operand_index"]]
    query = extraction["query"]["query_operand"]
    _require(query is None or query == operand, "binding", "/extraction/query/query_operand")
    markers, records, issues = (extraction[k] for k in ("markers", "convergence_records", "issues"))
    codes = {r["code"].removeprefix(_NATIVE_PREFIX) for r in issues}
    report_blocked = bool(codes & {"bundle_contract_rejected", "report_artifact_missing", "report_identity_conflict",
        "collection_artifact_conflict", "report_format_unsupported", "report_program_conflict", "report_version_missing",
        "report_version_unsupported", "report_encoding_invalid", "query_identity_conflict"})
    _require(query is None or extraction["query"]["record_count"] == 1, "binding", "/extraction/query/record_count")
    for i, issue in enumerate(issues):
        _require(issue["marker_index"] is None or issue["marker_index"] < len(markers), "binding", f"/extraction/issues/{i}/marker_index")
    marker_keys, previous_end = {}, 0
    for i, marker in enumerate(markers):
        path = f"/extraction/markers/{i}"
        start, end = marker["byte_span"]
        _require(previous_end <= start < end <= len(raw), "binding", path + "/byte_span")
        previous_end = end
        _require(marker["exact_text"].encode("utf-8") == raw[start:end], "binding", path + "/exact_text")
        _require((start == 0 or raw[start - 1:start] == b"\n") and marker["line_number"] == raw.count(b"\n", 0, start) + 1,
            "binding", path + "/line_number")
        token = json.dumps(["v1", context["bundle"]["identity"]["attempt_id"], selected["report"]["artifact_key"],
            extraction["report"]["sha256"], start, end], ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        expected_key = "blast-native-convergence:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        _require(marker["record_key"] == expected_key and expected_key not in marker_keys, "binding", path + "/record_key")
        marker_keys[expected_key] = i
        # 316 snapshots global/current-marker issues as each occurrence is emitted;
        # later marker-specific issues do not retroactively change earlier rows.
        expected_codes = list(dict.fromkeys(r["code"] for r in issues if r["marker_index"] in (None, i)))
        _require(marker["issue_codes"] == expected_codes, "binding", path + "/issue_codes")
        partial = _NATIVE_PREFIX + "marker_partial" in marker["issue_codes"]
        _require(marker["scope"] == ("query" if query is not None and not report_blocked and not partial else "unbound"),
            "binding", path + "/scope")
    seen, previous_index = set(), -1
    for i, record in enumerate(records):
        path = f"/extraction/convergence_records/{i}"
        key = record["record_key"]
        _require(key in marker_keys and key not in seen, "binding", path + "/record_key")
        marker_index = marker_keys[key]
        _require(marker_index > previous_index, "binding", path + "/record_key")
        previous_index = marker_index
        seen.add(key)
        marker = markers[marker_index]
        _require(_NATIVE_PREFIX + "marker_partial" not in marker["issue_codes"], "binding", path + "/record_key")
        _require(record["query_operand"] == (query if marker["scope"] == "query" else None), "binding", path + "/query_operand")
        _require(record["evidence"]["source"]["source_ref"] == extraction["report"]["source_ref"], "binding", path + "/evidence/source/source_ref")
        _require(record["evidence"]["original_record"] == extraction["report"]["native_text"], "binding", path + "/evidence/original_record")
    expected_records = [] if report_blocked else [m["record_key"] for m in markers
        if _NATIVE_PREFIX + "marker_partial" not in m["issue_codes"]]
    _require([r["record_key"] for r in records] == expected_records, "binding", "/extraction/convergence_records")
    incompatible = bool(codes & {"bundle_contract_rejected", "report_identity_conflict", "collection_artifact_conflict",
        "report_program_conflict", "query_identity_conflict", "query_operand_conflict"})
    scoped = any(m["scope"] == "query" for m in markers)
    expected_status = ("incompatible" if incompatible else
        "partial" if scoped and codes & {"source_partial", "native_failed", "marker_partial"} else
        "complete" if scoped else "unavailable")
    _require(extraction["status"] == expected_status, "binding", "/extraction/status")
    matching = [a for a in collection["artifacts"] if a["artifact_key"] == selected["report"]["artifact_key"]]
    expected_artifact = dict(artifact_key=selected["report"]["artifact_key"], role="primary_report",
        format=report_descriptor["format"], fields=None if report_descriptor["format"] == "json15" else report_descriptor["fields"],
        delimiter=report_descriptor["delimiter"], **selected["report"]["capture"])
    conflicts = [r for r in issues if r["code"] == _NATIVE_PREFIX + "collection_artifact_conflict" and
                 r["source_pointer"] == "/collection/artifacts"]
    _require(matching == [expected_artifact] or len(conflicts) == 1 and conflicts[0]["details"] == {"artifacts": matching},
        "binding", "/collection/artifacts")


def validate_native_blast_database_convergence_binding(binding, *, collection):
    """Validate and detach a saved binding without reinterpreting native bytes."""
    binding = _copy(binding, "binding", "")
    collection = _copy(collection, "binding", "/collection")
    _shape(binding, _BINDING, "binding", "")
    context = binding["source_context"]
    try:
        _producer.validate_native_blast_database_bundle(context["bundle"], original_job=context["original_job"],
            attempt_identity=context["attempt_identity"])
    except ValueError as error:
        raise ValueError(_PREFIX + "binding_invalid", "/source_context") from error
    _context_collection(context, collection, "binding")
    report, query, captures = _selections(context)
    selected = binding["selected"]
    for field, expected in (("report_output_key", report["output_key"]), ("query_input_key", query["input_key"])):
        _require(selected[field] == expected, "binding", "/selected/" + field)
    for name, descriptor in (("report", report), ("query", query)):
        _saved_input(selected[name], name=name, capture=captures[name], descriptor=descriptor, issues=binding["issues"])
    expected_binding, query_issues = _classify(collection, query["input_key"], selected["query"]["artifact_key"])
    _require(binding["query_binding"] == expected_binding, "binding", "/query_binding")
    input_issues = [r for name in ("report", "query") for r in binding["issues"] if r["pointer"] == "/selected/" + name]
    _require(binding["issues"] == input_issues + query_issues, "binding", "/issues")
    invoked = expected_binding["status"] == "unique" and all(selected[n]["status"] == "available" for n in ("report", "query"))
    _require(binding["invocation"] == ("invoked" if invoked else "not_invoked"), "binding", "/invocation")
    _require((binding["extraction"] is not None) == invoked, "binding", "/extraction")
    _require((binding["extraction_artifact"] is not None) == invoked, "binding", "/extraction_artifact")
    if invoked:
        _require(binding["issues"] == [], "binding", "/issues")
        _saved_extraction(binding, collection, report)
    return binding


__all__ = ["bind_native_blast_database_convergence", "validate_native_blast_database_convergence_binding"]
