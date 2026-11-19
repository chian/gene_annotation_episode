"""The A108 contextual grading of this episode, run through the real runner on a real Store.

The run is linked with the public API (``link``) and stepped with ``next_decision`` and ``run_unit``: the
Episode is entered as ``run()`` enters it (its yield controller built from ``credit`` of the initial summary), its
first decision is the episode's own ``decide`` (the model is not asked), and the grading tool then runs as a real
journaled tool unit on real held records. The saved sheet, the features code reads from it and the return admitted
by ``RETURN_FORM`` are checked. Nothing is faked."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_prompt import (
    A108_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_FEATURES, GRADING_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    CELLS, PROVIDER)

from .a108_world import SERVICES, SETTINGS, graded_commit, grading_arguments, held_world, reading_assignment, saved

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path
TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'kind': 'source_answer',
        'answer_kind': 'screening', 'credit_unit': 1.0, 'examined': []}


def linked(directory, world, task):
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                             directory),
                     'continuation': {PATH: SETTINGS}, 'services': SERVICES}
    entry = {'assignment': reading_assignment(world, task), 'message': {'objective': 'grade'}, 'selection': []}
    return link(BindingRegistry([EPISODE()]), PATH, entry, run_id='a108-grading', journal=RunJournal(
        directory / 'journal.sqlite3'), collaborators=collaborators)


def screening(world):
    paper = world['paper']
    return {**TASK, 'examined': [{'source_ref': paper['id'], 'artifact_ref': paper['artifact_ref'], 'start': 0,
                                  'end': 8}]}


def test_the_next_decision_offers_the_grader_with_its_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world, screening(world))
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = EPISODE.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0
    assert summary['finding'] == {'grading_sheets': [], 'aggregation_cells': [], 'assessment_refs': [], 'observation_refs': []}
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert {'literature_a108_grading_populate', 'literature_a108_aggregate', 'reason'} <= set(tools)
    assert 'report' not in tools
    assert GRADING_INSTRUCTIONS in request.instructions and A108_GRADING_TASK in request.instructions
    assert 'not scored checklist items' in request.instructions
    assert '"literature_a108_grading_populate"' in json.dumps(request.output_schema)
    world['store'].close()


def test_the_grading_tool_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world, screening(world))
    asyncio.run(run.next_decision())
    envelope = {'arguments': grading_arguments(world), 'scope': world['scope'],
                'page_source_ref': world['paper']['id'], 'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': ['evidence_amount'],
                              'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(run.run_unit(ToolCall('literature_a108_grading_populate', envelope)))
    assert outcome['outcome']['status'] == 'completed', outcome['outcome']
    sheet_ref = outcome['outcome']['result']['sheet_ref']
    view = run.view
    records = view.records
    assert records.holds(sheet_ref) and records.receipt(sheet_ref)['how'] == 'produced'
    assert records.get(sheet_ref)['provider'] == PROVIDER
    sheet = saved(world['store'], sheet_ref)['sheet']
    assert sheet['cells']['evidence_amount']['value'] == 1 and sheet['cells']['support_count']['value'] == 1
    rows = records.table(CELLS).select({'sheet_ref': sheet_ref})
    assert [row['component'] for row in rows] == ['evidence_amount']

    summary = EPISODE.internal_summary(view)
    finding = summary['finding']
    assert len(finding['grading_sheets']) == 1
    features = finding['grading_sheets'][0]
    assert set(features) == set(GRADING_FEATURES)
    assert features['sheet_refs'] == [sheet_ref] and features['assertion_refs'] == [world['claim']['id']]
    assert (features['evidence_type'], features['grader_type']) == ('physiology', 'physiology_resource_response')
    assert (features['support_count'], features['conflict_count'], features['evidence_amount'],
            features['net_support'], features['unresolved_count']) == (1, 0, 1, 1, 0)
    assert features['status'] == 'populated' and features['target_context_established'] is True
    assert features['direct_observation_count'] == 1 and features['physiology_report_observation_count'] == 1
    assert features['source_count'] >= 1 and features['criterion_unmet_count'] == 0
    # The automatic main sheet (``literature_sheet_updates``) unions the evidence_amount cell.
    cells = {cell['evidence_type']: cell for cell in finding['aggregation_cells']}
    assert set(cells) == {'physiology', 'overall'}
    assert cells['overall']['evidence_amount'] == 1 and cells['overall']['domain_count'] == 1

    selection = ('literature_a108_grading_cells', 'literature_screening_answers')
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0}
    result = EPISODE.final_to_parent(summary, completion, selection)
    form = EPISODE.return_form.select(selection)
    assert form.admit(result, 'return') == json.loads(json.dumps(result))
    returned = set(form.record_refs(result))
    assert {sheet_ref, world['claim']['id'], rows[0]['id']} <= returned
    assert result['literature_screening_answers'] == {'examined_span_count': 0, 'commissioned_spans_covered': False}
    text = [name for name, spec in form.fields['finding'].form.fields['grading_sheets'].items.fields.items()
            if spec.type == 'text']
    assert all(hasattr(form.fields['finding'].form.fields['grading_sheets'].items.fields[name], 'options')
               for name in text)
    world['store'].close()


def test_a_conflicting_relation_without_its_scope_criterion_stays_unresolved(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world, screening(world))
    asyncio.run(run.next_decision())
    envelope = {'arguments': grading_arguments(world, relation='conflict'), 'scope': world['scope'],
                'page_source_ref': world['paper']['id'], 'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': ['evidence_amount'],
                              'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(run.run_unit(ToolCall('literature_a108_grading_populate', envelope)))
    assert outcome['outcome']['status'] == 'completed', outcome['outcome']
    features = EPISODE.internal_summary(run.view)['finding']['grading_sheets'][0]
    assert features['status'] == 'partial' and features['evidence_amount'] == 0
    assert features['unresolved_count'] == 1 and features['demoted_conflict_count'] == 1
    assert features['criterion_unmet_count'] == 1
    world['store'].close()


def test_an_invalid_selection_is_an_invalid_outcome_that_enters_the_iterator(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world, screening(world))
    asyncio.run(run.next_decision())
    arguments = grading_arguments(world)
    arguments['observations'][0]['original_observation_ref'] = world['claim']['id']
    envelope = {'arguments': arguments, 'scope': world['scope'], 'page_source_ref': world['paper']['id'],
                'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': [], 'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(run.run_unit(ToolCall('literature_a108_grading_populate', envelope)))
    assert outcome['outcome']['status'] == 'invalid'
    summary = EPISODE.internal_summary(run.view)
    assert summary['finding']['grading_sheets'] == []
    assert summary['literature_selected_population_attempt'] == {'tool': 'literature_a108_grading_populate',
                                                                'status': 'invalid'}
    world['store'].close()


def test_the_reasoning_commit_is_saved_with_its_grading_sheet_in_one_unit(tmp_path):
    world = held_world(tmp_path)
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'kind': 'source_answer',
            'answer_kind': 'assessment', 'credit_unit': 1.0, 'source_refs': [world['paper']['id']]}
    run = linked(tmp_path, world, task)
    asyncio.run(run.next_decision())
    envelope = {'arguments': graded_commit(world), 'scope': world['scope'], 'page_source_ref': world['paper']['id'],
                'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': ['evidence_amount'],
                              'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(run.run_unit(ToolCall('reason', envelope)))
    assert outcome['outcome']['status'] in ('completed', 'partial'), outcome['outcome']
    processing = outcome['outcome']['evidence_processing']
    assert processing['kind'] == 'graded' and len(processing['gradings']) == 1
    sheet_ref = processing['gradings'][0]['result']['sheet_ref']
    summary = EPISODE.internal_summary(run.view)
    finding = summary['finding']
    assert [item['sheet_refs'] for item in finding['grading_sheets']] == [[sheet_ref]]
    assert len(finding['assessment_refs']) == 1
    assessment = run.view.records.get(finding['assessment_refs'][0])
    assert assessment['investigation_finding']['status'] == 'retained'
    assert EPISODE.credit(summary, run.view.records) == 1.0
    closed = asyncio.run(run.run())
    assert closed['record'].ended_by == 'yield_stop' and closed['result'].as_record()['credit'] == 1.0
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, ())
    admitted = EPISODE.return_form.select(()).admit(result, 'return')
    assert 'investigation_finding' not in json.dumps(admitted) and 'Strain QX-7' not in json.dumps(admitted)
    world['store'].close()


def test_a_source_read_runs_through_the_tool_registry_with_its_declared_service(tmp_path):
    world = held_world(tmp_path)
    run = linked(tmp_path, world, screening(world))
    asyncio.run(run.next_decision())
    envelope = {'arguments': {'source_ref': world['paper']['id'], 'representation': 'original', 'offset': 0,
                              'limit': 40},
                'scope': world['scope'], 'page_source_ref': world['paper']['id'],
                'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': [], 'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(run.run_unit(ToolCall('source_read', envelope)))
    assert outcome['outcome']['status'] == 'completed', outcome['outcome']
    assert 'Strain QX-7' in json.dumps(outcome['outcome']['result'])
    world['store'].close()
