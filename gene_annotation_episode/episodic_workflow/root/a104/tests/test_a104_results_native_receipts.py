"""Actual Results receipt/publication bodies over controlled original file returns.

Store, Journal, selected-action authentication, immutable intent/observation/
window/receipt files, publication and readback are real. The resource observation
and file-byte ports are controlled; no native or network acquisition occurs.
"""
import asyncio
import base64
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .test_a104_results_preservation import binding_home, frame, own_module


@pytest.fixture
def native_receipt(frame):
    assignment = frame.assignment
    assert assignment['selector'] == {'path': '/controlled-original-workspace/original-output.txt', 'offset': 0, 'limit': 1}
    target = {'resource_kind': 'hpc', 'resource_id': 'aurora', 'origin_episode_id': 'controlled-original-native',
        'assignment': {'workspace': '/controlled-original-workspace', 'requested_job': {}},
        'handle': 'controlled-original-native-handoff'}
    arguments = {'path': '/controlled-original-workspace/original-output.txt', 'offset': 0, 'limit': 1}
    key = f'{frame.run_id}:{frame.child.episode_id}:2'
    selected = {'kind': 'tool', 'tool': 'execution.results.read', 'arguments': arguments}
    frame.store.db.execute("UPDATE runtime_episodes SET state='active',completion=NULL WHERE run_id=? AND episode_id=?",
        (frame.run_id, frame.child.episode_id))
    frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
        'action': own_module('runtime')._json(selected), 'result': None, 'credit': None})
    observed, reads, target_reads = [], [], []
    result = {'mode': 'bytes'}
    def read_target(reference, scope):
        assert reference == assignment['handoff_ref'] and scope == frame.scope
        target_reads.append(reference)
        return deepcopy(target)
    def observe(selected_target, *, operation_key):
        assert selected_target == target and operation_key == key
        observed.append(operation_key)
        return {'observed_at': '2026-11-11T00:00:00Z', 'state': 'succeeded', 'qualification': 'controlled observation port'}
    def read_file(selected_target, **operands):
        assert selected_target == target and operands == {**arguments, 'operation_key': key + ':file:0'}
        reads.append(deepcopy(operands))
        if result['mode'] == 'unavailable':
            raise FileNotFoundError('controlled missing original output')
        if result['mode'] == 'invalid':
            raise ValueError('controlled_original_file_invalid')
        return {'path': arguments['path'], 'offset': 0, 'returned_bytes': 1, 'size_bytes': 4,
            'bytes_base64': base64.b64encode(b'A').decode(), 'qualification': 'current filesystem bytes only'}
    frame.owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(
        read_target=read_target, observe_target=observe, read_file=read_file))
    return SimpleNamespace(frame=frame, target=target, arguments=arguments, key=key, selected=selected,
        observed=observed, reads=reads, target_reads=target_reads, result=result)


@pytest.mark.parametrize('mode', ('bytes', 'unavailable', 'invalid'))
def test_actual_native_result_publication_retains_qualifications_and_failure_receipts(native_receipt, mode):
    case, frame = native_receipt, native_receipt.frame
    case.result['mode'] = mode
    returned = asyncio.run(frame.owner._execute_native_results(frame.child, case.target,
        case.selected['tool'], case.arguments, case.key))
    # The original acquired-information outcome is completed even when its
    # per-window failure list is nonempty; do not rewrite this to evidence absence.
    assert returned['status'] == 'completed'
    body = returned['result']
    assert body['acquisition_origin'] == {'content_location': 'current_resource_filesystem',
        'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot',
        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
    assert body['assignment'] == frame.assignment and body['target'] == case.target
    if mode == 'bytes':
        assert body['windows'][0]['bytes_base64'] == 'QQ==' and body['failures'] == []
    else:
        assert body['windows'] == [] and body['failures'] == [{'path': case.arguments['path'],
            'code': 'execution_result_file_unavailable' if mode == 'unavailable' else 'controlled_original_file_invalid',
            'exception_type': 'FileNotFoundError' if mode == 'unavailable' else 'ValueError'}]
    reference, = returned['record_refs']
    assert returned['changed_record_refs'] == [reference]
    frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
        'result': own_module('runtime')._json(returned), 'credit': 0.0})
    replay = asyncio.run(frame.owner._execute_native_results(frame.child, case.target,
        case.selected['tool'], case.arguments, case.key))
    assert replay == returned and len(case.observed) == len(case.reads) == 1
    assert frame.owner._read_result(reference, frame.scope) == body


@pytest.mark.parametrize('change', ('selected_arguments', 'receipt_bytes', 'target_identity', 'saved_outcome'))
def test_actual_native_receipt_read_rejects_changed_original_controls(native_receipt, change):
    case, frame = native_receipt, native_receipt.frame
    returned = asyncio.run(frame.owner._execute_native_results(frame.child, case.target,
        case.selected['tool'], case.arguments, case.key))
    reference, = returned['record_refs']
    frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
        'result': own_module('runtime')._json(returned), 'credit': 0.0})
    if change == 'selected_arguments':
        changed = deepcopy(case.selected)
        changed['arguments']['offset'] = 1
        frame.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=2',
            (own_module('runtime')._json(changed), frame.run_id, frame.child.episode_id))
        expected = 'execution_result_selected_action_conflict'
    elif change == 'receipt_bytes':
        contracts = own_module('execution_contracts')
        path = frame.owner._result_directory(frame.child) / (contracts.digest(case.key) + '.receipt.json')
        body = json.loads(path.read_bytes())
        body['observation']['state'] = 'changed-original-observation'
        path.write_text(contracts.canonical(body))
        expected = 'execution_result_original_receipt_conflict'
    elif change == 'target_identity':
        case.target['handle'] = 'changed-native-handoff'
        expected = 'execution_result_original_target_conflict'
    else:
        changed = deepcopy(returned)
        changed['result']['observation']['state'] = 'changed-saved-outcome'
        frame.journal.save('runtime_actions', {'episode_id': frame.child.episode_id, 'decision_index': 2,
            'result': own_module('runtime')._json(changed)})
        expected = 'execution_result_saved_outcome_conflict'
    with pytest.raises(ValueError, match=expected):
        frame.owner._read_result(reference, frame.scope)
    assert len(case.observed) == len(case.reads) == 1
