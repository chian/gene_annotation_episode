"""Engineered AppService artifact bundle; the caller's adapter contract supplies its parameters version and form."""
from copy import deepcopy
import hashlib
from .annotation_native_fixtures import encoded, gto

def arguments(*, data=None, raw=None):
    data = gto() if data is None else data
    data = deepcopy(data)
    if "analysis_events" in data and type(data["analysis_events"]) is list and data["analysis_events"]:
        data["analysis_events"][0]["success"] = 1
    raw = encoded(data) if raw is None else raw
    sha = hashlib.sha256(raw).hexdigest()
    source = "source_" + "a" * 24
    task = {"resource_id": "engineered-appservice", "task_id": "engineered-task",
        "required_application_id": "GenomeAnnotation", "native_application_id": "GenomeAnnotation",
        "submitted_parameters": {"scientific_name": "engineered fixture"},
        "submitted_start_parameters": {}, "scheduler_returned_parameters": None,
        "effective_parameters": None, "submission_receipt_ref": "source_" + "b" * 24,
        "submission_operation_key": "engineered:original:0", "submission_source_ref": "source_" + "c" * 24}
    artifact = {"role": "caller_selected_gto", "source_ref": source,
        "raw_artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(raw),
        "workspace_object": {"path": "/engineered/output.genome", "uuid": "engineered-output-object",
            "type": "genome", "metadata_receipt_ref": "source_" + "d" * 24},
        "task_association": {"kind": "task_info_object", "evidence_ref": "source_" + "e" * 24,
            "pointer": "/result_files/0", "task_id": task["task_id"],
            "output_path": "/engineered/output.genome", "output_uuid": "engineered-output-object",
            "byte_version_status": "current_bytes_observed", "version_evidence": []},
        "transfer": {"receipt_ref": source, "body_complete": True, "requested_range": None,
            "observed_range": None, "total_size": len(raw), "object_complete": "yes"},
        "declared_format": {"format": "gto", "version": None, "mode": None,
            "producer_source_ref": None, "transformation_evidence": []}, "requirement_ids": ["native-genome"]}
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task,
        "artifacts": [artifact], "input_bindings": [], "query_bindings": [],
        "supplied_scientific_metadata": [], "supplied_contents": [],
        "acquisition_receipt_refs": [source], "requested_selector_sha256": "f" * 64,
        "status": "ok", "missing_requirements": [], "diagnostics": []}
    parameters = {"analysis_id": "selected-engineered-annotation",
        "application_id": "GenomeAnnotation", "documents": [{"document_id": "genome",
            "requirement_id": "native-genome", "representation": "gto"}]}
    return {"bundle": bundle, "artifact_bytes": {artifact["raw_artifact_ref"]: raw}, "supplied_values": [],
        "parameters": parameters}
