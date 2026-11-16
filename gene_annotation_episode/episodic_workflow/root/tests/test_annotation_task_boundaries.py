"""Private root task boundary checks with controlled engineering collaborators.

These are not scientific scoring or full Workflow/iterator integration tests.
They intentionally import the production private task, not copied method bodies.
"""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.task import AnnotationTask


def forbidden(*args, **kwargs):
    raise AssertionError('saved work attempted new execution or context refresh')


class Journal:
    def __init__(self):
        self.rows = {}
        self.writes = []

    def row(self, table, episode_id, index=None):
        return self.rows.get((table, episode_id, index))

    def save(self, table, row):
        row = deepcopy(row)
        index = row.get('decision_index', row.get('call_index'))
        self.rows[(table, row['episode_id'], index)] = row
        self.writes.append((table, row))

    def measure(self, *args):
        return nullcontext()


def bare_task(workflow):
    task = object.__new__(AnnotationTask)
    task.workflow = workflow
    task.path = (('annotation', 'root'),)
    task.episode_id = 'root-boundary-fixture'
    task.scope = {'subject_refs': []}
    task.calls = 0
    task.feedback = None
    task.last_outcome = None
    task.last_outcome_index = None
    task._inprocess_replay_ready = False
    return task


def test_next_consumes_original_answered_request_without_refreshing_summary():
    journal = Journal()
    original = {'context': {'pending_work': [{'handle': 'original-child'}]},
        'schema': {'type': 'object'}}
    workflow = SimpleNamespace(journal=journal, inprocess_replay=None, execution_binding=None)
    source = bare_task(workflow)
    source._execution_context = None
    source._decision_inputs = forbidden
    journal.save('runtime_model_calls', {'episode_id': source.episode_id, 'call_index': 0,
        'purpose': 'decision', 'request': json.dumps(original), 'response': '{}'})
    seen, selected = [], object()
    async def call(context, schema):
        seen.append((deepcopy(context), deepcopy(schema)))
        return {}, 0, context, schema
    source.call = call
    source.apply_response = lambda *args: selected
    assert asyncio.run(source.next(SimpleNamespace(units_consumed=0))) is selected
    assert seen == [(original['context'], original['schema'])]


def test_finish_uses_saved_typed_candidate_without_recomputing_facts():
    journal, releases = Journal(), []
    async def release(episode_id):
        releases.append(episode_id)
    workflow = SimpleNamespace(journal=journal, facts=forbidden, release=release)
    source = bare_task(workflow)
    source.request = SimpleNamespace(report_contract=object())
    form = {'qualified_result': 'original unavailable observation'}
    journal.save('runtime_forms', {'episode_id': source.episode_id,
        'facts': '{}', 'form': json.dumps(form)})
    before = deepcopy(journal.rows)
    result = asyncio.run(source.finish(object()))
    assert result.as_record() == {'form': form}
    assert releases == [source.episode_id]
    assert journal.rows == before


def test_json_assignment_preserves_explicit_null_and_omitted_fields():
    from gene_annotation_episode.episodic_workflow.root.task_action_contracts import (
        _action_generation_schema, _decode_action_response)
    assignment = {'type': 'object', 'properties': {
        'required_null': {'type': 'null'}, 'optional_value': {'type': 'integer'}},
        'required': ['required_null'], 'additionalProperties': False}
    schema = {'type': 'object', 'properties': {
        'kind': {'const': 'episode_child'}, 'assignment': assignment,
        'optional_transport': {'type': 'integer'}},
        'required': ['kind', 'assignment'], 'additionalProperties': False}
    before = deepcopy(schema)
    generated = _action_generation_schema(schema)
    assert generated['properties']['assignment']['type'] == 'string'
    original = {'required_null': None}
    supplied = {'kind': 'episode_child', 'assignment': json.dumps(original),
        'optional_transport': None}
    assert _decode_action_response(supplied, schema) == {
        'kind': 'episode_child', 'assignment': original}
    assert schema == before


def test_typed_return_uses_canonical_parent_report_and_frozen_schema():
    from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract
    from gene_annotation_episode.episodic_workflow.root.method_loop.communication import ParentReport
    schema = {'type': 'object', 'properties': {'measurement': {'type': 'number'}},
        'required': ['measurement'], 'additionalProperties': False}
    contract = TypedReportContract('Return the engineering fixture measurement', schema, lambda ref: False)
    schema['properties']['measurement']['type'] = 'string'
    exposed = contract.schema
    exposed['properties']['measurement']['type'] = 'boolean'
    report = contract.admit({'measurement': -0.375}, audit_identifiers=())
    assert isinstance(report, ParentReport)
    assert report.contract is contract
    assert report.as_record() == {'measurement': -0.375}
    assert contract.schema['properties']['measurement']['type'] == 'number'
    with pytest.raises(ValueError):
        contract.admit({'measurement': 'not a number'}, audit_identifiers=())


def test_decision_frame_replaces_changed_fields_without_mutating_inputs():
    from gene_annotation_episode.episodic_workflow.root.task_decision import state_frame
    previous = {'pending_work': [{'handle': 'first'}], 'obsolete': True,
        'current_credit': -0.375}
    current = {'pending_work': [], 'current_credit': -0.375}
    frozen_previous, frozen_current = deepcopy(previous), deepcopy(current)
    bootstrap = state_frame(previous)
    delta = state_frame(current, previous)
    assert bootstrap['kind'] == 'decision_bootstrap'
    assert bootstrap['fields'] == previous
    assert delta['kind'] == 'decision_update'
    assert delta['base_revision'] == bootstrap['revision']
    assert delta['fields'] == {'pending_work': []}
    assert delta['removed_fields'] == ['obsolete']
    assert previous == frozen_previous and current == frozen_current
