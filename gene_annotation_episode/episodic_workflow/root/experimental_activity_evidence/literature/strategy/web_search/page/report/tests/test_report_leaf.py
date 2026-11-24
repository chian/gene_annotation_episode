"""The report leaf through the real runner, without the model: it is handed the sheet class (never an experiment type) and the
windows in document order; each window is named once, in order (a window named none is done without a record and the next
window is offered), and the Episode ends by the list bound when every window is done. Nothing is faked."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, Rejected, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    EXPERIMENT_TYPE_LINES, experiment_types_of_class)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ...chunk.tests.leaf_world import SETTINGS, held_world
from ..episode import SourceCoverageImprovement
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent

PATH = SourceCoverageImprovement.binding_path
FIRST, SECOND = 'First window of the paper.', 'Second window of the paper.'
TEXT = FIRST + SECOND
WINDOWS = [[0, len(FIRST)], [len(FIRST), len(TEXT)]]


def linked(world, run_id):
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls', world['directory']),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([SourceCoverageImprovement()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(world['directory'] / 'journal.sqlite3'), collaborators=collaborators)


def report_world(tmp_path):
    world = held_world(tmp_path, TEXT, 0, len(TEXT), name='report', experiment_type='spr')
    assignment = world['input']['assignment']
    del assignment['offset'], assignment['limit']
    assignment['windows'] = WINDOWS
    return world


def test_the_commission_hands_the_sheet_class_and_no_experiment_type(tmp_path):
    assert 'sheet_class' in ASSIGNMENT_FORM.fields and 'experiment_type' not in ASSIGNMENT_FORM.fields
    assert ASSIGNMENT_FORM.fields['sheet_class'].options == ('ligand_binding', 'activity_rate')
    world = report_world(tmp_path)
    assert 'experiment_type' not in world['input']['assignment']
    assert 'experiment_type' not in read_from_parent(world['input']['assignment'], {})
    world['store'].close()


def test_each_window_is_named_once_in_order_and_a_window_named_none_holds_no_record(tmp_path):
    world = report_world(tmp_path)
    run = linked(world, 'a105-report-offline')
    types = experiment_types_of_class('ligand_binding')
    for window, text in enumerate((FIRST, SECOND)):
        request = asyncio.run(run.next_decision())
        assert request.context['window'] == text and 'experiment_type' not in request.context
        assert request.context['methods'] == {name: EXPERIMENT_TYPE_LINES[name] for name in types}
        assert request.output_schema['properties']['method']['enum'] == [*types, 'none']
        summary = SourceCoverageImprovement._summary(SourceCoverageImprovement(), run.view)
        assert summary['input_list'] == WINDOWS[window:]
        with pytest.raises(Rejected):
            SourceCoverageImprovement.action({'method': 'spectro_direct'}, summary, run.view.records, None)
        call = SourceCoverageImprovement.action({'method': 'none'}, summary, run.view.records, None)
        assert call.arguments['experiment_type'] is None and call.arguments['chunk'] == text
        asyncio.run(run.run_unit(call))
    after = SourceCoverageImprovement._summary(SourceCoverageImprovement(), run.view)
    assert after['input_list'] == [] and after['named_methods'] == [None, None] and after['record_refs'] == []
    result = asyncio.run(run.run())['result'].as_record()
    assert result['credit'] == 0.0 and run.journal.run_state('a105-report-offline')[1]['ended_by'] == 'yield_stop'
    world['store'].close()
