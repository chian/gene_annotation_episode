"""Current delivery evidence at the actual shared-loop observation boundary.

Decisions, units, progress facts and child processes are explicit engineering
fixtures. Real Workflow/C1/C2/C3/C4/F2, immutable C8 readers and the standard
signed YieldController run here. These checks perform no model or science work.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from method_loop.archive import ArchivedRecord, JsonArchive
from method_loop.durable import DurableExecutionStore, canonical, content_digest
from method_loop.identities import EpisodeRef, UnitRef

from gene_annotation_episode.completion_evidence import CompletionEvidence
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, ProgressProvider
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit
from gene_annotation_episode.local_return_history import LocalReturnHistory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.runtime import (ExecutionContextController, Record, Workflow,
    WorkflowError, assemble_workflow)
from gene_annotation_episode.state import Store
from test_progress_receipt_runtime import (GOAL, UNIT, SavedProgressTools, child,
    observations, own, saved_settings, seed)
from test_recursive_monitoring import assignment
from test_runtime import ScriptedProvider


CURRENT = 'completed_action_inputs_binding_v1'
CONTEXT = 'completed_action_estimation_context_v5'
BINDING = {'kind': 'explicit_test_received_progress_units', 'unit': UNIT}


def forbidden(*args, **kwargs):
    raise AssertionError('completion capture must only read original recorded evidence')


class RecordingYieldController(YieldController):
    def __init__(self, *args, **kwargs):
        self.inputs = []
        super().__init__(*args, **kwargs)

    def observe(self, label, value, *, is_root):
        self.inputs.append(deepcopy(value.as_record()))
        return super().observe(label, value, is_root=is_root)


def host(store, directory, saved, *, script=(), stop_after=3, settings=None,
         signed_projection=False, estimator_hook=None, current=True):
    """Script choices only; the ordinary Episode owns every actual UnitRef."""
    receiver = EpisodeRef(saved.run_id, (('annotation', 'root'),)).episode_id
    inherited = assignment(saved.target['handle'],
        known=[saved.snapshots['baseline']['progress_ref']], permitted=['source'])
    context = BindingContext(saved.run_id, receiver, 'annotation',
        (('annotation', 'root'),), saved.scope, inherited,
        {'message': {'episode_assignment': inherited}})
    holder, controllers, estimates, projections = {}, [], [], []
    credit = ProgressInformationCredit(saved.provider, information_unit=UNIT)

    def project(bound_store, scope):
        workflow = holder['workflow']
        selection = {'run_id': context.run_id, 'episode_id': context.episode_id,
            **workflow.progress_selection(context)}
        result = credit(context, selection)
        if signed_projection:
            # Explicit fixture correction policy over ACTUALLY received C8 refs.
            # The packet neither supplies nor transforms these units.
            received = set(selection['known_progress_refs']) - set(selection['initial_progress_refs'])
            result = {**result, 'credit': {0: 0, 1: 5.25, 2: 2.0, 3: 2.125}[len(received)]}
        projections.append(deepcopy(result))
        return result

    def estimate(history, parameters, contexts):
        assert len(history) == len(contexts)
        if history:
            estimates.append((tuple(history), deepcopy(contexts)))
            if estimator_hook is not None:
                estimator_hook(holder['workflow'], history, contexts)
        # This declared fixture estimator controls only test termination through
        # the production numerical comparison; there is no runtime turn cap.
        gain = 0 if len(history) >= stop_after else 1
        return YieldEstimate(len(history), NumericBand.exact(gain), parameters,
            {'fixture': 'explicit_completed_action_estimate'})

    def controller(path, initial):
        value = RecordingYieldController(str(path), initial, 0, estimate_with_context=estimate)
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
        if not current:
            options['completed_action_inputs_version'] = None
        workflow = Workflow(store, tools, provider, directory, saved.run_id,
            credit_binding=BINDING, **options)
    else:
        workflow = assemble_workflow(store, tools, provider, directory, saved.run_id, settings, **options)
    holder['workflow'] = workflow
    root = workflow.build('annotation', 'root', GOAL, saved.scope, episode_assignment=inherited)
    return SimpleNamespace(workflow=workflow, root=root, context=context, provider=provider,
        tools=tools, controllers=controllers, estimates=estimates, projections=projections)


class ChildTransport:
    """Intercept physical start; consume actual immutable C3 via Workflow C4."""
    def __init__(self, bound, saved, monkeypatch, *, publish_order=None, failed=False):
        self.bound, self.saved = bound, saved
        self.workflow, self.backend = bound.workflow, bound.workflow.execution_backend
        self.started, self.published = [], []
        self.tokens = {}
        self.publish_order, self.failed = publish_order, failed
        monkeypatch.setattr(self.backend, 'start', self.start)

    def start(self, handle):
        spec = self.backend.load_commission(handle)
        if handle not in self.tokens:
            with self.backend._connect() as db:
                token = db.execute('SELECT execution_token FROM commissions WHERE handle=?',
                    (handle,)).fetchone()[0]
            assert self.backend._claim(handle, token)
            self.tokens[handle] = token
            self.started.append(spec)
        if self.publish_order is not None and len(self.started) == len(self.publish_order):
            for index in self.publish_order:
                self.publish(self.started[index], ('A', 'B', 'C')[index], failed=self.failed)
        return self.backend.status(handle)

    def publish(self, spec, snapshot='A', *, failed=False):
        if any(item[0]['handle'] == spec['handle'] for item in self.published):
            return
        reference = self.saved.snapshots[snapshot]['progress_ref']
        form = {'selected': [reference], 'interpretation': 'unresolved'}
        self.workflow.journal.save('runtime_forms', {'episode_id': spec['child']['episode_id'],
            'facts': canonical({'fixture_saved_progress_refs': [reference]}), 'form': canonical(form)})
        payload = {'version': 'returned_episode_v1', 'handle': spec['handle'], 'return_id': '',
            'commission_sha256': content_digest(spec),
            'returned_at': datetime.now(timezone.utc).isoformat(), 'outcome': 'closed',
            'completion': {'ended_by': 'yield_stop', 'end_reason': '', 'units_consumed': 0},
            'episode_archive': self.workflow.archive.store({'fixture_return': True}).descriptor(),
            'result_archive': self.workflow.archive.store({'form': form}).descriptor(), 'form': form,
            'facts_archive': None, 'pending_handles': [], 'failure': None}
        if failed:
            payload.update(outcome='execution_failed', completion=None, episode_archive=None,
                result_archive=None, form=None, failure={'code': 'execution_failed',
                    'affected_refs': [spec['handle']], 'diagnostic_ref': None, 'partial_record_refs': []})
        payload['return_id'] = content_digest({key: value for key, value in payload.items()
            if key != 'return_id'})
        self.backend.publish_return(spec['handle'], self.tokens[spec['handle']], payload)
        self.published.append((spec, payload))


def guard_capture(bound, monkeypatch):
    """Forbid side effects only while the actual producer is running."""
    original = CompletionEvidence.capture
    captured = []

    def capture(producer, episode_id, **kwargs):
        workflow, store = bound.workflow, bound.workflow.store
        before = store.db.total_changes
        with monkeypatch.context() as patched:
            for name in ('status', 'start', 'commission', 'acknowledge', 'publish_return',
                         'return_page', 'load_commission', 'record_progress', '_claim', 'wait_events'):
                patched.setattr(workflow.execution_backend, name, forbidden)
            for name in ('save', 'measure', 'elapsed_view', 'commission_returned'):
                patched.setattr(workflow.journal, name, forbidden)
            for name in ('transaction', 'artifact', 'put', 'get', 'get_artifact'):
                patched.setattr(store, name, forbidden)
            for name in ('source_credit_view', 'project_credit', 'archive_reference', 'pending_work'):
                patched.setattr(workflow, name, forbidden)
            patched.setattr(LocalReturnHistory, 'capture', forbidden)
            patched.setattr(ProgressProvider, 'observe', forbidden)
            patched.setattr(ArchivedRecord, 'load', forbidden)
            patched.setattr(ArchivedRecord, 'iter_json', forbidden)
            patched.setattr(JsonArchive, 'store', forbidden)
            for controller in bound.controllers:
                patched.setattr(controller, 'observe', forbidden)
            store.db.execute('PRAGMA query_only=ON')
            try:
                value = original(producer, episode_id, **kwargs)
                assert store.db.total_changes == before
            finally:
                store.db.execute('PRAGMA query_only=OFF')
        captured.append((kwargs['unit_ref'], deepcopy(kwargs['controller_input'].as_record()), value))
        return value

    monkeypatch.setattr(CompletionEvidence, 'capture', capture)
    return captured


def run(bound):
    return asyncio.run(bound.root.run_async(bound.workflow.context))


def packet(context):
    assert context['version'] == CONTEXT
    return context['current_completion_evidence']


def test_actual_out_of_order_returns_align_signed_raw_deltas_current_evidence_and_on_unit(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        seen_unobserved = []

        def inspect(workflow, history, contexts):
            current = packet(contexts[-1])
            index = current['original_decision_index']
            selected = workflow.local_return_history.read_return(current['episode_id'], index)
            sample = selected['sample']
            assert sample['observation_state'] == 'unobserved'
            assert sample['unit_ref'] is sample['raw_controller_delta'] is None
            assert sample['completion_sequence'] == len(history) - 1
            assert current['received_progress_refs'] == sample['received_progress_refs']
            assert current['progress_records'] and current['child_return']['return_id'] == sample['return_id']
            assert workflow.journal.row('runtime_observations', current['episode_id'], len(history) - 1) is None
            # E2 selection-time history stays frozen; current C4 is separate.
            assert contexts[-1]['local_return_history_at_selection']['samples'] == []
            assert current['unit_ref'] == UnitRef(current['episode_id'], len(history) - 1).as_record()
            assert json.loads(store.db.execute('SELECT data FROM runtime_estimation_contexts '
                'WHERE episode_id=? AND decision_index=?', (current['episode_id'], index)).fetchone()[0]) == contexts[-1]
            seen_unobserved.append(index)

        bound = host(store, directory, saved, script=[child(saved.scope) for _ in range(3)],
            signed_projection=True, estimator_hook=inspect)
        transport = ChildTransport(bound, saved, monkeypatch, publish_order=[2, 0, 1])
        captures = guard_capture(bound, monkeypatch)
        result = run(bound)
        episode_id = bound.root.source.episode_id
        rows = observations(store, episode_id)
        assert result.units_consumed == 3 and seen_unobserved == [2, 0, 1]
        assert bound.controllers[0].estimator.scores == (5.25, -3.25, .125)
        assert [row['decision_index'] for row in rows] == [2, 0, 1]
        assert len(transport.started) == len(transport.published) == len(captures) == len(rows) == 3
        for sequence, (row, captured) in enumerate(zip(rows, captures)):
            unit_ref, original, evidence = captured
            slot = bound.workflow.completions.slot(episode_id, sequence)
            admission = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions '
                'WHERE parent_episode_id=? AND original_decision_index=?',
                (episode_id, row['decision_index'])).fetchone()[0])
            assert unit_ref.as_record() == row['unit_ref'] == evidence['unit_ref']
            assert original == row['credit'] == slot['controller_input'] == admission['controller_input']
            assert 'estimation_context' not in original and 'current_completion_evidence' not in original
            assert evidence['child_return']['admission_id'] == admission['admission_id']
            assert evidence['received_record_refs'] == admission['received_record_refs']
            assert bound.estimates[sequence][0] == (5.25, -3.25, .125)[:sequence + 1]
            assert [packet(value)['original_decision_index'] for value in
                bound.estimates[sequence][1]] == [2, 0, 1][:sequence + 1]
        history = bound.workflow.local_return_history.capture(episode_id,
            credit_kind='scientific', credit_binding=BINDING)
        assert [sample['raw_controller_delta'] for sample in history['samples']] == [5.25, -3.25, .125]


def test_repeated_actual_progress_delivery_retains_refs_without_manufacturing_gain(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        bound = host(store, directory, saved, script=[own('A'), own('A')], stop_after=2)
        captures = guard_capture(bound, monkeypatch)
        result = run(bound)
        rows = observations(store, bound.root.source.episode_id)
        reference = saved.snapshots['A']['progress_ref']
        assert result.units_consumed == 2
        assert bound.controllers[0].estimator.scores == (UNIT, 0)
        assert len(captures) == len(rows) == len(bound.tools.calls) == 2
        assert [row['step']['marginal_credit'] for row in rows] == [UNIT, 0]
        for _, _, evidence in captures:
            assert evidence['action_kind'] == 'tool' and evidence['child_return'] is None
            assert evidence['received_progress_refs'] == [reference]
            assert evidence['progress_records'] == [saved.snapshots['A']]
            assert not {'raw_controller_delta', 'novelty_count', 'credit', 'controller_step'} & evidence.keys()
        assert store.db.execute('SELECT count(*) FROM runtime_estimation_contexts').fetchone()[0] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_completion_slots').fetchone()[0] == 2


@pytest.mark.parametrize('closed_delivery', ['runtime', 'admission'])
def test_selected_wait_stops_before_available_return_admission_and_closed_parent_keeps_history(tmp_path,
        monkeypatch, closed_delivery):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)

        def choose_wait(context):
            item, = context['pending_work']['items']
            return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
                'events': [{'handle': item['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}}, 'report_update': {}}

        bound = host(store, directory, saved, script=[child(saved.scope), choose_wait], stop_after=1)
        transport = ChildTransport(bound, saved, monkeypatch)
        original_wait = bound.workflow.execution_backend.wait_events

        async def event(condition):
            transport.publish(transport.started[0])
            return await original_wait(condition)

        monkeypatch.setattr(bound.workflow.execution_backend, 'wait_events', event)
        captures = guard_capture(bound, monkeypatch)
        result = run(bound)
        episode_id = bound.root.source.episode_id
        rows = observations(store, episode_id)
        assert result.ended_by == 'yield_stop' and result.units_consumed == 1
        assert rows[0]['decision_index'] == 1 and rows[0]['step']['marginal_credit'] == 0
        evidence = captures[0][2]
        assert evidence['action_kind'] == 'wait' and evidence['child_return'] is None
        assert evidence['received_record_refs'] == evidence['received_progress_refs'] == []
        context = bound.controllers[0].inputs[0]['estimation_context']
        assert context['wait_outcome']['wake_reason'] == 'returned'
        assert context['pending_work_after_action']['items'][0]['return_available'] is True
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_return_admissions'").fetchone()[0] == 0
        assert bound.workflow.execution_backend.status(transport.started[0]['handle'])['return_available'] is True
        # A later durable return for the now-closed receiver cannot add an
        # estimator packet, observation or rewrite the selected wait's history.
        original_context = store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0]
        source_checkpoint = store.db.execute('SELECT source_state FROM runtime_source_states '
            'WHERE episode_id=?', (episode_id,)).fetchone()[0]
        original_actions = [dict(row) for row in store.db.execute('SELECT * FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (episode_id,))]
        last_outcome = deepcopy(bound.root.source.last_outcome)
        last_outcome_index = bound.root.source.last_outcome_index
        spec, returned = transport.published[0]
        if closed_delivery == 'runtime':
            assert bound.workflow.next_return(bound.root.source) is None
            closed = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
            assert bound.workflow.execution_backend.status(spec['handle'])['acknowledgment_id'] == closed['admission_id']
        else:
            receiver = ReceiverBindingV1(store, bound.workflow.journal, 0,
                bound.workflow.returned_request(spec).report_contract,
                forbidden, forbidden, forbidden, forbidden)
            closed = admit_return(spec, returned, receiver)
        assert closed['state'] == 'receiver_closed' and closed['controller_input'] is None
        assert observations(store, episode_id) == rows and len(captures) == 1
        assert store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0] == original_context
        assert store.db.execute('SELECT source_state FROM runtime_source_states '
            'WHERE episode_id=?', (episode_id,)).fetchone()[0] == source_checkpoint
        assert bound.root.source.last_outcome == last_outcome
        assert bound.root.source.last_outcome_index == last_outcome_index
        assert [dict(row) for row in store.db.execute('SELECT * FROM runtime_actions '
            'WHERE episode_id=? ORDER BY decision_index', (episode_id,))] == original_actions


def test_failed_child_execution_adds_no_completion_packet_or_observation(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        bound = host(store, directory, saved, script=[child(saved.scope), own('A')], stop_after=1)
        ChildTransport(bound, saved, monkeypatch, publish_order=[0], failed=True)
        captures = guard_capture(bound, monkeypatch)
        result = run(bound)
        rows = observations(store, bound.root.source.episode_id)
        assert result.units_consumed == 1 and len(captures) == 1
        assert captures[0][2]['original_decision_index'] == rows[0]['decision_index'] == 1
        failed = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        assert failed['state'] == 'execution_failed' and failed['controller_input'] is None
        assert store.db.execute('SELECT count(*) FROM runtime_estimation_contexts').fetchone()[0] == 1


def test_interruption_after_context_commit_replays_saved_packet_without_recapture_or_new_work(tmp_path, monkeypatch):
    directory = tmp_path / 'run'

    class Interrupted(Exception):
        pass

    def interrupt(workflow, history, contexts):
        current = packet(contexts[-1])
        assert workflow.journal.row('runtime_observations', current['episode_id'], 0) is None
        assert workflow.store.db.execute('SELECT count(*) FROM runtime_estimation_contexts').fetchone()[0] == 1
        raise Interrupted('fixture interruption after context commit before on_unit')

    with Store(tmp_path / 'state') as store:
        saved = seed(store, directory)
        first = host(store, directory, saved, script=[own('A')], stop_after=1, estimator_hook=interrupt)
        captures = guard_capture(first, monkeypatch)
        with pytest.raises(Interrupted, match='after context commit before on_unit'):
            run(first)
        episode_id = first.root.source.episode_id
        context_row = store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0]
        slot = first.workflow.completions.slot(episode_id, 0)
        consumed = deepcopy(first.controllers[0].inputs)
        assert len(captures) == len(first.tools.calls) == 1 and observations(store, episode_id) == []
        first.workflow.progress_provider.receive_outcome(episode_id,
            {'status': 'completed', 'progress_refs': [saved.snapshots['C']['progress_ref']]},
            saved.scope, 'fixture-later-progress-before-replay')

    with Store(tmp_path / 'state') as store:
        saved.provider = ProgressProvider(store, DurableExecutionStore(directory / 'episode-execution'),
            run_id=saved.run_id)
        restored = host(store, directory, saved, stop_after=1)
        with monkeypatch.context() as patched:
            patched.setattr(CompletionEvidence, 'capture', forbidden)
            patched.setattr(restored.workflow.local_return_history, 'capture', forbidden)
            patched.setattr(restored.provider, 'complete', forbidden)
            patched.setattr(restored.tools, 'execute', forbidden)
            result = run(restored)
        assert result.units_consumed == 1
        assert restored.controllers[0].inputs == consumed
        assert restored.workflow.completions.slot(episode_id, 0) == slot
        assert store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0] == context_row
        rows = observations(store, episode_id)
        assert len(rows) == 1 and rows[0]['credit'] == slot['controller_input']
        assert rows[0]['unit_ref'] == packet(json.loads(context_row))['unit_ref']


@pytest.mark.parametrize('restore_current_marker', [False, True])
def test_markerless_assembly_replays_legacy_context_without_current_packet(tmp_path, monkeypatch,
        restore_current_marker):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        settings = {**saved_settings(), 'wait_inputs': {'version': 'wait_inputs_binding_v2'},
            'episode_progress_receipts': {'version': 'received_progress_order_v1'}}
        original_settings = deepcopy(settings)
        legacy = host(store, directory, saved, script=[own('A')], stop_after=1, settings=settings)
        assert legacy.workflow.completed_action_inputs_version is None
        with monkeypatch.context() as patched:
            patched.setattr(CompletionEvidence, 'capture', forbidden)
            run(legacy)
        context = legacy.controllers[0].inputs[0]['estimation_context']
        assert context['version'] == 'completed_action_estimation_context_v4'
        assert 'current_completion_evidence' not in context
        assert settings == original_settings
        raw = store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0]
        rows = observations(store, legacy.root.source.episode_id)
        replay_settings = deepcopy(settings)
        if restore_current_marker:
            replay_settings['completed_action_inputs'] = {'version': CURRENT}
        restored = host(store, directory, saved, stop_after=1, settings=replay_settings)
        assert restored.workflow.completed_action_inputs_version == (CURRENT if restore_current_marker else None)
        with monkeypatch.context() as patched:
            patched.setattr(CompletionEvidence, 'capture', forbidden)
            patched.setattr(restored.provider, 'complete', forbidden)
            patched.setattr(restored.tools, 'execute', forbidden)
            run(restored)
        assert restored.controllers[0].inputs == legacy.controllers[0].inputs
        assert observations(store, legacy.root.source.episode_id) == rows
        assert store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0] == raw


def test_direct_observe_without_unit_identity_keeps_legacy_path(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        directory = tmp_path / 'run'
        saved = seed(store, directory)
        bound = host(store, directory, saved, script=[own('A')], stop_after=1, current=False)
        run(bound)
        original = bound.workflow.completions.slot(bound.root.source.episode_id, 0)
        saved_context = store.db.execute('SELECT data FROM runtime_estimation_contexts').fetchone()[0]
        controller = RecordingYieldController('legacy-direct-fixture', 0, 0)
        wrapper = ExecutionContextController(controller, bound.workflow.journal,
            bound.root.source.episode_id, capture_current_completion=forbidden)
        wrapper.observe(original['label'], Record(original['controller_input']), is_root=True)
        assert controller.inputs[0]['estimation_context'] == json.loads(saved_context)
        assert 'current_completion_evidence' not in controller.inputs[0]['estimation_context']
        assert len(observations(store, bound.root.source.episode_id)) == 1


@pytest.mark.parametrize('marker', [None, {}, [], {'version': 'unknown'},
    {'version': CURRENT, 'extra': True}])
def test_unknown_completion_binding_fails_before_factory_or_transport(tmp_path, monkeypatch, marker):
    with Store(tmp_path / 'state') as store:
        settings = {**saved_settings(), 'completed_action_inputs': marker}
        provider = ScriptedProvider([])
        monkeypatch.setattr(provider, 'complete', forbidden)
        with pytest.raises(WorkflowError, match='unsupported_completed_action_inputs_binding'):
            assemble_workflow(store, object(), provider, tmp_path / 'run', 'invalid-marker', settings,
                controller_factory=forbidden, project_credit=forbidden)
        assert provider.contexts == []
