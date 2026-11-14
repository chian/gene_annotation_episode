from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_contracts import issue, validate_rna_issue
VERSION = 'native_rna_structure_capture_v1'
PROVIDER = 'episode.execution_result'
ORIGIN = {'content_location': 'retained_complete_producer_bundle', 'attempt_output_version': 'original_producer_manifest_and_verified_file_digests', 'window_consistency': 'complete_files_matched_to_original_manifest', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
CAPTURE_FIELDS = {'version', 'bundle_artifact_ref', 'bundle_validated', 'artifacts', 'invalid_artifacts', 'absent_artifacts', 'failures', 'capture_complete'}
FILE_FIELDS = {'kind', 'role', 'format', 'relative_path', 'artifact_ref', 'sha256', 'size_bytes'}

def require(condition, code='rna_original_attempt_mismatch'):
    if not condition:
        raise ValueError(code)

def decode_json(raw, *, canonical_bytes=False):

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'rna_invalid_native_schema')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('rna_invalid_native_schema')
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
        encoded = (canonical(result) + '\n').encode()
        require(not canonical_bytes or raw == encoded, 'rna_invalid_native_schema')
        return result
    except (UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError('rna_invalid_native_schema') from error

def retained(store, reference):
    """Use the shared artifact verifier and check its complete metadata."""
    metadata = store._require(reference, {'artifact'})
    path = artifact_path(store, reference)
    require(reference == 'artifact_' + metadata['sha256'] and path.stat().st_size == metadata['size'], 'rna_capture_digest_mismatch')
    return (metadata, path)

def is_native_rna_structure_target(target):
    return isinstance(target, dict) and target.get('resource_kind') == 'local' and isinstance(target.get('assignment'), dict) and isinstance(target['assignment'].get('requested_job'), dict) and ('native_rna_structure' in target['assignment']['requested_job'])

def qualify_target_plan(target, plan):
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_contracts import validate_rna_structure_run_plan
    plan = validate_rna_structure_run_plan(plan)
    ident = plan['identity']
    require(is_native_rna_structure_target(target) and target['assignment']['requested_job'] == plan['requested_job'])
    require(all((target[left] == ident[right] for left, right in (('run_id', 'run_id'), ('origin_episode_id', 'episode_id'), ('resource_id', 'resource_id'), ('execution_id', 'execution_id'), ('request_sha256', 'requested_job_sha256')))))
    require(target['assignment'].get('resource_kind') == 'local' and target['assignment'].get('resource_id') == target['resource_id'])
    root = Path(target['assignment']['workspace']) / '.episode-operations' / digest({'run': ident['run_id'], 'episode': ident['episode_id']}) / digest(ident['operation_key'])
    require(Path(ident['execution_id']) == root / 'native.json')
    return plan

def validate_capture(store, capture, *, bundle=None):
    require(type(capture) is dict and set(capture) == CAPTURE_FIELDS and (capture['version'] == VERSION), 'rna_invalid_native_schema')
    require(type(capture['bundle_validated']) is bool and type(capture['capture_complete']) is bool, 'rna_invalid_native_schema')
    for key in ('artifacts', 'invalid_artifacts', 'absent_artifacts', 'failures'):
        require(type(capture[key]) is list, 'rna_invalid_native_schema')
    for failure in capture['failures']:
        validate_rna_issue(failure)
        require(failure['stage'] == 'capture', 'rna_invalid_native_schema')
    if capture['bundle_artifact_ref'] is not None:
        retained(store, capture['bundle_artifact_ref'])
    if not capture['bundle_validated']:
        require(not capture['capture_complete'] and (not capture['artifacts']) and (not capture['invalid_artifacts']) and (not capture['absent_artifacts']) and (len(capture['failures']) == 1), 'rna_invalid_native_schema')
        return deepcopy(capture)
    require(bundle is not None and capture['bundle_artifact_ref'] is not None)
    require(decode_json(store.get_artifact(capture['bundle_artifact_ref']), canonical_bytes=True) == bundle)
    expected, seen, failures = (bundle['files'], set(), [])
    for category in ('artifacts', 'invalid_artifacts'):
        previous = -1
        for row in capture[category]:
            require(type(row) is dict and set(row) == FILE_FIELDS, 'rna_invalid_native_schema')
            matches = [i for i, item in enumerate(expected) if all((item[key] == row[key] for key in ('kind', 'role', 'format', 'relative_path')))]
            require(len(matches) == 1 and matches[0] not in seen and (matches[0] > previous))
            index = previous = matches[0]
            seen.add(index)
            declared = expected[index]
            require(declared['state'] == 'present')
            metadata, _ = retained(store, row['artifact_ref'])
            require((metadata['sha256'], metadata['size']) == (row['sha256'], row['size_bytes']), 'rna_capture_digest_mismatch')
            equal = (row['sha256'], row['size_bytes']) == (declared['sha256'], declared['size_bytes'])
            require(equal == (category == 'artifacts'), 'rna_capture_digest_mismatch')
    require(capture['absent_artifacts'] == [row for row in expected if row['state'] == 'absent'])
    invalid = {row['relative_path'] for row in capture['invalid_artifacts']}
    for i, row in enumerate(expected):
        if row['state'] == 'present' and (i not in seen or row['relative_path'] in invalid):
            failures.append(issue('rna_capture_unavailable' if i not in seen else 'rna_capture_digest_mismatch', stage='capture', record_key=bundle['record_key'], field=f'/files/{i}', artifact_role=row['role']))
    require(capture['failures'] == failures and capture['capture_complete'] == (not failures), 'rna_capture_digest_mismatch')
    return deepcopy(capture)

def rna_structure_source_payload(*, bundle, capture, prepared):
    require(capture['bundle_validated'] and capture['bundle_artifact_ref'] is not None)
    auxiliary = [row['artifact_ref'] for row in capture['artifacts'] + capture['invalid_artifacts']]
    if prepared is not None and prepared['source_grading_artifact_ref'] is not None:
        auxiliary.append(prepared['source_grading_artifact_ref'])
    return {'provider': PROVIDER, 'accession': 'native_rna_structure_' + digest(bundle['identity']), 'uri': None, 'artifact_ref': capture['bundle_artifact_ref'], 'text_ref': None, 'request_ref': None, 'version': 'native_rna_structure_bundle_v1', 'retrieved_at': bundle['finished_at'], 'auxiliary_artifact_refs': list(dict.fromkeys(auxiliary))}
