"""Retain one selected BV-BRC Data result and its complete numerical grading.

The host supplies the persisted preparation and already custody-qualified input
pages/metadata. This module performs no acquisition, source discovery, episode
action, observation publication or credit calculation. Native parsers and the
separate deterministic calculators retain their own responsibilities.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .library.bvbrc_data_calculators import calculate_facet_fractions, calculate_feature_sequence_counts, calculate_page_counts
from .library.bvbrc_data_feature_sequences import extract_feature_sequence_join
from .library.bvbrc_data_fields import FIELD_REGISTRY
from .library.bvbrc_data_molecular import extract_molecular_experiment_rows
from .library.bvbrc_data_query import validate_data_query
from .library.bvbrc_data_readers import parse_data_snapshot, validate_data_sheet
from .library.bvbrc_data_schema import json_digest, validate
from .library.bvbrc_data_views import validate_data_result_selector
from .domain import ContractError, canonical, identity
from .tool_grading_artifacts import retain_tool_grading
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_projection_validation import _publication_inputs, requested_projection_failures


__all__ = ('publish_bvbrc_data',)

















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
