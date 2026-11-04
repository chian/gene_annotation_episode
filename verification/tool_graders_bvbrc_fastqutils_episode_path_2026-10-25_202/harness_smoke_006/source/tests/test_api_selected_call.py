"""Real AppService primitive + selected-call persistence, synthetic HTTP values.

These verify transport recovery, not the still separate host custody, episode
selection, scientific publication or parent-return integration.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_selected_call import perform_selected_call
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects, EffectConflict
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_application_definitions import get_application_spec
from gene_annotation_episode.execution_contracts import digest
from test_api_bvbrc_appservice import (harness, bound, content_binding, original_request,
    prepare, rpc_snapshot, submit_operation)


@pytest.fixture
def execution(harness, tmp_path):
    # Use the actual Store and snapshot methods, without advertising an
    # installed service factory/host that this component does not supply.
    core = APIServiceExecution.__new__(APIServiceExecution)
    core.store, core.run_id = harness.store, 'synthetic-run'
    core.selected_effects = SelectedAPIEffects(tmp_path / 'effects', run_id=core.run_id)
    context = SimpleNamespace(run_id=core.run_id, episode_id='api',
        assignment={'request': original_request()}, scope=harness.scope)
    return SimpleNamespace(core=core, context=context, base=tmp_path / 'actions', h=harness)


def run(e, operation, *, index=0, fresh=True):
    key = f'{e.context.run_id}:{e.context.episode_id}:{index}'
    directory = e.base / digest(key)
    directory.mkdir(parents=True, exist_ok=True)
    return asyncio.run(perform_selected_call(e.core, e.context, e.h.service, operation,
        operation_key=key, directory=directory, fresh=fresh))


def success(e):
    operation = submit_operation(e.h)
    e.h.client.value = {'id': '123', 'app': 'Homology', 'status': 'Q'}
    return operation


def state(e, result):
    row, = result['effect_receipts']
    return e.core.selected_effects.read(row['effect_ref'],
        original_job_owner=row['descriptor']['original_job_owner'])


def test_success_retains_original_snapshot_and_does_not_confirm_before_native_validation(execution):
    e = execution
    operation = success(e)
    result = run(e, operation)
    assert result['failure'] is None
    assert result['snapshot'].content == rpc_snapshot(
        operation['native_operands']['call']['rpc_request'], e.h.client.value).content
    assert state(e, result)['state'] == 'issued_unknown'
    event = e.h.service.decode(operation, result['snapshot'])
    assert event['handoff_ready'] is True and event['native_handle']['task_id'] == '123'
    again = run(e, operation, fresh=False)
    assert again == result
    assert len(e.h.client.calls) == 1


def test_saved_native_response_can_be_decoded_after_local_interruption(execution, monkeypatch):
    import gene_annotation_episode.api_selected_call as module
    e = execution
    operation = success(e)
    write = module._immutable
    def interrupt(path, value):
        write(path, value)
        if path.name == 'call_response.json':
            raise KeyboardInterrupt('after response commit')
    monkeypatch.setattr(module, '_immutable', interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    monkeypatch.setattr(module, '_immutable', write)
    restored = run(e, operation, fresh=False)
    assert restored['failure'] is None
    assert e.h.service.decode(operation, restored['snapshot'])['handoff_ready']
    assert len(e.h.client.calls) == 1


def test_unknown_submission_keeps_original_slot_across_recovery_and_new_selection(execution, monkeypatch):
    e = execution
    operation = success(e)
    def interrupted(rpc):
        e.h.client.calls.append(('rpc', rpc))
        raise KeyboardInterrupt('lost response')
    monkeypatch.setattr(e.h.client, 'rpc', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    restored = run(e, operation, fresh=False)
    assert restored['failure']['code'] == 'issued_effect_unknown'
    assert restored['failure']['effect_outcome'] == 'unknown'
    assert state(e, restored)['state'] == 'issued_unknown'
    with pytest.raises(EffectConflict):
        run(e, operation, index=1)
    assert len(e.h.client.calls) == 1


def test_crash_before_issue_closes_unissued_without_fabricating_attempt(execution, monkeypatch):
    e = execution
    operation = success(e)
    issue = e.core.selected_effects.mark_issued
    def interrupt(reservation):
        raise KeyboardInterrupt('before issue')
    monkeypatch.setattr(e.core.selected_effects, 'mark_issued', interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    monkeypatch.setattr(e.core.selected_effects, 'mark_issued', issue)
    restored = run(e, operation, fresh=False)
    assert restored['failure']['code'] == 'api_operation_not_issued'
    assert state(e, restored)['state'] == 'not_sent'
    assert state(e, restored)['issued_at'] is None
    assert e.h.client.calls == []
    selected_later = run(e, operation, index=1)
    assert selected_later['failure'] is None and len(e.h.client.calls) == 1
    assert state(e, restored)['state'] == 'not_sent'


def test_crash_after_issue_marker_remains_unknown_even_before_client_entry(execution, monkeypatch):
    e = execution
    operation = success(e)
    issue = e.core.selected_effects.mark_issued
    def interrupt(reservation):
        issue(reservation)
        raise KeyboardInterrupt('after durable issue marker')
    monkeypatch.setattr(e.core.selected_effects, 'mark_issued', interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    monkeypatch.setattr(e.core.selected_effects, 'mark_issued', issue)
    restored = run(e, operation, fresh=False)
    assert restored['failure']['effect_outcome'] == 'unknown'
    assert e.h.client.calls == []
    with pytest.raises(EffectConflict):
        run(e, operation, index=1)


def test_actual_pretransport_not_sent_allows_explicit_later_action(execution, monkeypatch):
    e = execution
    operation = success(e)
    rpc = e.h.client.rpc
    def refused(request):
        raise AcquisitionError('credentials_unavailable', phase='transport', submission_outcome='not_sent')
    monkeypatch.setattr(e.h.client, 'rpc', refused)
    failed = run(e, operation)
    assert failed['failure']['effect_outcome'] == 'not_sent'
    assert state(e, failed)['state'] == 'not_sent'
    monkeypatch.setattr(e.h.client, 'rpc', rpc)
    assert run(e, operation, fresh=False) == failed
    assert e.h.client.calls == []
    assert run(e, operation, index=1)['failure'] is None
    assert len(e.h.client.calls) == 1


@pytest.mark.parametrize('claimed_outcome', ['unknown', 'not_sent'])
def test_error_body_and_failure_remain_together_without_reacquisition(execution, monkeypatch, claimed_outcome):
    e = execution
    operation = success(e)
    snapshot = replace(rpc_snapshot(operation['native_operands']['call']['rpc_request'], []),
        content=b'partial native bytes', transport={'status': 502, 'body_complete': False})
    def failed(request):
        e.h.client.calls.append(('rpc', request))
        raise AcquisitionError('native_http_failure', phase='transport',
            submission_outcome=claimed_outcome, snapshot=snapshot)
    monkeypatch.setattr(e.h.client, 'rpc', failed)
    result = run(e, operation)
    assert result['snapshot'] == snapshot
    # Received bytes contradict a claim that no call was sent.
    assert result['failure']['effect_outcome'] == 'unknown'
    assert run(e, operation, fresh=False) == result
    assert len(e.h.client.calls) == 1


def test_read_recovery_does_not_reissue_and_does_not_create_effects(execution, monkeypatch):
    e = execution
    operation = prepare(e.h, 'enumerate_apps', {}, bound(original_request(), 'enumerate_apps', {}))
    def lost(request):
        e.h.client.calls.append(('rpc', request))
        raise KeyboardInterrupt()
    monkeypatch.setattr(e.h.client, 'rpc', lost)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    result = run(e, operation, fresh=False)
    assert result['failure']['code'] == 'api_operation_response_unknown'
    assert result['failure']['effect_outcome'] is None
    assert result['effect_receipts'] == [] and len(e.h.client.calls) == 1


def test_interrupted_local_preparation_can_recompute_exact_frozen_operands(execution, monkeypatch):
    e = execution
    request = original_request()
    args = {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}}
    bindings = bound(request, 'prepare', args, definition_envelope=get_application_spec('Homology'))
    bindings['definition'] = {'content': content_binding(), 'pointer': ''}
    operation = prepare(e.h, 'prepare', args, bindings)
    invoke = e.h.service.invoke
    def interrupted(command):
        raise KeyboardInterrupt()
    monkeypatch.setattr(e.h.service, 'invoke', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    monkeypatch.setattr(e.h.service, 'invoke', invoke)
    restored = run(e, operation, fresh=False)
    assert restored == {'snapshot': None, 'failure': None, 'effect_receipts': []}
    assert e.h.service.decode(operation, None)['facts']['c3_result']['status'] == 'ok'
    assert e.h.client.calls == []


@pytest.mark.parametrize('change', ['arguments', 'assignment', 'scope', 'owner', 'resource', 'mutation_flag'])
def test_changed_frozen_identity_cannot_invoke_again(execution, change):
    e = execution
    operation = success(e)
    run(e, operation)
    altered = deepcopy(operation)
    if change == 'arguments':
        altered['native_operands']['arguments']['input_evidence_refs'] = ['changed']
    elif change == 'assignment':
        e.context.assignment['changed'] = True
    elif change == 'scope':
        e.context.scope = {'subject_refs': []}
    elif change == 'owner':
        altered['effects'][0]['original_job_owner']['launch_episode_id'] = 'other'
    elif change == 'resource':
        altered['effects'][0]['resource_id'] = 'other'
    else:
        altered['mutates_remote'] = False
    with pytest.raises((ValueError, OSError)):
        run(e, altered, fresh=False)
    assert len(e.h.client.calls) == 1


def test_fresh_flag_cannot_override_existing_intent_and_unknown_reply(execution, monkeypatch):
    e = execution
    operation = success(e)
    def interrupted(request):
        e.h.client.calls.append(('rpc', request))
        raise KeyboardInterrupt()
    monkeypatch.setattr(e.h.client, 'rpc', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(e, operation)
    assert run(e, operation, fresh=True)['failure']['effect_outcome'] == 'unknown'
    assert len(e.h.client.calls) == 1


def test_async_upload_reads_store_on_owner_thread_and_only_transport_on_worker(execution, monkeypatch):
    import hashlib
    import json
    import threading
    from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
    from test_api_bvbrc_appservice import CONFIG, SHOCK_UUID, server, upload_operation
    e = execution
    content = b'\x00\xffactual retained bytes\n'
    reply = {'status': 200, 'data': {'id': SHOCK_UUID,
        'file': {'size': len(content), 'checksum': {'sha256': hashlib.sha256(content).hexdigest()}}},
        'error': None}
    owner_thread, read_threads = threading.get_ident(), []
    read = e.core.store.get_artifact
    def recorded_read(ref):
        read_threads.append(threading.get_ident())
        return read(ref)
    with server(json.dumps(reply).encode()) as (url, calls):
        e.h.service.client = BVBRCAnalysisClient(CONFIG['endpoints'])
        operation = upload_operation(e.h, url + '/node/' + SHOCK_UUID, content)
        monkeypatch.setattr(e.core.store, 'get_artifact', recorded_read)
        result = run(e, operation)
        assert result['failure'] is None
        assert e.h.service.decode(operation, result['snapshot'])['facts']['projection']['confirmation'] == 'accepted_bytes_match'
        assert run(e, operation, fresh=False) == result
    assert len(calls) == 1 and content in calls[0]['body']
    assert read_threads and set(read_threads) == {owner_thread}


def test_missing_upload_bytes_never_marks_native_effect_issued(execution, monkeypatch):
    from test_api_bvbrc_appservice import SHOCK_UUID, upload_operation
    e = execution
    operation = upload_operation(e.h, 'https://shock.example.invalid/node/' + SHOCK_UUID)
    def missing(ref):
        raise KeyError(ref)
    monkeypatch.setattr(e.core.store, 'get_artifact', missing)
    result = run(e, operation)
    assert result['failure']['code'] == 'input_not_possessed'
    assert state(e, result)['state'] == 'not_sent'
    assert state(e, result)['issued_at'] is None
    assert e.h.client.calls == []
