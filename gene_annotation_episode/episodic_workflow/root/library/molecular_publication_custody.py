"""Original retained molecular bytes and scientific publication custody.

The selected publisher keeps its original domain dispatch and ITC fallback.
Artifact identity, grading publication and control receipts remain coupled.
"""
from datetime import datetime, timezone
import hashlib
import json

from gene_annotation_episode.domain import ContractError, canonical
from .molecular_action_custody import _publication_profile


def _publication_bytes(store, reference):
    """Verify the original artifact ID, metadata and complete retained bytes."""
    from gene_annotation_episode.native_file_capture import NativeFileCaptureError, _metadata
    metadata = _metadata(store, reference)
    # This is an authenticated producer's internal read. Model-facing material
    # access has separate File permissions; no such permission is conferred here.
    raw = store.get_artifact(reference)
    if len(raw) != metadata["size"] or hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise NativeFileCaptureError("retained_artifact_mismatch")
    return raw


def retain_molecular_publication(registry, prepared, *, tool_name):
    """Retain an owned worker's validated output through one publication path."""
    if tool_name == "predict_protein_disorder_regions":
        from gene_annotation_episode.episodic_workflow.root.library.protein_disorder_tools import _retain_protein_disorder_publication
        return _retain_protein_disorder_publication(registry, prepared)
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        from gene_annotation_episode.episodic_workflow.root.library.arsenic_speciation_tools import _retain_arsenic_speciation_publication
        return _retain_arsenic_speciation_publication(registry, prepared)
    if tool_name == "analyze_protease_kinetics":
        from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_tools import _retain_protease_kinetics_publication
        return _retain_protease_kinetics_publication(registry, prepared)
    if tool_name == "result.variants.vcf":
        from gene_annotation_episode.episodic_workflow.root.library.vcf_result_tools import _retain_vcf_result_publication
        return _retain_vcf_result_publication(registry, prepared)
    if tool_name == "analyze_cas9_mutation_outcomes":
        from gene_annotation_episode.episodic_workflow.root.library.reference_edit_outcome_tools import _retain_reference_edit_outcome_publication
        return _retain_reference_edit_outcome_publication(registry, prepared)
    from gene_annotation_episode.materials import artifact_file
    from gene_annotation_episode.episodic_workflow.root.library.tool_grading_artifacts import retain_tool_grading
    result_version, control_version, _, prefix = _publication_profile(tool_name)
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


