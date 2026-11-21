"""A real run of the resource result acquisition episode with the real model, fetching the result of a real job.

The run's caller holds a real finished local job (``acquisition_world``: a Python program that sums the squares of
1..100 and writes ``answer.txt``). It commissions the acquisition episode with the job's handoff row in custody and
the requested file name. ``link(...).run()`` runs the Episode with the standard ``ModelProvider`` and the same job
services; every decision is the model's: it routes among the episode's defined actions and code runs them. Selected
only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from .acquisition_world import (ANSWER, EPISODE, PATH, PROGRAM, SETTINGS, collaborators, entry, launched_job,
                                world)

RUN_ID = 'branch102_acquisition'
SELECTION = ('check_refs',)
LONG = 'import time\ntime.sleep(20)\n' + PROGRAM          # longer than the model takes to answer once


@pytest.mark.model_run
def test_the_model_fetches_the_result_of_the_job_and_the_run_ends_by_its_yield_controller(tmp_path):
    store, services = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    handoff_ref = launched_job(store, tmp_path, services, journal)
    registry = BindingRegistry([EPISODE()])
    continuation = {PATH: SETTINGS}
    first = asyncio.run(link(registry, PATH, entry(handoff_ref, ['answer.txt'], SELECTION),
                             run_id=RUN_ID,
                             journal=journal,
                             collaborators=collaborators(store, tmp_path, services, continuation)).run())
    result = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes(RUN_ID)
    path = episode['path']
    calls, units = journal.model_calls(RUN_ID, path), journal.units(RUN_ID, path)
    assert calls and units and len(list((tmp_path / 'model_calls').glob('call-*'))) == len(calls)
    print('DECISIONS', json.dumps([call['response'] for call in calls]))
    print('UNITS', json.dumps([(unit[2]['tool'], unit[2]['outcome']['status']) for unit in units]))
    print('RESULT', json.dumps(result))
    assert EPISODE.return_form.select(SELECTION).admit(result, 'return') == result
    assert result['credit'] == episode['completion']['credit'] == units[-1][1]['credit'] == 1.0
    assert result['finding'] == {'job_state': 'finished', 'fetch_outcome': 'results_acquired'}
    assert [store.get_artifact(ref) for ref in result['result_refs']] == [ANSWER]
    fetched = [unit[2]['outcome'] for unit in units if unit[2]['tool'] == 'fetch_results'
               and unit[2]['outcome']['status'] == 'completed']
    assert fetched and result['closure_refs'] == [fetched[0]['closure_ref']]
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, continuation)).run())
    assert resumed['result'].as_record() == result
    assert journal.model_calls(RUN_ID, path) == calls and journal.units(RUN_ID, path) == units
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    store.close()


@pytest.mark.model_run
def test_the_model_meets_a_job_that_is_still_running_and_the_run_ends_by_its_yield_controller(tmp_path):
    """The job sleeps twenty seconds before it writes its result and the caller does not wait for it: the model has
    ``wait`` among its actions. What it chooses is its own; the run ends by its yield controller either way (the
    controller is given a low cost, because a wait is long beside the other units), the return is admitted, and a
    resumed run replays the recorded units, a wait among them, without waiting or asking the model again."""
    store, services = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    handoff_ref = launched_job(store, tmp_path, services, journal, LONG)
    registry = BindingRegistry([EPISODE()])
    continuation = {PATH: {**SETTINGS, 'cost': 0.05}}
    first = asyncio.run(link(registry, PATH, entry(handoff_ref, ['answer.txt']), run_id='branch102_running',
                             journal=journal,
                             collaborators=collaborators(store, tmp_path, services, continuation)).run())
    result = first['result'].as_record()
    assert journal.run_state('branch102_running')[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes('branch102_running')
    calls, units = (journal.model_calls('branch102_running', episode['path']),
                    journal.units('branch102_running', episode['path']))
    print('DECISIONS', json.dumps([call['response'] for call in calls]))
    print('UNITS', json.dumps([(unit[2]['tool'], unit[2]['outcome']['status'], unit[1]['credit'])
                               for unit in units]))
    print('RESULT', json.dumps(result))
    assert calls and units and EPISODE.return_form.admit(result, 'return') == result
    assert result['credit'] == episode['completion']['credit'] == float(len(result['result_refs']))
    assert [store.get_artifact(ref) for ref in result['result_refs']] in ([], [ANSWER])
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id='branch102_running', journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, continuation)).run())
    assert resumed['result'].as_record() == result
    assert journal.units('branch102_running', episode['path']) == units
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    store.close()
