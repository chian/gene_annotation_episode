"""A real run of this episode with the real model, through the public runner only.

The entry assignment holds a source that reports one assay (its effect, variance, controls and fixed predictions,
each a number with its printed unit), the anchored assay reference, the reaction term and the proposed annotation
(``grading_world.py``). ``link(...).run()`` runs the Episode with the standard ``ModelProvider``; every decision is the
model's. The run ends through the yield controller; the journal holds the model calls and the units; credit and
finding are what the episode's own code computes from the held records and the saved sheet; the return holds exactly
the fields ``RETURN_FORM`` admits; and a resume replays the recorded answers without a new model call.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config

from .grading_world import held_world, model_settings

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
PATH = EPISODE.binding_path
RUN_ID = 'real104_passage'


def collaborators(world, directory):
    return {'store': world['store'],
            'model_provider': world['provider'],
            'continuation': {PATH: model_settings(directory)}, 'services': {}}


@pytest.mark.model_run
def test_the_model_grades_the_passage_and_the_run_ends_by_its_yield_controller(tmp_path):
    world = held_world(tmp_path)
    world['provider'] = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry([EPISODE()])
    closed = asyncio.run(link(registry, PATH, world['input'], run_id=RUN_ID, journal=journal,
                              collaborators=collaborators(world, tmp_path)).run())
    result = closed['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    (episode_row,) = list(journal.episodes(RUN_ID))
    path = episode_row['path']
    calls, units = journal.model_calls(RUN_ID, path), journal.units(RUN_ID, path)
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    assert calls and units and asked == len(calls)
    print('MODEL_DECISIONS', json.dumps([{'position': call['position'], 'response': call['response']}
                                          for call in calls], indent=1)[:12000])
    print('UNITS', json.dumps([(unit[2]['tool'], unit[2]['outcome'].get('status'), unit[2]['outcome'].get('feedback'))
                               for unit in units])[:6000])
    print('RESULT', json.dumps(result)[:4000])
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators(world, tmp_path)).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    world['store'].close()
