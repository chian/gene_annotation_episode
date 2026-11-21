"""hpc_resource_prediction through the real runner without a model: the caller steps the Episode with
``next_decision`` and ``run_unit`` (``BINDING_CONTRACT.md``, "Stepping a run"). The world is ``hpc_world`` with the
local-shell transport: the tests choose every command themselves. Each test saves the model request it saw as
``model_request.json`` in its temporary directory (under the run directory)."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, ToolCall, link, resume
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HPC_LEDGER, HpcLedger, ledger_id

from . import hpc_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCResourcePrediction
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path


def entry(world, **assignment):
    return {'assignment': {'owner_episode_id': 'episode_owner', 'commission_id': 'c1', 'scope': world['scope'],
                           **assignment}, 'message': {}, 'selection': []}


def linked(world, run_id='prediction_steps'):
    return link(BindingRegistry([EPISODE()]), PATH, entry(world), run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators'])


def step(run, name, **arguments):
    """One tool unit with the arguments the episode's ``action`` gives it: the model's, the ledger id and the scope."""
    summary = EPISODE.internal_summary(run.view)
    call = ToolCall(name, {**arguments, 'ledger': summary['ledger']['ledger_id'], 'scope': summary['scope']})
    return asyncio.run(run.run_unit(call))['outcome']


def test_the_first_unit_opens_the_ledger_and_the_model_is_then_asked_with_the_ledger_in_view(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='local_shell')
    run = linked(world)
    first = asyncio.run(run.next_decision())
    assert isinstance(first, ToolCall) and first.name == 'hpc_open'
    opened = asyncio.run(run.run_unit(first))
    view = opened['outcome']['ledger']
    assert view['ledger_id'] == ledger_id(hpc_world.commission())
    # The Episode created the ledger: its rows are work-table rows it produced and holds.
    rows = run.view.records.table(HPC_LEDGER).select({'ledger': view['ledger_id']})
    assert [row['identity'] for row in rows] == ['commission', 'owner', 'reference_model', 'entry:' + rows[0]['episode_id']]
    assert view['ledger_refs'] == [row['id'] for row in rows] and set(view['ledger_refs']) <= set(opened['produced'])
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    (tmp_path / 'model_request.json').write_text(json.dumps(
        {'role': request.role, 'instructions': request.instructions, 'context': request.context,
         'output_schema': request.output_schema}, indent=1, sort_keys=True))
    assert EPISODE.credit(EPISODE.internal_summary(run.view), run.view.records) == 0.0


def test_fitting_the_measured_cases_earns_the_measured_improvement_and_a_bad_selection_is_an_invalid_unit(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='local_shell')
    run = linked(world)
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    refused = step(run, 'hpc_model_fit', training_ids=['case_1', 'case_7'])        # a validation case
    assert refused['status'] == 'invalid'
    assert refused['feedback']['code'] == 'training_ids_must_be_original_nonvalidation_cases'
    fitted = step(run, 'hpc_model_fit', training_ids=['case_' + str(index) for index in range(1, 7)])
    assert fitted['status'] == 'completed'
    result = fitted['result']
    assert result['validation_quality'] > result['reference_quality']
    summary = EPISODE.internal_summary(run.view)
    credit = EPISODE.credit(summary, run.view.records)
    assert credit == pytest.approx(0.1 * (result['validation_quality'] - result['reference_quality'])) and credit > 0
    state = summary['ledger_state']
    assert state['current_model_ref'] == result['model_ref'] and result['model_ref'] in state['model_refs']
    assert state['current_model_support']['observations'] == 6
    assert [unit['tool'] for unit in summary['units_so_far']] == ['hpc_model_fit', 'hpc_model_fit']
    assert summary['last_outcome']['tool'] == 'hpc_model_fit' and 'ledger' not in summary['last_outcome']
    # The ledger's own credit view holds the same model credit, derived from the held evidence.
    ledger = HpcLedger.existing(run.view.records, summary['ledger']['ledger_id'])
    assert ledger.credit_view()['components']['model'] == pytest.approx(credit)
    read = step(run, 'hpc_read', reference=result['model_ref'])
    assert read['status'] == 'completed' and read['result']['training_ids'] == sorted(
        'case_' + str(index) for index in range(1, 7))
    assert step(run, 'hpc_read', reference='no_such_record')['feedback']['code'] == 'unknown_hpc_evidence:no_such_record'


def test_the_resource_is_reached_only_through_job_access_and_what_it_cannot_answer_is_a_returned_outcome(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='local_shell')
    run = linked(world)
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    # The command runs once on the route (a local shell here); the project directory does not exist on this machine.
    discovered = step(run, 'hpc_discovery_run', command='echo reached')
    assert discovered['status'] == 'completed' and discovered['result']['returncode'] != 0
    assert discovered['result']['stdout'] == '' and 'BioReason-Aurora-Test' in discovered['result']['stderr']
    ledger = HpcLedger.existing(run.view.records, discovered['ledger']['ledger_id'])
    assert [row['body']['command'] for row in ledger.records('discovery')] == ['echo reached']
    assert [build['name'] for build in world['journal'].service_builds('prediction_steps')] == ['job_access']
    # No scheduler is installed here: the queue command fails and the unit returns that.
    observed = step(run, 'hpc_queue_observe')
    assert observed['status'] == 'failed' and observed['feedback']['code'] == 'queue_observation_failed'
    assert observed['ledger']['queue_refs'] == []
    compared = step(run, 'hpc_compare', model_ref='reference_model', queue_ref='queue:none')
    assert compared['status'] == 'invalid' and compared['feedback']['code'] == 'unknown_hpc_evidence:queue:none'
    proposed = step(run, 'hpc_candidate_propose', candidate_json=json.dumps(
        {**hpc_world.candidate('four_nodes', 4, 1800)}))
    assert proposed['result'] == {'candidate_ref': 'candidate:four_nodes', 'candidate_id': 'four_nodes'}
    assert [row['id'] for row in proposed['ledger']['candidates']] == ['one_node', 'two_nodes', 'four_nodes']
    again = step(run, 'hpc_candidate_propose', candidate_json=json.dumps(hpc_world.candidate('four_nodes', 8, 1800)))
    assert again['status'] == 'invalid' and again['feedback']['code'] == 'candidate_identity_is_immutable'


def test_a_transport_that_does_not_exist_is_a_failed_unit_and_nothing_is_contacted(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='absent', cost=0.0)
    run = linked(world)
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    for name, arguments in (('hpc_discovery_run', {'command': 'qstat -Q'}), ('hpc_queue_observe', {})):
        outcome = step(run, name, **arguments)
        assert outcome['status'] == 'failed' and outcome['feedback']['code'] == 'transport_unavailable'
        assert outcome['feedback']['category'] == 'resource_request'
    assert EPISODE.internal_summary(run.view)['last_outcome']['feedback']['code'] == 'transport_unavailable'


def test_the_controller_ends_the_episode_the_return_is_controlled_and_resume_replays_it(tmp_path):
    world = hpc_world.world(tmp_path, [PATH], transport='absent')
    run = linked(world, 'prediction_closed')
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    step(run, 'hpc_model_fit', training_ids=['case_' + str(index) for index in range(1, 7)])
    while not run.view.controller_state.stop:                     # units that earn nothing: the controller stops
        step(run, 'hpc_read', reference='commission')
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    assert set(result) == {'credit', 'finding', 'hpc_ledger_refs'} and result['credit'] > 0
    assert result['finding'] == {'model_fitted': True, 'training_cases_used': 6, 'candidates': 2, 'comparisons': 0,
                                 'queue_observations': 0}
    FINAL.RETURN_FORM.select(()).admit(result, 'return')
    assert len(result['hpc_ledger_refs']) >= 7 and all(ref.startswith('row_') for ref in result['hpc_ledger_refs'])
    units = len(world['journal'].units('prediction_closed', run.view.path))
    replayed = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id='prediction_closed', journal=world['journal'],
                                  collaborators=world['collaborators']).run())
    assert replayed['result'].as_record() == result
    assert len(world['journal'].units('prediction_closed', run.view.path)) == units
    # The ledger travels in custody: an Episode that is passed the rows finds the fitted model under its commission.
    passed = link(BindingRegistry([EPISODE()]), PATH, entry(world, ledger_row_refs=result['hpc_ledger_refs']),
                  run_id='prediction_again', journal=world['journal'], collaborators=world['collaborators'])
    opened = asyncio.run(passed.run_unit(asyncio.run(passed.next_decision())))
    assert len(opened['produced']) == 1                              # only its own entry record
    view = opened['outcome']['ledger']
    assert view['current_model_ref'] != 'reference_model' and view['model_entry']['model_ref'] == view['current_model_ref']
    assert set(result['hpc_ledger_refs']) < set(view['ledger_refs'])
