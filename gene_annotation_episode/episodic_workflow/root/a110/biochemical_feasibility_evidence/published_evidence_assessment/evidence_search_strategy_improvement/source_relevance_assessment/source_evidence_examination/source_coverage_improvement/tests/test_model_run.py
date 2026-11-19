"""The real model reads a reaction source and grades it; the runner records every call and resume replays them.

``link(...).run()`` of this leaf with the standard ``ModelProvider`` over the packaged ``[models]`` configuration,
on the held world of ``test_reaction_grading.py``: a short paper that reports two preparations' product ratios, a
named alternative and a resource budget, the retained ``a110_source_reaction_measurements_v1`` dataset of those
numbers, a source of literal witnesses and an interpretation source. The model decides every unit; the run ends
when the yield controller stops it. Nothing in the episode files records a call: the journal holds them, and a
resumed run returns the recorded result without asking the model again.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .test_reaction_grading import PATH, held_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
RUN_ID = 'a110_reaction_leaf_model_run'
EPISODE_PATH = ((PATH.replace('/', '__'), RUN_ID),)
SETTINGS = {'cost': 0.02, 'parameters': {'uncertainty_alpha': 0.05}}


@pytest.mark.model_run
def test_the_model_grades_the_reaction_source_and_resume_replays_its_recorded_answers(tmp_path):
    store, entry, _, _ = held_world(tmp_path, requested=['ratio_mean', 'reaction_comparison', 'resource_capacity',
                                                         'resource_coverage'])
    calls = tmp_path / 'model_calls'
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), calls, tmp_path),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    registry = BindingRegistry([EPISODE()])
    first = asyncio.run(link(registry, PATH, entry, run_id=RUN_ID, journal=journal,
                             collaborators=collaborators).run())['result'].as_record()
    state = journal.run_state(RUN_ID)[1]
    assert state['ended_by'] == 'yield_stop'
    recorded = journal.model_calls(RUN_ID, EPISODE_PATH)
    assert recorded and len(list(calls.glob('call-*'))) == len(recorded)
    units = journal.units(RUN_ID, EPISODE_PATH)
    tools = [unit[2]['tool'] for unit in units]
    print('A110_LEAF_TOOLS', json.dumps(tools))
    print('A110_LEAF_RESULT', json.dumps(first, sort_keys=True))
    assert set(first) == {'credit', 'finding'} and first['credit'] >= 0
    assert EPISODE.return_form.select(()).admit(first, 'return') == first
    finding = first['finding']
    assert finding['retained_finding_count'] == len(finding['finding_refs'])
    assert all(sheet['evidence_type'] == 'prediction_contrast' for sheet in finding['reaction_sheets'])

    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == first
    assert len(list(calls.glob('call-*'))) == len(recorded)
    assert journal.model_calls(RUN_ID, EPISODE_PATH) == recorded
    store.close()
