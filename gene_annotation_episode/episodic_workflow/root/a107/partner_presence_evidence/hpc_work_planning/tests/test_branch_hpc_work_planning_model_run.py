"""Branch run of hpc_work_planning over its children with the real model (``-m model_run``): the head, the
prediction and allocation-execution sisters and the job children. The world is ``hpc_world`` with the absent
transport: there is no HPC here, the resource's route cannot be reached, and an action that asks it returns a
failed unit. The head opens the HPC ledger, commissions its sisters over it in custody, is ended by its yield
controller and returns the ledger rows; resuming the closed run replays every episode without a model call."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, link, resume

from ..hpc_resource_prediction.tests import hpc_world
from .test_hpc_work_planning_runs import EPISODE, PATH, episodes, paths

RUN_ID = 'a107_hpc_planning_branch'


def decisions_of(journal, path):
    return [{'action': unit[2].get('tool', unit[2].get('slot')),
             'status': unit[2]['outcome']['status'] if unit[2]['kind'] == 'tool' else 'completed',
             'arguments': {name: value for name, value in unit[2]['arguments'].items()
                           if name not in ('ledger', 'scope', 'owner_episode_id', 'commission_identity',
                                           'commission_id', 'commission_source_ref', 'tool_request')},
             'report': unit[2].get('report'),
             'feedback': unit[2]['outcome'].get('feedback') if unit[2]['kind'] == 'tool' else None}
            for unit in journal.units(RUN_ID, path)]


@pytest.mark.model_run
def test_the_planning_head_commissions_its_sisters_over_the_ledger(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='absent')
    entry = {'assignment': {'commission_id': 'c1', 'scope': world['scope']}, 'message': {}, 'selection': []}
    journal = world['journal']
    closed = asyncio.run(link(BindingRegistry(episodes()), PATH, entry, run_id=RUN_ID, journal=journal,
                              collaborators=world['collaborators']).run())
    result = closed['result'].as_record()
    recorded = journal.episodes(RUN_ID)
    by_episode = {'/'.join(part[1] for part in item['path']): {
        'binding_path': item['binding_path'], 'completion': item['completion'],
        'model_calls': len(journal.model_calls(RUN_ID, tuple(map(tuple, item['path'])))),
        'decisions': decisions_of(journal, tuple(map(tuple, item['path'])))} for item in recorded}
    (tmp_path / 'model_decisions.json').write_text(json.dumps({'episodes': by_episode, 'result': result}, indent=1,
                                                             sort_keys=True))
    calls = {name: item['model_calls'] for name, item in by_episode.items()}
    units = {name: len(item['decisions']) for name, item in by_episode.items()}
    assert journal.run_state(RUN_ID)[0] == 'closed' and journal.run_failure(RUN_ID) is None
    head = by_episode[RUN_ID]
    assert head['decisions'][0]['action'] == 'hpc_open' and head['model_calls'] >= 1
    assert EPISODE.return_form.select(()).admit(result, 'return') is not None
    assert set(result) == {'credit', 'finding', 'hpc_ledger_refs'}
    assert all(item['completion']['ended_by'] == 'yield_stop' for item in by_episode.values())
    # The closed run resumed: every recorded unit is replayed, the result is rebuilt equal, no model is asked.
    again = asyncio.run(resume(BindingRegistry(episodes()), run_id=RUN_ID, journal=journal,
                               collaborators=world['collaborators']).run())
    assert again['result'].as_record() == result
    after = journal.episodes(RUN_ID)
    assert {'/'.join(part[1] for part in item['path']): len(journal.model_calls(RUN_ID, tuple(map(tuple, item['path']))))
            for item in after} == calls
    assert {'/'.join(part[1] for part in item['path']): len(journal.units(RUN_ID, tuple(map(tuple, item['path']))))
            for item in after} == units
