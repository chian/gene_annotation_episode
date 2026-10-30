"""Original received expression-file identity, separate from native byte checks.

This reader grants no new receipt and makes no claim that supplied sample or
gene labels identify the annotation target. The finite native driver validates
the actual matrix bytes against the selected SHA and size before fitting.
"""
from method_loop.identities import EpisodeRef

from .communication import plain
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .native_expression_nmf_contracts import validate_expression_nmf_requested_job
from .native_file_capture import NativeFileCaptureError, _metadata


_BASELINE_ROLES = {'launch', 'launch_local', 'launch_api', 'launch_hpc', 'results'}


def _require(condition, code):
    if not condition:
        raise ValueError('expression_nmf_input_' + code)


def _received_context(store, context):
    _require(isinstance(context, BindingContext) and context.path
        and context.role == context.path[-1][0], 'invalid_context')
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='expression_nmf_input_')
    authority.authenticate(context, allow_unsaved=True)
    saved = store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?',
        (context.run_id, context.episode_id)).fetchone()
    if saved is None:
        for table in ('runtime_actions', 'runtime_forms', 'runtime_model_calls', 'runtime_observations'):
            _require(store.db.execute(f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1',
                (context.run_id, context.episode_id)).fetchone() is None, 'invalid_context')
    # Use only the existing read path; do not run the receipt schema writer.
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
    current, visited = context, set()
    while True:
        _require(current.episode_id not in visited, 'invalid_context')
        visited.add(current.episode_id)
        manifest = receipts.manifest(current.episode_id)
        parent_id = EpisodeRef(context.run_id, current.path[:-1]).episode_id if len(current.path) > 1 else None
        _require('received_report_prefix' in manifest and manifest['parent_episode_id'] == parent_id
            and authority._equal(current.request.get('message', {}).get('knowledge_inheritance'), manifest),
            'invalid_context')
        through = manifest['through_receipt_index']
        _require(through is None if parent_id is None else type(through) is int and through >= 0,
            'invalid_context')
        if parent_id is None:
            break
        parent = authority.context(parent_id)
        _require(parent.path == current.path[:-1], 'invalid_context')
        store.validate_scope(plain(current.scope), parent_scope=plain(parent.scope))
        current = parent
    store.validate_scope(plain(context.scope))
    return set(receipts.known(context.episode_id, baseline=context.role in _BASELINE_ROLES))


def validate_expression_nmf_job_inputs(store, context, assignment, *, reference_access):
    if 'native_expression_nmf' not in assignment.get('requested_job', {}):
        return []
    requested = validate_expression_nmf_requested_job(assignment['requested_job'])
    file = requested['native_expression_nmf']['input']
    known = _received_context(store, context)
    reference = file['artifact_ref']
    _require(type(reference) is str and reference == 'artifact_' + file['sha256'], 'artifact_metadata_mismatch')
    access = reference_access(context, reference, 'artifact')
    _require(access is None or type(access) is bool, 'invalid_reference_access')
    _require(access is not False, 'protected_reference_denied')
    _require(reference in known, 'not_received')
    try:
        metadata = _metadata(store, reference)
    except NativeFileCaptureError as error:
        raise ValueError('expression_nmf_input_artifact_metadata_mismatch') from error
    _require(metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'],
        'artifact_metadata_mismatch')
    expected_path = store.path / 'artifacts' / file['sha256'][:2] / file['sha256']
    _require(file['path'] == str(expected_path), 'selected_path_mismatch')
    return [reference]


__all__ = ['validate_expression_nmf_job_inputs']
