"""Selected-effect persistence; no HTTP, tool execution or runtime decisions."""
from copy import deepcopy
import multiprocessing
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_selected_effects import SelectedAPIEffects, EffectConflict
from gene_annotation_episode.execution_contracts import canonical, digest


OWNER = {'run_id': 'run', 'launch_episode_id': 'launch',
    'parent_commission_operation_key': 'run:science:0',
    'original_launch_assignment_sha256': 'a' * 64}


def context(episode='api'):
    return SimpleNamespace(run_id='run', episode_id=episode)


def descriptor(kind='appservice_submit', *, payload='b', owner=None, **slot):
    return {'version': 'selected_api_effects_v1', 'original_job_owner': deepcopy(owner or OWNER),
        'resource_id': 'bvbrc', 'kind': kind, 'slot': {'kind': kind, **slot},
        'payload_sha256': payload * 64, 'predecessor_evidence_refs': []}


def failure(code='missing_configuration', outcome='not_sent'):
    return {'code': code, 'phase': 'transport', 'affected_refs': [], 'affected_pointers': [],
        'effect_outcome': outcome, 'valid_record_refs': [], 'requirements': []}


def outcomes(reservation, state='confirmed'):
    return [{'effect_ref': ref, 'state': state,
        'confirmation_source_ref': 'source_confirmation' if state == 'confirmed' else None,
        'native_effect_identifiers': {'task_id': '123'} if state == 'confirmed' else {},
        'ancillary_effects': [], 'failure': failure() if state == 'not_sent' else None}
        for ref in reservation['effect_refs']]


def files(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*.json')}


def test_exact_replay_and_reopen_preserve_states_without_another_issue(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    original = [descriptor()]
    reservation = journal.reserve(context(), 'run:api:0', original)
    assert journal.read(reservation['effect_refs'][0], original_job_owner=OWNER)['state'] == 'prepared_not_issued'
    assert journal.reserve(context(), 'run:api:0', original) == reservation
    issued = journal.mark_issued(reservation)
    assert issued['first_issue'] is True
    assert issued['effects'][0]['state'] == 'issued_unknown'
    saved = files(tmp_path)
    reopened = SelectedAPIEffects(tmp_path, run_id='run')
    replay = reopened.mark_issued(reservation)
    assert replay['first_issue'] is False
    assert replay['effects'] == issued['effects']
    assert files(tmp_path) == saved
    confirmed = reopened.record_outcome(reservation, outcomes(reservation))
    saved = files(tmp_path)
    assert reopened.record_outcome(reservation, outcomes(reservation)) == confirmed
    assert reopened.read(reservation['effect_refs'][0], original_job_owner=OWNER) == confirmed[0]
    assert reopened.mark_issued(reservation)['first_issue'] is False
    assert files(tmp_path) == saved


def test_separate_create_upload_submit_slots_and_batch_atomic_conflict(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    create_a = descriptor('workspace_create', target_path='/u/w/a')
    create_b = descriptor('workspace_create', target_path='/u/w/b')
    first = journal.reserve(context(), 'run:api:0', [create_a])
    journal.mark_issued(first)
    before = files(tmp_path)
    with pytest.raises(EffectConflict, match='already_reserved') as exc:
        journal.reserve(context(), 'run:api:1', [create_b, create_a])
    assert exc.value.effect_refs == tuple(first['effect_refs'])
    assert files(tmp_path) == before
    second = journal.reserve(context(), 'run:api:2', [create_b])
    assert second['effect_refs'] != first['effect_refs']
    upload = journal.reserve(context(), 'run:api:3', [descriptor('shock_upload', shock_node_id='node-a')])
    submit = journal.reserve(context(), 'run:api:4', [descriptor()])
    for reservation in (second, upload, submit):
        assert journal.mark_issued(reservation)['first_issue'] is True


@pytest.mark.parametrize('first,second', [
    (descriptor('workspace_create', target_path='/u/w/a'),
     descriptor('workspace_create', target_path='/u//w/a/', payload='c')),
    (descriptor('shock_upload', shock_node_id='node'),
     descriptor('shock_upload', shock_node_id='node', payload='c')),
])
def test_relabeling_same_physical_target_cannot_evade_slot(tmp_path, first, second):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    journal.reserve(context(), 'run:api:0', [first])
    with pytest.raises(EffectConflict, match='payload_conflict'):
        journal.reserve(context('other-child'), 'run:other-child:0', [second])


def test_changed_payload_and_same_action_conflict(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    first = journal.reserve(context(), 'run:api:0', [descriptor()])
    with pytest.raises(EffectConflict, match='action_reused'):
        journal.reserve(context(), 'run:api:0', [descriptor(payload='c')])
    with pytest.raises(EffectConflict, match='payload_conflict') as exc:
        journal.reserve(context(), 'run:api:1', [descriptor(payload='c')])
    assert exc.value.effect_refs == tuple(first['effect_refs'])


def test_definitive_not_sent_allows_only_new_explicit_attempt(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    first = journal.reserve(context(), 'run:api:0', [descriptor()])
    journal.mark_issued(first)
    journal.record_outcome(first, outcomes(first, 'not_sent'))
    saved = journal.read(first['effect_refs'][0], original_job_owner=OWNER)
    second = journal.reserve(context(), 'run:api:1', [descriptor()])
    assert second['effect_refs'] != first['effect_refs']
    assert journal.mark_issued(first)['first_issue'] is False
    assert journal.mark_issued(second)['first_issue'] is True
    assert journal.read(first['effect_refs'][0], original_job_owner=OWNER) == saved


def test_unknown_is_not_failure_or_release_and_can_finish_original_response(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    first = journal.reserve(context(), 'run:api:0', [descriptor()])
    journal.mark_issued(first)
    unknown = outcomes(first, 'issued_unknown')
    unknown[0]['failure'] = failure('response_missing', 'unknown')
    journal.record_outcome(first, unknown)
    with pytest.raises(EffectConflict):
        journal.reserve(context(), 'run:api:1', [descriptor()])
    assert journal.record_outcome(first, outcomes(first))[0]['state'] == 'confirmed'
    with pytest.raises(ValueError, match='closed_outcome_conflict'):
        journal.record_outcome(first, outcomes(first, 'not_sent'))


@pytest.mark.parametrize('alteration', ['no_issue', 'no_source', 'unknown_not_sent', 'missing_member', 'wrong_ref'])
def test_outcome_requires_original_issue_and_actual_complete_batch_facts(tmp_path, alteration):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    reservation = journal.reserve(context(), 'run:api:0', [descriptor()])
    if alteration != 'no_issue':
        journal.mark_issued(reservation)
    values = outcomes(reservation)
    if alteration == 'no_source':
        values[0]['confirmation_source_ref'] = None
    elif alteration == 'unknown_not_sent':
        values = outcomes(reservation, 'not_sent')
        values[0]['failure']['effect_outcome'] = 'unknown'
    elif alteration == 'missing_member':
        values = []
    elif alteration == 'wrong_ref':
        values[0]['effect_ref'] = 'different'
    before = files(tmp_path)
    with pytest.raises(ValueError):
        journal.record_outcome(reservation, values)
    assert files(tmp_path) == before


def test_capability_generation_requires_original_same_object_predecessor(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    first_desc = descriptor('download_capability', object_identity='object', generation=0)
    first = journal.reserve(context(), 'run:api:0', [first_desc])
    next_desc = descriptor('download_capability', object_identity='object', generation=1)
    next_desc['predecessor_evidence_refs'] = first['effect_refs']
    with pytest.raises(EffectConflict, match='predecessor_required'):
        journal.reserve(context(), 'run:api:1', [next_desc])
    journal.mark_issued(first)
    second = journal.reserve(context(), 'run:api:1', [next_desc])
    assert journal.mark_issued(second)['first_issue'] is True
    for field, value in (('generation', 3), ('object_identity', 'unrelated')):
        invalid = deepcopy(next_desc)
        invalid['slot'][field] = value
        with pytest.raises(EffectConflict, match='predecessor_required'):
            journal.reserve(context(), 'run:api:2', [invalid])


def test_wrong_owner_and_changed_reservation_do_not_read_or_issue(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    original = journal.reserve(context(), 'run:api:0', [descriptor()])
    other = {**OWNER, 'launch_episode_id': 'another-launch'}
    with pytest.raises(ValueError, match='not_owned'):
        journal.read(original['effect_refs'][0], original_job_owner=other)
    altered = {**original, 'resource_id': 'different'}
    with pytest.raises(ValueError, match='original_reservation_conflict'):
        journal.mark_issued(altered)
    with pytest.raises(EffectConflict, match='action_reused'):
        journal.reserve(context(), 'run:api:0', [descriptor(owner=other)])
    new = journal.reserve(context('other-api'), 'run:other-api:0', [descriptor(owner=other)])
    assert new != original
    assert journal.mark_issued(new)['first_issue'] is True


@pytest.mark.parametrize('problem', ['kind', 'empty', 'duplicate', 'run', 'action', 'nan', 'bool_generation'])
def test_invalid_identity_batches_never_reserve(tmp_path, problem):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    rows, key, ctx = [descriptor()], 'run:api:0', context()
    if problem == 'kind':
        rows[0]['kind'] = 'workspace_create'
    elif problem == 'empty':
        rows = []
    elif problem == 'duplicate':
        rows *= 2
    elif problem == 'run':
        ctx.run_id = 'other'
    elif problem == 'action':
        key = 'run:api:00'
    elif problem == 'nan':
        rows[0]['payload_sha256'] = float('nan')
    else:
        rows = [descriptor('download_capability', object_identity='object', generation=True)]
    with pytest.raises((ValueError, TypeError)):
        journal.reserve(ctx, key, rows)
    assert files(tmp_path) == {}


def test_state_corruption_is_detected_on_reopen(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    original = journal.reserve(context(), 'run:api:0', [descriptor()])
    journal.mark_issued(original)
    path = next(tmp_path.rglob('states/*.json'))
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        SelectedAPIEffects(tmp_path, run_id='run').read(original['effect_refs'][0], original_job_owner=OWNER)


def test_interrupted_reservation_reuses_same_immutable_action_owner(tmp_path, monkeypatch):
    import gene_annotation_episode.api_selected_effects as module
    original_write = module._immutable
    def interrupt(path, value):
        if path.name == 'intent.json':
            raise KeyboardInterrupt('before intent publication')
        original_write(path, value)
    monkeypatch.setattr(module, '_immutable', interrupt)
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    with pytest.raises(KeyboardInterrupt):
        journal.reserve(context(), 'run:api:0', [descriptor()])
    assert len(list(tmp_path.rglob('owner.json'))) == 1
    assert not list(tmp_path.rglob('intent.json'))
    monkeypatch.setattr(module, '_immutable', original_write)
    with pytest.raises(EffectConflict, match='action_reused'):
        journal.reserve(context(), 'run:api:0', [descriptor(owner={**OWNER, 'launch_episode_id': 'other'})])
    saved = journal.reserve(context(), 'run:api:0', [descriptor()])
    assert journal.mark_issued(saved)['first_issue'] is True


def test_interruption_after_issue_marker_never_grants_second_issue(tmp_path, monkeypatch):
    import gene_annotation_episode.api_selected_effects as module
    original_write = module._immutable
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    reservation = journal.reserve(context(), 'run:api:0', [descriptor()])
    def interrupt(path, value):
        original_write(path, value)
        if path.parent.name == 'states':
            raise KeyboardInterrupt('after issue publication')
    monkeypatch.setattr(module, '_immutable', interrupt)
    with pytest.raises(KeyboardInterrupt):
        journal.mark_issued(reservation)
    monkeypatch.setattr(module, '_immutable', original_write)
    before = files(tmp_path)
    reopened = SelectedAPIEffects(tmp_path, run_id='run')
    assert reopened.mark_issued(reservation)['first_issue'] is False
    with pytest.raises(EffectConflict):
        reopened.reserve(context(), 'run:api:1', [descriptor()])
    assert files(tmp_path) == before


def test_partial_batch_confirmation_preserves_each_member_and_replays(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    reservation = journal.reserve(context(), 'run:api:0', [
        descriptor('workspace_create', target_path='/u/w/a'),
        descriptor('workspace_create', target_path='/u/w/b')])
    journal.mark_issued(reservation)
    values = outcomes(reservation)
    values[0]['native_effect_identifiers'] = {'workspace_uuid': 'actual-a'}
    values[0]['ancillary_effects'] = [{'parent_path': '/u/w', 'observed': True}]
    values[1].update(state='issued_unknown', confirmation_source_ref=None,
        native_effect_identifiers={}, failure=failure('member_outcome_unknown', 'unknown'))
    rows = journal.record_outcome(reservation, values)
    assert [row['state'] for row in rows] == ['confirmed', 'issued_unknown']
    before = files(tmp_path)
    assert journal.record_outcome(reservation, list(reversed(values))) == rows
    assert files(tmp_path) == before
    for path in ('/u/w/a', '/u/w/b'):
        with pytest.raises(EffectConflict):
            journal.reserve(context(), 'run:api:1', [descriptor('workspace_create', target_path=path)])


def test_capability_predecessor_can_include_effect_and_native_receipt(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    first = journal.reserve(context(), 'run:api:0', [
        descriptor('download_capability', object_identity='object', generation=0)])
    journal.mark_issued(first)
    next_value = descriptor('download_capability', object_identity='object', generation=1)
    next_value['predecessor_evidence_refs'] = [*first['effect_refs'], 'source_capability_receipt']
    next_reservation = journal.reserve(context(), 'run:api:1', [next_value])
    assert journal.mark_issued(next_reservation)['first_issue'] is True


UUID = '11111111-1111-1111-1111-111111111111'


@pytest.mark.parametrize('first', ['path', 'uuid'])
def test_object_alias_evidence_keeps_existing_capability_identity(tmp_path, first):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    initial = journal.resolve_object_identity(OWNER, 'bvbrc',
        path='/u/w/file' if first == 'path' else None,
        uuid=UUID if first == 'uuid' else None, evidence_refs=['source_original'])
    reservation = journal.reserve(context(), 'run:api:0', [descriptor('download_capability',
        object_identity=initial, generation=0)])
    journal.mark_issued(reservation)
    observed = journal.resolve_object_identity(OWNER, 'bvbrc', path='/u//w/file/',
        uuid=UUID.upper(), evidence_refs=['source_actual_metadata'])
    assert observed == initial
    with pytest.raises(EffectConflict):
        journal.reserve(context(), 'run:api:1', [descriptor('download_capability',
            object_identity=observed, generation=0)])
    next_request = descriptor('download_capability', object_identity=observed, generation=1)
    next_request['predecessor_evidence_refs'] = reservation['effect_refs']
    assert journal.mark_issued(journal.reserve(context(), 'run:api:1', [next_request]))['first_issue']


def test_new_alias_proof_joins_prior_identities_without_changing_receipts(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    path_id = journal.resolve_object_identity(OWNER, 'bvbrc', path='/u/w/file', uuid=None,
        evidence_refs=['source_original_path'])
    uuid_id = journal.resolve_object_identity(OWNER, 'bvbrc', path=None, uuid=UUID,
        evidence_refs=['source_original_uuid'])
    assert path_id != uuid_id
    reserved = journal.reserve(context(), 'run:api:0', [descriptor('download_capability',
        object_identity=path_id, generation=0)])
    journal.mark_issued(reserved)
    before = journal.read(reserved['effect_refs'][0], original_job_owner=OWNER)
    combined = journal.resolve_object_identity(OWNER, 'bvbrc', path='/u/w/file', uuid=UUID,
        evidence_refs=['source_exact_path_uuid_pair'])
    assert combined in {path_id, uuid_id}
    assert journal.read(reserved['effect_refs'][0], original_job_owner=OWNER) == before
    for alias in (path_id, uuid_id, combined):
        with pytest.raises(EffectConflict):
            journal.reserve(context(), 'run:api:1', [descriptor('download_capability',
                object_identity=alias, generation=0)])


def test_alias_discovered_after_two_reservations_prevents_both_from_issuing(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    ids = [journal.resolve_object_identity(OWNER, 'bvbrc', path='/u/w/file', uuid=None,
               evidence_refs=['source_path']),
           journal.resolve_object_identity(OWNER, 'bvbrc', path=None, uuid=UUID,
               evidence_refs=['source_uuid'])]
    reservations = [journal.reserve(context(), f'run:api:{i}', [descriptor('download_capability',
        object_identity=value, generation=0)]) for i, value in enumerate(ids)]
    journal.resolve_object_identity(OWNER, 'bvbrc', path='/u/w/file', uuid=UUID,
        evidence_refs=['source_alias_pair'])
    for value in reservations:
        with pytest.raises(EffectConflict, match='alias_reservation_conflict'):
            journal.mark_issued(value)
        assert journal.read(value['effect_refs'][0], original_job_owner=OWNER)['state'] == 'prepared_not_issued'
    # Explicitly close an unissued attempt; do not select which one to run.
    journal.record_outcome(reservations[0], outcomes(reservations[0], 'not_sent'))
    assert journal.mark_issued(reservations[1])['first_issue']


def test_aliases_are_owner_resource_scoped_and_survive_reopen(tmp_path):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    arguments = {'path': '/u/w/file', 'uuid': UUID, 'evidence_refs': ['source_metadata']}
    one = journal.resolve_object_identity(OWNER, 'bvbrc', **arguments)
    saved = files(tmp_path)
    reopened = SelectedAPIEffects(tmp_path, run_id='run')
    assert reopened.resolve_object_identity(OWNER, 'bvbrc', **arguments) == one
    assert files(tmp_path) == saved
    two = reopened.resolve_object_identity(OWNER, 'other', **arguments)
    three = reopened.resolve_object_identity({**OWNER, 'launch_episode_id': 'other'}, 'bvbrc', **arguments)
    assert len({one, two, three}) == 3


@pytest.mark.parametrize('arguments', [
    {'path': None, 'uuid': None, 'evidence_refs': ['source']},
    {'path': '/u/w/a', 'uuid': None, 'evidence_refs': []},
    {'path': 'relative', 'uuid': None, 'evidence_refs': ['source']},
    {'path': None, 'uuid': 'not-a-uuid', 'evidence_refs': ['source']},
])
def test_invalid_object_aliases_cannot_create_record(tmp_path, arguments):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    with pytest.raises(ValueError):
        journal.resolve_object_identity(OWNER, 'bvbrc', **arguments)
    assert files(tmp_path) == {}


def _reserve_in_process(path, episode, barrier, queue):
    journal = SelectedAPIEffects(path, run_id='run')
    barrier.wait(timeout=10)
    try:
        receipt = journal.reserve(context(episode), 'run:' + episode + ':0', [descriptor()])
        queue.put(('reserved', receipt))
    except EffectConflict as error:
        queue.put(('conflict', error.code))


def test_processes_cannot_reserve_two_original_submissions(tmp_path):
    mp = multiprocessing.get_context('fork')
    barrier, queue = mp.Barrier(2), mp.Queue()
    processes = [mp.Process(target=_reserve_in_process, args=(str(tmp_path), name, barrier, queue))
                 for name in ('api-one', 'api-two')]
    for process in processes:
        process.start()
    result = [queue.get(timeout=15) for _ in processes]
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0
    assert sorted(row[0] for row in result) == ['conflict', 'reserved']
    assert len(list(tmp_path.rglob('intent.json'))) == 1
    queue.close()
