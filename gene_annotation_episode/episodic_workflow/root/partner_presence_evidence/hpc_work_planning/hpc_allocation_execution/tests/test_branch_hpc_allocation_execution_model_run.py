"""Branch run of hpc_allocation_execution alone with the real model (``-m model_run``). The ledger the episode
works on is created the way real runs create it: the prediction sister's own ``hpc_open`` tool, run as a unit of a
run of that episode in the same world, and the allocation's entry assignment names the ledger id and its rows (the
caller writes no ledger row). The world is ``hpc_world`` with the absent transport: there is no HPC here, the
resource's route cannot be reached, and an action that asks it returns a failed unit. The episode is ended by its
yield controller and returns the ledger rows in custody; resuming the closed run replays it without a model call."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, link, resume

from ...hpc_resource_prediction.tests import hpc_world
from .test_hpc_allocation_execution_runs import EPISODE, PATH, PREDICTION, episodes, paths

RUN_ID = 'a107_hpc_allocation_branch'


@pytest.mark.model_run
def test_the_allocation_episode_runs_on_the_ledger_the_prediction_sister_opened(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='absent')
    ledger, rows = hpc_world.ledger_of_the_prediction_sister(world, PREDICTION)
    entry = {'assignment': {'owner_episode_id': 'episode_owner', 'ledger': ledger, 'ledger_row_refs': rows,
                            'commission_id': 'c1', 'scope': world['scope']}, 'message': {}, 'selection': []}
    journal = world['journal']
    closed = asyncio.run(link(BindingRegistry(episodes()), PATH, entry, run_id=RUN_ID, journal=journal,
                              collaborators=world['collaborators']).run())
    result = closed['result'].as_record()
    path = tuple(map(tuple, journal.episodes(RUN_ID)[0]['path']))
    units, calls = journal.units(RUN_ID, path), journal.model_calls(RUN_ID, path)
    decisions = [{'action': unit[2].get('tool', unit[2].get('slot')),
                  'status': unit[2]['outcome']['status'] if unit[2]['kind'] == 'tool' else 'completed',
                  'arguments': {name: value for name, value in unit[2]['arguments'].items()
                                if name not in ('ledger', 'scope', 'owner_episode_id', 'commission_identity')},
                  'feedback': unit[2]['outcome'].get('feedback') if unit[2]['kind'] == 'tool' else None}
                 for unit in units]
    (tmp_path / 'model_decisions.json').write_text(json.dumps(
        {'decisions': decisions, 'result': result, 'model_calls': len(calls)}, indent=1, sort_keys=True))
    assert journal.run_state(RUN_ID)[0] == 'closed' and journal.run_failure(RUN_ID) is None
    assert decisions[0]['action'] == 'hpc_read' and len(calls) >= 1
    assert EPISODE.return_form.select(()).admit(result, 'return') is not None
    assert set(result) == {'credit', 'finding', 'hpc_ledger_refs'} and set(rows) <= set(result['hpc_ledger_refs'])
    # The closed run resumed: the recorded units are replayed, the result is rebuilt equal, no model is asked.
    again = asyncio.run(resume(BindingRegistry(episodes()), run_id=RUN_ID, journal=journal,
                               collaborators=world['collaborators']).run())
    assert again['result'].as_record() == result
    assert len(journal.model_calls(RUN_ID, path)) == len(calls) and len(journal.units(RUN_ID, path)) == len(units)
