"""The real model examines a reaction source and may commission its investigations; the runner records every call
and resume replays them.

``link(...).run()`` of this episode and its three children with the standard ``ModelProvider`` over the packaged
``[models]`` configuration, on the held reaction world (``episode_support/literature/storage/tests/
reaction_world.py``). The model decides every unit of the parent and of every child it commissions; each Episode
ends when its yield controller stops it. What the parent received from each child is the child's credit and its
controlled finding. A resumed run returns the recorded result without asking the model again.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from .test_parent_grading import EPISODE, PATH, bindings, collaborators, held_world, page_entry

RUN_ID = 'a110_reaction_examination_model_run'
EPISODE_PATH = ((PATH.replace('/', '__'), RUN_ID),)
SETTINGS = {'cost': 0.02, 'parameters': {'uncertainty_alpha': 0.05}}


@pytest.mark.model_run
def test_the_model_examines_the_source_and_resume_replays_its_recorded_answers(tmp_path):
    requested = ['ratio_mean', 'reaction_comparison', 'resource_capacity', 'resource_coverage']
    store, entry, _, _ = held_world(tmp_path, requested=requested)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry(bindings())
    paths = [PATH, *EPISODE.child_slots.values()]
    links = collaborators(tmp_path, store, paths)
    links['continuation'] = {path: SETTINGS for path in paths}
    calls = tmp_path / 'model_calls'
    first = asyncio.run(link(registry, PATH, page_entry(entry, requested), run_id=RUN_ID, journal=journal,
                             collaborators=links).run())['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    units = journal.units(RUN_ID, EPISODE_PATH)
    print('A110_PARENT_UNITS', json.dumps([unit[2].get('tool', unit[2].get('slot')) for unit in units]))
    for unit in units:
        if unit[2]['kind'] == 'child':
            report = unit[2]['report']
            print('A110_CHILD_REPORT', json.dumps(report, sort_keys=True))
            assert set(report) == {'slot', 'credit', 'finding'}
            assert unit[2]['completion']['ended_by'] == 'yield_stop'
    print('A110_PARENT_RESULT', json.dumps(first, sort_keys=True))
    assert set(first) == {'credit', 'finding'} and first['credit'] >= 0
    assert EPISODE.return_form.select(()).admit(first, 'return') == first
    asked = len(list(calls.glob('call-*')))
    assert asked > 0

    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=links).run())
    assert resumed['result'].as_record() == first
    assert len(list(calls.glob('call-*'))) == asked
    store.close()
