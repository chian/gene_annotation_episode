"""Actual private selection/acquisition and original decision snapshot controls.

Constructors and external tools are controlled. These tests exercise the real
own-axis Workflow.selected, ActionLeaf acquisition and private task methods;
they do not claim autonomous literature assessment or saved-run restoration.
"""
from __future__ import annotations
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import MethodType, SimpleNamespace
import pytest

AXIS = 'a107'
PREFIX = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
runtime = importlib.import_module(PREFIX + '.runtime')
FIXTURE = json.loads((Path(__file__).parent / 'fixtures/organization_original/literature_task_methods.json').read_text())
HOMES = FIXTURE['homes']

def original_function(text, name):
    namespace = dict(vars(runtime))
    exec(compile(text, '<original-own-axis-literature-method>', 'exec'), namespace)
    return namespace[name]

class Journal:
    def __init__(self, events):
        self.events = events
        self.actions = {}
        self.db = SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchone=lambda: None))
    def row(self, table, episode_id, index=None):
        return self.actions.get(index) if table == 'runtime_actions' else None
    def save(self, table, value):
        assert table == 'runtime_actions'
        self.events.append(('save', deepcopy(value)))
        self.actions[value['decision_index']] = deepcopy(value)
    @contextmanager
    def measure(self, *args):
        self.events.append(('measure_enter', args))
        try:
            yield
        finally:
            self.events.append(('measure_exit', args))
    def elapsed_view(self, episode_id):
        return {'elapsed': 0.0}

def make_source(home):
    module = importlib.import_module(PREFIX + '.' + home['home'].replace('/', '.') + '.episode')
    binding = object.__new__(getattr(module, home['owner_class']))
    source = object.__new__(module.SourceInvestigationTask)
    source.path = (('scientific_process', 'parent'), (home['role'], 'private'))
    source.episode_id = 'controlled-literature-episode'
    source.scope = {'subject_refs': []}
    source.last_outcome = source.last_outcome_index = source.feedback = None
    source._delivery_resolution_ref = source._execution_context = None
    source._restored = False
    source.calls = 0
    source.report_values, source.report_basis = {}, []
    source.interpret_schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    source.request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'goal': 'Retain the source qualification'}), report_contract=None)
    return source, binding

def action_harness(home, status, original=False):
    events = []
    source, binding = make_source(home)
    workflow = object.__new__(runtime.Workflow)
    source.workflow = workflow
    workflow.run_id = 'controlled-literature-run'
    workflow.journal = Journal(events)
    workflow.store = SimpleNamespace(transaction=nullcontext)
    workflow.execution_binding = workflow.inprocess_replay = None
    workflow.scientific_process_binding = None
    workflow.annotation_child_roles = tuple(row['role'] for row in HOMES)
    workflow.project_credit = SimpleNamespace(task_credit=False)
    workflow.root_action_boundary = None
    workflow.wait_inputs_version = 'wait_inputs_binding_v1'
    workflow.completed_action_inputs_version = None
    workflow.specialist = lambda actual: binding
    workflow.binding_context = lambda actual: SimpleNamespace(role=home['role'])
    workflow.available_child_roles = lambda actual: binding.child_roles(home['role'])
    workflow._closed_child_commission = lambda *args: None
    outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None}
    if status in {'invalid', 'failed', 'unavailable', 'pending'}:
        outcome['feedback'] = {'status': status, 'category': 'controlled_source_result'}
    async def execute(actual, tool, arguments, **identity):
        events.append(('tool', tool, deepcopy(arguments), identity))
        return deepcopy(outcome)
    workflow.execute = execute
    workflow.receive_native_outcome = lambda actual, result, index: events.append(('native_outcome', deepcopy(result), index))
    workflow.receive_outcome = lambda actual, selection, result, index: events.append(('observed_outcome', deepcopy(selection), deepcopy(result), index))
    async def scores(actual, index, result):
        events.append(('scores', index, deepcopy(result)))
        return result
    workflow.automatic_score_updates = scores
    def credit(actual):
        events.append(('credit',))
        return {'credit': 0.375}
    workflow.source_credit_view = credit
    workflow.controller_value = lambda actual, index, value: {'original_progress': value, 'decision_index': index}
    workflow.retain_shared_grading_results = lambda *args: events.append(('shared_grading',))
    source.checkpoint = lambda: events.append(('checkpoint', deepcopy(source.last_outcome), deepcopy(source.feedback)))
    if original:
        source.execute = MethodType(original_function(home['execute_function'], 'execute'), source)
    return source, workflow, events

def acquire(workflow, source, selection, index=7):
    unit = workflow.selected(source, deepcopy(selection), index)
    assert isinstance(unit, runtime.ActionLeaf)
    completed = asyncio.run(unit.acquire_async(None))
    return completed.contribution.controller_input

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
@pytest.mark.parametrize('kind', ('reason', 'wait'))
def test_unavailable_units_reject_before_acquisition(home, kind):
    source, workflow, events = action_harness(home, 'failed')
    with pytest.raises(ValueError, match='^action_not_available_to_episode$'):
        workflow.selected(source, {'kind': kind, 'commit': {}, 'condition': {}}, 7)
    assert events == []
    assert workflow.journal.actions == {}
    assert source.last_outcome is None

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
def test_foreign_child_rejects_before_acquisition(home):
    source, workflow, events = action_harness(home, 'failed')
    with pytest.raises(ValueError, match='^child_role_not_available_to_parent$'):
        workflow.selected(source, {'kind': 'episode_child', 'role': 'results', 'assignment': {}}, 7)
    assert events == [] and workflow.journal.actions == {}

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
@pytest.mark.parametrize('status', ('completed', 'partial', 'invalid', 'failed', 'unavailable'))
def test_acquired_tool_outcomes_retain_original_progress(home, status):
    selection = {'kind': 'tool', 'tool': 'controlled.source.read', 'arguments': {'source': 'original'}}
    comparisons = []
    for original in (True, False):
        source, workflow, events = action_harness(home, status, original)
        progress = acquire(workflow, source, selection)
        assert progress == {'original_progress': 0.375, 'decision_index': 7}
        assert source.last_outcome['status'] == status
        assert sum(event[0] == 'tool' for event in events) == 1
        assert sum(event[0] == 'observed_outcome' for event in events) == 1
        assert sum(event[0] == 'scores' for event in events) == 1
        comparisons.append((events, workflow.journal.actions, source.last_outcome, source.feedback, progress))
    assert comparisons[0] == comparisons[1]

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
def test_saved_failed_outcome_replays_without_reexecution(home):
    selection = {'kind': 'tool', 'tool': 'controlled.source.read', 'arguments': {}}
    comparisons = []
    for original in (True, False):
        source, workflow, events = action_harness(home, 'failed', original)
        first = acquire(workflow, source, selection)
        second = acquire(workflow, source, selection)
        assert first == second
        assert sum(event[0] == 'tool' for event in events) == 1
        assert sum(event[0] == 'observed_outcome' for event in events) == 1
        assert sum(event[0] == 'scores' for event in events) == 1
        comparisons.append((events, workflow.journal.actions, first, second))
    assert comparisons[0] == comparisons[1]

class SnapshotCaptured(Exception):
    def __init__(self, context, schema):
        self.context, self.schema = deepcopy(context), deepcopy(schema)

def snapshot_harness(home, mode):
    source, binding = make_source(home)
    events = []
    workflow = SimpleNamespace(run_id='controlled-literature-run', journal=Journal(events),
        inprocess_replay=None, execution_binding=None)
    source.workflow = workflow
    source.last_outcome = {'status': 'failed', 'feedback': {'status': 'failed', 'detail': 'original failed read'}}
    source.feedback = source.last_outcome['feedback']
    source.last_outcome_index = 3
    workflow.journal.actions[3] = {'action': json.dumps({'kind': 'tool'}), 'result': json.dumps(source.last_outcome), 'credit': 0.375}
    @contextmanager
    def snapshot():
        events.append(('snapshot_enter',))
        try:
            yield
        finally:
            events.append(('snapshot_exit',))
    workflow.store = SimpleNamespace(read_snapshot=snapshot, get=lambda ref: None,
        reference_subset=lambda refs, scope: refs)
    def working_state(actual):
        events.append(('working_state',))
        return {'retained_qualification': 'unresolved'}
    workflow.working_state = working_state
    workflow.local_outcome_preview = lambda value, **kwargs: deepcopy(value)
    credit = {'credit': 0.375, 'retained_finding_count': 0}
    if mode == 'annotation':
        credit = {'credit': {'mode': 'annotation_axis_credit', 'root_score': 0.375},
            'proposed_annotations': [], 'comparisons': [], 'axis_components': {}}
    workflow.source_credit_view = lambda actual: deepcopy(credit)
    workflow.receipt_projection = lambda actual: True
    workflow.source_credit_binding = lambda actual: {'version': 'controlled_original_binding'}
    workflow.pending_work = lambda actual: {'items': []}
    workflow.delivery_status = lambda episode_id: []
    workflow.controller_binding = {'version': 'controlled_iterator_binding'}
    workflow.catalog = lambda scope, **kwargs: []
    workflow.knowledge = SimpleNamespace(context=lambda: {})
    workflow.job_episode_options = lambda actual: None
    workflow.extra_report_sources = lambda actual: {}
    workflow.is_scientific_source = lambda actual: True
    workflow.annotation_context = lambda scope, **kwargs: {'retained_scientific_context': True}
    def specialist_context(context, view):
        events.append(('specialist_context',))
        return {'private_context': 'original'}
    workflow.specialist = lambda actual: SimpleNamespace(decision_context=specialist_context)
    workflow.binding_context = lambda actual: SimpleNamespace(role=home['role'])
    workflow.tools = SimpleNamespace(model_contract_catalog=lambda context: context['available_report_facts'])
    workflow.action_schema = lambda actual: {'type': 'object', 'const': 'controlled_original_schema'}
    def delivery(actual, reference, context):
        events.append(('delivery_inputs', reference))
        return {**context, 'pending_child_delivery': {'delivery_ref': reference}}, {'type': 'object', 'const': 'controlled_delivery_schema'}
    workflow.delivery_resolution_inputs = delivery
    view = SimpleNamespace(units_consumed=0, child_reports=(),
        controller_state={'arms': [], 'annotation_credits': {}, 'root_score': 0.375, 'decision': 'continue'})
    def model_inputs(context, *, reports):
        events.append(('model_inputs', deepcopy(context), len(reports)))
        return deepcopy(context)
    view.model_inputs = model_inputs
    async def call(context, schema):
        raise SnapshotCaptured(context, schema)
    source.call = call
    return source, view, events

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
@pytest.mark.parametrize('mode', ('plain', 'annotation', 'delivery'))
def test_actual_next_uses_private_summary_with_original_snapshot(home, mode, monkeypatch):
    delivery_ref = 'original-delivery' if mode == 'delivery' else None
    original_source, original_view, original_events = snapshot_harness(home, mode)
    expected = original_function(home['snapshot_function'], '_decision_snapshot')(
        original_source, original_view, delivery_ref)
    source, view, events = snapshot_harness(home, mode)
    summary_module = importlib.import_module(PREFIX + '.' + home['home'].replace('/', '.') + '.internal_summary')
    summary = getattr(summary_module, 'SourceDecisionSummary', None)
    calls = []
    if summary is not None:
        original_summary = summary._decision_snapshot
        def selected_summary(actual, current_view, reference=None):
            calls.append((actual is source, current_view is view, reference))
            return original_summary(actual, current_view, reference)
        monkeypatch.setattr(summary, '_decision_snapshot', selected_summary)
    with pytest.raises(SnapshotCaptured) as caught:
        asyncio.run(source.next(view, delivery_ref=delivery_ref))
    assert (caught.value.context, caught.value.schema) == expected
    assert events == original_events
    assert calls == [(True, True, delivery_ref)]

def test_pending_tool_result_keeps_original_nonobservation_boundary():
    home = HOMES[0]
    selection = {'kind': 'tool', 'tool': 'controlled.source.read', 'arguments': {}}
    comparisons = []
    for original in (True, False):
        source, workflow, events = action_harness(home, 'pending', original)
        with pytest.raises(runtime.ActionFailure):
            acquire(workflow, source, selection)
        assert not any(event[0] in {'scores', 'credit', 'observed_outcome'} for event in events)
        comparisons.append((events, workflow.journal.actions, source.last_outcome))
    assert comparisons[0] == comparisons[1]


# This source is appended to the permanent controlled literature tests.
RESPONSE_FIXTURE = json.loads((Path(__file__).parent / 'fixtures/organization_original/literature_invalid_response_methods.json').read_text())
RESPONSE_METHODS = {row['home']: row['apply_response_function'] for row in RESPONSE_FIXTURE['homes']}

@pytest.mark.parametrize('home', HOMES, ids=lambda h: h['home'])
@pytest.mark.parametrize('kind', ('reason', 'wait', 'results_minhash'))
def test_invalid_response_keeps_original_feedback_and_has_no_acquisition(home, kind):
    if kind == 'results_minhash':
        selection = {'kind': 'episode_child', 'role': 'results', 'assignment': {
            'version': 'execution_results_assignment_v1',
            'selector': {'version': 'bvbrc_minhash_result_selector_v2'}}}
        detail = 'child_role_not_available_to_parent'
    else:
        selection = {'kind': kind, 'condition': {}, 'commit': {}}
        detail = 'action_not_available_to_episode'
    schema = {'type': 'object', 'properties': {'selection': {'type': 'object'},
        'report_update': {'type': 'object'}}, 'required': ['selection', 'report_update']}
    results = []
    for original in (True, False):
        source, workflow, events = action_harness(home, 'failed')
        workflow.decision_exchanges = None
        source.record_effect = lambda index, status: events.append(('effect', index, status))
        callback = (MethodType(original_function(RESPONSE_METHODS[home['home']], 'apply_response'), source)
            if original else source.apply_response)
        value = callback({'selection': deepcopy(selection), 'report_update': {}}, 7,
            {'visible_record_refs': []}, deepcopy(schema))
        assert value is None
        assert source.feedback == {'status': 'invalid', 'category': 'action_contract', 'detail': detail}
        assert events == [('effect', 7, 'rejected')]
        assert workflow.journal.actions == {} and source.last_outcome is None
        results.append((source.feedback, source.report_values, source.report_basis, events))
    assert results[0] == results[1]
