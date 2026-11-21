"""A real run of the local resource work execution episode with the real model, through the public runner only.

The world (``local_world``) is a Store that holds the work as a record (a small real computation: a Python program
that reads its staged input and writes the sum of the squares of 1..100 to ``result.txt``) and one local resource of
the run's job services. ``link(...).run()`` runs the Episode with the standard ``ModelProvider``; every decision is
the model's: it routes among the episode's defined actions and code runs them. The model writes no command. The
launched job is real (a detached systemd service): a later run fetches its result through the returned handoff row.
Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from .local_world import ANSWER, EPISODE, PATH, SETTINGS, collaborators, entry, later_fetch, world

RUN_ID = 'branch102_local'


@pytest.mark.model_run
def test_the_model_launches_the_work_on_the_local_resource_and_the_run_ends_by_its_yield_controller(tmp_path):
    store, services, records = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry([EPISODE()])
    continuation = {PATH: SETTINGS}
    first = asyncio.run(link(registry, PATH, entry(records), run_id=RUN_ID, journal=journal,
                             collaborators=collaborators(store, tmp_path, services, continuation)).run())
    result = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes(RUN_ID)
    path = episode['path']
    calls, units = journal.model_calls(RUN_ID, path), journal.units(RUN_ID, path)
    assert calls and units and len(list((tmp_path / 'model_calls').glob('call-*'))) == len(calls)
    print('DECISIONS', json.dumps([call['response'] for call in calls]))
    print('UNITS', json.dumps([(unit[2]['tool'], unit[2]['outcome']['status'], unit[1]['credit'])
                               for unit in units]))
    print('RESULT', json.dumps(result))
    assert EPISODE.return_form.admit(result, 'return') == result
    assert result['credit'] == episode['completion']['credit'] == units[-1][1]['credit'] == 7.0
    assert result['finding']['job_state'] in ('queued', 'running', 'finished')
    launches = [unit[2]['outcome'] for unit in units if unit[2]['tool'] == 'launch_work']
    assert len(launches) == 1 and result['handoff_refs'] == [launches[0]['handoff_ref']]
    assert later_fetch(store, tmp_path, services, journal, result['handoff_refs'][0], 'result.txt') == ANSWER
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, continuation)).run())
    assert resumed['result'].as_record() == result
    assert journal.model_calls(RUN_ID, path) == calls and journal.units(RUN_ID, path) == units
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    store.close()
