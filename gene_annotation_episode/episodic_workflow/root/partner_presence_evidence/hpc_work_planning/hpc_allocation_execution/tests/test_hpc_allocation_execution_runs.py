"""hpc_allocation_execution through the real runner without a model: the caller steps the Episode with
``next_decision`` and ``run_unit``. The world is the prediction sister's ``hpc_world``; the ledger the allocation
works on is created the way real runs create it, by the prediction episode's own ``hpc_open`` tool unit, and its id
and rows are passed in the entry assignment. The first test saves the model request it saw as
``model_request.json`` in its temporary directory (under the run directory)."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, ToolCall, link, resume
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HpcLedger

from ...hpc_resource_prediction.tests import hpc_world

PACKAGE = __name__.rsplit('.', 2)[0]
SUBTREE = (('', 'HPCAllocationExecution'), ('execution_job_submission', 'ExecutionJobSubmission'),
           ('execution_job_submission.hpc_job_execution', 'HpcJobExecution'),
           ('execution_job_submission.api_job_execution', 'ApiJobExecution'),
           ('execution_job_submission.local_job_execution', 'LocalJobExecution'),
           ('execution_progress_assessment', 'ExecutionProgressAssessment'),
           ('execution_result_acquisition', 'ExecutionResultAcquisition'))
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCAllocationExecution
TASK = importlib.import_module(PACKAGE + '.task')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PREDICTION = importlib.import_module(PACKAGE.rsplit('.', 1)[0] + '.hpc_resource_prediction.episode').HPCResourcePrediction
PATH = EPISODE.binding_path


def episodes():
    return [getattr(importlib.import_module(PACKAGE + ('.' + module if module else '') + '.episode'), name)()
            for module, name in SUBTREE]


def paths():
    return [PREDICTION.binding_path, *(PATH + ('/' + module.replace('.', '/') if module else '')
                                       for module, _ in SUBTREE)]


def linked(world, run_id='allocation_steps'):
    ledger, rows = hpc_world.ledger_of_the_prediction_sister(world, PREDICTION)
    entry = {'assignment': {'owner_episode_id': 'episode_owner', 'ledger': ledger, 'ledger_row_refs': rows,
                            'commission_id': 'c1', 'scope': world['scope']}, 'message': {}, 'selection': []}
    return link(BindingRegistry(episodes()), PATH, entry, run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators']), ledger, rows


def step(run, name, **arguments):
    """One tool unit with the arguments the episode's ``action`` gives it (``owner_arguments``)."""
    summary = EPISODE.internal_summary(run.view)
    return asyncio.run(run.run_unit(ToolCall(name, TASK.owner_arguments(summary, arguments))))['outcome']


def test_the_first_unit_reads_the_commission_from_the_passed_ledger_and_the_model_is_then_asked(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='local_shell')
    run, ledger, rows = linked(world)
    first = asyncio.run(run.next_decision())
    assert isinstance(first, ToolCall) and first.name == 'hpc_read' and first.arguments['ledger'] == ledger
    read = asyncio.run(run.run_unit(first))
    assert read['outcome']['result']['objective'] == hpc_world.commission()['objective'] and read['produced'] == []
    # The rows are held because the entry assignment named them: they are the prediction sister's.
    assert {run.view.records.receipt(ref)['how'] for ref in rows} == {'entry'}
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and request.instructions == TASK.INSTRUCTIONS
    (tmp_path / 'model_request.json').write_text(json.dumps(
        {'role': request.role, 'instructions': request.instructions, 'context': request.context,
         'output_schema': request.output_schema}, indent=1, sort_keys=True))
    assert set(request.context) == {'commission', 'resource', 'ledger', 'launches', 'monitors', 'acquisitions',
                                    'credit', 'units_so_far', 'last_outcome', 'feedback', 'actions'}
    assert request.context['units_so_far'] == [] and request.context['last_outcome'] is None
    assert request.context['ledger']['current_model_ref'] == 'reference_model'
    assert [item['id'] for item in request.context['ledger']['candidates']] == ['one_node', 'two_nodes']
    assert [item['selection'] for item in request.context['actions']][:3] == ['hpc_queue_observe', 'hpc_compare',
                                                                             'hpc_plan']
    assert 'hpc_history_refresh' not in request.output_schema['properties']['selection']['enum']


def test_planning_reaches_the_resource_only_through_job_access_and_refuses_what_the_ledger_cannot_support(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='local_shell', cost=0.0)
    run, ledger, rows = linked(world)
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    # No scheduler is installed here: the queue command fails on the route and the unit returns that.
    observed = step(run, 'hpc_queue_observe')
    assert observed['status'] == 'failed' and observed['feedback']['code'] == 'queue_observation_failed'
    # Without a queue observation nothing can be compared or frozen: the refusals are units, not errors.
    compared = step(run, 'hpc_compare', model_ref='reference_model', queue_ref='queue:none')
    assert compared['status'] == 'invalid' and compared['feedback']['code'] == 'unknown_hpc_evidence:queue:none'
    planned = step(run, 'hpc_plan', candidate_id='two_nodes', model_ref='reference_model', queue_ref='queue:none')
    assert planned['status'] == 'invalid' and planned['feedback']['code'] == 'unknown_hpc_evidence:queue:none'
    unknown = step(run, 'hpc_plan', candidate_id='ten_nodes', model_ref='reference_model', queue_ref='queue:none')
    assert unknown['feedback']['code'] == 'unknown_candidate:ten_nodes'
    assert planned['ledger_view']['plans'] == []
    discovered = step(run, 'hpc_discovery_run', command='echo reached')
    assert discovered['status'] == 'completed' and discovered['result']['returncode'] != 0
    proposed = step(run, 'hpc_candidate_propose', candidate_json=json.dumps(hpc_world.candidate('four_nodes', 4, 900)))
    assert proposed['result']['candidate_ref'] == 'candidate:four_nodes'
    summary = EPISODE.internal_summary(run.view)
    assert [unit['action'] for unit in summary['units_so_far']] == [
        'hpc_queue_observe', 'hpc_compare', 'hpc_plan', 'hpc_plan', 'hpc_discovery_run', 'hpc_candidate_propose']
    assert summary['last_outcome']['action'] == 'hpc_candidate_propose' and 'ledger_view' not in summary['last_outcome']
    assert [item['id'] for item in summary['ledger_state']['candidates']] == ['one_node', 'two_nodes', 'four_nodes']
    assert EPISODE.credit(summary, run.view.records) == 0.0
    # This Episode's own rows (the discovery and the candidate) are in the ledger beside the rows it was passed.
    held = HpcLedger.existing(run.view.records, ledger)
    assert len(held.records('discovery')) == 1 and len(held.records('candidate')) == 1
    assert set(rows) < set(summary['ledger_view']['ledger_refs'])


def test_the_controller_ends_the_episode_the_return_is_controlled_and_resume_replays_it(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='absent')
    run, ledger, rows = linked(world, 'allocation_closed')
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    refused = step(run, 'hpc_queue_observe')
    assert refused['status'] == 'failed' and refused['feedback']['code'] == 'transport_unavailable'
    while not run.view.controller_state.stop:                     # units that earn nothing: the controller stops
        step(run, 'hpc_read', reference='commission')
    result = asyncio.run(run.run())['result'].as_record()
    assert result == {'credit': 0.0, 'hpc_ledger_refs': rows,
                      'finding': {'accepted_obligations': 0, 'remaining_obligations': 1, 'plans_frozen': 0,
                                  'plans_handed_off': 0, 'plans_closed': 0, 'results_published': 0}}
    FINAL.RETURN_FORM.select(()).admit(result, 'return')
    units = len(world['journal'].units('allocation_closed', run.view.path))
    replayed = asyncio.run(resume(BindingRegistry(episodes()), run_id='allocation_closed', journal=world['journal'],
                                  collaborators=world['collaborators']).run())
    assert replayed['result'].as_record() == result
    assert len(world['journal'].units('allocation_closed', run.view.path)) == units
