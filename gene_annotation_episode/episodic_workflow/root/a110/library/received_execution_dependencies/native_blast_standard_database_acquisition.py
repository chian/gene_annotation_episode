from __future__ import annotations
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest, validate_target
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_contracts import validate_standard_blast_database_bundle
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
VERSION = 'native_blast_standard_database_capture_v1'
_FAILURES = {'plan_missing', 'plan_identity_mismatch', 'bundle_missing', 'bundle_invalid', 'attempt_mismatch', 'file_missing', 'file_read_failed', 'file_size_mismatch', 'file_digest_mismatch', 'file_changed'}

def is_standard_blast_database_target(target):
    return type(target) is dict and target.get('resource_kind') == 'hpc' and ('native_blast_standard_database' in target.get('assignment', {}).get('requested_job', {}))

def _decode(raw):

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate_json_key:' + key)
            value[key] = item
        return value

    def nonfinite(value):
        raise ValueError('nonfinite_json:' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)

def _retained(store, reference, *, sha256=None, size_bytes=None):
    try:
        path = artifact_path(store, reference)
        size = path.stat().st_size
    except OSError as error:
        raise ContractError('native_blast_standard_database_frozen_artifact_unavailable', detail={'artifact_ref': reference, 'exception_type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}) from error
    record = store.get(reference)
    if size != record['size'] or (sha256 is not None and record['sha256'] != sha256) or (size_bytes is not None and record['size'] != size_bytes):
        raise ContractError('native_blast_standard_database_frozen_artifact_changed')
    return path

def _attempt(target, witness):
    """Check the reader's ledger witness against the immutable original target."""
    validate_target(target)
    if not is_standard_blast_database_target(target):
        raise ContractError('native_blast_standard_database_hpc_target_required')
    if isinstance(witness, dict) and witness.get('version') == 'terminal_native_database_attempt_v1':
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_database_terminal_custody import validate_terminal_database_attempt
        return validate_terminal_database_attempt(target, witness)
    if type(witness) is not dict or set(witness) != {'authenticated_attempt', 'plan_path', 'ledger', 'job_request'}:
        raise ContractError('native_blast_standard_database_actual_attempt_witness_required')
    authenticated, ledger, job_request = (witness[k] for k in ('authenticated_attempt', 'ledger', 'job_request'))
    if type(authenticated) is not dict or set(authenticated) != {'identity', 'attempt_directory', 'plan_sha256'}:
        raise ContractError('native_blast_standard_database_actual_attempt_witness_required')
    owner = authenticated['identity']
    expected = {'run_id': target['run_id'], 'episode_id': target['origin_episode_id'], 'resource_id': target['resource_id'], 'execution_id': target['execution_id'], 'requested_job_sha256': target['request_sha256'], 'assignment_sha256': digest(target['assignment'])}
    if type(owner) is not dict or set(owner) != set(expected) | {'operation_key', 'attempt_id', 'submission_token'} or any((owner[k] != value for k, value in expected.items())) or (owner['attempt_id'] != digest(owner['operation_key'])) or (owner['submission_token'] != digest({k: owner[k] for k in ('run_id', 'episode_id', 'assignment_sha256', 'operation_key')})):
        raise ContractError('native_blast_standard_database_original_attempt_identity_conflict')
    root = Path(target['assignment']['workspace']) / '.episode-jobs' / digest({'run_id': owner['run_id'], 'episode_id': owner['episode_id']}) / owner['assignment_sha256'] / 'attempts' / owner['attempt_id']
    plan_path = str(root / 'native-blast-standard-database-plan.json')
    if authenticated['attempt_directory'] != str(root) or witness['plan_path'] != plan_path or ledger.get('version') != 'practical_pbs_submission_v2' or (ledger.get('job_id') != owner['execution_id']) or any((ledger.get(k) != owner[k] for k in ('attempt_id', 'operation_key', 'assignment_sha256', 'submission_token'))) or (ledger.get('selection', {}).get('requested_job_sha256') != owner['requested_job_sha256']) or (job_request.get('job_request_sha256') != owner['requested_job_sha256']) or (job_request.get('submission_token') != owner['submission_token']) or any((row.get('native_blast_standard_database_plan_path') != plan_path or row.get('native_blast_standard_database_plan_sha256') != authenticated['plan_sha256'] for row in (ledger, job_request))):
        raise ContractError('native_blast_standard_database_original_attempt_identity_conflict')
    return authenticated

def _validate_capture(store, capture, *, target=None, operation_key=None, directory=None):
    fields = {'version', 'target', 'operation_key', 'plan_artifact_ref', 'bundle_artifact_ref', 'artifact_refs', 'status', 'failures'}
    if type(capture) is not dict or set(capture) != fields or capture['version'] != VERSION or (capture['status'] not in {'complete', 'partial', 'unsealed', 'invalid'}) or (type(capture['artifact_refs']) is not dict) or (type(capture['failures']) is not list) or any((type(row) is not dict or set(row) != {'code', 'artifact_key'} or row['code'] not in _FAILURES or (row['artifact_key'] is not None and type(row['artifact_key']) is not str) for row in capture['failures'])) or (target is not None and capture['target'] != target) or (operation_key is not None and capture['operation_key'] != operation_key) or ((capture['status'] == 'complete') != (not capture['failures'])):
        raise ContractError('native_blast_standard_database_capture_receipt_invalid')
    for reference in [capture['plan_artifact_ref'], capture['bundle_artifact_ref'], *capture['artifact_refs'].values()]:
        if reference is not None:
            _retained(store, reference)
    if directory is None:
        return capture
    directory = Path(directory)
    if _read(directory / 'capture-intent.json') != {'target': capture['target'], 'operation_key': capture['operation_key']}:
        raise ContractError('native_blast_standard_database_capture_intent_conflict')
    if capture['status'] in {'complete', 'partial'}:
        attempt = _attempt(capture['target'], _read(directory / 'authenticated-attempt.json'))
        plan = _decode(_retained(store, capture['plan_artifact_ref']).read_bytes())
        if digest(plan) != attempt['plan_sha256']:
            raise ContractError('native_blast_standard_database_original_plan_identity_conflict')
        bundle = validate_standard_blast_database_bundle(_decode(_retained(store, capture['bundle_artifact_ref']).read_bytes()), original_job=capture['target']['assignment']['requested_job']['native_blast_standard_database'], attempt_identity=attempt)
        if bundle['plan'] != plan:
            raise ContractError('native_blast_standard_database_original_plan_identity_conflict')
        rows = {r['artifact_key']: r for r in bundle['artifacts']}
        if not set(capture['artifact_refs']) <= set(rows) or (capture['status'] == 'complete' and set(capture['artifact_refs']) != set(rows)):
            raise ContractError('native_blast_standard_database_capture_artifact_association_conflict')
        for key, reference in capture['artifact_refs'].items():
            _retained(store, reference, sha256=rows[key]['sha256'], size_bytes=rows[key]['size_bytes'])
    return capture

def _source_payload(bundle, capture):
    return {'provider': 'episode.execution_result', 'accession': 'native_blast_standard_database_' + digest(bundle['identity']), 'uri': None, 'artifact_ref': capture['bundle_artifact_ref'], 'text_ref': None, 'request_ref': None, 'version': 'native_blast_standard_database_bundle_v1', 'retrieved_at': bundle['sealed_at'], 'auxiliary_artifact_refs': list(dict.fromkeys((capture['artifact_refs'][row['artifact_key']] for row in bundle['artifacts'] if row['artifact_key'] in capture['artifact_refs'])))}
