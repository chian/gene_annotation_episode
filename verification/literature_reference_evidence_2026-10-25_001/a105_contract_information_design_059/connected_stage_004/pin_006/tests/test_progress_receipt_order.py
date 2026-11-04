"""Ordered own/form receipts through actual Store, C8 and J boundaries.

These checks select explicit fixture information units. They execute no models,
native jobs or scientific investigations and install no production policy.
"""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionStore, canonical, content_digest
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.state import Store
from test_recursive_monitoring import assignment, durable_target


FORM_SCHEMA = obj({
    'selected': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'episode_progress'}},
    'unrequested': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'artifact'}},
    'flag': {'type': 'string', 'enum': ['unresolved']},
})


def outcome(refs=(), *, status='completed', **extra):
    return {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': list(refs), 'result': {'retained_value': 1}, **extra}


def form(refs=(), *, unrequested=()):
    return {'selected': list(refs), 'unrequested': list(unrequested), 'flag': 'unresolved'}


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        executions = DurableExecutionStore(tmp_path / 'executions')
        target = durable_target(tmp_path, store, executions)
        scope = target['child']['scope']
        provider = ProgressProvider(store, executions, run_id=target['run_id'])
        snapshots = [provider.observe(target['handle'], list(FIELDS), scope,
            permitted_committed_record_types=['source'])]
        for name in ('A', 'B', 'C'):
            source = store._caller_source({'fixture_committed': name}, 'fixture')
            provider.expose(target['handle'], operation_key='committed-' + name,
                committed_record_refs=[source['id']], provenance_refs=[source['id']])
            snapshots.append(provider.observe(target['handle'], list(FIELDS), scope,
                permitted_committed_record_types=['source']))
        yield SimpleNamespace(store=store, executions=executions, target=target,
            scope=scope, provider=provider, snapshots=snapshots,
            refs=[row['progress_ref'] for row in snapshots])


def forbid_target_reads(saved, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('receiving saved progress must not read a live target')

    for name in ('_target', 'observe', 'direct_dependencies', '_exposures'):
        monkeypatch.setattr(saved.provider, name, forbidden)
    for name in ('load_commission', 'status'):
        monkeypatch.setattr(saved.executions, name, forbidden)
    saved.provider.job_provider = SimpleNamespace(scope=forbidden, observe=forbidden,
        direct_dependencies=forbidden)


def counts(saved):
    return {table: saved.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        for table in ('runtime_progress_observations', 'runtime_progress_deliveries',
                      'runtime_progress_receipts', 'records')}


def test_interleaved_receipts_drive_j_prefixes_and_monitor_consumers(saved, monkeypatch):
    initial, own_first, child_combined, own_last = saved.refs
    provider = saved.provider
    forbid_target_reads(saved, monkeypatch)
    context = BindingContext(provider.run_id, 'receiver', 'monitor',
        (('monitor', 'receiver'),), saved.scope,
        assignment(saved.target['handle'], known=[initial]), {})
    credit = ProgressInformationCredit(provider, information_unit=.25)

    def selection(context):
        return {'run_id': context.run_id, 'episode_id': context.episode_id,
            'initial_progress_refs': [initial], 'known_progress_refs': [initial,
                *provider.received_progress_refs(context.episode_id, context.scope)]}

    def forbidden_grouping(*args, **kwargs):
        pytest.fail('ordered monitor consumers must use the host progress selection')

    services = SimpleNamespace(progress_selection=selection,
        reference_in_scope=lambda reference, scope, namespace: reference == saved.target['handle'],
        read_progress=provider.read_progress, read_record=saved.store.get, own_outcomes=forbidden_grouping,
        received_progress_refs=forbidden_grouping)
    monitor = MonitorEpisodes(services)
    prefixes = []

    def check(expected, units):
        assert provider.received_progress_refs('receiver', saved.scope) == expected
        assert monitor._received(context) == [initial, *expected]
        assert monitor.facts(context, {})['monitoring_progress_refs'] == [initial, *expected]
        projected = credit(context, selection(context))
        assert projected['credit'] == .25 * units
        assert [row['progress_ref'] for row in projected['monitoring_information_contributions']] == expected
        prefixes.append(projected['credit'])

    check([], 0)
    first = outcome([own_first, own_first], result={'progress_refs': [own_last]})
    assert provider.receive_outcome('receiver', first, saved.scope, 'own-first') == [own_first]
    check([own_first], 1)
    admitted = form([child_combined, own_first, child_combined], unrequested=[own_last])
    assert provider.receive_form('receiver', admitted, FORM_SCHEMA, saved.scope, 'typed') == [child_combined, own_first]
    check([own_first, child_combined], 2)
    assert provider.receive_outcome('receiver', outcome([own_last], status='partial'),
        saved.scope, 'own-last') == [own_last]
    check([own_first, child_combined, own_last], 3)
    before = counts(saved)
    assert provider.receive_outcome('receiver', deepcopy(first), saved.scope, 'own-first') == [own_first]
    assert provider.receive_form('receiver', deepcopy(admitted), FORM_SCHEMA, saved.scope, 'typed') == [child_combined, own_first]
    assert counts(saved) == before
    assert prefixes == [0, .25, .5, .75]
    assert not saved.store.list('observation') and not saved.store.list('assessment')


def test_first_listed_order_is_preserved_and_later_keys_do_not_move_refs(saved, monkeypatch):
    initial, first, combined, last = saved.refs
    provider = saved.provider
    forbid_target_reads(saved, monkeypatch)
    assert provider.receive_outcome('receiver', outcome([combined, first, combined]),
        saved.scope, 'own') == [combined, first]
    provider.receive_form('receiver', form([first, last, combined]), FORM_SCHEMA,
        saved.scope, 'form')
    provider.receive_outcome('receiver', outcome([last, first]), saved.scope, 'another-own')
    assert provider.received_progress_refs('receiver') == [combined, first, last]
    context = BindingContext(provider.run_id, 'receiver', 'monitor',
        (('monitor', 'receiver'),), saved.scope, {}, {})
    project = ProgressInformationCredit(provider, information_unit=2)
    selection = {'run_id': context.run_id, 'episode_id': context.episode_id,
        'initial_progress_refs': [initial], 'known_progress_refs': provider.received_progress_refs('receiver')}
    result = project(context, selection)
    assert result['credit'] == 4
    assert [row['progress_ref'] for row in result['monitoring_information_contributions']] == [combined, last]
    rows = saved.store.db.execute('SELECT progress_ref,operation_key FROM runtime_progress_receipts '
        'ORDER BY rowid').fetchall()
    assert [tuple(row) for row in rows] == [(combined, 'own'), (first, 'own'), (last, 'form')]


@pytest.mark.parametrize('status', ['pending', 'failed', 'invalid', None])
def test_unfinished_or_failed_outcomes_are_rejected_without_publication(saved, monkeypatch, status):
    forbid_target_reads(saved, monkeypatch)
    before = counts(saved)
    with pytest.raises(ContractError, match='progress_completed_outcome_required'):
        saved.provider.receive_outcome('receiver', outcome([saved.refs[1]], status=status),
            saved.scope, 'unfinished')
    assert counts(saved) == before


@pytest.mark.parametrize('references', [None, 'progress_string', {}, [''], [1], [['nested']]])
def test_only_explicit_progress_reference_arrays_are_accepted(saved, references):
    before = counts(saved)
    with pytest.raises(ContractError, match='progress_outcome_references_required'):
        saved.provider.receive_outcome('receiver', outcome(progress_refs=references),
            saved.scope, 'invalid-refs')
    assert counts(saved) == before


def test_outcome_without_explicit_refs_does_not_search_nested_results(saved, monkeypatch):
    forbid_target_reads(saved, monkeypatch)
    value = {'status': 'completed', 'result': {'progress_refs': saved.refs,
        'snapshot': saved.snapshots[-1]}, 'record_refs': saved.refs}
    assert saved.provider.receive_outcome('receiver', value, saved.scope, 'no-explicit-refs') == []
    assert saved.provider.received_progress_refs('receiver') == []
    assert saved.provider.receive_outcome('receiver', value, saved.scope, 'no-explicit-refs') == []
    assert counts(saved)['runtime_progress_deliveries'] == 1


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), object(), {1: 'not-a-json-key'}])
def test_complete_outcome_and_scope_must_be_finite_json(saved, value):
    before = counts(saved)
    with pytest.raises(ValueError):
        saved.provider.receive_outcome('receiver', outcome([saved.refs[1]],
            result={'deep': [{'value': value}]}), saved.scope, 'nonfinite-outcome')
    with pytest.raises(ValueError):
        saved.provider.receive_outcome('receiver', outcome([saved.refs[1]]),
            {**saved.scope, 'extra': value}, 'nonfinite-scope')
    assert counts(saved) == before


@pytest.mark.parametrize('change', [
    {'result': {'retained_value': 2}}, {'changed_record_refs': ['other']},
    {'status': 'partial'}, {'status': 'failed'}, {'unrelated': {'nested': True}},
    {'progress_refs': ['progress_unavailable']},
])
def test_complete_outcome_is_immutable_under_delivery_key(saved, monkeypatch, change):
    forbid_target_reads(saved, monkeypatch)
    original = outcome([saved.refs[1]])
    saved.provider.receive_outcome('receiver', original, saved.scope, 'original')
    before = counts(saved)
    with pytest.raises(ContractError, match='progress_delivery_identity_conflict'):
        saved.provider.receive_outcome('receiver', {**original, **change}, saved.scope, 'original')
    assert counts(saved) == before
    assert saved.provider.receive_outcome('receiver', original, saved.scope, 'original') == [saved.refs[1]]


def test_scope_and_channel_are_part_of_delivery_identity(saved):
    provider, scope = saved.provider, saved.scope
    value = outcome([saved.refs[1]])
    provider.receive_outcome('receiver', value, scope, 'original')
    # This is the same effective whole-sequence scope, expressed explicitly.
    changed_scope = {**scope, 'segments': [{'target_ref': scope['subject_refs'][0],
        'start': 0, 'end': 5, 'unit': 'aa'}]}
    with pytest.raises(ContractError, match='progress_delivery_identity_conflict'):
        provider.receive_outcome('receiver', value, changed_scope, 'original')
    with pytest.raises(ContractError, match='progress_delivery_identity_conflict'):
        provider.receive_form('receiver', form([saved.refs[1]]), FORM_SCHEMA, scope, 'original')
    provider.receive_form('receiver', form([saved.refs[2]]), FORM_SCHEMA, scope, 'form-first')
    with pytest.raises(ContractError, match='progress_delivery_identity_conflict'):
        provider.receive_outcome('receiver', outcome([saved.refs[2]]), scope, 'form-first')


@pytest.mark.parametrize('channel', ['own', 'form'])
def test_publication_failure_rolls_back_delivery_and_every_new_receipt(saved, channel):
    provider = saved.provider
    first, combined = saved.refs[1:3]
    saved.store.db.execute("CREATE TEMP TRIGGER receipt_interruption BEFORE INSERT ON runtime_progress_receipts "
        "WHEN NEW.progress_ref='" + combined + "' BEGIN SELECT RAISE(ABORT, 'fixture interruption'); END")
    before = counts(saved)
    with pytest.raises(sqlite3.IntegrityError, match='fixture interruption'):
        if channel == 'own':
            provider.receive_outcome('receiver', outcome([first, combined]), saved.scope, 'interrupted')
        else:
            provider.receive_form('receiver', form([first, combined]), FORM_SCHEMA, saved.scope, 'interrupted')
    assert counts(saved) == before
    saved.store.db.execute('DROP TRIGGER receipt_interruption')
    # The key was not consumed by the attempted delivery.
    assert provider.receive_outcome('receiver', outcome([combined, first]),
        saved.scope, 'interrupted') == [combined, first]


def test_outer_transaction_rolls_back_both_channels_without_moving_existing_receipts(saved):
    provider = saved.provider
    first, combined, last = saved.refs[1:]
    provider.receive_outcome('receiver', outcome([first]), saved.scope, 'retained')
    before = counts(saved)
    with pytest.raises(RuntimeError, match='caller rollback'):
        with saved.store.transaction():
            provider.receive_form('receiver', form([combined]), FORM_SCHEMA, saved.scope, 'rolled-form')
            provider.receive_outcome('receiver', outcome([last, first]), saved.scope, 'rolled-own')
            assert provider.received_progress_refs('receiver') == [first, combined, last]
            raise RuntimeError('caller rollback')
    assert counts(saved) == before
    assert provider.received_progress_refs('receiver') == [first]
    provider.receive_outcome('receiver', outcome([last]), saved.scope, 'rolled-own')
    provider.receive_form('receiver', form([combined]), FORM_SCHEMA, saved.scope, 'rolled-form')
    assert provider.received_progress_refs('receiver') == [first, last, combined]


def test_run_scope_and_receiver_isolation_use_saved_c8_records(saved):
    provider = saved.provider
    first, combined = saved.refs[1:3]
    provider.receive_outcome('receiver-A', outcome([first, combined]), saved.scope, 'same-key')
    provider.receive_outcome('receiver-B', outcome([combined, first]), saved.scope, 'same-key')
    assert provider.received_progress_refs('receiver-A') == [first, combined]
    assert provider.received_progress_refs('receiver-B') == [combined, first]
    narrow = {'subject_refs': saved.scope['subject_refs'], 'segments': [{
        'target_ref': saved.scope['subject_refs'][0], 'start': 0, 'end': 1, 'unit': 'aa'}]}
    before = counts(saved)
    with pytest.raises(ContractError, match='progress_reference_outside_scope'):
        provider.receive_outcome('narrow', outcome([first]), narrow, 'outside')
    with pytest.raises(ContractError, match='progress_reference_outside_scope'):
        provider.received_progress_refs('receiver-A', narrow)
    with pytest.raises(ContractError, match='progress_reference_unavailable'):
        provider.receive_outcome('receiver-A', outcome(['progress_unavailable']), saved.scope, 'missing')
    other = ProgressProvider(saved.store, saved.executions, run_id='other-run')
    with pytest.raises(ContractError, match='progress_reference_unavailable'):
        other.receive_outcome('receiver-A', outcome([first]), saved.scope, 'same-key')
    assert other.received_progress_refs('receiver-A') == []
    assert counts(saved) == before


def test_existing_form_digest_and_mixed_receipts_replay_after_reopen(saved, monkeypatch):
    provider = saved.provider
    first, combined, last = saved.refs[1:]
    original_form = form([first, combined])
    signature = content_digest({'form': original_form, 'schema': FORM_SCHEMA, 'scope': saved.scope})
    # Seed the exact previous receive_form representation, without a channel field.
    with saved.store.transaction():
        saved.store.db.execute('INSERT INTO runtime_progress_deliveries VALUES(?,?,?,?,?)',
            (provider.run_id, 'receiver', 'legacy-form', signature, canonical([first, combined])))
        for ref in (first, combined):
            saved.store.db.execute('INSERT INTO runtime_progress_receipts VALUES(?,?,?,?)',
                (provider.run_id, 'receiver', ref, 'legacy-form'))
    original_own = outcome([last, first], status='partial')
    assert provider.receive_outcome('receiver', original_own, saved.scope, 'own') == [last, first]
    before = counts(saved)
    forbid_target_reads(saved, monkeypatch)
    with Store(saved.store.path) as reopened:
        restored = ProgressProvider(reopened, saved.executions, run_id=provider.run_id)
        assert restored.receive_form('receiver', original_form, FORM_SCHEMA,
            saved.scope, 'legacy-form') == [first, combined]
        assert restored.receive_outcome('receiver', original_own, saved.scope, 'own') == [last, first]
        assert restored.received_progress_refs('receiver', saved.scope) == [first, combined, last]
        row = reopened.db.execute('SELECT signature,progress_refs FROM runtime_progress_deliveries '
            'WHERE operation_key=?', ('legacy-form',)).fetchone()
        assert row['signature'] == signature and json.loads(row['progress_refs']) == [first, combined]
    assert counts(saved) == before
