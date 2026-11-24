"""The table leaf through the real runner, without the model: it is handed the sheet class (never an experiment type), it is
asked to name the method the table region reports from the types of that class, and a region named none is done without a
record, which ends the Episode by the list bound. Nothing is faked."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    EXPERIMENT_TYPE_LINES, experiment_types_of_class)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ...chunk.tests.leaf_world import SETTINGS, held_world
from ..episode import TableEvidenceExtraction
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent

PATH = TableEvidenceExtraction.binding_path
TABLE = 'Table 2.\nVariant\tKd (nM)\nwild type\t12 +/- 2\nmutant\t340 +/- 40\nEach value is the mean of three experiments.'


def linked(world, run_id):
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls', world['directory']),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    return link(BindingRegistry([TableEvidenceExtraction()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(world['directory'] / 'journal.sqlite3'), collaborators=collaborators)


def table_world(tmp_path, experiment_type='fp'):
    return held_world(tmp_path, 'Preceding. ' + TABLE + ' Following.', 11, len(TABLE.encode()), name='table',
                      experiment_type=experiment_type)


def test_the_commission_hands_the_sheet_class_and_no_experiment_type(tmp_path):
    assert 'sheet_class' in ASSIGNMENT_FORM.fields and 'experiment_type' not in ASSIGNMENT_FORM.fields
    assert ASSIGNMENT_FORM.fields['sheet_class'].options == ('ligand_binding', 'activity_rate')
    world = table_world(tmp_path)
    assert 'experiment_type' not in world['input']['assignment']
    assert 'experiment_type' not in read_from_parent(world['input']['assignment'], {})
    world['store'].close()


def test_the_table_leaf_names_the_method_from_the_types_of_the_class(tmp_path):
    world = table_world(tmp_path)
    run = linked(world, 'a105-table-offline')
    request = asyncio.run(run.next_decision())
    types = experiment_types_of_class('ligand_binding')
    assert request.context['methods'] == {name: EXPERIMENT_TYPE_LINES[name] for name in types}
    assert request.context['table'] == TABLE and 'experiment_type' not in request.context
    assert request.output_schema['properties']['method']['enum'] == [*types, 'none']
    summary = TableEvidenceExtraction._summary(TableEvidenceExtraction(), run.view)
    assert summary['input_list'] == [[11, 11 + len(TABLE.encode())]]
    world['store'].close()


def test_a_table_region_named_none_is_done_without_a_record_and_the_list_bound_ends_the_episode(tmp_path):
    world = table_world(tmp_path)
    run = linked(world, 'a105-table-offline')
    asyncio.run(run.next_decision())
    summary = TableEvidenceExtraction._summary(TableEvidenceExtraction(), run.view)
    call = TableEvidenceExtraction.action({'method': 'none'}, summary, run.view.records, None)
    assert call.name == 'extract' and call.arguments['experiment_type'] is None
    asyncio.run(run.run_unit(call))
    after = TableEvidenceExtraction._summary(TableEvidenceExtraction(), run.view)
    assert after['input_list'] == [] and after['named_methods'] == [None] and after['record_refs'] == []
    result = asyncio.run(run.run())['result'].as_record()
    assert result['credit'] == 0.0 and run.journal.run_state('a105-table-offline')[1]['ended_by'] == 'yield_stop'
    world['store'].close()
