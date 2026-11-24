"""Branch run: the A107 local job execution episode with the real model (``-m model_run``).

The episode is linked as the entry of a run with the public API, a real Store, RunJournal, the real ModelProvider
and the services ``job_services`` builds (the real detached local route). The world holds a small valid
``practical_assignment`` for the local resource: a job that writes ``answer.txt``, and a handoff requirement
with a credit of 4. The model is asked for one defined action; code launches the job."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from ..episode import LocalJobExecution
from .launch_world import HANDOFF_CREDIT, PATH, RESOURCE_ID, collaborators, dump, entry, job_ended, world

RUN = 'a107-local-model'


@pytest.mark.model_run
def test_the_model_launches_the_local_job_and_resume_replays_it(tmp_path):
    held = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry([LocalJobExecution()])
    run = link(registry, PATH, entry(held), run_id=RUN, journal=journal,
               collaborators=collaborators(held, 'model_calls'))
    try:
        closed = asyncio.run(run.run())
    finally:
        dump(journal, RUN)
    result = closed['result'].as_record()
    print('RESULT', json.dumps(result, default=str))
    request = json.loads((tmp_path / 'model_calls' / 'call-00001' / 'request.json').read_text())
    print('REQUEST', json.dumps({name: request[name] for name in ('instructions', 'context', 'output_schema')},
                                indent=1))
    # The model chose the launch; the Episode ended at handoff, by its yield controller, after that one unit.
    path = tuple(tuple(item) for item in journal.episodes(RUN)[0]['path'])
    decisions = [call['response'] for call in journal.model_calls(RUN, path)]
    assert decisions == [{'action': {'name': 'launch_job', 'resource_id': RESOURCE_ID}}]
    (label, _, unit, _), = journal.units(RUN, path)
    outcome = unit['outcome']
    assert unit['tool'] == 'launch_job' and outcome['status'] == 'completed'
    assert journal.run_state(RUN)[1]['ended_by'] == 'yield_stop'
    # The handoff row was written and is returned as a record reference in a controlled return, admitted by the
    # episode's return form; the handoff earned the credit of the assignment's requirement.
    assert result == {'credit': HANDOFF_CREDIT,
                      'finding': {'launches_handed_off': 1, 'launches_failed': 0, 'holds': 0},
                      'execution_handoff_refs': [outcome['handoff_ref']], 'execution_completed': True}
    held_how = {item['ref']: item['how'] for item in journal.receipts(RUN, path)}
    assert outcome['handoff_ref'].startswith('row_') and held_how[outcome['handoff_ref']] == 'produced'
    assert outcome['kind'] == 'local' and outcome['resource_id'] == RESOURCE_ID
    # A real detached local job was started: it does its work after the Episode has ended.
    directory = job_ended(held, outcome['job'])
    assert (directory / 'answer.txt').read_text() == '42'
    # Resume replays the run with no new model call and no second job.
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume(registry, run_id=RUN, journal=journal,
                                 collaborators=collaborators(held, 'model_calls_resumed')).run())
    assert resumed['result'].as_record() == result and asked == 1
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    assert [item.name for item in (tmp_path / 'jobs').iterdir()] == [outcome['job']]
    held['store'].close()
