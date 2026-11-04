"""Store-backed source/receipt codec; no complete AppService host claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.api_selected_call import perform_selected_call
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_appservice_records import AppServiceRecords, provisional_receipt_ref
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _immutable, _read
from test_api_bvbrc_appservice import harness, original_request, bound, prepare, PREFIX


@pytest.fixture
def receipt_fixture(harness, tmp_path):
    h = harness
    api = APIServiceExecution.__new__(APIServiceExecution)
    api.store, api.run_id, api.directory = h.store, 'synthetic-run', tmp_path / 'api'
    api.selected_effects = SelectedAPIEffects(tmp_path, run_id=api.run_id)
    journal = Journal(h.store, api.run_id)
    path = (('launch_api', 'fixture'),)
    assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'synthetic-api',
        'service': 'bvbrc_appservice', 'request': original_request(),
        'endpoint': 'usable_handoff', 'constraints': {}}
    request = {'message': {'scope': h.scope, 'episode_assignment': assignment}}
    context = BindingContext(api.run_id, EpisodeRef(api.run_id, path).episode_id,
        'launch_api', path, h.scope, assignment, request)
    journal.save('runtime_episodes', {'episode_id': context.episode_id, 'path': canonical(path),
        'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
    operation = prepare(h, 'enumerate_apps', {}, bound(original_request(), 'enumerate_apps', {}))
    key = f'{api.run_id}:{context.episode_id}:0'
    journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': PREFIX + 'enumerate_apps', 'arguments': {}}),
        'result': None, 'credit': None})
    directory = api._manifest(context) / 'actions' / digest(key)
    directory.mkdir(exist_ok=True)
    intent = {'run_id': api.run_id, 'episode_id': context.episode_id, 'operation_key': key,
        'name': PREFIX + 'enumerate_apps', 'arguments': {},
        'assignment_sha256': digest(context.assignment), 'prepared': operation,
        'started_at': '2026-10-24T12:00:00+00:00'}
    _immutable(directory / 'intent.json', intent)
    call = asyncio.run(perform_selected_call(api, context, h.service, operation,
        operation_key=key, directory=directory, fresh=True))
    records = AppServiceRecords(api)
    return SimpleNamespace(h=h, api=api, records=records, context=context,
        journal=journal, directory=directory, key=key, operation=operation, call=call)


def receipt(f):
    binding = f.records.retain_snapshot(f.context, f.operation, f.call['snapshot'], operation_key=f.key)
    origin = f.records._origin(f.context, f.operation, f.key)
    value = {'version': 'bvbrc_appservice_support_receipt_v1',
        'receipt_ref': provisional_receipt_ref(origin), 'purpose': 'support',
        'origin': origin, 'snapshot': binding, 'effect_receipt_refs': [], 'status': 'ok', 'diagnostics': []}
    return value


def publish(f):
    return f.records.publish(f.context, 'CommonReceipt', receipt(f), operation_key=f.key)


def complete(f, published):
    outcome = {'status': 'completed', 'record_refs': [published['source_ref']],
        'changed_record_refs': [published['source_ref']], 'result': published, 'feedback': None}
    _immutable(f.directory / 'outcome.json', outcome)
    f.journal.save('runtime_actions', {'episode_id': f.context.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': PREFIX + 'enumerate_apps', 'arguments': {}}),
        'result': canonical(outcome), 'credit': 0})


def test_actual_source_and_self_reference_codec_reopen_without_transport(receipt_fixture):
    f = receipt_fixture
    published = publish(f)
    value = published['value']
    assert value['receipt_ref'] == published['source_ref']
    native = f.h.store.get(value['snapshot']['source_ref'])
    assert f.h.store.get_artifact(native['artifact_ref']) == f.call['snapshot'].content
    encoded = json.loads(f.h.store.get_artifact(f.h.store.get(published['source_ref'])['artifact_ref']))
    assert 'receipt_ref' not in encoded['value']
    complete(f, published)
    reopened = AppServiceRecords(f.api)
    assert reopened.read(published['source_ref']) == published
    count = f.h.store.count('source')
    assert publish(f) == published
    assert f.h.store.count('source') == count and len(f.h.client.calls) == 1
    assert f.h.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_pending_publication_read_does_not_claim_completed_action(receipt_fixture):
    f = receipt_fixture
    published = publish(f)
    assert f.records.read(published['source_ref'], require_completed=False) == published
    with pytest.raises((ValueError, FileNotFoundError)):
        f.records.read(published['source_ref'])
    complete(f, published)
    assert f.records.read(published['source_ref']) == published


@pytest.mark.parametrize('change', ['body', 'time', 'request', 'transport'])
def test_unrecorded_snapshot_cannot_be_substituted(receipt_fixture, change):
    f = receipt_fixture
    original_source_count = f.h.store.count('source')
    original = f.call['snapshot']
    changed = {'body': {'content': original.content + b' '},
        'time': {'retrieved_at': 'later'}, 'request': {'request': {'unselected': True}},
        'transport': {'transport': {'status': 200, 'body_complete': True}}}[change]
    with pytest.raises(ValueError, match='original_transport_conflict'):
        f.records.retain_snapshot(f.context, f.operation, replace(original, **changed), operation_key=f.key)
    assert f.h.store.count('source') == original_source_count


@pytest.mark.parametrize('change', ['own_ref', 'origin', 'snapshot'])
def test_receipt_requires_exact_original_action_and_snapshot(receipt_fixture, change):
    f = receipt_fixture
    value = receipt(f)
    if change == 'own_ref':
        value['receipt_ref'] = 'arbitrary_source'
    elif change == 'origin':
        value['origin']['operation_key'] = f.key[:-1] + '1'
    else:
        value['snapshot']['transport']['status'] = 404
    with pytest.raises(ValueError):
        f.records.publish(f.context, 'CommonReceipt', value, operation_key=f.key)
    assert not (f.directory / 'typed_receipt.json').exists()


def test_completed_runtime_value_must_match_actual_retained_outcome(receipt_fixture):
    f = receipt_fixture
    published = publish(f)
    complete(f, published)
    f.h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?',
        (canonical({'status': 'completed', 'record_refs': [], 'result': None}), f.api.run_id, f.context.episode_id))
    with pytest.raises(ValueError, match='completed_action_required'):
        f.records.read(published['source_ref'])


def test_original_call_metadata_corruption_is_detected_on_read(receipt_fixture):
    f = receipt_fixture
    published = publish(f)
    complete(f, published)
    path = f.directory / 'call_response.json'
    changed = _read(path)
    changed['snapshot']['request'] = {'different': True}
    from gene_annotation_episode.practical_execution_records import canonical as record_bytes
    path.write_bytes((record_bytes(changed) + '\n').encode('utf-8'))
    with pytest.raises(ValueError, match='original_transport_conflict'):
        f.records.read(published['source_ref'])


def test_wrong_saved_episode_context_is_rejected(receipt_fixture):
    f = receipt_fixture
    published = publish(f)
    complete(f, published)
    altered = deepcopy(plain(f.context.request))
    altered['message']['scope'] = {'subject_refs': []}
    f.h.store.db.execute('UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?',
        (canonical(altered), f.api.run_id, f.context.episode_id))
    with pytest.raises(ValueError):
        f.records.read(published['source_ref'])


def test_handoff_codec_rewrites_only_two_declared_self_fields():
    # Exact codec behavior, deliberately no claim of an actual task handoff.
    from gene_annotation_episode.bvbrc_appservice_records import _encode
    value = {'receipt': {'receipt_ref': 'provisional'},
        'original_task': {'submission_receipt_ref': 'provisional', 'submission_source_ref': 'native'},
        'native_submission_record': {'literal': 'provisional'}}
    encoded = _encode('TaskHandoff', value)
    assert encoded['receipt'] == {}
    assert encoded['original_task'] == {'submission_source_ref': 'native'}
    assert encoded['native_submission_record']['literal'] == 'provisional'
    value['original_task']['submission_receipt_ref'] = 'unrelated_receipt'
    with pytest.raises(ValueError, match='self_identity_conflict'):
        _encode('TaskHandoff', value)
