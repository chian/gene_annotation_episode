"""Capture the sealed outputs of one original, explicitly selected attempt.

These functions acquire bytes only. They choose no job, resource, parser,
retry or continuation. Complete immutable captures feed the separate graders.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest
PROVIDER = 'episode.execution_result'
ORIGIN = {'content_location': 'retained_complete_producer_bundle', 'attempt_output_version': 'original_producer_manifest_and_verified_file_digests', 'window_consistency': 'complete_files_matched_to_original_manifest', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

def is_native_hmmer_target(target):
    return target.get('resource_kind') in {'local', 'hpc'} and 'native_hmmer' in target.get('assignment', {}).get('requested_job', {})

def original_source_payload(*, bundle, capture, prepared):
    """Stable source content independent of acquisition page/metric selection."""
    reference = capture['bundle_artifact_ref']
    auxiliary = [row['artifact_ref'] for row in capture['artifacts']]
    auxiliary += [row['artifact_ref'] for row in capture['invalid_artifacts']]
    if prepared is not None and prepared.get('source_grading_artifact_ref') is not None:
        auxiliary.append(prepared['source_grading_artifact_ref'])
    return {'provider': PROVIDER, 'accession': 'native_hmmer_' + digest(bundle['identity']), 'uri': None, 'artifact_ref': reference, 'text_ref': None, 'request_ref': None, 'version': 'native_hmmer_bundle_v1', 'retrieved_at': bundle['finished_at'], 'auxiliary_artifact_refs': sorted(set(auxiliary))}
