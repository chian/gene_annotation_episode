"""The leaf run with the real model: ``link(...).run()`` with the standard ``ModelProvider`` on the held A108 world
(``a108_world``). The commission is an assessment answer about the paper: a completion task whose target is one
credit unit, so the run ends when the yield controller stops it. The result is checked as the parent receives it
(credit and the controlled finding admitted by the return form), and ``resume`` of the closed run replays the
recorded answers without asking the model again.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .a108_world import SERVICES, SETTINGS, held_world, reading_assignment

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path
RUN_ID = 'a108_leaf_model_run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)
SELECTION = ['literature_a108_grading_cells']


def assessment_task(world):
    return {'version': 'literature_local_task_v1', 'evidence_axis': 'A108', 'kind': 'source_answer',
            'answer_kind': 'assessment', 'credit_unit': 1.0, 'source_refs': [world['paper']['id']]}


@pytest.mark.model_run
def test_the_leaf_grades_the_source_with_the_real_model_and_resume_replays_it(tmp_path):
    world = held_world(tmp_path)
    calls = tmp_path / 'model_calls'
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    collaborators = {'store': world['store'], 'model_provider': ModelProvider(load_config(), calls, tmp_path),
                     'continuation': {PATH: SETTINGS}, 'services': SERVICES}
    registry = BindingRegistry([EPISODE()])
    entry = {'assignment': reading_assignment(world, assessment_task(world)),
             'message': {'objective': 'Does the paper show that the target organism uses succinate? Grade it.'},
             'selection': SELECTION}
    closed = asyncio.run(link(registry, PATH, entry, run_id=RUN_ID, journal=journal,
                              collaborators=collaborators).run())
    result = closed['result'].as_record()
    state = journal.run_state(RUN_ID)[1]
    assert state['ended_by'] == 'yield_stop'
    form = EPISODE.return_form.select(SELECTION)
    assert form.admit(result, 'return') == result
    units = journal.units(RUN_ID, JOURNAL_PATH)
    tools = [unit[2]['tool'] for unit in units]
    (tmp_path / 'decisions.json').write_text(json.dumps({'tools': tools, 'result': result}, indent=1))
    print('A108_LEAF_TOOLS', tools)
    print('A108_LEAF_RESULT', json.dumps(result))
    finding = result['finding']
    for features in finding['grading_sheets']:
        assert features['sheet_refs'][0] in form.record_refs(result)
    recorded = journal.model_calls(RUN_ID, JOURNAL_PATH)
    assert recorded
    asked = len(list(calls.glob('call-*')))

    again = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=collaborators).run())
    assert again['result'].as_record() == result
    assert len(list(calls.glob('call-*'))) == asked
    assert journal.model_calls(RUN_ID, JOURNAL_PATH) == recorded
    world['store'].close()
