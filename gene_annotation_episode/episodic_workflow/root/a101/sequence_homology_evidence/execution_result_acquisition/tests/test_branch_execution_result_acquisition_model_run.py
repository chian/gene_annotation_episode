"""Branch run of the result acquisition episode on a REAL local job (the plain fetch of a local file result).

The caller's world is ``plain_world``: a real Store, the job services of ``job_services`` (a real detached local
job), and the launch of the job through the job probe test episode. The handoff row it writes is held in the
Store; the entry assignment passes it, with the execution target the commissioner builds from the row, as the
launching child's return would. The acquisition then runs with the real model. Two worlds: a finished job, and a
job that has not finished.

Selected only with ``-m model_run``."""
import asyncio
import json

import pytest

from episode_runtime import resume

from ..messages.final_to_parent import RETURN_FORM
from .plain_world import (PATH, RESULT_TEXT, collaborators, entry_input, finishing_job, launch_job, linked,
                          waiting_job, world)


def acquire(directory, w, run_id, entry):
    registry, run = linked(w, run_id, entry)
    closed = asyncio.run(run.run())
    path = ((PATH.replace('/', '__'), run_id),)
    result = closed['result'].as_record()
    units = [unit[2] for unit in w['journal'].units(run_id, path)]
    for unit in units:
        print('UNIT', unit['tool'], unit['outcome'].get('status'), unit['outcome'].get('state'),
              unit['outcome'].get('failure'), unit['outcome'].get('feedback'))
    print('ENDED_BY', w['journal'].run_state(run_id)[1]['ended_by'], 'RESULT', result)
    assert w['journal'].run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert RETURN_FORM.select(entry['selection']).admit(result, 'return') == result
    asked = len(list((directory / 'model_calls').glob('call-*')))
    assert asked >= len(units)
    again = asyncio.run(resume(registry, run_id=run_id, journal=w['journal'], collaborators=collaborators(w)).run())
    assert again['result'].as_record() == result
    assert len(list((directory / 'model_calls').glob('call-*'))) == asked
    return result, units


@pytest.mark.model_run
def test_the_model_fetches_the_result_of_a_finished_local_job(tmp_path):
    w = world(tmp_path)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    result, units = acquire(tmp_path, w, 'a101-local-fetch-finished', entry_input(w, launch_run, handoff_ref))
    collected, = [unit['outcome'] for unit in units if unit['tool'] == 'execution_results_collect']
    assert collected['status'] == 'completed'
    assert result['credit'] == 1.0 and result['execution_completed'] is True
    finding = result['finding']
    assert finding['execution_completed'] is True and finding['results_not_available'] == 0
    assert finding['windows_acquired'] >= 1 and finding['bytes_acquired'] >= len(RESULT_TEXT)
    assert result['execution_handoff_refs'] == [handoff_ref]
    # The fetched file is among the returned records, with the result record and its information artifact.
    window, = json.loads(w['store'].get_artifact(collected['artifact_ref']))['windows']
    assert w['store'].get_artifact(window['artifact_ref']) == RESULT_TEXT.encode()
    assert {collected['result_ref'], collected['artifact_ref'], window['artifact_ref']} <= set(
        result['execution_result_refs'])


@pytest.mark.model_run
def test_the_model_meets_a_job_that_has_not_finished(tmp_path):
    w = world(tmp_path)
    release = tmp_path / 'release'
    launch_run, handoff_ref = launch_job(w, waiting_job(release), wait_for_end=False)
    try:
        result, units = acquire(tmp_path, w, 'a101-local-fetch-unfinished',
                                entry_input(w, launch_run, handoff_ref))
    finally:
        release.touch()
    assert result['credit'] == 0.0 and result['execution_completed'] is False
    assert result['execution_result_refs'] == [] and result['finding']['bytes_acquired'] == 0
    refused = [unit for unit in units if unit['tool'] == 'execution_results_collect']
    assert all(unit['outcome']['failure']['code'] == 'results_not_available' for unit in refused)
    assert result['finding']['results_not_available'] == len(refused)
    # What the parent learns: the job was last seen running (a status request ran) or was refused unobserved.
    checked = any(unit['tool'] == 'execution_results_status' for unit in units)
    assert result['finding']['job_state'] == ('running' if checked else 'not_observed')
    assert checked or refused
