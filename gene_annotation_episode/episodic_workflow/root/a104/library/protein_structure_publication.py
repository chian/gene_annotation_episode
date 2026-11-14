"""Ordinary source and sequence publication for retained protein results.

Payload construction is pure; publication validates retained original bytes.
The result host separately authenticates capture and worker custody. A source's
auxiliary list preserves original files and grants no receiving episode access.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_acquisition import ProteinStructureCapture
from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_contracts import NativeProteinBundle, validate_protein_structure_bundle
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_contracts import validate_file_identity
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_result_worker import ProteinResultWorkerResult, validate_protein_structure_result_worker_result

def protein_structure_source_payload(*, bundle: NativeProteinBundle, capture: ProteinStructureCapture, worker_result: ProteinResultWorkerResult | None, request_ref: str | None=None) -> dict:
    """Build the single approved immutable payload from qualified actual files.

This checks the supplied metadata relationship. It does not acquire bytes or
establish original episode authority. Saved recalculation must use the original
source, rather than pass its later worker output to this function.
    """
    if capture['bundle_validated'] is not True or capture['original_plan'] is None or capture['bundle_file'] is None:
        raise ValueError('capture_incomplete')
    original = validate_protein_structure_bundle(bundle, plan=capture['original_plan'])
    bundle_file = validate_file_identity(capture['bundle_file'])
    if bundle_file['format'] != 'native_protein_structure_bundle_v1' or bundle_file['sha256'] != digest(original) or bundle_file['byte_length'] != len(canonical(original).encode('utf-8')):
        raise ValueError('input_digest_mismatch')
    references = []
    for row in capture['files']:
        if row['observed'] is not None:
            references.append(validate_file_identity(row['observed'])['artifact_ref'])
    if worker_result is not None:
        result = validate_protein_structure_result_worker_result(worker_result)
        operation = original['requested_job']['native_protein_structure']['request']['operation']
        if result['mode'] != 'original_native_result' or result['operation'] != operation:
            raise ValueError('original_commission_mismatch')
        for name in ('native_result_file', 'sheet_file', 'components_file'):
            if result[name] is not None:
                references.append(result[name]['file_identity']['artifact_ref'])
    return {'provider': 'episode.execution_result', 'accession': 'native_protein_structure_' + digest(original['identity']), 'uri': None, 'artifact_ref': bundle_file['artifact_ref'], 'text_ref': None, 'request_ref': request_ref, 'version': 'native_protein_structure_bundle_v1', 'retrieved_at': original['finished_at'], 'auxiliary_artifact_refs': list(dict.fromkeys(references))}
