"""Ordered progress through actual Workflow own actions and C4 admission.

The annotation receiver deliberately uses test-only J monitoring units as its
scalar. Scripted tools read real saved C8 observations; an intercepted C2 start
publishes a constrained fixture child return. No model, native job, worker
subprocess, scientific investigation or production scoring policy runs here.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import json
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionStore, canonical, content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import FIELDS, MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.runtime import Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from test_recursive_monitoring import assignment, durable_target
from test_runtime import FixtureController, ScriptedProvider


UNIT = .25
GOAL = 'Exercise received monitoring facts with explicit fixture units'
FORM_SCHEMA = obj({
    'selected': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'episode_progress'}},
    'interpretation': {'type': 'string', 'enum': ['unresolved']},
})


class SavedProgressTools:
    """A completed own action reads one saved observation, without polling."""

    def __init__(self, provider, snapshots):
        self.provider, self.snapshots, self.calls = provider, snapshots, []

    def catalog(self, scope=None):
        return [{'name': 'fixture.saved_progress', 'input_schema': obj({
            'snapshot': {'type': 'string', 'enum': list(self.snapshots)}})}]

    def execute(self, name, arguments, *, scope, operation_key):
        assert name == 'fixture.saved_progress'
        self.calls.append((deepcopy(arguments), operation_key))
        snapshot = self.provider.read_progress(self.snapshots[arguments['snapshot']]['progress_ref'], scope)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': [snapshot['progress_ref'], snapshot['progress_ref']],
            'result': snapshot}


class RecordingController(FixtureController):
    """Retain the exact input consumed by the existing fixture controller."""

    def __init__(self, *args):
        super().__init__(*args)
        self.inputs = []

    def observe(self, label, value, *, is_root):
        self.inputs.append(deepcopy(value.as_record()))
        return super().observe(label, value, is_root=is_root)


def own(name):
    return {'selection': {'kind': 'tool', 'tool': 'fixture.saved_progress',
        'arguments': {'snapshot': name}}, 'report_update': {}}


def child(scope):
    return {'selection': {'kind': 'child', 'goal': 'Return the selected saved fixture observation',
        'scope': scope, 'purpose': 'Return only the selected typed progress references',
        'schema_json': json.dumps(FORM_SCHEMA), 'initial_report_json': json.dumps({
            'selected': [], 'interpretation': 'unresolved'})}, 'report_update': {}}


def saved_settings():
    """A legacy saved settings shape, intentionally lacking the receipt mode."""
    return {'bindings': {'credit': 'fixture.monitoring_units', 'controller': 'fixture.controller',
            'scientific_child_credit': 'fixture.zero_child_credit'},
        'binding_versions': {'credit': {'fixture': 1}, 'controller': {'fixture': 1},
            'scientific_child_credit': {'fixture': 1}},
        'binding_definitions': {'credit': {'kind': 'test_only_monitoring_units'}},
        'controller': None, 'restoration': {'preview_size': 8}}


def seed(store, directory):
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    backend = DurableExecutionStore(directory / 'episode-execution')
    target = durable_target(directory.parent, store, backend)
    provider = ProgressProvider(store, backend, run_id=target['run_id'])
    scope = target['child']['scope']
    snapshots = {'baseline': provider.observe(target['handle'], list(FIELDS), scope,
        permitted_committed_record_types=['source'])}
    sources = []
    for label in ('A', 'B', 'C'):
        source = store._caller_source({'fixture_committed': label}, 'fixture')
        sources.append(source['id'])
        provider.expose(target['handle'], operation_key='fixture-committed-' + label,
            committed_record_refs=[source['id']])
        snapshots[label] = provider.observe(target['handle'], list(FIELDS), scope,
            permitted_committed_record_types=['source'])
    return SimpleNamespace(target=target, snapshots=snapshots, sources=sources,
        provider=provider, scope=scope, run_id=target['run_id'])


def host(store, directory, saved, *, script=(), settings=None, stop_after=3):
    receiver_id = EpisodeRef(saved.run_id, (('annotation', 'root'),)).episode_id
    inherited = assignment(saved.target['handle'],
        known=[saved.snapshots['baseline']['progress_ref']], permitted=['source'])
    context = BindingContext(saved.run_id, receiver_id, 'annotation',
        (('annotation', 'root'),), saved.scope, inherited,
        {'message': {'episode_assignment': inherited}})
    holder, controllers, projections = {}, [], []
    credit = ProgressInformationCredit(saved.provider, information_unit=UNIT)

    def project(store, scope):
        workflow = holder['workflow']
        selection = {'run_id': context.run_id, 'episode_id': context.episode_id,
            **workflow.progress_selection(context)}
        view = credit(context, selection)
        projections.append(deepcopy(view))
        return view

    def controller(path, initial):
        value = RecordingController(str(path), initial, stop_after)
        controllers.append(value)
        return value

    provider = ScriptedProvider(script)
    tools = SavedProgressTools(saved.provider, saved.snapshots)
    options = {'controller_factory': controller, 'project_credit': project,
        'project_child_credit': lambda store, scope, **kwargs: 0,
        'episode_binding_descriptors': [MonitorEpisodes(None).as_record()],
        'role_credit_bindings': {'monitor': {'definition': credit.as_record(), 'project': credit}},
        'execution_binding': {'factory_module': 'fixture', 'factory_name': 'intercepted_start',
            'arguments': {}, 'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}}
    if settings is None:
        workflow = Workflow(store, tools, provider, directory, saved.run_id, **options)
    else:
        workflow = assemble_workflow(store, tools, provider, directory, saved.run_id, settings, **options)
    holder['workflow'] = workflow
    root = workflow.build('annotation', 'root', GOAL, saved.scope, episode_assignment=inherited)
    return SimpleNamespace(workflow=workflow, root=root, context=context, tools=tools,
        provider=provider, controllers=controllers, projections=projections, inherited=inherited)


def publish_fixture_child(host, saved, monkeypatch, reference):
    """Intercept physical start only; next_return consumes real C1/C2/C3 rows."""
    workflow, published = host.workflow, []
    backend = workflow.execution_backend

    def start(handle):
        spec = backend.load_commission(handle)
        form = {'selected': [reference], 'interpretation': 'unresolved'}
        workflow.journal.save('runtime_forms', {'episode_id': spec['child']['episode_id'],
            'facts': canonical({'fixture_saved_progress_refs': [reference]}), 'form': canonical(form)})
        payload = {'version': 'returned_episode_v1', 'handle': handle, 'return_id': '',
            'commission_sha256': content_digest(spec), 'returned_at': '2026-10-21T12:00:00+00:00',
            'outcome': 'closed', 'completion': {'ended_by': 'yield_stop', 'end_reason': '',
                'units_consumed': 0},
            'episode_archive': workflow.archive.store({'fixture_return': True}).descriptor(),
            'result_archive': workflow.archive.store({'form': form}).descriptor(), 'form': form,
            'facts_archive': workflow.archive.store({'fixture_saved_progress_refs': [reference]}).descriptor(),
            'pending_handles': [], 'failure': None}
        payload['return_id'] = content_digest({key: value for key, value in payload.items()
            if key != 'return_id'})
        # Only fixture transport setup uses the backend's private authority.
        # All return loading, admission, receipts, credit and observation use
        # the ordinary host consumers; no independent worker is claimed.
        with backend._connect() as connection:
            token = connection.execute('SELECT execution_token FROM commissions WHERE handle=?',
                (handle,)).fetchone()[0]
        assert backend._claim(handle, token)
        backend.publish_return(handle, token, payload)
        published.append((spec, payload))
        return backend.status(handle)

    monkeypatch.setattr(backend, 'start', start)
    return published


def observations(store, episode_id):
    return [json.loads(row[0]) for row in store.db.execute(
        'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
        (episode_id,))]


def check_monitor(host, saved, references):
    workflow = host.workflow
    context = replace(host.context, role='monitor', path=(('monitor', 'receipt-consumer'),))
    selection = workflow.progress_selection(host.root.source)
    assert workflow.services.progress_selection(context) == selection
    assert selection['initial_progress_refs'] == [saved.snapshots['baseline']['progress_ref']]
    assert selection['known_progress_refs'] == references
    monitor = workflow.episode_bindings.for_role('monitor')
    facts = monitor.facts(context, {})
    assert monitor._received(context) == facts['monitoring_progress_refs'] == references
    assert facts['monitoring_committed_record_refs'] == saved.sources[:2]
    latest = workflow.progress_provider.read_progress(references[-1], saved.scope)
    assert facts['monitoring_observed_at_unix_seconds'] == datetime.fromisoformat(latest['observed_at']).timestamp()
    assert facts['monitoring_execution_state'] == latest['execution_status']['lifecycle_state']
    assert facts['monitoring_result_available'] == latest['result_available']
    schema = obj({'progress': {**deepcopy(FORM_SCHEMA['properties']['selected']),
        'x-source': 'monitoring_progress_refs'}})
    monitor.validate_report(context, {'progress': references}, schema)
    with pytest.raises(ValueError, match='progress_selection_receiver_identity_mismatch'):
        workflow.services.progress_selection(replace(context, run_id='another-run'))


@pytest.mark.parametrize('first_channel', ['own', 'child'])
def test_actual_host_prefixes_preserve_first_receipt_order_and_one_observation(tmp_path, monkeypatch, first_channel):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        first_own = first_channel == 'own'
        script = ([own('A'), child(saved.scope), own('B')] if first_own else
                  [child(saved.scope), own('B'), own('B')])
        # Cover both direct construction's default and the saved current mode.
        settings = None if first_own else {**saved_settings(),
            'episode_progress_receipts': {'version': 'received_progress_order_v1'}}
        bound = host(store, directory, saved, script=script, settings=settings)
        assert bound.workflow.progress_receipt_order == 'received_progress_order_v1'
        child_ref = saved.snapshots['B' if first_own else 'A']['progress_ref']
        published = publish_fixture_child(bound, saved, monkeypatch, child_ref)
        original_observation_count = store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0]
        record = asyncio.run(bound.root.run_async(bound.workflow.context))

        baseline, first, combined = [saved.snapshots[name]['progress_ref'] for name in ('baseline', 'A', 'B')]
        expected = [baseline, first, combined]
        assert record.units_consumed == 3
        assert [controller.scores for controller in bound.controllers] == [[UNIT, UNIT, 0]]
        rows = observations(store, bound.root.source.episode_id)
        assert len(rows) == 3
        assert [row['credit']['credit'] for row in rows] == [UNIT, 2 * UNIT, 2 * UNIT]
        assert [row['step']['delta'] for row in rows] == [UNIT, UNIT, 0]
        assert [context['current_credit'] for context in bound.provider.contexts] == [0, UNIT, 2 * UNIT]
        assert len(bound.tools.calls) == 2 and len(published) == 1
        assert store.db.execute('SELECT count(*) FROM runtime_completion_slots').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == original_observation_count
        assert bound.workflow.progress_provider.received_progress_refs(bound.root.source.episode_id) == [first, combined]
        check_monitor(bound, saved, expected)

        receipt_rows = store.db.execute('SELECT progress_ref,operation_key FROM runtime_progress_receipts '
            'WHERE episode_id=? ORDER BY rowid', (bound.root.source.episode_id,)).fetchall()
        first_index, second_index = (0, 1)
        first_suffix, second_suffix = ('own_progress', 'typed_form') if first_own else ('typed_form', 'own_progress')
        assert [tuple(row) for row in receipt_rows] == [
            (first, f'{saved.run_id}:{bound.root.source.episode_id}:{first_index}:{first_suffix}'),
            (combined, f'{saved.run_id}:{bound.root.source.episode_id}:{second_index}:{second_suffix}')]
        admission = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        assert admission['state'] == 'admitted' and admission['report']['selected'] == [child_ref]
        assert admission['controller_input']['credit'] == (2 * UNIT if first_own else UNIT)
        assert not store.list('assessment') and not store.list('observation')
        assert bound.projections[-1]['monitoring_information_contributions'] == [
            {'progress_ref': first, 'target_handle': saved.target['handle'], 'new_fact_count': 1},
            {'progress_ref': combined, 'target_handle': saved.target['handle'], 'new_fact_count': 1}]


def test_saved_absent_mode_keeps_legacy_grouped_selection(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        settings = saved_settings()
        original_settings = deepcopy(settings)
        bound = host(store, directory, saved,
            script=[own('A'), child(saved.scope), own('B')], settings=settings)
        assert bound.workflow.progress_receipt_order == 'legacy_grouped_v1'
        first, combined = [saved.snapshots[name]['progress_ref'] for name in ('A', 'B')]
        publish_fixture_child(bound, saved, monkeypatch, combined)
        asyncio.run(bound.root.run_async(bound.workflow.context))
        assert settings == original_settings and 'episode_progress_receipts' not in settings
        assert bound.controllers[0].scores == [UNIT, 0, 0]
        assert [row['credit']['credit'] for row in observations(store, bound.root.source.episode_id)] == [UNIT] * 3
        # The old grouped representation retains forms before scanned own refs.
        assert bound.workflow.progress_provider.received_progress_refs(bound.root.source.episode_id) == [combined]
        check_monitor(bound, saved, [saved.snapshots['baseline']['progress_ref'], combined, first])
        assert store.db.execute("SELECT count(*) FROM runtime_progress_deliveries WHERE operation_key LIKE '%:own_progress'").fetchone()[0] == 0


def test_frozen_c4_and_f2_replay_survive_later_receipts_without_reprojection(tmp_path, monkeypatch):
    directory = tmp_path / 'run'
    with Store(tmp_path / 'state') as store:
        saved = seed(store, directory)
        bound = host(store, directory, saved, script=[own('A'), child(saved.scope), own('B')])
        published = publish_fixture_child(bound, saved, monkeypatch, saved.snapshots['B']['progress_ref'])
        asyncio.run(bound.root.run_async(bound.workflow.context))
        episode_id = bound.root.source.episode_id
        original_observations = observations(store, episode_id)
        original_controller_inputs = deepcopy(bound.controllers[0].inputs)
        original_slots = [bound.workflow.completions.slot(episode_id, index) for index in range(3)]
        original_admission = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        spec, returned = published[0]
        bound.workflow.progress_provider.receive_outcome(episode_id,
            {'status': 'completed', 'progress_refs': [saved.snapshots['C']['progress_ref']]},
            saved.scope, 'fixture-later-received-progress')
        assert bound.workflow.source_credit_view(bound.root.source)['credit'] == 3 * UNIT

    with Store(tmp_path / 'state') as reopened:
        saved.provider = ProgressProvider(reopened, DurableExecutionStore(directory / 'episode-execution'), run_id=saved.run_id)
        restored = host(reopened, directory, saved)

        def forbidden(*args, **kwargs):
            pytest.fail('frozen historical input must not receive or project current facts')

        receiver = ReceiverBindingV1(reopened, restored.workflow.journal,
            original_admission['original_decision_index'], restored.workflow.returned_request(spec).report_contract,
            forbidden, forbidden, forbidden, forbidden)
        assert admit_return(spec, returned, receiver) == original_admission
        monkeypatch.setattr(restored.workflow, 'source_credit_view', forbidden)
        monkeypatch.setattr(restored.workflow.progress_provider, 'receive_outcome', forbidden)
        monkeypatch.setattr(restored.workflow.progress_provider, 'receive_form', forbidden)
        replay = asyncio.run(restored.root.run_async(restored.workflow.context))
        assert replay.units_consumed == 3
        assert restored.controllers[0].scores == [UNIT, UNIT, 0]
        assert restored.controllers[0].inputs == original_controller_inputs
        assert observations(reopened, episode_id) == original_observations
        assert [restored.workflow.completions.slot(episode_id, index) for index in range(3)] == original_slots
        assert not restored.provider.contexts and not restored.tools.calls
        assert reopened.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
        assert restored.workflow.progress_provider.received_progress_refs(episode_id) == [
            saved.snapshots[name]['progress_ref'] for name in ('A', 'B', 'C')]


def test_committed_own_outcome_recovers_before_projection_without_reexecuting_tool(tmp_path, monkeypatch):
    directory = tmp_path / 'run'
    with Store(tmp_path / 'state') as store:
        saved = seed(store, directory)
        interrupted = host(store, directory, saved, script=[own('A')])
        episode_id = interrupted.root.source.episode_id

        def interrupt_before_receipt(*args, **kwargs):
            action = interrupted.workflow.journal.row('runtime_actions', episode_id, 0)
            assert json.loads(action['result'])['progress_refs'] == [saved.snapshots['A']['progress_ref']] * 2
            assert action['credit'] is None and store.db.in_transaction
            raise KeyboardInterrupt('fixture interruption after committed outcome')

        with monkeypatch.context() as patched:
            patched.setattr(interrupted.workflow.progress_provider, 'receive_outcome', interrupt_before_receipt)
            with pytest.raises(KeyboardInterrupt, match='after committed outcome'):
                asyncio.run(interrupted.root.run_async(interrupted.workflow.context))
        assert len(interrupted.tools.calls) == 1
        assert observations(store, episode_id) == []
        assert interrupted.workflow.progress_provider.received_progress_refs(episode_id) == []
        assert interrupted.workflow.completions.slot(episode_id, 0) is None

    with Store(tmp_path / 'state') as reopened:
        saved.provider = ProgressProvider(reopened, DurableExecutionStore(directory / 'episode-execution'), run_id=saved.run_id)
        recovered = host(reopened, directory, saved, script=[child(saved.scope), own('B')])
        publish_fixture_child(recovered, saved, monkeypatch, saved.snapshots['B']['progress_ref'])
        record = asyncio.run(recovered.root.run_async(recovered.workflow.context))
        assert record.units_consumed == 3 and recovered.controllers[0].scores == [UNIT, UNIT, 0]
        # Recovery delivers the existing A outcome; only the later B read runs.
        assert [call[0] for call in recovered.tools.calls] == [{'snapshot': 'B'}]
        assert [row['credit']['credit'] for row in observations(reopened, episode_id)] == [UNIT, 2 * UNIT, 2 * UNIT]
        assert recovered.workflow.progress_provider.received_progress_refs(episode_id) == [
            saved.snapshots[name]['progress_ref'] for name in ('A', 'B')]
        first_key = f'{saved.run_id}:{episode_id}:0:own_progress'
        assert reopened.db.execute('SELECT count(*) FROM runtime_progress_deliveries WHERE operation_key=?',
            (first_key,)).fetchone()[0] == 1
        assert reopened.db.execute('SELECT count(*) FROM runtime_completion_slots').fetchone()[0] == 3
