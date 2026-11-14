"""A105 original ITC prepared-result publication; no worker or catalog setup."""
from datetime import datetime, timezone
import json
from .domain import canonical
from gene_annotation_episode.domain import ContractError
from .assay_artifact_custody import _publication_bytes
from .itc_binding_tool_values import (ITC_TOOL, RESULT_VERSION, _validate_result, _worker_request, project_itc_tool_result)

def partial_itc_publication(registry, prepared):
    """Expose only already-retained scientific outputs after a projection error."""
    from .tool_grading_artifacts import source_tool_grading_entries
    rows, references = [], []
    for reference in registry._written:
        source = registry.store.get(reference)
        if source.get("provider") != ITC_TOOL or source.get("version") != RESULT_VERSION:
            continue
        native = source["artifact_ref"]
        value = _validate_result(json.loads(registry.store.get_artifact(native)), _worker_request(prepared["request"]))
        entries = source_tool_grading_entries(registry.store, reference)
        if len(entries) != 1 or canonical(entries[0]["grading"]) != canonical(dict(sheet=value["sheet"], scores=value["components"])):
            raise ContractError("ordinary_itc_partial_publication_conflict")
        observation = value["sheet"]["fit_observation"]
        rows.append(dict(source_ref=reference, native_file=dict(artifact_ref=native, format="json"),
            grading_ref=entries[0]["artifact_ref"], fit_call_state=None if observation is None else observation["call_state"],
            fit_call_count=None if observation is None else observation["call_count"], fit_call_scope="retained_fit_observation"))
        references.extend((reference, native, entries[0]["artifact_ref"]))
    if not rows:
        raise ContractError("ordinary_itc_partial_scientific_source_missing")
    return dict(version="ordinary_itc_partial_values_v1", mode=prepared["request"]["arguments"]["mode"],
        projection_state="unavailable", retained_sources=rows), list(dict.fromkeys(references))

def retain_itc_publication(registry, prepared):
    """Retain an owned worker's validated output through one publication path."""
    from .materials import artifact_file
    from .tool_grading_artifacts import retain_tool_grading
    tool_name = ITC_TOOL
    result_version, control_version, prefix = RESULT_VERSION, "ordinary_itc_publication_v1", "ordinary_itc_"
    work, stored, item = prepared["work"], prepared["stored"], prepared["item"]
    native = artifact_file(registry.store, work.output_path, "application/json")
    if canonical(json.loads(_publication_bytes(registry.store, native))) != canonical(stored):
        raise ContractError(prefix + "native_capture_conflict")
    grading = retain_tool_grading(registry.store, provider=tool_name, native_artifact_ref=native,
        grading=dict(sheet=stored["sheet"], scores=stored["components"]))
    controls = registry.store.artifact(canonical(dict(version=control_version,
        request=prepared["request"], native_artifact_ref=native,
        execution_selection=json.loads((work.output_path.parent / "execution-selection.json").read_bytes()),
        native_handle=json.loads((work.output_path.parent / "native-handle.json").read_bytes()),
        execution=work.metadata)), "application/json")
    source = registry._put("source", dict(provider=tool_name, accession=None, uri=None,
        artifact_ref=native, text_ref=None, request_ref=controls, version=result_version,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[item["witness"]["reference"]] if item["witness"]["namespace"] == "source" else [],
        auxiliary_artifact_refs=[grading]), origin="tool")
    return dict(source=source, native_artifact_ref=native, grading_ref=grading)

def publish_itc_work(registry, arguments, prepared):
    if arguments["mode"] == "read_stored":
        projection = prepared["projection"]
        return projection, [projection["source_ref"], projection["native_file"]["artifact_ref"], projection["grading_ref"]]
    publication = retain_itc_publication(registry, prepared)
    projection = project_itc_tool_result(prepared["stored"], selection=arguments,
        source_ref=publication["source"]["id"], artifact_ref=publication["native_artifact_ref"],
        grading_ref=publication["grading_ref"])
    return projection, [publication["source"]["id"], publication["native_artifact_ref"], publication["grading_ref"]]

