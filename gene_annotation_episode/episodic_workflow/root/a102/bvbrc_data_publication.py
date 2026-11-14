"""Retain one selected BV-BRC Data result and its complete numerical grading.

The host supplies the persisted preparation and already custody-qualified input
pages/metadata. This module performs no acquisition, source discovery, episode
action, observation publication or credit calculation. Native parsers and the
separate deterministic calculators retain their own responsibilities.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .bvbrc_data_calculators import (
    calculate_facet_fractions, calculate_feature_sequence_counts, calculate_page_counts,
)
from .bvbrc_data_feature_sequences import extract_feature_sequence_join
from .bvbrc_data_fields import FIELD_REGISTRY
from .bvbrc_data_molecular import extract_molecular_experiment_rows
from .bvbrc_data_query import validate_data_query
from .bvbrc_data_readers import parse_data_snapshot, validate_data_sheet
from .bvbrc_data_schema import json_digest, validate
from .bvbrc_data_views import validate_data_result_selector
from .domain import ContractError, canonical, identity
from .tool_grading_artifacts import retain_tool_grading


__all__ = ("publish_bvbrc_data", "requested_projection_failures")

_NON_FAILURES = {"bvbrc_schema_observed_variant", "bvbrc_input_unavailable"}
_INVALID_REASONS = {
    "native_value_invalid", "unrepresentable_numeric_value", "conflicting_metadata",
    "ambiguous_join", "sequence_type_mismatch", "incompatible_input",
}


def _same(left, right):
    return json_digest(left) == json_digest(right)


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _unique(values):
    result, seen = [], set()
    for value in values:
        key = json_digest(value)
        if key not in seen:
            result.append(deepcopy(value))
            seen.add(key)
    return result


def _issue(code, *, row=None, field=None, path=None, phase="projection"):
    return {"code": code, "phase": phase, "row_index": row, "field": field,
            "native_path": path, "http_status": None}


def _publication_inputs(request, selector, value):
    _require(value is not None, "bvbrc_publication_inputs_required")
    inputs = validate("PublicationInputs", value)
    prepared = inputs["prepared"]
    _require(_same(prepared["original_request"], request), "bvbrc_publication_request_mismatch")
    _require(_same(prepared["page_selector"], selector["page"]), "bvbrc_publication_page_mismatch")
    selected = [{"collection": item["binding"]["collection"],
                 "source_ref": item["binding"]["source_ref"]} for item in inputs["input_results"]]
    _require(_same(selected, selector["inputs"]), "bvbrc_publication_input_selection_mismatch")
    _require(_same(inputs["supplied_metadata"], selector["supplied_metadata"]),
             "bvbrc_publication_metadata_selection_mismatch")
    for item in inputs["input_results"]:
        binding, sheet = item["binding"], validate_data_sheet(item["sheet"])
        _require(binding["collection"] == sheet["collection"]
                 and binding["native_sha256"] == sheet["custody"]["native_sha256"],
                 "bvbrc_publication_input_binding_mismatch")
        _require(sheet["mode"] == "page" and sheet["qualification"]["service_matches"]
                 and sheet["qualification"]["request_matches"]
                 and sheet["custody"]["native_profile"] == "solr_json_envelope_v1",
                 "bvbrc_publication_input_incompatible")
    expected = _unique([{"source_ref": item["provenance"]["source_ref"],
        "record_path": item["provenance"]["record_path"],
        "metadata_sha256": json_digest({key: child for key, child in item.items() if key != "provenance"})}
        for item in inputs["supplied_metadata"]])
    actual = [{key: item[key] for key in ("source_ref", "record_path", "metadata_sha256")}
              for item in inputs["metadata_bindings"]]
    _require(_same(expected, actual), "bvbrc_publication_metadata_binding_mismatch")
    return inputs


def _row_failures(row, fields):
    """Invalid selected values are failures; native absence remains an answer."""
    result = [issue for issue in row["issues"] if issue["code"] not in _NON_FAILURES
              and (issue["field"] is None or issue["field"] in fields)]
    for cell in row["cells"] + row["numerical_cells"]:
        if cell["field"] in fields and (cell["status"] in {"invalid", "unrepresentable"}
                or cell.get("reason") in _INVALID_REASONS):
            codes = [code for code in cell["issue_codes"] if code not in _NON_FAILURES]
            result.extend(_issue(code, row=row["row_index"], field=cell["field"],
                                 path=cell["native_path"]) for code in codes or ["bvbrc_invalid_native_field"])
    return result


def requested_projection_failures(grading: dict, *, input_results: list[dict]) -> list[dict]:
    """Qualify the selected output from saved data, without host admission.

    An accurate missing/unselected/zero value is a valid typed result. Invalid
    unrelated fields do not reject a narrower projection. Incomplete transport,
    wrong selected response and malformed requested values remain partial.
    This is an operational endpoint assessment, never scientific acceptance.
    """
    grading = validate("PublishedGrading", grading)
    selector = validate_data_result_selector(grading["selector"],
        request=grading["prepared"]["original_request"])
    inputs = _publication_inputs(grading["prepared"]["original_request"], selector, {
        "version": "bvbrc_data_publication_inputs_v1", "prepared": grading["prepared"],
        "input_results": input_results, "supplied_metadata": selector["supplied_metadata"],
        "metadata_bindings": grading["metadata_bindings"],
    })
    _require(_same(grading["input_bindings"], [item["binding"] for item in inputs["input_results"]]),
             "bvbrc_publication_input_binding_mismatch")
    parsed = grading["parse_result"]
    current = parsed["sheet"]
    _require(current is not None or parsed["status"] == "failed" and bool(parsed["failures"]),
             "bvbrc_publication_parse_failure_required")
    pages = ([] if current is None else [validate_data_sheet(current)]) + [
        item["sheet"] for item in inputs["input_results"]]
    failures = list(parsed["failures"]) if current is None else []
    for page in pages:
        failures.extend(issue for issue in page["issues"]
            if issue["row_index"] is None and issue["code"] not in _NON_FAILURES)
        if not page["transport"]["body_complete"] and not any(
                issue["code"] == "bvbrc_response_body_incomplete" for issue in page["issues"]):
            failures.append(_issue("bvbrc_response_body_incomplete", phase="transport"))

    projection = selector["projection"]
    family = projection["family"]
    if family == "collection_rows" and current is not None:
        fields = set(projection["numeric_fields"] + projection["metadata_fields"])
        fields.add(FIELD_REGISTRY[current["collection"]]["unique_key"])
        for row in current["rows"]:
            if row["row_index"] in projection["row_indices"]:
                failures.extend(_row_failures(row, fields))
    elif family == "feature_sequence":
        joined = grading["feature_sequence_sheet"]
        _require(joined is not None, "bvbrc_feature_sequence_sheet_required")
        for edge in joined["edges"]:
            fields = set(projection["feature_metadata_fields"])
            fields.update({"feature_id", "md5", "sequence", "sequence_type",
                edge["sequence_kind"].lower() + "_sequence_md5", edge["sequence_kind"].lower() + "_length"})
            failures.extend(issue for issue in edge["issues"] if issue["code"] not in _NON_FAILURES
                and (issue["field"] is None or issue["field"] in fields))
            if edge["join_status"] in {"conflict", "type_mismatch"}:
                failures.append(_issue("bvbrc_join_conflict", phase="join"))
            for page in pages:
                selected = {location["row_key"] for location in edge["feature_rows"] + edge["sequence_rows"]
                            if location["collection"] == page["collection"]
                            and location["native_sha256"] == page["custody"]["native_sha256"]}
                for row in page["rows"]:
                    if row["row_key"] in selected:
                        failures.extend(_row_failures(row, fields))
    elif family == "molecular_experiment":
        molecular = grading["molecular_sheet"]
        _require(molecular is not None, "bvbrc_molecular_sheet_required")
        selected_metadata = {(item["source_level"], item["field"]) for item in projection["metadata_fields"]}
        for row in molecular["rows"]:
            identity_fields = {"id", "exp_id", "bioset_id", "feature_id", "entity_id"}
            fields = identity_fields | set(projection["measurement_fields"]) | {
                field for level, field in selected_metadata if level == "result"}
            failures.extend(issue for issue in row["issues"] if issue["code"] not in _NON_FAILURES
                and (issue["field"] is None or issue["field"] in fields))
            if row["relationship_status"] == "conflict":
                failures.append(_issue("bvbrc_join_conflict", phase="join"))
            for cell in row["measurements"]:
                if cell["field"] in projection["measurement_fields"] and (
                        cell["status"] == "invalid" or cell["reason"] in _INVALID_REASONS
                        or "bvbrc_join_conflict" in cell["issue_codes"]):
                    failures.append(_issue("bvbrc_join_conflict" if "bvbrc_join_conflict" in cell["issue_codes"]
                        else "bvbrc_invalid_native_field", field=cell["field"], path=cell["native_path"]))
            for metadata in row["metadata"]:
                if ((metadata["source_level"], metadata["field"]) in selected_metadata
                        and (metadata["status"] == "conflict" or metadata["reason"] in _INVALID_REASONS)):
                    # Supplied fields are outside the native Issue.field enum;
                    # their exact locations remain in the molecular sheet.
                    native_field = metadata["field"] if metadata["source_level"] != "supplied" else None
                    failures.append(_issue("bvbrc_join_conflict" if metadata["status"] == "conflict"
                        else "bvbrc_invalid_native_field", field=native_field, phase="join"))
    return [validate("Issue", issue) for issue in _unique(failures)]


def publish_bvbrc_data(tools, *, request, selector, snapshot,
                       publication_inputs, scope, operation_key) -> dict:
    """Publish supplied native bytes, full grading and one source record.

    The caller has already validated input receipt, scope and receiver custody.
    Structural cross-checks below do not confer that host authority. No source
    is looked up to discover or supplement the explicitly supplied inputs.
    """
    request = validate_data_query(request)
    selector = validate_data_result_selector(selector, request=request)
    inputs = _publication_inputs(request, selector, publication_inputs)
    prepared = inputs["prepared"]
    parsed = parse_data_snapshot(snapshot, prepared=prepared)
    sheet = parsed["sheet"]
    grading = {"version": "bvbrc_data_grading_v1", "prepared": prepared,
        "selector": selector, "parse_result": parsed,
        "page_components": None if sheet is None else calculate_page_counts(sheet),
        "facet_components": None if sheet is None or sheet["mode"] != "facet" else
            calculate_facet_fractions(sheet, denominator_policy="same_response_exact_document_count"),
        "feature_sequence_sheet": None, "feature_sequence_components": None, "molecular_sheet": None,
        "input_bindings": [item["binding"] for item in inputs["input_results"]],
        "metadata_bindings": inputs["metadata_bindings"]}
    pages = ([] if sheet is None else [sheet]) + [item["sheet"] for item in inputs["input_results"]]

    def collection(name):
        return [page for page in pages if page["collection"] == name]

    projection = selector["projection"]
    if projection["family"] == "feature_sequence":
        joined = extract_feature_sequence_join(collection("genome_feature"), collection("feature_sequence"),
            feature_ids=projection["feature_ids"], sequence_kind=projection["sequence_kind"])
        grading["feature_sequence_sheet"] = joined
        grading["feature_sequence_components"] = calculate_feature_sequence_counts(joined)
    elif projection["family"] == "molecular_experiment":
        grading["molecular_sheet"] = extract_molecular_experiment_rows(collection("bioset_result"),
            bioset_pages=collection("bioset"), experiment_pages=collection("experiment"),
            feature_pages=collection("genome_feature"), result_ids=projection["result_ids"],
            supplied_metadata=inputs["supplied_metadata"])
    grading = validate("PublishedGrading", grading)
    failures = requested_projection_failures(grading, input_results=inputs["input_results"])
    store = tools.store
    store.validate_scope(scope)
    with store.transaction():
        artifact = store.artifact(snapshot.content, snapshot.media_type)
        snapshot_record = asdict(snapshot)
        snapshot_record.pop("content")
        snapshot_record.update(content_ref=artifact, sha256=snapshot.sha256, prepared=prepared)
        request_ref = store.artifact(canonical(snapshot_record), "application/json")
        grading_ref = retain_tool_grading(store, provider="bvbrc_data",
            native_artifact_ref=artifact, grading=grading)
        body = {"provider": "bvbrc_data", "accession": None, "uri": snapshot.url,
            "artifact_ref": artifact, "text_ref": None, "request_ref": request_ref,
            "version": None, "retrieved_at": snapshot.retrieved_at,
            "auxiliary_artifact_refs": [grading_ref]}
        source_ref = identity("source", {"origin": "external", "record": body})
        try:
            store.get(source_ref)
            existed = True
        except ContractError as error:
            if str(error) != "unknown_reference":
                raise
            existed = False
        source = store.put("source", body, origin="external")
    return {"status": "partial" if failures else "completed", "operation_ref": identity("operation", {
        "key": operation_key, "service": "bvbrc_data", "request": prepared["effective_request"],
        "snapshot_sha256": snapshot.sha256}),
        "record_refs": [source["id"]], "changed_record_refs": [] if existed else [source["id"]],
        "result": {"source_ref": source["id"], "raw_artifact_ref": artifact,
            "grading_artifact_ref": grading_ref, "collection": request["collection"], "mode": request["mode"],
            "parse_status": parsed["status"], "qualification": None if sheet is None else sheet["qualification"],
            "requested_projection_complete": not failures, "projection_failures": failures},
        "feedback": None if not failures else {"category": "representation",
            "code": "bvbrc_data_result_partial", "failures": failures}}
