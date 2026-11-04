"""Selected native receipts, read-only admission and exact own acquisition.

The tiny job/check/parser are actual native work. Parent selections, receipt
prefixes and numerical policies are fixtures; these tests run no model.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.resource_information import ResourceInformation
from gene_annotation_episode.resource_episodes import LAUNCH_VERSION, RESULTS_VERSION, ResourceEpisodes
from gene_annotation_episode.homology_episodes import obj
from test_homology_jobs import wait_terminal
from test_resource_episode_branches import resources, context, selected


def record_episode(r, bound):
    request = {'message': {'episode_assignment': dict_plain(bound.assignment), 'scope': r.scope}}
    with r.store.transaction():
        r.journal.save('runtime_episodes', {'episode_id': bound.episode_id,
            'path': canonical(bound.path), 'request': canonical(request),
            'initial_credit': 0, 'state': 'running'})


def dict_plain(value):
    from gene_annotation_episode.communication import plain
    return plain(value)


def select_check(r, bound, index=0, *, tool='homology.check_handoff', arguments=None):
    arguments = {} if arguments is None else arguments
    selection = {'kind': 'tool', 'tool': tool, 'arguments': arguments}
    with r.store.transaction():
        r.journal.save('runtime_actions', {'episode_id': bound.episode_id, 'decision_index': index,
            'action': canonical(selection), 'result': None, 'credit': None})
    return f'{bound.run_id}:{bound.episode_id}:{index}'


def checked_job(r, *, key='native', persist=True):
    assigned = r.binding.prepare_assignment(context(r, 'launch', r.launch), 'launch_local',
        selected(r), r.scope, 'assignment:' + key)
    bound = context(r, 'launch_local', assigned, key=key)
    record_episode(r, bound)
    job_ref = assigned['adapter_assignment']['job_ref']
    r.jobs.configure(job_ref, 2)
    r.jobs.stage(job_ref)
    r.jobs.submit(job_ref)
    operation = select_check(r, bound)
    outcome = asyncio.run(r.binding.execute(bound, 'homology.check_handoff', {}, operation))
    assert outcome['status'] == 'completed'
    if persist:
        save_outcome(r, bound, 0, outcome)
    return bound, operation, outcome


def save_outcome(r, bound, index, outcome):
    with r.store.transaction():
        r.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (canonical(outcome), bound.run_id, bound.episode_id, index))


def receipt_services(r, selections):
    def selection(bound):
        refs, initial = selections.get(bound.episode_id, ([], []))
        return {'run_id': bound.run_id, 'episode_id': bound.episode_id,
            'known_record_refs': deepcopy(refs), 'initial_known_record_refs': deepcopy(initial)}
    r.services.record_selection = selection
    r.binding = ResourceEpisodes(r.services, resource_adapters=[r.adapter])


def forbid_checks(monkeypatch, r):
    def forbidden(*args, **kwargs):
        raise AssertionError('receiving read must not check or poll native work')
    for method in ('check_handoff', 'receive', 'status', 'handoff', '_handle'):
        monkeypatch.setattr(r.jobs, method, forbidden)


def test_actual_selected_check_publication_and_crash_recovery_without_native_recheck(resources, monkeypatch):
    r = resources
    bound, operation, outcome = checked_job(r, persist=False)
    assert r.journal.row('runtime_actions', bound.episode_id, 0)['result'] is None
    reference, = outcome['resource_information_refs']
    source = r.store.get(reference)
    reader = ResourceInformation(r.store, run_id=bound.run_id, jobs=r.jobs)
    body = reader.read_handoff_source(reference, scope=r.scope)
    assert set(body) == {'version', 'run_id', 'episode_id', 'operation_key', 'tool_name',
        'arguments', 'scope', 'assignment_sha256', 'query_ref', 'registry_ref', 'job',
        'execution_handoff', 'outcome'}
    assert body['job'] == {'job_ref': outcome['execution_handoff']['execution_handle'],
        'query_ref': r.query, 'cpu': 2, 'search_mode': 'maximum_sensitivity'}
    assert body['outcome']['record_refs'] == []
    assert 'resource_information_refs' not in body['outcome']
    assert source['retrieved_at'] == outcome['execution_handoff']['checked_at']
    assert source['operand_refs'] == [r.query]
    assert source['text_ref'] == source['artifact_ref']
    assert r.store.get_artifact(source['artifact_ref']) == canonical(body).encode()
    forbid_checks(monkeypatch, r)
    assert reader.read_handoff_source(reference, scope=r.scope) == body
    assert asyncio.run(r.binding.execute(bound, 'homology.check_handoff', {}, operation)) == outcome
    assert r.store.db.execute("SELECT count(*) FROM records WHERE json_extract(data,'$.provider')="
        "'episode.resource_handoff'").fetchone()[0] == 1
    save_outcome(r, bound, 0, {**outcome, 'pending_work_after_action': []})
    assert reader.selected_handoff(bound, 'homology.check_handoff', {}, operation) == outcome


@pytest.mark.parametrize('change', ['arguments', 'tool', 'assignment', 'receiver', 'scope'])
def test_published_operation_rejects_changed_identity(resources, change):
    r = resources
    bound, operation, outcome = checked_job(r)
    reader = r.adapter.information
    tool, arguments = 'homology.check_handoff', {}
    if change == 'arguments':
        arguments = {'changed': True}
    elif change == 'tool':
        tool = 'homology.environment'
    elif change == 'assignment':
        assignment = dict_plain(bound.assignment)
        assignment['constraints']['cpu'] = 1
        bound = replace(bound, assignment=assignment)
    elif change == 'receiver':
        bound = replace(bound, episode_id='episode_other')
    else:
        bound = replace(bound, scope={'subject_refs': r.scope['subject_refs'], 'segments': []})
    with pytest.raises(ValueError, match='resource_information_identity_conflict'):
        reader.selected_handoff(bound, tool, arguments, operation)


def test_source_admission_is_exact_schema_declared_and_read_only(resources, monkeypatch):
    r = resources
    bound, operation, outcome = checked_job(r)
    reference, = outcome['resource_information_refs']
    handoff = outcome['execution_handoff']
    receiver = context(r, 'annotation', {}, key='scientific')
    schema = obj({'nested': {'type': 'array', 'items': obj({
        'one': {'type': ['object', 'null'], 'x-source': 'execution_handoff'},
        'many': {'type': 'array', 'x-source': 'execution_handoffs'},
        'ordinary': {'type': 'object'}})}})
    form = {'nested': [{'one': handoff, 'many': [handoff, handoff], 'ordinary': handoff},
        {'one': None, 'many': [], 'ordinary': {'invented': True}}]}
    forbid_checks(monkeypatch, r)
    before = r.store.db.total_changes
    assert r.adapter.information.references_for_form(receiver, form, schema) == [reference]
    assert r.binding.received_form_references(receiver, form, schema, 'admit') == [reference]
    assert r.adapter.information.references_for_form(receiver, {'unknown': handoff}, obj({})) == []
    assert r.store.db.total_changes == before
    changed = deepcopy(handoff)
    changed['checked_at'] = '2020-01-01T00:00:00+00:00'
    with pytest.raises(ValueError, match='resource_information_handoff_proof_missing'):
        r.adapter.information.references_for_form(receiver, changed, {'x-source': 'execution_handoff'})
    outside = {'subject_refs': []}
    with pytest.raises(ValueError, match='outside_scope'):
        r.adapter.information.read_handoff_source(reference, scope=outside)


def test_launch_closes_with_received_child_proof_and_results_initial_is_inherited(resources, monkeypatch):
    r = resources
    child, operation, outcome = checked_job(r)
    handoff = outcome['execution_handoff']
    parent = context(r, 'launch', r.launch, key='receiving_launch')
    reference, = outcome['resource_information_refs']
    receipt_services(r, {parent.episode_id: ([reference], [])})
    forbid_checks(monkeypatch, r)
    facts = r.binding.facts(parent, {})
    assert facts['execution_handoff'] == handoff
    assert facts['execution_handoffs'] == [handoff]
    r.binding.validate_report(parent, {'handoff': handoff}, obj({
        'handoff': r.binding.fact_sources('launch')['execution_handoff']['report_schema']}))
    assigned = r.binding.prepare_assignment(context(r, 'annotation', {}), 'results', {
        'version': RESULTS_VERSION, 'handoff': handoff, 'requested_data_selector': {}},
        r.scope, 'results-assignment')
    result = context(r, 'results', assigned, key='results')
    assert r.binding.initial_references(result) == [reference]
    receipt_services(r, {result.episode_id: ([reference], [reference])})
    assert r.binding.facts(result, {})['execution_handoff'] == handoff
    assert r.binding.facts(result, {})['job_handoff'] == outcome['result']['handoff']
    assert r.binding.initial_references(parent) == []


def test_multiple_received_physical_identities_and_latest_original_check(resources, monkeypatch):
    r = resources
    child1, _, first = checked_job(r, key='first')
    child2, _, second = checked_job(r, key='second')
    operation = select_check(r, child1, 1)
    later = asyncio.run(r.binding.execute(child1, 'homology.check_handoff', {}, operation))
    save_outcome(r, child1, 1, later)
    parent = context(r, 'launch', r.launch, key='parent_multiple')
    references = [*second['resource_information_refs'], *first['resource_information_refs'],
        *later['resource_information_refs']]
    receipt_services(r, {parent.episode_id: (references, [])})
    forbid_checks(monkeypatch, r)
    facts = r.binding.facts(parent, {})
    assert facts['execution_handoff'] is None
    expected = sorted([later['execution_handoff'], second['execution_handoff']],
        key=lambda value: (value['resource_selection']['capability_binding_ref'], value['execution_handle']))
    assert facts['execution_handoffs'] == expected
    assert r.binding.resolve(parent, later['execution_handoff']['checked_at'], 'resource_check_timestamp')
    r.binding.validate_report(parent, {'all': expected}, obj({
        'all': r.binding.fact_sources('launch')['execution_handoffs']['report_schema']}))


def test_selected_parent_recheck_publishes_new_original_proof_and_replays(resources, monkeypatch):
    r = resources
    child, _, original = checked_job(r)
    parent = context(r, 'launch', r.launch, key='parent_check')
    record_episode(r, parent)
    args = {'handoff': original['execution_handoff']}
    operation = select_check(r, parent, tool='resource.check_handoff', arguments=args)
    outcome = asyncio.run(r.binding.execute(parent, 'resource.check_handoff', args, operation))
    assert outcome['status'] == 'completed'
    assert outcome['resource_information_refs'] != original['resource_information_refs']
    forbid_checks(monkeypatch, r)
    assert asyncio.run(r.binding.execute(parent, 'resource.check_handoff', args, operation)) == outcome
    assert r.adapter.information.read_handoff_source(outcome['resource_information_refs'][0],
        scope=r.scope)['outcome']['execution_handoff'] == outcome['execution_handoff']


@pytest.mark.parametrize('change,code', [
    ('selection', 'identity_conflict'), ('outcome', 'saved_outcome_conflict'),
    ('job', 'job_identity_conflict'), ('source_time', 'source_identity_conflict'),
    ('artifact', 'artifact_digest_mismatch')])
def test_recognized_changed_proof_fails_specifically(resources, change, code):
    r = resources
    child, _, outcome = checked_job(r)
    reference = outcome['resource_information_refs'][0]
    source = r.store.get(reference)
    if change == 'selection':
        row = r.journal.row('runtime_actions', child.episode_id, 0)
        action = json.loads(row['action'])
        action['arguments'] = {'changed': True}
        with r.store.transaction():
            r.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=?',
                (canonical(action), child.run_id, child.episode_id))
    elif change == 'outcome':
        altered = deepcopy(outcome)
        altered['result']['sample']['native_returncode'] = 9
        save_outcome(r, child, 0, altered)
    elif change == 'job':
        with r.jobs.db:
            r.jobs.db.execute("UPDATE orders SET search_mode='native_defaults' WHERE job_ref=?",
                (outcome['execution_handoff']['execution_handle'],))
    elif change == 'source_time':
        source['retrieved_at'] = '2020-01-01T00:00:00+00:00'
        with r.store.transaction():
            r.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), reference))
    else:
        artifact = r.store.get(source['artifact_ref'])
        (r.store.path / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']).write_bytes(b'changed')
    with pytest.raises(ValueError, match=code):
        r.adapter.information.read_handoff_source(reference, scope=r.scope)
    if change == 'job':
        with r.jobs.db:
            r.jobs.db.execute("UPDATE orders SET search_mode='maximum_sensitivity' WHERE job_ref=?",
                (outcome['execution_handoff']['execution_handle'],))


def test_failed_and_unrelated_tools_publish_nothing_and_unrelated_source_is_none(resources):
    r = resources
    bound = context(r, 'launch', r.launch)
    failed = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
        'result': None, 'feedback': {'code': 'receiving_interface_unavailable'}}
    assert r.adapter.information.publish_handoff(bound, 'resource.check_handoff', {}, failed, 'failed') == failed
    unrelated = {**failed, 'status': 'completed'}
    assert r.adapter.information.publish_handoff(bound, 'resource.inspect', {}, unrelated, 'inspect') == unrelated
    with r.store.transaction():
        source = r.store._caller_source({'fixture': True}, 'fixture.unrelated')
    assert r.adapter.information.read_handoff_source(source['id'], scope=r.scope) is None
    assert r.adapter.information._sources() == []


def test_old_incomplete_proof_is_rejected_without_migration_or_native_work(resources, monkeypatch):
    r = resources
    bound, _, outcome = checked_job(r)
    source = r.store.get(outcome['resource_information_refs'][0])
    body = r.adapter.information.read_handoff_source(source['id'], scope=r.scope)
    body.pop('outcome')
    with r.store.transaction():
        artifact = r.store.artifact(canonical(body), 'application/json')
        old = r.store.put('source', {key: value for key, value in source.items()
            if key not in {'id', 'record_type', 'origin', 'artifact_ref', 'text_ref'}} | {
            'artifact_ref': artifact, 'text_ref': artifact}, origin='tool')
    forbid_checks(monkeypatch, r)
    before = r.store.db.total_changes
    with pytest.raises(ValueError, match='resource_information_malformed_proof'):
        r.adapter.information.read_handoff_source(old['id'], scope=r.scope)
    with pytest.raises(ValueError, match='resource_information_malformed_proof'):
        r.adapter.information.references_for_form(bound, outcome['execution_handoff'],
            {'x-source': 'execution_handoff'})
    assert r.store.db.total_changes == before


def test_own_recorded_legacy_check_stays_readable_without_manufacturing_a_source(resources, monkeypatch):
    r = resources
    bound, _, first = checked_job(r)
    operation = select_check(r, bound, 1)
    native = r.jobs.check_handoff(first['result']['handoff'])
    legacy = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
        'result': native, 'feedback': None, 'execution_handoff': r.adapter._wrap(bound, native)}
    save_outcome(r, bound, 1, legacy)
    forbid_checks(monkeypatch, r)
    before = r.store.db.total_changes
    assert r.adapter.information.selected_handoff(bound, 'homology.check_handoff', {}, operation) is None
    facts = r.binding.facts(bound, {})
    assert facts['execution_handoff'] == legacy['execution_handoff']
    with pytest.raises(ValueError, match='resource_information_handoff_proof_missing'):
        r.adapter.information.references_for_form(bound, legacy['execution_handoff'],
            {'x-source': 'execution_handoff'})
    assert r.store.db.total_changes == before
    assert len(r.adapter.information._sources()) == 1


def test_own_partial_publication_rows_keep_exact_provenance_and_exclude_foreign_outcomes(resources, monkeypatch):
    r = resources
    child, _, outcome = checked_job(r)
    handoff = outcome['execution_handoff']
    wait_terminal(r.jobs, handoff['execution_handle'])
    assigned = r.binding.prepare_assignment(context(r, 'annotation', {}), 'results', {
        'version': RESULTS_VERSION, 'handoff': handoff, 'requested_data_selector': {'offset': 0, 'limit': 10}},
        r.scope, 'results-assignment')
    bound = context(r, 'results', assigned, key='partial_result')
    record_episode(r, bound)
    args = {'limit': 10}
    operation = select_check(r, bound, tool='homology.extract', arguments=args)
    original_put = r.store.put
    def fail_observation(kind, data, **kwargs):
        if kind == 'observation':
            raise ContractError('fixture_publication_failure')
        return original_put(kind, data, **kwargs)
    monkeypatch.setattr(r.store, 'put', fail_observation)
    acquired = asyncio.run(r.binding.execute(bound, 'homology.extract', args, operation))
    assert acquired['status'] == 'partial'
    save_outcome(r, bound, 0, acquired)  # Actual work saved; credit still null.
    monkeypatch.setattr(r.store, 'put', original_put)
    forbid_checks(monkeypatch, r)
    before = r.store.db.total_changes
    rows = r.adapter.information.own_result_rows(bound)
    assert len(rows) == 1
    row, = rows
    assert row == {'snapshot_ref': acquired['result']['snapshot_ref'], 'query_ref': r.query,
        'execution_context': {'job_ref': handoff['execution_handle'], 'registry_ref': r.jobs.config['registry_ref']},
        **acquired['result']['publication_rows'][0]}
    assert row['record_type'] == 'reference' and row['source_byte_spans']
    assert r.store.db.total_changes == before
    assert r.adapter.information.own_result_rows(replace(bound, episode_id='episode_foreign')) == []
    assert r.adapter.information.own_result_rows(child) == []
    # A global witness is not this episode's acquisition unless its exact row
    # appeared in the original saved own outcome.
    altered = deepcopy(acquired)
    altered['result']['publication_rows'] = []
    save_outcome(r, bound, 0, altered)
    assert r.adapter.information.own_result_rows(bound) == []
    save_outcome(r, bound, 0, acquired)
    with r.store.transaction():
        r.store.db.execute('UPDATE homology_result_witnesses SET source_byte_spans=? '
            'WHERE snapshot_ref=? AND ordinal=?', ('[]', row['snapshot_ref'], row['ordinal']))
    with pytest.raises(ValueError, match='result_witness_conflict'):
        r.adapter.information.own_result_rows(bound)
