"""Publish supplied Rfam results, full numerical data and a requested view.

The API episode supplies the original submission, selected response and handle.
This function performs no acquisition, polling, job lookup, observation creation
or credit calculation. Native bytes, the numerical sheet and its calculation
remain distinct retained artifacts with an acyclic source lineage.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import json

from .acquisition import SourceSnapshot
from .api_services import publish_existing_acquisition
from .domain import ContractError
from .execution_contracts import canonical
from .rfam_batch_alignment import parse_rfam_alignment_display
from .rfam_batch_contracts import (
    RFAM_CALCULATION_PARAMETERS, RFAM_ISSUE_CODES, finite_json_copy, make_issue,
    rfam_digest, validate_rfam_result_selector,
)
from .rfam_batch_grader import calculate_rfam_batch_components
from .rfam_batch_inputs import _metadata_bundle, populate_rfam_batch_json_sheet
from .rfam_batch_views import project_rfam_batch_result


__all__ = ["publish_rfam_batch_result", "validate_rfam_metadata_source_scope"]


def _snapshot_identity(snapshot):
    return {"service": snapshot.service, "url": snapshot.url,
        "request": snapshot.request, "retrieved_at": snapshot.retrieved_at,
        "content_sha256": snapshot.sha256, "media_type": snapshot.media_type,
        "transport": snapshot.transport}


def _strict_object(content, code="rfam_model_metadata_conflict"):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError(code)
            result[key] = value
        return result

    try:
        value = json.loads(content, object_pairs_hook=pairs)
        value = finite_json_copy(value, code=code)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ContractError(code) from error
    if type(value) is not dict:
        raise ContractError(code)
    return value


def validate_rfam_metadata_source_scope(store, reference, scope):
    """Read only source records/operand roots; never read artifact bytes.

    Store does not propagate source operand/parent roots into record_roots, so
    their explicit retained relationships must be checked as well. The return
    reader reuses this exact validation before trusting a metadata parent.
    """
    selected = store._require(reference, {"source"})
    allowed = set(store.validate_scope(scope)["subject_refs"])
    pending, seen = [selected], set()
    while pending:
        source = pending.pop()
        if source["id"] in seen:
            continue
        seen.add(source["id"])
        roots = set(store.roots(source["id"]))
        for operand in source.get("operand_refs", []):
            roots.update(store.roots(operand))
        if source.get("query_selection_ref") is not None:
            roots.update(store.roots(source["query_selection_ref"]))
        if not roots <= allowed:
            raise ContractError("rfam_subject_out_of_scope")
        pending.extend(store._require(ref, {"source"}) for ref in source.get("parent_source_refs", []))
    return selected


def _metadata(tools, reference, scope):
    """Read only the caller-selected source and verify its named custody."""
    if reference is None:
        return None
    code = "rfam_model_metadata_conflict"
    store = tools.store

    def source(ref):
        row = validate_rfam_metadata_source_scope(store, ref, scope)
        store.get_artifact(row["artifact_ref"])
        return row

    selected = source(reference)
    bundle = _metadata_bundle(_strict_object(store.get_artifact(selected["artifact_ref"])), [])
    if bundle is None:
        raise ContractError(code)
    for record in bundle["records"]:
        original = source(record["source_ref"])
        metadata = store.get(record["metadata_ref"])
        if metadata["record_type"] == "artifact":
            allowed = [original["artifact_ref"], *original.get("auxiliary_artifact_refs", [])]
            if metadata["id"] not in allowed:
                raise ContractError(code)
            store.get_artifact(metadata["id"])
        elif metadata["id"] != original["id"] and metadata.get("source_ref") != original["id"]:
            raise ContractError(code)
    for binding in bundle["bindings"]:
        evidence = source(binding["evidence_source_ref"])
        # A real pointer proves only the supplied locator, never that accession
        # equality establishes the searched model's release or full length.
        try:
            _pointer(_strict_object(store.get_artifact(evidence["artifact_ref"])),
                     binding["evidence_json_pointer"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ContractError(code) from error
    return bundle


def _optional_metadata(tools, reference, scope):
    """Qualify optional metadata without sacrificing the acquired result.

    The selected source joins lineage only after its record type and scope are
    checked. An unknown/out-of-scope reference remains in the original selector
    and diagnostic; its bytes are never read.
    """
    if reference is None:
        return None, None, None
    retained, field = None, "model_metadata_ref"
    try:
        validate_rfam_metadata_source_scope(tools.store, reference, scope)
        retained, field = reference, "model_metadata"
        return _metadata(tools, reference, scope), retained, None
    except (ValueError, KeyError, TypeError, OSError) as error:
        code = ("rfam_subject_out_of_scope" if str(error) == "rfam_subject_out_of_scope" else
            "rfam_source_identity_conflict" if isinstance(error, OSError) or str(error) in {
                "artifact_digest_mismatch", "unknown_artifact"} else "rfam_model_metadata_conflict")
        return None, retained, make_issue(code, "metadata", field=field)


def _metadata_diagnostic(parsed, failure):
    if failure is None:
        return parsed
    shared = parsed["version"] == "rfam_batch_parse_result_v2"
    if parsed["version"] == "rfam_batch_tblout_parse_result_v1" or shared and parsed["representation"] == "tblout":
        parsed["issues"].append({"code": "rfam_batch_model_metadata_invalid", "severity": "error",
            "field": "model_metadata_ref" if failure["field"] == "model_metadata_ref" else "supplied_model_metadata",
            "native_query_name": None, "source_line": None})
        if shared and parsed["sheet"] is not None:
            parsed["sheet"]["issues"].append(deepcopy(parsed["issues"][-1]))
            for row in parsed["sheet"]["hits"]:
                row["source_details"]["missing"].update(model_length_positions="model_metadata_conflict",
                    model_coverage_fraction="model_metadata_conflict")
    else:
        parsed["issues"].append(deepcopy(failure))
        if parsed["sheet"] is not None:
            sheet = parsed["sheet"]
            sheet["issues"].append(deepcopy(failure))
            for row in sheet["hits"]:
                details = row["source_details"] if shared else row
                details["missing"].update(model_length_positions="model_metadata_conflict",
                    model_coverage_fraction="model_metadata_conflict")
                issue = make_issue(failure["code"], "metadata", hit_key=row["hit_id" if shared else "hit_key"],
                    field="model_length_positions")
                row["issues"].append(issue)
                sheet["issues"].append(deepcopy(issue))
                parsed["issues"].append(deepcopy(issue))
    if parsed["status"] == "complete":
        parsed["status"] = "partial"
    if shared and parsed["sheet"] is not None and parsed["sheet"]["status"] in {"available", "complete"}:
        parsed["sheet"]["status"] = "partial"
    return parsed


def _pointer(value, pointer):
    if type(pointer) is not str or not pointer.startswith("/"):
        raise ContractError("rfam_projection_reference_conflict")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if type(value) is list else value[token]
    return value


def _unavailable(code, *, format="unrecognized", status="unsupported"):
    return {"version": "rfam_batch_parse_result_v1", "status": status,
        "format": format, "sheet": None, "issues": [make_issue(code)]}


def _json_parse(snapshot, identity, capture, metadata):
    initial = populate_rfam_batch_json_sheet(snapshot.content,
        input_identity=identity, capture=capture, model_metadata=metadata)
    if initial["sheet"] is None:
        return initial
    # The native parser already rejected duplicate keys, invalid JSON and
    # document identity conflicts. Resolve each exact validated row pointer.
    native = json.loads(snapshot.content)
    alignments = []
    shared = initial["version"] == "rfam_batch_parse_result_v2"
    for row in initial["sheet"]["hits"]:
        details = row["source_details"] if shared else row
        strand = row["strand"] if shared else row["native"]["strand"]
        if not details["identity_valid"] or strand not in ("+", "-"):
            continue
        raw = _pointer(native, details["native_json_pointer"])
        if raw.get("alignment") is None:
            continue
        alignments.append(parse_rfam_alignment_display(raw["alignment"],
            hit_identity={"artifact_ref": capture["artifact_ref"], "hit_key": row["hit_id" if shared else "hit_key"],
                "query_occurrence_key": row["query_occurrence_key"],
                "family_accession": row["model"]["accession"] if shared else row["family_accession"]},
            query_sequence=identity["submitted_sequence"],
            native_start=row["sequence_from"] if shared else row["native"]["start"],
            native_end=row["sequence_to"] if shared else row["native"]["end"], native_strand=strand))
    return populate_rfam_batch_json_sheet(snapshot.content,
        input_identity=identity, capture=capture, model_metadata=metadata,
        alignment_components={"version": "rfam_alignment_components_bundle_v1",
            "artifact_ref": capture["artifact_ref"], "source_sha256": capture["source_sha256"],
            "rows": alignments})


def _projection_issue(issue):
    """Keep specific closed native codes, with source lines as line locators."""
    if "scope" in issue:
        return deepcopy(issue)
    from .rfam_batch_table import RFAM_BATCH_TABLE_ISSUE_CODES
    if issue["code"] not in RFAM_BATCH_TABLE_ISSUE_CODES:
        raise ContractError("rfam_projection_reference_conflict")
    return {"code": issue["code"], "scope": "document", "hit_key": None,
        "field": issue["field"], "source_pointer":
            None if issue["source_line"] is None else "line:" + str(issue["source_line"])}


def _report_projection_issue(issue, sheet=None):
    """Map a report diagnostic without inventing JSON pointers or row joins.

    The full native diagnostic, including severity and query name, stays in
    parse/sheet artifacts. A hit reference is added only for one exact retained
    query-and-source-line association; query-level issues remain unbound.
    """
    from .rfam_batch_report_contracts import RFAM_REPORT_ISSUE_CODES
    from .rfam_batch_contracts import closed_object, is_int, is_text

    code = "rfam_projection_reference_conflict"
    closed_object(issue, ("code", "severity", "field", "native_query_name", "source_line"), code=code)
    if (issue["code"] not in RFAM_REPORT_ISSUE_CODES or issue["severity"] not in {"error", "warning"}
            or any(issue[key] is not None and not is_text(issue[key]) for key in ("field", "native_query_name"))
            or issue["source_line"] is not None and not is_int(issue["source_line"], minimum=1)):
        raise ContractError(code)
    shared = sheet is not None and sheet.get("schema") == "infernal_search_sheet_v2"
    hits = []
    for hit in [] if sheet is None else sheet["hits"]:
        details = hit["source_details"] if shared else hit
        query_name = hit["sequence"]["name"] if shared else hit["native_query_name"]
        if (issue["native_query_name"] is not None and query_name == issue["native_query_name"]
                and issue["source_line"] is not None and issue["source_line"] in (
                    details["score_line"], details["alignment_header_line"], details["alignment_summary_line"])):
            hits.append(hit)
    return {"code": issue["code"], "scope": "row" if issue["native_query_name"] is not None else "document",
        "hit_key": hits[0]["hit_id" if shared else "hit_key"] if len(hits) == 1 else None, "field": issue["field"],
        "source_pointer": None if issue["source_line"] is None else "line:" + str(issue["source_line"])}


def publish_rfam_batch_result(tools, *, request, selector, snapshot, scope,
        operation_key, submission_snapshot, handle):
    """Retain supplied original-operation artifacts and requested numerical rows.

    A valid unavailable cell and an accurately qualified partial population are
    deliverable typed facts. Rejected attribution, an unsupported projection,
    impossible selected keys and an incomplete acquisition remain partial.
    """
    from .api_rfam import RfamBatchService

    if not isinstance(submission_snapshot, SourceSnapshot):
        raise ContractError("rfam_original_handle_required")
    # A sentinel client makes the no-acquisition boundary explicit. Only the
    # existing local preparation and pure decoder are used here.
    service = RfamBatchService(tools, client=object())
    selector = validate_rfam_result_selector(selector)
    prepared = service.prepare("api.rfam.fetch", request, {}, scope=scope,
        previous_events=[], handle=handle, selector=selector)
    request = prepared["request"]
    received = service.decode(prepared, snapshot)
    submitted = service.prepare("api.rfam.submit", request, {}, scope=scope,
        previous_events=[])
    submission = service.decode(submitted, submission_snapshot)
    if not submission["handoff_ready"] or submission["native_handle"] != prepared["native_handle"]:
        raise ContractError("rfam_original_handle_conflict")
    evidence_kind = snapshot.transport.get("evidence_kind", "native_response")
    if evidence_kind not in {"native_response", "official_documentation_example", "synthetic_fixture"}:
        raise ContractError("rfam_capture_invalid")
    batch = request["mode"] == "sequence_batch"
    report = selector["version"] == "rfam_batch_result_selector_v3"
    arguments = {"request": request, "selector": selector, "handle": prepared["native_handle"],
        "submission": _snapshot_identity(submission_snapshot), "response": _snapshot_identity(snapshot)}

    def publisher():
        original = tools._source("rfam_batch", None, snapshot=submission_snapshot)
        source = tools._source("rfam_batch", None, snapshot=snapshot,
            parent_source_refs=[original["id"]])
        metadata, metadata_source, metadata_failure = _optional_metadata(
            tools, selector["model_metadata_ref"], scope)
        identity = {"version": "rfam_batch_file_input_v1" if batch else "rfam_batch_input_identity_v1",
            **deepcopy(snapshot.request["input_operand"]),
            "expected_job_id": prepared["native_handle"]["job_id"],
            "submission_source_ref": original["id"]}
        capture = {"artifact_ref": source["artifact_ref"], "source_ref": source["id"],
            "source_sha256": snapshot.sha256, "evidence_kind": evidence_kind,
            "representation": selector["representation"], "http_status": snapshot.transport["status"],
            "body_complete": snapshot.transport["body_complete"],
            "request_job_id": prepared["native_handle"]["job_id"]}
        acquisition_error = None
        if not received["result_available"] or not capture["body_complete"]:
            acquisition_error = received["failure_code"] or "rfam_response_unknown"
        if capture["http_status"] != 200:
            parsed = _unavailable(acquisition_error or "rfam_http_error", status="rejected")
        elif report:
            from .rfam_batch_report import populate_rfam_batch_report_sheet
            parsed = populate_rfam_batch_report_sheet(snapshot.content,
                input_identity=identity, capture={**capture,
                    "request_file_sha256": identity["submitted_file_sha256"],
                    "submission_source_ref": original["id"]},
                submitted_content=base64.b64decode(submission_snapshot.request["file_base64"], validate=True))
        elif batch and selector["representation"] == "tblout":
            from .rfam_batch_table import populate_rfam_batch_tblout_sheet
            parsed = populate_rfam_batch_tblout_sheet(snapshot.content,
                input_identity=identity, capture={**capture,
                    "request_file_sha256": identity["submitted_file_sha256"],
                    "submission_source_ref": original["id"]},
                submitted_content=base64.b64decode(submission_snapshot.request["file_base64"], validate=True),
                model_metadata=metadata)
        elif batch and selector["representation"] == "json":
            # Batch JSON has no query identity. Its order cannot supply one.
            parsed = _unavailable("rfam_multiple_sequences_schema_unestablished",
                format="rfam_multiple_sequences_json_untyped")
            try:
                native = _strict_object(snapshot.content, "rfam_json_invalid")
                if type(native.get("hits")) is not list or "opened" not in native:
                    parsed["format"] = "unrecognized"
            except ContractError:
                parsed = _unavailable("rfam_json_invalid", status="rejected")
        elif selector["representation"] == "json":
            parsed = _json_parse(snapshot, identity,
                {**capture, "request_sequence_sha256": identity["submitted_sequence_sha256"]}, metadata)
        else:
            # Single unheaded files have no generally proven table query-name
            # mapping. Reports stay separate artifacts, never JSON displays.
            parsed = _unavailable("rfam_text_format_unverified")

        parsed = _metadata_diagnostic(parsed, metadata_failure)
        sheet, calculation = parsed["sheet"], None
        if sheet is not None:
            if report:
                from .rfam_batch_report_grader import calculate_rfam_batch_report_components
                calculation = calculate_rfam_batch_report_components(sheet,
                    parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
            elif batch:
                from .rfam_batch_table_grader import calculate_rfam_batch_table_components
                calculation = calculate_rfam_batch_table_components(parsed,
                    parameters={"hit_scope": "reported"})
            else:
                calculation = calculate_rfam_batch_components(sheet,
                    parameters=deepcopy(RFAM_CALCULATION_PARAMETERS))
        store = tools.store
        parse_ref = store.artifact(canonical(parsed), "application/json")
        sheet_ref = None if sheet is None else store.artifact(canonical(sheet), "application/json")
        calculation_ref = None if calculation is None else store.artifact(canonical(calculation), "application/json")
        projection, errors = None, []
        if acquisition_error is not None:
            errors.append(make_issue(acquisition_error))
        if selector["projection"] is not None:
            if sheet is None:
                errors.extend((_report_projection_issue(issue) if report and "severity" in issue
                    else _projection_issue(issue)) for issue in parsed["issues"]
                    if issue.get("scope") != "metadata" and issue["code"] not in {
                        "rfam_batch_model_metadata_invalid", "rfam_batch_model_provenance_unverified"})
            else:
                bindings = {"source_ref": source["id"], "sheet_ref": sheet_ref,
                    "calculation_ref": calculation_ref, "sheet_digest": rfam_digest(sheet),
                    "calculation_digest": rfam_digest(calculation)}
                try:
                    if report:
                        from .rfam_batch_report_views import project_rfam_batch_report_result
                        projection = project_rfam_batch_report_result(sheet, calculation,
                            projection=selector["projection"], artifact_bindings=bindings)
                    elif batch:
                        from .rfam_batch_table_views import project_rfam_batch_table_result
                        projection = project_rfam_batch_table_result(parsed, calculation,
                            projection=selector["projection"], artifact_bindings=bindings)
                    else:
                        projection = project_rfam_batch_result(sheet, calculation,
                            projection=selector["projection"], artifact_bindings=bindings)
                except ContractError as error:
                    if str(error) not in RFAM_ISSUE_CODES:
                        raise
                    errors.append(make_issue(str(error), "projection", field="projection"))
                if report:
                    # Attribution failures are not repaired by accurately
                    # returning unavailable cells. Optional numerical missing
                    # values and qualified partial populations remain valid.
                    attribution_codes = {"rfam_batch_report_foreign_query", "rfam_batch_foreign_native_query",
                        "rfam_batch_report_length_conflict", "rfam_batch_report_name_ambiguous",
                        "rfam_batch_report_query_missing", "rfam_batch_report_query_invalid"}
                    errors.extend(_report_projection_issue(issue, sheet) for issue in parsed["issues"]
                        if issue["severity"] == "error" and issue["code"] in attribution_codes)
        errors = list({canonical(issue): issue for issue in errors}.values())
        result = {"source_ref": source["id"], "submission_source_ref": original["id"],
            "artifact_ref": source["artifact_ref"], "format": parsed["format"],
            "sheet_ref": sheet_ref, "calculation_ref": calculation_ref,
            "projection": projection, "projection_errors": errors}
        manifest = {"version": "rfam_batch_retained_grading_v1", "request": request,
            "selector": selector, **result, "input_identity": identity, "parse_ref": parse_ref}
        if parsed["version"] == "rfam_batch_parse_result_v2":
            manifest.update(version="rfam_batch_retained_grading_v2", parse_digest=rfam_digest(parsed),
                sheet_schema=None if sheet is None else sheet["schema"],
                sheet_digest=None if sheet is None else rfam_digest(sheet),
                calculation_schema=None if calculation is None else calculation["schema"],
                calculation_digest=None if calculation is None else rfam_digest(calculation))
        parents = [original["id"], source["id"]]
        if metadata_source is not None:
            parents.append(metadata_source)
        grading = tools._source("rfam_batch.grading", manifest,
            parent_source_refs=list(dict.fromkeys(parents)),
            auxiliary_artifact_refs=[ref for ref in (parse_ref, sheet_ref, calculation_ref) if ref is not None])
        result["grading_source_ref"] = grading["id"]
        return result, [original["id"], source["id"], grading["id"]]

    return publish_existing_acquisition(tools, "rfam.fetch", arguments, snapshot,
        scope, operation_key, publisher=publisher)
