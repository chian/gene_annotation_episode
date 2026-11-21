"""Branch run of the result acquisition episode on a REAL local job, with the real model.

The caller's world is ``plain_world``: a real Store, the job services of ``job_services`` (a real detached local
job) and the launch of the job through the job probe test episode. The handoff row it writes is held in the Store;
the entry assignment passes it in custody with the job's directory, as the commissioner that holds the row builds
it. The acquisition then runs by the Episode's own decisions: the model selects each operation and code carries it
out. The job that has not ended is run offline in ``test_plain_results.py``.

Selected only with ``-m model_run``."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import resume

from .plain_world import (PACKAGE, PATH, RESULT_TEXT, collaborators, entry_input, finishing_job, launch_job, linked,
                          world)

RETURN_FORM = importlib.import_module(PACKAGE + '.messages.final_to_parent').RETURN_FORM


def acquire(directory, w, run_id, entry):
    registry, run = linked(w, run_id, entry)
    request = asyncio.run(run.next_decision())
    print('REQUEST', PATH, json.dumps({'instructions': request.instructions, 'context': request.context,
                                       'output_schema': request.output_schema}, sort_keys=True))
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
    print('MODEL_CALLS', asked, 'UNITS', len(units))
    assert asked >= len(units)
    again = asyncio.run(resume(registry, run_id=run_id, journal=w['journal'], collaborators=collaborators(w)).run())
    assert again['result'].as_record() == result
    assert len(list((directory / 'model_calls').glob('call-*'))) == asked
    return result, units


@pytest.mark.model_run
def test_the_model_fetches_the_result_of_a_finished_local_job(tmp_path):
    w = world(tmp_path)
    launch_run, handoff_ref = launch_job(w, finishing_job(), wait_for_end=True)
    result, units = acquire(tmp_path, w, 'local-fetch-finished', entry_input(w, launch_run, handoff_ref))
    collected, = [unit['outcome'] for unit in units if unit['tool'] == 'execution_results_collect']
    assert collected['status'] == 'completed'
    assert result['credit'] == 1.0 and result['execution_completed'] is True
    finding = result['finding']
    assert finding['execution_completed'] is True and finding['results_not_available'] == 0
    assert finding['job_state'] == 'finished'
    assert finding['windows_acquired'] >= 1 and finding['bytes_acquired'] >= len(RESULT_TEXT)
    assert result['execution_handoff_refs'] == [handoff_ref]
    # The result record is returned; selected with it, its information artifact and the fetched file.
    window, = json.loads(w['store'].get_artifact(collected['artifact_ref']))['windows']
    assert w['store'].get_artifact(window['artifact_ref']) == RESULT_TEXT.encode()
    assert collected['result_ref'] in result['execution_result_refs']
    assert {collected['artifact_ref'], window['artifact_ref']} <= set(result['execution_result_artifact_refs'])
