"""The A105 grading of the source examination and of the reading children it commissions, through the real runner
on a real Store. Offline: the first decision is code's Jev assessment of the page's candidates against the commission's
information needs, and the candidates of a real paper and the report's windows over the remaining chunks. With the
real model (``-m model_run``): the examination runs to the stop of its yield estimator, a child it commissions
returns only its credit and the controlled features of its sheets, and a resume replays the recorded answers."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ChildCall, RunJournal, ToolCall, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    spr_passages)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_page_content import (
    PROSE_CHUNK, page_candidates, report_windows)

from .grading_world import CHILD_PATHS, SETTINGS, held_world
from .test_branch_page_model_run import popz_world

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


def test_the_first_decision_is_the_jev_assessment_of_every_candidate_against_the_commissions_needs(tmp_path):
    """Offline, on the real PopZ page of the page test: before the page plans, its first decision is made by code (no
    model call): ``assess_content`` of the page's candidates (the prose chunks of the source, byte offsets) against the
    information needs of the commission (the result and the molecule identity of the commissioned SPR experiment). Every
    candidate is unconsumed, the input list is the candidates, and the one action offered is the assessment."""
    world = popz_world(tmp_path)
    run = linked_run(tmp_path, world, 'a105-examination-assessment-decision')
    decision = asyncio.run(run.next_decision())
    summary = EPISODE()._summary(run.view)
    content = world['text'].encode('utf-8')
    candidates = page_candidates(content)
    assert summary['content_candidates'] == candidates and candidates
    assert all(item['candidate_type'] == PROSE_CHUNK for item in candidates)        # the paragraph holds no table
    assert candidates[0]['start'] == 0 and candidates[-1]['end'] == len(content)
    assert summary['consumed_candidate_ids'] == [] and summary['content_assessment_ref'] is None
    assert summary['unconsumed_chunk_ids'] == [item['candidate_id'] for item in candidates]
    assert summary['input_list'] == summary['unconsumed_chunk_ids']
    assert summary['report_windows'] == [[0, len(content)]]                        # consecutive chunks: one window
    assert [need['need_id'] for need in summary['information_needs']] == [
        'result:' + world['assay'], 'identity:' + world['assay']]
    assert summary['jev_goal']['claim'] == {'predicate': 'binds', 'subject_id': 'PopZ', 'partner_id': 'ParB'}
    assert isinstance(decision, ToolCall) and decision.name == 'assess_content'
    assert decision.arguments['information_needs'] == summary['information_needs']
    assert EPISODE.offered_actions(summary, None) == ['assess_content']
    assert EPISODE.credit(summary, run.view.records) == 0
    assert list((tmp_path / 'model_calls').glob('call-*')) == []
    world['store'].close()


def test_the_candidates_of_a_real_paper_cover_its_text_and_the_report_reads_each_remaining_chunk_once():
    """On the real text of Bowman et al. 2008 (``spr_passages.PRIMARY``): the candidates are in document order with
    byte offsets that decode; consecutive prose chunks overlap by at most nano-graphrag's overlap and no prose chunk holds
    a table's bytes; with one chunk consumed the report's windows hold every remaining chunk exactly once and none of the
    consumed one's bytes outside its overlaps with its neighbours."""
    content = spr_passages.PRIMARY.read_text(encoding='utf-8').encode('utf-8')
    candidates = page_candidates(content)
    chunks = [item for item in candidates if item['candidate_type'] == PROSE_CHUNK]
    tables = [item for item in candidates if item['candidate_type'] != PROSE_CHUNK]
    assert len(chunks) > 3
    for item in candidates:
        content[item['start']:item['end']].decode('utf-8')
    for chunk in chunks:
        assert not any(chunk['start'] < table['end'] and table['start'] < chunk['end'] for table in tables)
    consumed = chunks[1]['candidate_id']
    remaining = {item['candidate_id'] for item in chunks} - {consumed}
    windows = report_windows(candidates, remaining)
    for chunk in chunks:
        inside = [window for window in windows if window[0] <= chunk['start'] and chunk['end'] <= window[1]]
        assert len(inside) == (0 if chunk['candidate_id'] == consumed else 1)
    assert all(earlier[1] <= later[0] for earlier, later in zip(windows, windows[1:]))


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
