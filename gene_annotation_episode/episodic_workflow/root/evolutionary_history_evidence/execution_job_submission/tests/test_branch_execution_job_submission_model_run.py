"""Branch run: the A104 job submission episode over its local launch child, with the real model (``-m model_run``).

The submission is linked as the entry of a run with the public API, a real Store, RunJournal, the real
ModelProvider and the services ``job_services`` builds (the real detached local route). Its model chooses the
resource to commission; the launch child's model chooses the launch; code launches the job. The submission receives
the child's controlled return and returns the handoff record in custody."""
import asyncio
import json

import pytest

from episode_runtime import RunJournal, link, resume

from ..local_job_execution.episode import LocalJobExecution
from .submission_world import (CHILD_HANDOFF_CREDIT, HANDOFF_UNIT, PATH, RESOURCE_ID, collaborators, dump, entry,
                               job_ended, registry, world)

RUN = 'a104-submission-model'


def requests(directory):
    return [json.loads((call / 'request.json').read_text()) for call in sorted(directory.glob('call-*'))]


@pytest.mark.model_run
def test_the_submission_commissions_the_local_launch_and_receives_the_handoff_in_a_controlled_return(tmp_path):
    held = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = link(registry(), PATH, entry(held), run_id=RUN, journal=journal,
               collaborators=collaborators(held, 'model_calls'))
    try:
        closed = asyncio.run(run.run())
    finally:
        dump(journal, RUN)
        for request in requests(tmp_path / 'model_calls'):
            print('REQUEST', json.dumps({name: request[name] for name in ('instructions', 'context',
                                                                           'output_schema')}, indent=1))
    result = closed['result'].as_record()
    print('RESULT', json.dumps(result, default=str))
    episodes = {episode['binding_path']: tuple(tuple(item) for item in episode['path'])
                for episode in journal.episodes(RUN)}
    assert set(episodes) == {PATH, LocalJobExecution.binding_path}
    parent, child = episodes[PATH], episodes[LocalJobExecution.binding_path]
    # The submission's model ended on the commission (any answer before it is a library lookup); the launch
    # child's model chose the launch.
    answers = [call['response']['action'] for call in journal.model_calls(RUN, parent)]
    print('PARENT ANSWERS', json.dumps(answers))
    assert answers[-1] == {'name': 'commission_launch', 'resource_id': RESOURCE_ID}
    assert all(answer['name'] in ('knowledge_lookup', 'launch_instruction_lookup') for answer in answers[:-1])
    assert [call['response'] for call in journal.model_calls(RUN, child)] == [
        {'action': {'name': 'launch_job', 'resource_id': RESOURCE_ID}}]
    (_, _, launched, _), = journal.units(RUN, child)
    outcome = launched['outcome']
    assert launched['tool'] == 'launch_job' and outcome['status'] == 'completed'
    # The parent received the child's controlled return: credit, counts, the flag and the handoff record reference.
    looked, *lookups, commissioned = [unit[2] for unit in journal.units(RUN, parent)]
    assert looked['tool'] == 'execution_capabilities' and commissioned['slot'] == 'launch_local'
    assert len(lookups) == len(answers) - 1
    assert commissioned['result'] == {
        'credit': CHILD_HANDOFF_CREDIT, 'finding': {'launches_handed_off': 1, 'launches_failed': 0, 'holds': 0},
        'execution_handoff_refs': [outcome['handoff_ref']], 'execution_completed': True}
    assert commissioned['completion'] == {'ended_by': 'yield_stop', 'units_consumed': 1}   # ended at handoff
    sent = dict(commissioned['message']['assignment'])
    sent.pop('launch_instructions', None)                    # the pins of sections a lookup read, when any
    assert sent == held['assignment']['requests'][RESOURCE_ID]
    # The handoff row travelled in custody: produced by the child, returned to the parent.
    assert {item['ref']: item['how'] for item in journal.receipts(RUN, child)}[outcome['handoff_ref']] == 'produced'
    assert {item['ref']: item['how'] for item in journal.receipts(RUN, parent)}[outcome['handoff_ref']] == 'returned'
    # The submission earned its handoff unit, ended by its yield controller and returned the handoff record.
    assert journal.run_state(RUN)[1]['ended_by'] == 'yield_stop'
    assert result['credit'] == HANDOFF_UNIT and result['execution_completed'] is True
    assert result['execution_handoff_refs'] == [outcome['handoff_ref']]
    assert result['finding'] == {
        'handoff_established': True, 'handoff_resources': [RESOURCE_ID], 'new_handoff_count': 1, 'launches_run': 1,
        'launches': [{'slot': 'launch_local', 'resource_id': RESOURCE_ID, 'completed': True,
                      'handoff_refs': [outcome['handoff_ref']]}]}
    # A real detached local job was started: it does its work after both Episodes have ended.
    assert (job_ended(held, outcome['job']) / 'answer.txt').read_text() == '42'
    # Resume replays the run with no new model call and no second job.
    asked = len(requests(tmp_path / 'model_calls'))
    resumed = asyncio.run(resume(registry(), run_id=RUN, journal=journal,
                                 collaborators=collaborators(held, 'model_calls_resumed')).run())
    assert resumed['result'].as_record() == result and asked == len(answers) + 1
    assert len(requests(tmp_path / 'model_calls')) == asked and not requests(tmp_path / 'model_calls_resumed')
    assert [item.name for item in (tmp_path / 'jobs').iterdir()] == [outcome['job']]
    held['store'].close()
