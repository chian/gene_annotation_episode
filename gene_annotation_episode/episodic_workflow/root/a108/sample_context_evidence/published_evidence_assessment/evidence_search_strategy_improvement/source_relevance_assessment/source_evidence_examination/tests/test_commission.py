"""The source evidence examination and its ordered-reading child on the real runner and a real Store.

The parent is linked with the public API and its first decision is its own ``decide`` (no model call): it offers
the three child commissions and the A108 grading tools with the grader's instructions. Its commission of the
ordered-reading child is admitted by the child's own forms, the child (run in its own linked run on the same Store)
saves a real subscoring sheet, and what the parent takes from the child's admitted return (``read_from_child``) is
controlled data only: credit, the features of the child's sheets with their references, and the requested cell rows."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_FEATURES, GRADING_INSTRUCTIONS)

from ..source_coverage_improvement.tests.a108_world import grading_arguments
from .a108_page import (CONTINUATION, EPISODE, PATH, SERVICES, assessment_task, bindings, held_world,
                        page_assignment)

LEAF = importlib.import_module(EPISODE.__module__.rsplit('.', 1)[0]
                               + '.source_coverage_improvement.episode').SourceCoverageImprovement
TO_CHILD = importlib.import_module(EPISODE.__module__.rsplit('.', 1)[0] + '.messages.msg_to_child')
FROM_CHILD = importlib.import_module(EPISODE.__module__.rsplit('.', 1)[0] + '.messages.read_from_child')


def collaborators(directory, world, name):
    return {'store': world['store'], 'model_provider': ModelProvider(load_config(), directory / name, directory),
            'continuation': CONTINUATION, 'services': SERVICES}


def test_the_parent_offers_its_children_and_commissions_the_reading_that_returns_controlled_features(tmp_path):
    world = held_world(tmp_path)
    entry = {'assignment': page_assignment(world, assessment_task(world)), 'message': {'objective': 'examine'},
             'selection': []}
    registry = BindingRegistry(bindings())
    run = link(registry, PATH, entry, run_id='a108-examination', journal=RunJournal(tmp_path / 'parent.sqlite3'),
               collaborators=collaborators(tmp_path, world, 'parent_calls'))
    request = asyncio.run(run.next_decision())
    view = run.view
    assert view.controller_state is not None and view.units_consumed == 0
    summary = EPISODE.internal_summary(view)
    assert EPISODE.credit(summary, view.records) == 0
    assert summary['finding'] == {'grading_sheets': [], 'aggregation_cells': [], 'assessment_refs': [], 'observation_refs': []}
    assert isinstance(request, ModelRequest)
    tools = {item['name'] for item in request.context['tools']}
    assert {'source_coverage_improvement', 'table_evidence_extraction', 'passage_evidence_extraction', 'reason',
            'literature_a108_grading_populate'} <= tools and 'report' not in tools
    assert GRADING_INSTRUCTIONS in request.instructions

    window = {'source_ref': world['paper']['id'], 'representation': 'original', 'offset': 0, 'limit': 200}
    message = TO_CHILD.msg_to_child('source_coverage_improvement', {'objective': 'read', 'selection': window},
                                    summary)
    assert message.selection == ('literature_a108_grading_cells',)
    child_assignment = LEAF.assignment_form.admit(message.assignment, 'commission')
    child_form = LEAF.return_form.select(message.selection)

    # The child, commissioned with exactly that assignment, grades the source in a real tool unit.
    child_run = link(BindingRegistry([LEAF()]), LEAF.binding_path,
                     {'assignment': child_assignment, 'message': {'objective': 'read'},
                      'selection': list(message.selection)},
                     run_id='a108-reading', journal=RunJournal(tmp_path / 'child.sqlite3'),
                     collaborators=collaborators(tmp_path, world, 'child_calls'))
    asyncio.run(child_run.next_decision())
    envelope = {'arguments': grading_arguments(world), 'scope': world['scope'],
                'page_source_ref': world['paper']['id'], 'proposed_annotation_ref': world['claim']['id'],
                'requested': {'requested_a108_grading_components': ['evidence_amount'],
                              'requested_a108_aggregation_components': []}}
    outcome = asyncio.run(child_run.run_unit(ToolCall('literature_a108_grading_populate', envelope)))
    assert outcome['outcome']['status'] == 'completed'
    child_summary = LEAF.internal_summary(child_run.view)
    result = child_form.admit(LEAF.final_to_parent(child_summary, {'ended_by': 'yield_stop', 'units_consumed': 1,
                                                                   'credit': 0.0}, message.selection), 'return')

    report = FROM_CHILD.read_from_child('source_coverage_improvement', result, summary, view.records)
    assert set(report) == {'credit', 'finding', 'literature_a108_grading_cells'}
    assert [set(item) for item in report['finding']['grading_sheets']] == [set(GRADING_FEATURES)]
    assert report['finding']['grading_sheets'][0]['evidence_amount'] == 1
    assert len(report['literature_a108_grading_cells']) == 1
    text = json.dumps(report)
    assert 'Strain QX-7' not in text and 'succinate' not in text
    world['store'].close()
