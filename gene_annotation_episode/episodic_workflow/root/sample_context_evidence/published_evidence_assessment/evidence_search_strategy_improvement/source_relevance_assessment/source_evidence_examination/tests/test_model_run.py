"""The page run with the real model and Jev: ``link(...).run()`` with the standard ``ModelProvider`` on the held A108 world.
The first unit is the automatic ``assess_content`` (Jev measures the paper's candidates against the information needs of
the claim); the model then chooses one leaf child per decision. The run ends when the yield controller stops it; the leaf
returns as this episode receives them (``read_from_child``) are credit and controlled features only; ``resume`` of the
closed run replays the recorded answers without asking the model.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in and the Jev key."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_FEATURES)

from .a108_page import CONTINUATION, EPISODE, PATH, SERVICES, bindings, held_world, leads_task, page_assignment

RUN_ID = 'a108_examination_model_run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)


@pytest.mark.model_run
def test_the_page_assesses_then_commissions_a_leaf_with_the_real_model_and_resume_replays_it(tmp_path):
    world = held_world(tmp_path)
    calls = tmp_path / 'model_calls'
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), calls, tmp_path),
                     'continuation': CONTINUATION, 'services': SERVICES}
    registry = BindingRegistry(bindings())
    entry = {'assignment': page_assignment(world, leads_task()), 'message': {'purpose': 'examine'}, 'selection': []}
    closed = asyncio.run(link(registry, PATH, entry, run_id=RUN_ID, journal=journal,
                              collaborators=collaborators).run())
    result = closed['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    units = [unit[2] for unit in journal.units(RUN_ID, JOURNAL_PATH)]
    trace = [(unit['kind'], unit.get('slot') or unit.get('tool')) for unit in units]
    reports = [unit['report'] for unit in units if unit['kind'] == 'child']
    print('A108_EXAMINATION_UNITS', trace)
    print('A108_EXAMINATION_CHILD_REPORTS', json.dumps(reports))
    print('A108_EXAMINATION_RESULT', json.dumps(result))
    assert trace[0] == ('tool', 'assess_content')
    assert {kind for kind, _ in trace[1:]} <= {'child'}
    for report in reports:
        assert set(report) <= {'slot', 'credit', 'finding', 'leads', 'literature_a108_grading_cells',
                               'literature_a108_aggregation_cells'}
        for features in report['finding']['grading_sheets']:
            assert set(features) == set(GRADING_FEATURES)
        assert 'Strain QX-7' not in json.dumps(report)
    recorded = journal.model_calls(RUN_ID, JOURNAL_PATH)
    asked = len(list(calls.glob('call-*')))
    assert asked >= len(recorded)

    again = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=collaborators).run())
    assert again['result'].as_record() == result
    assert len(list(calls.glob('call-*'))) == asked
    world['store'].close()
