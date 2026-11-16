"""Original iterator + private task action boundaries; engineering inputs only.

RecordingController never stops. Each finite fixture is naturally exhausted;
there is no deadline, action cap, or other continuation replacement.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.method_loop import (
    Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain,
)
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import UnitRef
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionLeaf
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from .test_annotation_task_boundaries import Journal, bare_task, forbidden


class RecordingController:
    """Observe original inputs/identities without introducing a stopping policy."""
    epoch = 'engineering-input-observation'

    def __init__(self):
        self.observations = []

    def observe(self, *args, **kwargs):
        raise AssertionError('the original iterator must supply its canonical UnitRef')

    def observe_unit(self, label, value, *, unit_ref, is_root):
        assert isinstance(unit_ref, UnitRef)
        self.observations.append((label, value, unit_ref, is_root))
        return SimpleNamespace(stop=False, requests_transition=False)

    def state(self):
        return SimpleNamespace(stop=False, requests_transition=False, observed_inputs=len(self.observations))

    def transitioned(self, epoch):
        raise AssertionError('this fixture requested no transition')


class ResponseSource:
    """A finite input fixture; all admission/execution uses production methods."""
    def __init__(self, task, responses, schema):
        self.task, self.schema = task, schema
        self.responses = iter(responses)
        self.rejections = []

    async def next(self, view):
        for original_index, response in self.responses:
            unit = self.task.apply_response(response, original_index,
                {'visible_record_refs': []}, self.schema)
            if unit is not None:
                return unit
            self.rejections.append((original_index, deepcopy(self.task.feedback)))
        return None


def make_case(status, *, responses=None, journal=None):
    journal = journal or Journal()
    controller, events = RecordingController(), []
    progress = -0.375
    selection = {'kind': 'tool', 'tool': 'fixture.read', 'arguments': {}}
    form_schema = {'type': 'object', 'properties': {'measurement': {'type': 'number'}},
        'required': ['measurement'], 'additionalProperties': False}
    action_schema = {'type': 'object', 'properties': {
        'kind': {'const': 'tool'}, 'tool': {'const': 'fixture.read'},
        'arguments': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
        'required': ['kind', 'tool', 'arguments'], 'additionalProperties': False}
    schema = {'type': 'object', 'properties': {'selection': action_schema,
        'report_update': form_schema}, 'required': ['selection', 'report_update'],
        'additionalProperties': False}
    async def execute(source, tool, arguments, **kwargs):
        events.append(('execute', kwargs['decision_index']))
        return {'status': status, 'record_refs': [], 'changed_record_refs': [],
            'feedback': {'status': status, 'category': 'controlled_fixture'}}
    async def score(source, index, result):
        events.append(('score', index))
        return result
    workflow = SimpleNamespace(journal=journal, run_id='original-iterator-fixture',
        execution_binding=None, inprocess_replay=None, decision_exchanges=None,
        pending_work=lambda source: {'version': 'pending_work_v2', 'captured_at': '2026-11-01T00:00:00+00:00', 'items': []},
        execute=execute, automatic_score_updates=score,
        receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: events.append(('receipt', index)),
        source_credit_view=lambda source: {'credit': progress},
        controller_value=lambda source, index, credit: credit,
        permits_common_action=lambda *args: False,
        resolver=lambda *args, **kwargs: lambda ref: False,
        validate_report=lambda *args, **kwargs: None)
    source = bare_task(workflow)
    source._delivery_resolution_ref = None
    source.interpret_schema = form_schema
    source.report_values = {'measurement': 0}
    source.report_basis = []
    request = EpisodeRequest(EpisodeGoal('Inspect engineering outcome routing',
        'Preserve supplied input and identity'), Record({'initial_report': source.report_values}))
    source.request = request
    def selected(task, action, index):
        events.append(('selected', index))
        return ActionLeaf(action, extract=lambda value: task.execute(value, index),
            result=lambda unit, value: value, label=f'tool:{index}', decision_index=index)
    workflow.selected = selected
    response = {'selection': selection, 'report_update': {'measurement': 0}}
    responses = [(7, response)] if responses is None else responses
    driver = ResponseSource(source, responses, schema)
    grain = Grain('annotation', 'selected original action', 'retained outcome', lambda path: controller)
    context = Context(tree=EpisodeTree(grain), run_id=workflow.run_id)
    source.episode_id = Episode.identity(context, grain, 'root').episode_id
    episode = Episode(grain, 'root', driver, request, lambda record: Record({'credit': progress}))
    return SimpleNamespace(episode=episode, context=context, source=source, driver=driver,
        workflow=workflow, controller=controller, journal=journal, events=events,
        progress=progress, response=response)


@pytest.mark.parametrize('status', ['invalid', 'failed', 'unavailable'])
def test_executed_failed_outcome_enters_original_iterator_and_replays_same_unit(status):
    case = make_case(status)
    record = asyncio.run(case.episode.run_async(case.context))
    assert record.ended_by == 'exhausted'
    assert record.units_consumed == 1
    unit, = record.unit_records
    assert unit.unit_label == 'tool:7'
    assert unit.controller_input == case.progress
    assert unit.unit_ref == UnitRef(case.source.episode_id, 0)
    assert case.controller.observations == [('tool:7', case.progress, unit.unit_ref, True)]
    saved = case.journal.row('runtime_actions', case.source.episode_id, 7)
    assert json.loads(saved['result'])['status'] == status
    assert saved['credit'] == case.progress
    assert case.events == [('selected', 7), ('execute', 7), ('receipt', 7), ('score', 7)]

    before = deepcopy(case.journal.rows)
    replay = make_case(status, journal=case.journal)
    replay.workflow.execute = replay.workflow.automatic_score_updates = forbidden
    replay.workflow.source_credit_view = forbidden
    repeated = asyncio.run(replay.episode.run_async(replay.context))
    assert replay.controller.observations == case.controller.observations
    assert repeated.unit_records[0].unit_ref == unit.unit_ref
    assert repeated.unit_records[0].controller_input == unit.controller_input
    assert replay.journal.rows == before
    assert replay.events == [('selected', 7)]


def test_rejected_request_before_acquisition_creates_no_iterator_observation():
    bad = {'selection': {'kind': 'tool', 'tool': 'fixture.read'},
        'report_update': {'measurement': 0}}
    case = make_case('failed', responses=[(3, bad)])
    record = asyncio.run(case.episode.run_async(case.context))
    assert record.ended_by == 'exhausted' and record.units_consumed == 0
    assert record.unit_records == () and case.controller.observations == []
    assert case.events == [] and case.journal.rows == {}
    rejection, = case.driver.rejections
    assert rejection[0] == 3
    assert rejection[1]['status'] == 'invalid'
    assert rejection[1]['category'] == 'action_contract'


def test_rejection_then_returned_failure_keeps_original_action_index_and_single_observation():
    bad = {'selection': {'kind': 'tool', 'tool': 'fixture.read'},
        'report_update': {'measurement': 0}}
    good = {'selection': {'kind': 'tool', 'tool': 'fixture.read', 'arguments': {}},
        'report_update': {'measurement': 0}}
    case = make_case('failed', responses=[(3, bad), (7, good)])
    record = asyncio.run(case.episode.run_async(case.context))
    assert record.units_consumed == 1
    assert record.unit_records[0].unit_label == 'tool:7'
    assert record.unit_records[0].unit_ref == UnitRef(case.source.episode_id, 0)
    assert case.journal.row('runtime_actions', case.source.episode_id, 3) is None
    assert case.journal.row('runtime_actions', case.source.episode_id, 7)['credit'] == case.progress
    assert len(case.controller.observations) == 1
    assert [index for index, feedback in case.driver.rejections] == [3]


class FiniteUnits:
    def __init__(self, units):
        self.units = iter(units)

    def next(self, view):
        item = next(self.units, None)
        return item(view) if callable(item) else item


def test_saved_typed_form_redelivery_does_not_acquire_again_or_reobserve_credit():
    from gene_annotation_episode.episodic_workflow.root.method_loop import (
        ChildEpisodeUnit, ReportRedelivery)
    from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract
    parent_control, child_control = RecordingController(), RecordingController()
    parent_grain = Grain('annotation', 'child result', 'received engineering result',
        lambda path: parent_control)
    child_grain = Grain('engineering_fixture', 'fixture input', 'fixture result',
        lambda path: child_control)
    parent_goal = EpisodeGoal('Check saved typed communication', 'Original form')
    parent_request = EpisodeRequest(parent_goal, Record({}))
    schema = {'type': 'object', 'properties': {'measurement': {'type': 'number'}},
        'required': ['measurement'], 'additionalProperties': False}
    contract = TypedReportContract('Return the fixture measurement', schema, lambda ref: False)
    child_goal = EpisodeGoal.child(parent=parent_goal,
        objective='Return already-saved engineering form', result_contract='Typed fixture form')
    child_request = EpisodeRequest(child_goal, Record({}), contract)
    original_request = deepcopy(child_request.as_record())
    journal, releases = Journal(), []
    async def release(episode_id):
        releases.append(episode_id)
    task = bare_task(SimpleNamespace(journal=journal, facts=forbidden, release=release))
    task.request = child_request
    form = {'measurement': -0.375}
    journal.save('runtime_forms', {'episode_id': task.episode_id,
        'facts': '{}', 'form': json.dumps(form)})
    saved_rows = deepcopy(journal.rows)
    child = Episode(child_grain, 'original-child', FiniteUnits([]), child_request, task.finish)
    progress = Record({'credit': -0.375})
    selected = ChildEpisodeUnit(child,
        receive_result=lambda result, completion, request: progress,
        synthesize_report=lambda result, completion, request: result.as_record()['form'])
    observed_before_redelivery = []
    def redeliver(view):
        update, = view.updates
        observed_before_redelivery.extend(parent_control.observations)
        assert update.report.as_record() == form
        assert update.report.contract is contract
        return ReportRedelivery(update.record_id,
            report=contract.admit(deepcopy(form), audit_identifiers=()))
    parent = Episode(parent_grain, 'root', FiniteUnits([selected, redeliver]),
        parent_request, lambda record: Record({}))
    context = Context(tree=EpisodeTree(parent_grain, {parent_grain: (child_grain,)}),
        run_id='saved-form-engineering-fixture')
    record = asyncio.run(parent.run_async(context))
    assert record.units_consumed == 1 and record.ended_by == 'exhausted'
    assert parent_control.observations == observed_before_redelivery
    assert len(parent_control.observations) == 1
    assert parent_control.observations[0][1] is progress
    assert child_control.observations == []
    update = record.unit_records[0].episode_update
    assert update.report.as_record() == form and update.report.contract is contract
    assert update.record_id == record.unit_records[0].child.episode_id
    assert child_request.as_record() == original_request
    assert journal.rows == saved_rows
    assert releases == [task.episode_id]
