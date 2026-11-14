"""Original/current live-provider and report boundaries; no scientific execution."""
from copy import deepcopy
import asyncio
from types import SimpleNamespace

import pytest

from . import test_implicit_annotation_parent as original


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


def original_rebound(runtime, owner, method, name, replacement, monkeypatch):
    """The retained original body sees the same replacement as its old module.

    original_function intentionally compiles into an isolated original-global
    dictionary. Update that one dictionary entry as well as the genuine runtime
    module, so the comparison models the original live lookup, not a frozen copy.
    """
    function = original.original_function(runtime, owner, method)
    monkeypatch.setattr(runtime, name, replacement)
    monkeypatch.setitem(function.__globals__, name, replacement)
    return function


def test_controller_uses_runtime_provider_rebound_after_private_import(tmp_path, monkeypatch):
    runtime = original.module('runtime')
    original.module('continuation' if original.AXIS == 'a107' else 'yield')
    sentinel = object()
    received = []
    def wrapper(controller, journal, episode_id, **kwargs):
        received.append((controller, journal, episode_id, kwargs))
        return sentinel
    with original.actual_workflow(tmp_path) as workflow:
        source = original.root(workflow).source
        before = original_rebound(runtime, 'Workflow', 'controller',
                                  'ExecutionContextController', wrapper, monkeypatch)
        supplied = object()
        factory_calls = []
        workflow.controller_factory = lambda *args, **kwargs: factory_calls.append((args, kwargs)) or supplied
        workflow.has_native_estimation = lambda: False
        assert before(workflow, source.path) is sentinel
        assert runtime.Workflow.controller(workflow, source.path) is sentinel
        assert factory_calls[0] == factory_calls[1]
        assert len(received) == 2
        for controller, journal, episode_id, kwargs in received:
            assert controller is supplied and journal is workflow.journal
            assert episode_id == source.episode_id and kwargs['include_native'] is False
            assert callable(kwargs['capture_current_completion']) == (workflow.completed_action_inputs_version is not None)


@pytest.mark.parametrize('boundary', ('private_controller_value', 'public_finish'))
def test_record_provider_rebound_after_owner_import(tmp_path, monkeypatch, boundary):
    runtime = original.module('runtime')
    original.module('continuation')
    original.module('library/decision_source_outcomes')
    original.module('to_parent')
    actual_record = runtime.Record
    calls = []
    def record(value):
        calls.append(deepcopy(value))
        return actual_record(value)
    owner, method = ('Workflow', 'controller_value') if boundary == 'private_controller_value' else ('DecisionSource', 'finish')
    with original.actual_workflow(tmp_path) as workflow:
        source = original.root(workflow).source
        before = original_rebound(runtime, owner, method, 'Record', record, monkeypatch)
        if boundary == 'private_controller_value':
            old = before(workflow, source, 7, 3.5)
            live = runtime.Workflow.controller_value(workflow, source, 7, 3.5)
        else:
            workflow.pending_handles = lambda _source: []
            async def release(_episode_id):
                return None
            workflow.release = release
            old = asyncio.run(before(source, None))
            live = asyncio.run(runtime.DecisionSource.finish(source, None))
        assert old.as_record() == live.as_record()
        assert len(calls) == 2 and calls[0] == calls[1]


def test_shared_reference_provider_rebound_after_import(tmp_path, monkeypatch):
    runtime = original.module('runtime')
    original.module('library/decision_source_exchange')
    calls = []
    def references(value, record_lookup, **kwargs):
        calls.append((deepcopy(value), record_lookup, kwargs))
        return ['controlled-delivered-reference']
    with original.actual_workflow(tmp_path) as workflow:
        source = original.root(workflow).source
        before = original_rebound(runtime, 'DecisionSource', 'interpretation_context',
                                  '_references_in', references, monkeypatch)
        context = {'visible_record_refs': ['previous-reference']}
        exchanges = [{'lookup_result': {'records': [
            {'published_references': {'values': ['actual-publication-reference']}}]}}]
        old = before(source, context, exchanges)
        live = runtime.DecisionSource.interpretation_context(source, context, exchanges)
        assert old == live == {'visible_record_refs': ['previous-reference', 'controlled-delivered-reference']}
        assert len(calls) == 2 and calls[0][0] == calls[1][0] == {'record_refs': ['actual-publication-reference']}
        assert all(call[1] == workflow.store.get for call in calls)


REPORT_CASES = ('fresh', 'saved', 'late_job', 'late_specialist',
                'received_conflict', 'saved_read_error')


@pytest.mark.parametrize('scenario', REPORT_CASES)
def test_original_report_projection_and_callback_order(tmp_path, monkeypatch, scenario):
    runtime = original.module('runtime')
    original.module('to_parent')
    injected = RuntimeError('original_saved_form_read_failed')
    observed = []
    for use_original in (True, False):
        with original.actual_workflow(tmp_path / str(use_original)) as workflow:
            source = original.root(workflow).source
            events = []
            method = original.original_function(runtime, 'Workflow', 'facts') if use_original else runtime.Workflow.facts
            actual_row = workflow.journal.row
            def row(table, *keys):
                if table == 'runtime_forms':
                    events.append('saved_read')
                    if scenario == 'saved_read_error':
                        raise injected
                return actual_row(table, *keys)
            workflow.journal.row = row
            original_snapshot = workflow.store.read_snapshot
            from contextlib import contextmanager
            @contextmanager
            def snapshot():
                events.append('snapshot_enter')
                with original_snapshot():
                    yield
                events.append('snapshot_exit')
            workflow.store.read_snapshot = snapshot
            workflow.pending_handles = lambda _source: events.append('pending') or ['existing-pending']
            workflow.project_annotation_score = object()
            workflow.annotation_context = lambda *args, **kwargs: events.append('annotation') or {
                'annotation_score': None, 'proposed_annotations': [], 'annotation_comparisons': []}
            def credit(_source, **kwargs):
                events.append('credit')
                if scenario == 'late_job':
                    workflow.job_episodes = SimpleNamespace(roles=('annotation',),
                        facts=lambda *args, **kwargs: events.append('late_job_facts') or {'late_job_fact': True})
                return {'credit': 3.5}
            workflow.source_credit_view = credit
            actual_specialist = workflow.specialist
            specialist = SimpleNamespace(facts=lambda _context, snapshot:
                events.append(('late_specialist_facts', deepcopy(snapshot))) or {'late_specialist_fact': True})
            def select(value):
                events.append('specialist')
                return specialist if scenario == 'late_specialist' else actual_specialist(value)
            workflow.specialist = select
            workflow.episode_bindings.received_report_facts = lambda _context, **kwargs: (
                events.append(('received', deepcopy(kwargs))) or
                ({'credit': 99.0} if scenario == 'received_conflict' else {'received_unknown': True}))
            workflow.episode_bindings.current_report_facts = lambda _context: events.append('saved_refresh') or {'saved_current': True}
            subject = source.scope['subject_refs'][0]
            source.last_outcome = {'record_refs': [subject]}
            source.report_basis = [subject]
            workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': 2, 'action': runtime._json({'kind': 'tool', 'tool': 'controlled.existing_result'}),
                'result': runtime._json({'status': 'completed', 'record_refs': [subject], 'changed_record_refs': []}),
                'credit': 3.5})
            if scenario == 'saved':
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': runtime._json({'credit': 17.0, 'interpretations': {'unknown': True}}), 'form': None})
                workflow.source_credit_view = original.forbidden
            completion = SimpleNamespace(ended_by='yielded', end_reason='original-controller', units_consumed=1)
            try:
                value = method(workflow, source, completion_record=completion)
            except Exception as error:
                if scenario == 'saved_read_error':
                    assert error is injected
                    assert events == ['saved_read']
                else:
                    assert scenario == 'received_conflict'
                    assert type(error) is ValueError and str(error) == 'received_report_fact_conflict'
                outcome = ('raised', type(error).__name__, str(error))
            else:
                assert scenario not in ('received_conflict', 'saved_read_error')
                if scenario == 'saved':
                    assert value == {'credit': 17.0, 'saved_current': True}
                    assert events == ['saved_read', 'saved_refresh']
                else:
                    assert value['committed_record_refs'] == [subject]
                    assert value['interpretation_basis_refs'] == [subject]
                    assert value['received_unknown'] is True
                    if scenario == 'late_job':
                        assert value['late_job_fact'] is True and 'annotation' not in events
                    if scenario == 'late_specialist':
                        assert value['late_specialist_fact'] is True
                outcome = ('returned', runtime._plain(value))
            observed.append((outcome, events))
    assert observed[0] == observed[1]


@pytest.mark.parametrize('role', ('annotation', 'unrelated_job'))
def test_constructor_keeps_original_job_probe_order(tmp_path, role):
    runtime = original.module('runtime')
    observed = []
    for use_original in (True, False):
        with original.actual_workflow(tmp_path / str(use_original)) as workflow:
            events = []
            class Jobs:
                @property
                def roles(self):
                    events.append('job_roles')
                    return (role,)
                def credit_view(self, source):
                    events.append('job_credit')
                    return {'credit': 0.0}
            workflow.job_episodes = Jobs()
            workflow.expose_assigned_job = lambda source: events.append('expose_job')
            build = original.original_function(runtime, 'Workflow', 'build') if use_original else runtime.Workflow.build
            source = build(workflow, 'annotation', 'root', 'Preserve original construction',
                           workflow.store.validate_scope()).source
            observed.append((runtime._plain(source.request.as_record()), source.episode_id,
                             deepcopy(source.scope), list(events)))
            if not use_original:
                assert type(source) is original.module('episode').AnnotationTask
    assert observed[0] == observed[1]


@pytest.mark.parametrize('raises', (False, True), ids=('returned', 'failed'))
def test_constructor_keeps_rebound_original_default_source(tmp_path, monkeypatch, raises):
    runtime = original.module('runtime')
    original.module('episode')
    actual_type = runtime.DecisionSource
    injected = RuntimeError('original_default_source_failure')
    observed = []
    for use_original in (True, False):
        with original.actual_workflow(tmp_path / str(use_original)) as workflow:
            events = []
            def replacement(*args, **kwargs):
                events.append('original_default')
                if raises:
                    raise injected
                return actual_type(*args, **kwargs)
            with monkeypatch.context() as patch:
                build = original_rebound(runtime, 'Workflow', 'build', 'DecisionSource', replacement, patch)
                if not use_original:
                    build = runtime.Workflow.build
                try:
                    value = build(workflow, 'annotation', 'root', 'Retain mutable default',
                                  workflow.store.validate_scope()).source
                except RuntimeError as error:
                    assert raises and error is injected
                    result = ('raised', str(error))
                else:
                    assert not raises and type(value) is actual_type
                    result = ('returned', runtime._plain(value.request.as_record()), value.episode_id)
            assert events == ['original_default']
            observed.append((result, events))
    assert observed[0] == observed[1]


def test_continuation_keeps_actual_late_specialist_callbacks(tmp_path):
    runtime = original.module('runtime')
    observed = []
    for use_original in (True, False):
        with original.actual_workflow(tmp_path / str(use_original)) as workflow:
            source = original.root(workflow).source
            events = []
            binding = SimpleNamespace(
                continuation_for_action=lambda context, key: events.append(('continuation', key)) or {'pending': 'original'},
                completion_for_action=lambda context, key: events.append(('completion', key)) or {'completed': 'original'})
            workflow.specialist = lambda value: events.append('specialist') or binding
            method = original.original_function(runtime, 'Workflow', 'controller_value') if use_original else runtime.Workflow.controller_value
            result = method(workflow, source, 7, 3.5).as_record()
            assert result['hpc_continuation'] == {'pending': 'original'}
            assert result['practical_completion'] == {'completed': 'original'}
            assert events[0] == 'specialist'
            observed.append((result, events))
    assert observed[0] == observed[1]


def test_instructions_keep_late_job_specialist_and_text_rebinding(tmp_path, monkeypatch):
    runtime = original.module('runtime')
    prompt = original.module('runtime_prompt')
    owner = original.module('task_instructions' if original.AXIS == 'a107' else 'instructions')
    observed = []
    for use_original in (True, False):
        with original.actual_workflow(tmp_path / str(use_original)) as workflow:
            source = original.root(workflow).source
            # Original runtime_prompt reads this optional supplied port; both
            # authentic Workflow constructors leave it to the caller.
            workflow.native_event_information = None
            events = []
            class Jobs:
                @property
                def roles(self):
                    events.append('job_roles')
                    return ('annotation',)
                def instructions(self, role):
                    events.append(('job_instructions', role))
                    return 'Actual supplied job instructions'
            workflow.job_episodes = Jobs()
            binding = SimpleNamespace(instructions=lambda context: events.append('specialist_instructions') or 'Actual supplied specialist instructions')
            workflow.specialist = lambda value: events.append('specialist') or binding
            workflow.permits_common_action = lambda value, kind: events.append(('permits', kind)) or kind == 'reason'
            with monkeypatch.context() as patch:
                patch.setattr(prompt, 'REASONING_COMMIT_REQUIREMENT', 'Rebound original reasoning requirement')
                value = (prompt.instructions if use_original else owner.instructions)(source, {})
            assert value.startswith('Actual supplied job instructions\nActual supplied specialist instructions\nRebound original reasoning requirement')
            observed.append((value, events))
    assert observed[0] == observed[1]
