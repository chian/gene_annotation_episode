"""Branch run of hpc_resource_prediction alone with the real model (``-m model_run``). The world is ``hpc_world``
with the absent transport: there is no HPC here, the resource's route cannot be reached, and a tool that asks it
returns a failed unit. The episode creates the HPC ledger of its commission itself (no rows are passed), is ended by
its yield controller and returns the ledger rows in custody; resuming the closed run replays it without a model
call."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, link, resume

from . import hpc_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCResourcePrediction
PATH = EPISODE.binding_path
RUN_ID = 'a107_hpc_prediction_branch'


@pytest.mark.model_run
def test_the_prediction_episode_runs_on_its_own_with_the_real_model(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='absent')
    entry = {'assignment': {'owner_episode_id': 'episode_owner', 'commission_id': 'c1', 'scope': world['scope']},
             'message': {}, 'selection': []}
    run = link(BindingRegistry([EPISODE()]), PATH, entry, run_id=RUN_ID, journal=world['journal'],
               collaborators=world['collaborators'])
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    journal = world['journal']
    path = tuple(map(tuple, journal.episodes(RUN_ID)[0]['path']))
    units = journal.units(RUN_ID, path)
    calls = journal.model_calls(RUN_ID, path)
    decisions = [{'tool': unit[2]['tool'], 'status': unit[2]['outcome']['status'],
                  'arguments': {name: value for name, value in unit[2]['arguments'].items()
                                if name not in ('ledger', 'scope', 'owner_episode_id', 'commission_id',
                                                'commission_source_ref')},
                  'feedback': unit[2]['outcome'].get('feedback')} for unit in units]
    (tmp_path / 'model_decisions.json').write_text(json.dumps(
        {'decisions': decisions, 'result': result, 'model_calls': len(calls),
         'controller_steps': journal.controller_steps(RUN_ID, path)}, indent=1, sort_keys=True, default=str))
    assert journal.run_state(RUN_ID)[0] == 'closed' and journal.run_failure(RUN_ID) is None
    assert decisions[0]['tool'] == 'hpc_open' and len(calls) >= 1
    assert EPISODE.return_form.select(()).admit(result, 'return') is not None
    assert set(result) == {'credit', 'finding', 'hpc_ledger_refs'}
    assert len(result['hpc_ledger_refs']) >= 4 and all(ref.startswith('row_') for ref in result['hpc_ledger_refs'])
    # The closed run resumed: the recorded units are replayed, the result is rebuilt equal, no model is asked.
    again = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id=RUN_ID, journal=journal,
                               collaborators=world['collaborators']).run())
    assert again['result'].as_record() == result
    assert len(journal.model_calls(RUN_ID, path)) == len(calls) and len(journal.units(RUN_ID, path)) == len(units)
