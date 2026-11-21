"""The A105 grading of the source examination and of the reading children it commissions, through the real runner
on a real Store. Offline: the first decision offers ``reason``, the three children and the owner's grading
instructions; a ``reason`` unit saves the grading sheet; the finding is the controlled features read from it. With the
real model (``-m model_run``): the examination runs to the stop of its yield estimator, a child it commissions
returns only its credit and the controlled features of its sheets, and a resume replays the recorded answers."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ChildCall, ModelRequest, RunJournal, ToolCall, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)

from .grading_world import CHILD_PATHS, SETTINGS, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
PATH = EPISODE.binding_path
CHILDREN = [importlib.import_module(PACKAGE + '.' + name + '.episode') for name in CHILD_PATHS]
CHILD_CLASSES = [getattr(module, name) for module, name in zip(
    CHILDREN, ('TableEvidenceExtraction', 'SourceCoverageImprovement', 'PassageEvidenceExtraction'))]


def registry():
    return BindingRegistry([EPISODE(), *(cls() for cls in CHILD_CLASSES)])


def linked_run(directory, world, run_id, settings=SETTINGS):
    continuation = {PATH: settings, **{cls.binding_path: {**settings, 'launch_instruction_directory': None}
                                       for cls in CHILD_CLASSES}}
    world['collaborators'] = {'store': world['store'],
                              'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                              'continuation': continuation, 'services': {}}
    return link(registry(), PATH, world['input'], run_id=run_id, journal=RunJournal(directory / 'journal.sqlite3'),
                collaborators=world['collaborators'])


def test_the_next_decision_offers_reason_the_children_and_the_owners_grading_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-examination-decision')
    request = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    assert summary['assay_sheets'] == [] and summary['child_returns'] == []
    assert EPISODE.credit(summary, run.view.records) == 0
    assert isinstance(request, ModelRequest) and ASSAY_GRADING_TASK in request.instructions
    tools = {entry['name'] for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    assert {option['slot'] for option in request.context['child_options']} == set(EPISODE.child_slots)
    world['store'].close()


def test_the_reason_unit_saves_the_sheet_and_the_finding_is_its_features(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-examination-reason')
    asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    unit = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': reasoning_selection(world), 'scope': world['scope'], 'page_source_ref': world['source'],
        'assignment': summary['literature_assignment'], 'requested': summary['requested'],
        'proposed_annotation_ref': world['proposed'], 'examined_windows': []})))
    assert unit['outcome']['status'] == 'completed', json.dumps(unit['outcome'])[:2000]
    sheet_ref = unit['outcome']['evidence_processing']['gradings'][0]['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    assert [features['sheet_refs'] for features in summary['assay_sheets']] == [[sheet_ref]]
    assert EPISODE.credit(summary, run.view.records) == 1.0
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}, ())
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    world['store'].close()


@pytest.mark.model_run
def test_the_model_examines_the_source_and_resume_replays_its_answers(tmp_path):
    """The real model examines the source: it reads, grades or commissions a reading child. The examination ends
    through its yield estimator; what a commissioned child returned is its credit and the controlled features of its
    sheets; a resume replays every recorded answer without a new model call."""
    world = held_world(tmp_path)
    run_id = 'a105-examination-model'
    run = linked_run(tmp_path, world, run_id, settings={**SETTINGS, 'cost': 0.1})
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    path = ((EPISODE().grain_name, run_id),)
    units = journal.units(run_id, path)
    print('UNITS', [(unit[2]['kind'], unit[2].get('tool') or unit[2].get('slot'),
                     unit[2]['outcome'].get('status') if unit[2]['kind'] == 'tool' else unit[2]['report']['credit'])
                    for unit in units])
    print('RESULT', json.dumps(result)[:3000])
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    for unit in units:
        if unit[2]['kind'] == 'child':
            report = unit[2]['report']
            assert set(report) == {'slot', 'credit', 'assay_sheets', 'aggregation_sheets', 'counts',
                                   'lead_source_refs', 'screening_covered'}
            assert set(unit[2]['result']) == {'credit', 'finding'}
            print('CHILD', report['slot'], report['credit'], report['counts'])
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume(registry(), run_id=run_id, journal=journal,
                                 collaborators=world['collaborators']).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    world['store'].close()


@pytest.mark.model_run
def test_the_examination_commissions_the_table_reading_and_receives_its_credit_and_features(tmp_path):
    """The examination's first unit commissions its table-reading child (named here in place of the examination's
    own decision); the child runs with the real model until its yield estimator stops it, and the examination
    receives only the child's credit and the controlled features of the sheets it saved. The examination then runs
    on with the real model until its own estimator stops it, and a resume replays every recorded answer."""
    world = held_world(tmp_path)
    run_id = 'a105-examination-commission'
    run = linked_run(tmp_path, world, run_id, settings={**SETTINGS, 'cost': 0.1})
    page = {'source_ref': world['source'], 'representation': 'original', 'artifact_ref': world['artifact']}
    window = {'source_ref': world['source'], 'representation': 'original', 'offset': 0, 'limit': 400}
    unit = asyncio.run(run.run_unit(ChildCall('table', {
        'objective': 'grade_reported_experiment', 'page': page,
        'selection': window})))
    report = unit['report']
    print('CHILD', report['credit'], report['counts'], [features['sheet_refs'] for features in report['assay_sheets']])
    assert set(report) == {'slot', 'credit', 'assay_sheets', 'aggregation_sheets', 'counts', 'lead_source_refs',
                           'screening_covered'}
    assert set(unit['result']) == {'credit', 'finding'}
    for features in report['assay_sheets']:
        assert run.view.records.receipt(features['sheet_refs'][0])['how'] == 'returned'
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    units = journal.units(run_id, ((EPISODE().grain_name, run_id),))
    print('UNITS', [(item[2]['kind'], item[2].get('tool') or item[2].get('slot')) for item in units])
    print('RESULT', json.dumps(result)[:2000])
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    assert {features['sheet_refs'][0] for features in report['assay_sheets']} <= {
        features['sheet_refs'][0] for features in result['finding']['assay_sheets']}
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume(registry(), run_id=run_id, journal=journal,
                                 collaborators=world['collaborators']).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    world['store'].close()
