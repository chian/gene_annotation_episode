"""Original received event/support-file identity, separate from native byte checks.

This reader grants no new receipt and makes no claim that supplied sample or
gene labels identify the annotation target. The finite native driver validates
the actual event bytes against the selected SHA and size before parsing.
"""
from method_loop.identities import EpisodeRef

from .communication import plain
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .native_fluorescence_contracts import validate_fluorescence_requested_job
from .native_file_capture import NativeFileCaptureError, _metadata


_BASELINE_ROLES = {'launch', 'launch_local', 'launch_api', 'launch_hpc', 'results'}


def _require(condition, code):
    if not condition:
        raise ValueError('fluorescence_input_' + code)


def _received_context(store, context):
    _require(isinstance(context, BindingContext) and context.path
        and context.role == context.path[-1][0], 'invalid_context')
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='fluorescence_input_')
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


def validate_fluorescence_job_inputs(store, context, assignment, *, reference_access):
    if 'native_fluorescence' not in assignment.get('requested_job', {}):
        return []
    job = validate_fluorescence_requested_job(assignment['requested_job'])['native_fluorescence']
    known = _received_context(store, context)
    admitted = []
    files = [(row['source']['file'], row['path']) for row in job['inputs']]
    files.extend((row['file'], row['path']) for row in job['support_inputs'])
    files.extend((row['file'], row['path']) for row in job.get('report_inputs', []))
    for file, path in files:
        reference = file['artifact_ref']
        access = reference_access(context, reference, 'artifact')
        _require(access is None or type(access) is bool, 'invalid_reference_access')
        _require(access is not False, 'protected_reference_denied')
        _require(reference in known, 'not_received')
        try:
            metadata = _metadata(store, reference)
        except NativeFileCaptureError as error:
            raise ValueError('fluorescence_input_artifact_metadata_mismatch') from error
        _require(metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'],
            'artifact_metadata_mismatch')
        expected_path = store.path / 'artifacts' / file['sha256'][:2] / file['sha256']
        _require(path == str(expected_path), 'selected_path_mismatch')
        if reference not in admitted:
            admitted.append(reference)
    return admitted


__all__ = ['validate_fluorescence_job_inputs']
