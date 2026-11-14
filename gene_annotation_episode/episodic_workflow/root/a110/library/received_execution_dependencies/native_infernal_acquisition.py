from __future__ import annotations
from pathlib import PurePosixPath
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy, native_infernal_digest
VERSION = 'native_infernal_capture_v1'
PROVIDER = 'episode.execution_result'
ORIGIN = {'content_location': 'retained_complete_producer_bundle', 'attempt_output_version': 'original_producer_manifest_and_verified_file_digests', 'window_consistency': 'complete_files_matched_to_original_manifest', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
_CAPTURE_FIELDS = {'version', 'bundle_artifact_ref', 'bundle_validated', 'artifacts', 'invalid_artifacts', 'failures', 'complete'}
_ROW_FIELDS = {'role', 'format', 'relative_path', 'artifact_ref'}

def is_native_infernal_target(target):
    """Recognize the explicit request branch, without claiming an HPC binding."""
    return isinstance(target, dict) and target.get('resource_kind') in ('local', 'hpc') and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_infernal' in target['assignment']['requested_job'])

def _path(value, *, absolute=False):
    if type(value) is not str or not value or any((c in value for c in ('\x00', '\n', '\r', '\\'))) or value.startswith('//') or ('..' in value.split('/')) or (value in {'.', '/'}):
        raise ContractError('native_infernal_capture_path_invalid')
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        raise ContractError('native_infernal_capture_path_invalid')
    return path

def _shape(capture):
    capture = finite_json_copy(capture)
    if type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture['version'] != VERSION or (type(capture['bundle_validated']) is not bool) or (type(capture['complete']) is not bool) or (capture['bundle_artifact_ref'] is not None and type(capture['bundle_artifact_ref']) is not str) or any((type(capture[key]) is not list for key in ('artifacts', 'invalid_artifacts', 'failures'))):
        raise ContractError('native_infernal_capture_receipt_invalid')
    for row in capture['artifacts'] + capture['invalid_artifacts']:
        if type(row) is not dict or set(row) != _ROW_FIELDS or any((type(v) is not str or not v for v in row.values())):
            raise ContractError('native_infernal_capture_artifact_row_invalid')
        _path(row['relative_path'])
    for row in capture['failures']:
        if type(row) is not dict or set(row) != {'stage', 'code', 'record_key'} or row['stage'] != 'capture' or (type(row['code']) is not str) or (not row['code']) or (row['record_key'] is not None):
            raise ContractError('native_infernal_capture_failure_invalid')
    return capture

def original_source_payload(*, bundle, capture, prepared):
    """Stable original-attempt source; projection/page selection is not identity."""
    bundle, capture = (finite_json_copy(bundle), _shape(capture))
    if not capture['bundle_validated'] or capture['bundle_artifact_ref'] is None or type(bundle) is not dict or (bundle.get('version') != 'native_infernal_bundle_v1'):
        raise ContractError('native_infernal_source_validated_manifest_required')
    auxiliary = [row['artifact_ref'] for row in capture['artifacts'] + capture['invalid_artifacts']]
    if prepared is not None and prepared.get('source_grading_artifact_ref') is not None:
        auxiliary.append(prepared['source_grading_artifact_ref'])
    if any((type(ref) is not str or not ref for ref in auxiliary)):
        raise ContractError('native_infernal_source_artifact_reference_invalid')
    return {'provider': PROVIDER, 'accession': 'native_infernal_' + native_infernal_digest(bundle['identity']), 'uri': None, 'artifact_ref': capture['bundle_artifact_ref'], 'text_ref': None, 'request_ref': None, 'version': 'native_infernal_bundle_v1', 'retrieved_at': bundle['finished_at'], 'auxiliary_artifact_refs': sorted(set(auxiliary))}
