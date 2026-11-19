"""A real run of this episode with the real model (``episode_runtime/tests/test_model_run.py`` is the pattern): the
model reads the held paper source and decides, unit by unit, which tool to use; the run ends when the Episode's yield
controller stops it. The return is the credit and the controlled finding read by code from the sheets the model
saved; a resumed run replays the recorded answers without asking the model again.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, resume

from .a106_world import SETTINGS, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path
RUN_ID = 'a106_source_coverage_model_run'
# A positive continuation cost: with no credit the accumulation estimator stops the Episode.
RUN_SETTINGS = {PATH: {**SETTINGS, 'cost': 0.05}}


@pytest.mark.model_run
def test_the_model_reads_and_grades_the_source_and_resume_replays_its_recorded_answers(tmp_path):
    store, entry, _, names = held_world(tmp_path)
    linked, journal, collaborators = linked_run(tmp_path, [EPISODE()], PATH, entry, store, RUN_ID, RUN_SETTINGS)
    first = asyncio.run(linked.run())
    record = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    units = [unit[2] for unit in journal.units(RUN_ID, ((PATH.replace('/', '__'), RUN_ID),))]
    print('A106_LEAF_TOOLS', [(unit.get('tool'), (unit.get('outcome') or {}).get('status')) for unit in units])
    assert set(record) == {'credit', 'finding'}
    assert set(record['finding']) == {'intervention_assessments', 'a106_subscores'}
    EPISODE.return_form.select(()).admit(record, 'return')
    json.dumps(record, allow_nan=False)
    calls = list((tmp_path / 'model_calls').glob('call-*'))
    assert calls
    print('A106_LEAF_RESULT', json.dumps(record, sort_keys=True))
    print('A106_LEAF_UNITS', first['record'].units_consumed)

    resumed = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == record
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == len(calls)
    store.close()
