"""Validate genuine closed ATAC worker receipts without repeating execution.

The explicit existing case must contain a completed478 results action. These
checks deliberately alter in-memory copies; retained scientific bytes and
original closed actions are never changed.
"""
from copy import deepcopy
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_atac_episode_path_2026-10-27_478.fixture_helpers')


def deny(*args, **kwargs):
    raise AssertionError('historical receipt validation attempted new work')


@pytest.fixture(scope='module')
def original_worker():
    directory = Path(os.environ['ATAC478_EXISTING_CASE'])
    assert json.loads((directory / 'native-lifecycle.json').read_text())['returncode'] == 0
    configuration = json.loads((directory / 'fixture-configuration.json').read_text())
    patch = pytest.MonkeyPatch()
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        patch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_atac_native_files', 'prepare_atac_result_worker'):
        patch.setattr('gene_annotation_episode.native_atac_differential_results.' + name, deny)
    patch.setattr('socket.create_connection', deny)
    patch.setattr('socket.socket.connect', deny)
    patch.setattr('socket.socket.connect_ex', deny)

    try:
        with Store(directory / 'state') as store:
            before = {table: F.rows(store, table) for table in F.TABLES}
            owner = F.execution_owner(store, directory, configuration)
            patch.setattr(type(owner.job_progress_provider.targets), 'observe_target', deny)
            receipts = owner.atac_results.receipts
            candidates = []
            for row in F.rows(store, 'runtime_episodes'):
                context = owner.atac_returns.context(row['episode_id'])
                if context.role == 'results' and context.assignment['selector']['mode'] == 'native_result':
                    candidates.append(context)
            context, = candidates
            arguments = {'episode_id': context.episode_id,
                'operation_key': f'{F.RUN_ID}:{context.episode_id}:0', 'scope': F.plain(context.scope)}
            receipt = receipts.read_completed(**arguments)
            assert receipt['worker_execution']['returncode'] == 0 and receipt['delivery_complete']
            receipts.validate_worker(receipt, verify_control_bytes=True)
            yield receipts, receipt, arguments
            assert {table: F.rows(store, table) for table in F.TABLES} == before
    finally:
        patch.undo()


@pytest.mark.parametrize('changed_identity', ['source', 'interpreter', 'dependency'])
def test_completed_worker_rejects_substituted_execution_identity(original_worker, monkeypatch, changed_identity):
    receipts, original, arguments = original_worker
    changed = deepcopy(original)
    intent = changed['worker_execution']['intent']
    pin = (intent['source_pins'][0] if changed_identity == 'source' else
        intent['interpreter'] if changed_identity == 'interpreter' else intent['dependencies'][0]['files'][0])
    pin['sha256'] = ('f' if pin['sha256'] != 'f' * 64 else 'e') * 64
    with pytest.raises(ValueError, match='atac_differential_result_authority_conflict'):
        receipts.validate_worker(changed, verify_control_bytes=True)

    from gene_annotation_episode import atac_differential_result_receipts as module
    root = receipts.action_directory(arguments['episode_id'], arguments['operation_key'])
    actual_read = module.read_control

    def altered_control(path):
        path = Path(path)
        if path == root / 'receipt.json':
            return deepcopy(changed)
        if path == root / 'worker-execution.json':
            return deepcopy(changed['worker_execution'])
        return actual_read(path)

    with monkeypatch.context() as patch:
        patch.setattr(module, 'read_control', altered_control)
        with pytest.raises(ValueError, match='atac_differential_result_authority_conflict'):
            receipts.read_completed(**arguments)
    assert receipts.read_completed(**arguments) == original


def test_private_artifact_custody_handles_actual_nested_software_records(original_worker):
    receipts, original, arguments = original_worker
    assert original['worker_execution']['intent']['dependencies']
    assert all(isinstance(row, dict) for row in original['worker_execution']['intent']['dependencies'])
    for key in ('sheet', 'calculations', 'projection'):
        assert receipts.owns_reference(original['qualified_files'][key]['artifact_ref'])
    inputs = original['intent']['target']['assignment']['requested_job']['native_atac_differential']['request']['inputs']
    assert all(not receipts.owns_reference(row['file']['artifact_ref']) for row in inputs)
    assert not receipts.owns_reference('artifact_' + 'f' * 64)
    assert receipts.read_completed(**arguments) == original
