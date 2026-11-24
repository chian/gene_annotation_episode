"""hpc_work_planning through the real runner without a model: the caller steps the head with ``next_decision`` and
``run_unit`` (tool units only: a commissioned sister decides by its own model calls, which the model-run test
covers). The world is the prediction sister's ``hpc_world``. The first test saves the model request it saw as
``model_request.json`` in its temporary directory (under the run directory)."""
import asyncio
import importlib
import json

from episode_runtime import BindingRegistry, ModelRequest, ToolCall, link, resume
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc_ledger import HPC_LEDGER, ledger_id

from ..hpc_resource_prediction.tests import hpc_world

PACKAGE = __name__.rsplit('.', 2)[0]
JOB_CHILDREN = (('execution_job_submission', 'ExecutionJobSubmission'),
                ('execution_job_submission.hpc_job_execution', 'HpcJobExecution'),
                ('execution_job_submission.api_job_execution', 'ApiJobExecution'),
                ('execution_job_submission.local_job_execution', 'LocalJobExecution'),
                ('execution_progress_assessment', 'ExecutionProgressAssessment'),
                ('execution_result_acquisition', 'ExecutionResultAcquisition'))
SUBTREE = (('', 'HPCEpisode'), ('hpc_resource_prediction', 'HPCResourcePrediction'),
           ('hpc_allocation_execution', 'HPCAllocationExecution'), *JOB_CHILDREN,
           *(('hpc_allocation_execution.' + module, name) for module, name in JOB_CHILDREN))
EPISODE = importlib.import_module(PACKAGE + '.episode').HPCEpisode
TASK = importlib.import_module(PACKAGE + '.task')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path


def episodes():
    return [getattr(importlib.import_module(PACKAGE + ('.' + module if module else '') + '.episode'), name)()
            for module, name in SUBTREE]


def paths():
    return [PATH + ('/' + module.replace('.', '/') if module else '') for module, _ in SUBTREE]


def linked(world, run_id='planning_steps', **assignment):
    entry = {'assignment': {'commission_id': 'c1', 'scope': world['scope'], **assignment}, 'message': {},
             'selection': []}
    return link(BindingRegistry(episodes()), PATH, entry, run_id=run_id, journal=world['journal'],
                collaborators=world['collaborators'])


def step(run, name, **arguments):
    """One tool unit with the arguments the episode's ``action`` gives it (``owner_arguments``)."""
    summary = EPISODE.internal_summary(run.view)
    return asyncio.run(run.run_unit(ToolCall(name, TASK.owner_arguments(summary, arguments))))['outcome']


def test_the_first_unit_opens_the_ledger_and_the_model_is_then_offered_the_sisters_first(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='local_shell')
    run = linked(world)
    first = asyncio.run(run.next_decision())
    assert isinstance(first, ToolCall) and first.name == 'hpc_open'
    opened = asyncio.run(run.run_unit(first))
    assert opened['outcome']['result'] == {'ledger': ledger_id(hpc_world.commission()), 'credit_at_open': 0}
    rows = run.view.records.table(HPC_LEDGER).select({'ledger': opened['outcome']['result']['ledger']})
    assert [row['identity'] for row in rows] == ['commission', 'owner', 'reference_model']
    summary = EPISODE.internal_summary(run.view)
    # The summary reads the ledger through custody: the view is what the held rows show.
    assert summary['ledger_view']['ledger_refs'] == [row['id'] for row in rows]
    assert summary['ledger_view']['owner_episode_id'] == rows[0]['episode_id']
    assert summary['ledger_state']['measured_cases'] == {'training': 6, 'validation': 2}
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest) and request.instructions == TASK.INSTRUCTIONS
    (tmp_path / 'model_request.json').write_text(json.dumps(
        {'role': request.role, 'instructions': request.instructions, 'context': request.context,
         'output_schema': request.output_schema}, indent=1, sort_keys=True))
    assert set(request.context) == {'commission', 'resource', 'ledger', 'predictions', 'executions', 'launches',
                                    'monitors', 'acquisitions', 'credit', 'units_so_far', 'last_outcome',
                                    'feedback', 'actions'}
    assert [item['selection'] for item in request.context['actions']][:2] == ['hpc_prediction', 'hpc_execution']
    assert 'hpc_open' not in request.output_schema['properties']['selection']['enum']
    assert request.context['units_so_far'] == [] and request.context['last_outcome'] is None


def test_the_planners_own_steps_refuse_what_the_ledger_cannot_support_and_the_episode_closes_controlled(tmp_path):
    world = hpc_world.world(tmp_path, paths(), transport='absent')
    run = linked(world, 'planning_closed')
    asyncio.run(run.run_unit(asyncio.run(run.next_decision())))
    observed = step(run, 'hpc_queue_observe')
    assert observed['status'] == 'failed' and observed['feedback']['code'] == 'transport_unavailable'
    planned = step(run, 'hpc_plan', candidate_id='two_nodes', model_ref='reference_model', queue_ref='queue:none')
    assert planned['status'] == 'invalid' and planned['feedback']['code'] == 'unknown_hpc_evidence:queue:none'
    proposed = step(run, 'hpc_candidate_propose', candidate_json=json.dumps(hpc_world.candidate('four_nodes', 4, 900)))
    assert proposed['status'] == 'completed'
    summary = EPISODE.internal_summary(run.view)
    assert [item['id'] for item in summary['ledger_state']['candidates']] == ['one_node', 'two_nodes', 'four_nodes']
    assert [unit['action'] for unit in summary['units_so_far']] == ['hpc_queue_observe', 'hpc_plan',
                                                                    'hpc_candidate_propose']
    while not run.view.controller_state.stop:                     # units that earn nothing: the controller stops
        step(run, 'hpc_read', reference='commission')
    result = asyncio.run(run.run())['result'].as_record()
    assert set(result) == {'credit', 'finding', 'hpc_ledger_refs'} and result['credit'] == 0.0
    assert result['finding'] == {'accepted_obligations': 0, 'remaining_obligations': 1, 'plans_frozen': 0,
                                 'plans_handed_off': 0, 'plans_closed': 0, 'results_held': 0,
                                 'prediction_commissions': 0, 'execution_commissions': 0}
    assert len(result['hpc_ledger_refs']) == 4                    # commission, owner, reference model, candidate
    FINAL.RETURN_FORM.select(()).admit(result, 'return')
    units = len(world['journal'].units('planning_closed', run.view.path))
    replayed = asyncio.run(resume(BindingRegistry(episodes()), run_id='planning_closed', journal=world['journal'],
                                  collaborators=world['collaborators']).run())
    assert replayed['result'].as_record() == result
    assert len(world['journal'].units('planning_closed', run.view.path)) == units
    # A later commission of the same HPC work is passed the ledger back and continues it: the owner stands.
    later = linked(world, 'planning_again', received_record_refs=result['hpc_ledger_refs'])
    again = asyncio.run(later.run_unit(asyncio.run(later.next_decision())))
    assert again['produced'] == []
    continued = EPISODE.internal_summary(later.view)
    assert continued['ledger_view']['ledger_refs'] == result['hpc_ledger_refs']
    assert [item['id'] for item in continued['ledger_state']['candidates']][-1] == 'four_nodes'
