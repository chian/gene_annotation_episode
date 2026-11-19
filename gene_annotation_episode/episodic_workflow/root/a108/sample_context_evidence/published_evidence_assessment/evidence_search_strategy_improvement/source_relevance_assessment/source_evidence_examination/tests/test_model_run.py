"""The source evidence examination run with the real model: ``link(...).run()`` with the standard ``ModelProvider`` on
the held A108 world. The commission is an assessment answer about the paper (a completion task of one credit unit);
the commissioner's message asks for an ordered reading by the ``source_coverage_improvement`` child. The run ends when
the yield controller stops it; the child's return as this episode receives it (``read_from_child``) is credit and
controlled features only; ``resume`` of the closed run replays the recorded answers without asking the model.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_FEATURES)

from .a108_page import CONTINUATION, EPISODE, PATH, SERVICES, assessment_task, bindings, held_world, page_assignment

RUN_ID = 'a108_examination_model_run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)
OBJECTIVE = ('Your commissioner asks you to delegate: your first action must be the child commission '
             'source_coverage_improvement (an ordered reading of the paper from offset 0 over the whole paper), '
             'which grades what it reads. Question: does the paper show that the target organism uses succinate? '
             'Do not read or grade the paper yourself before that child has returned.')


@pytest.mark.model_run
def test_the_examination_commissions_its_reading_child_with_the_real_model_and_resume_replays_it(tmp_path):
    world = held_world(tmp_path)
    calls = tmp_path / 'model_calls'
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), calls, tmp_path),
                     'continuation': CONTINUATION, 'services': SERVICES}
    registry = BindingRegistry(bindings())
    entry = {'assignment': page_assignment(world, assessment_task(world)), 'message': {'objective': OBJECTIVE},
             'selection': []}
    closed = asyncio.run(link(registry, PATH, entry, run_id=RUN_ID, journal=journal,
                              collaborators=collaborators).run())
    result = closed['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    units = [unit[2] for unit in journal.units(RUN_ID, JOURNAL_PATH)]
    trace = [(unit['kind'], unit.get('slot') or unit.get('tool')) for unit in units]
    reports = [unit['report'] for unit in units if unit['kind'] == 'child']
    (tmp_path / 'decisions.json').write_text(json.dumps({'units': trace, 'reports': reports, 'result': result},
                                                        indent=1))
    print('A108_EXAMINATION_UNITS', trace)
    print('A108_EXAMINATION_CHILD_REPORTS', json.dumps(reports))
    print('A108_EXAMINATION_RESULT', json.dumps(result))
    assert ('child', 'source_coverage_improvement') in trace
    for report in reports:
        assert set(report) <= {'credit', 'finding', 'literature_a108_grading_cells', 'literature_a108_aggregation_cells'}
        assert type(report['credit']) in (int, float)
        for features in report['finding']['grading_sheets']:
            assert set(features) == set(GRADING_FEATURES)
        assert 'Strain QX-7' not in json.dumps(report)
    recorded = journal.model_calls(RUN_ID, JOURNAL_PATH)
    asked = len(list(calls.glob('call-*')))
    assert recorded and asked >= len(recorded)

    again = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=collaborators).run())
    assert again['result'].as_record() == result
    assert len(list(calls.glob('call-*'))) == asked
    assert journal.model_calls(RUN_ID, JOURNAL_PATH) == recorded
    world['store'].close()
