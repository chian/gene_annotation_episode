"""A real run of the resource work submission episode over its local resource child, with the real model.

The world (``submission_world``) is a Store that holds the work as a record (a small real computation: a Python
program that reads its staged input and writes the sum of the squares of 1..100 to ``result.txt``) and two declared
resources: a bound local one and an HPC one that is not bound. The parent episode's model chooses the resource and
commissions the launch; the child's model routes the launch and its receiving check. ``link(...).run()`` runs the
subtree with the standard ``ModelProvider``; every decision is a model's choice among defined actions, and code
runs them. No model writes a command. The launched job is real (a detached systemd service): a later run fetches
its result through the handoff row the parent returns. Selected only with ``-m model_run``; it needs the owner's
Codex sign-in."""
import asyncio
import json

import pytest

from episode_runtime import RunJournal, link, resume

from .submission_world import (ANSWER, EPISODE, LOCAL, PATH, SETTINGS, collaborators, entry, later_fetch, registry,
                               world)

RUN_ID = 'branch102_submission'
SELECTION = ('check_refs',)


@pytest.mark.model_run
def test_the_model_commissions_the_local_child_to_launch_the_work_and_the_run_ends_by_its_yield_controller(tmp_path):
    store, services, records = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    first = asyncio.run(link(registry(), PATH, entry(records, selection=SELECTION), run_id=RUN_ID,
                             journal=journal,
                             collaborators=collaborators(store, tmp_path, services, SETTINGS)).run())
    result = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    episodes = journal.episodes(RUN_ID)
    recorded = {}
    for episode in episodes:
        calls, units = journal.model_calls(RUN_ID, episode['path']), journal.units(RUN_ID, episode['path'])
        recorded[episode['binding_path']] = (calls, units)
        print('EPISODE', episode['binding_path'], 'DECISIONS', json.dumps([call['response'] for call in calls]),
              'UNITS', json.dumps([(unit[2].get('tool') or unit[2].get('slot'), unit[1]['credit'])
                                   for unit in units]))
    print('RESULT', json.dumps(result))
    assert set(recorded) == {PATH, LOCAL.binding_path} and all(calls and units for calls, units in recorded.values())
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == sum(len(calls) for calls, _ in recorded.values())
    assert EPISODE.return_form.select(SELECTION).admit(result, 'return') == result
    assert result['credit'] == 7.0 and result['finding']['route_kind'] == 'local'
    assert result['finding']['job_state'] in ('queued', 'running', 'finished')
    assert len(result['handoff_refs']) == 1 and result['check_refs']
    assert [unit[2]['slot'] for unit in recorded[PATH][1] if unit[2]['kind'] == 'child'] == ['launch_local']
    assert later_fetch(store, tmp_path, services, journal, result['handoff_refs'][0], 'result.txt') == ANSWER
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry(), run_id=RUN_ID, journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, SETTINGS)).run())
    assert resumed['result'].as_record() == result
    for episode in episodes:
        assert (journal.model_calls(RUN_ID, episode['path']),
                journal.units(RUN_ID, episode['path'])) == recorded[episode['binding_path']]
    assert not list((tmp_path / 'resume' / 'model_calls').glob('call-*'))
    assert len(list((tmp_path / 'jobs').iterdir())) == 1
    store.close()
