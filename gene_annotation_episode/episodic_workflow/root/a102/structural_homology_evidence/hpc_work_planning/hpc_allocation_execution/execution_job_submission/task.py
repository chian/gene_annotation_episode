"""The task: choose which permitted concrete execution request to commission on an explicit resource_id.

One unit is one model-selected action: a read of the bound resources' capabilities and recorded inventory (the
tool ``execution_capabilities``; the old ``execution.capabilities``), or the commission of the resource child
that owns the iterative execution of one request. The binding path is fixed under the HPC work-planning ancestors,
so the old action policy for an ``hpc`` ancestor applies: tool and child (the old ``reason``, ``wait`` and
``redeliver_report`` actions are not offered here; ``wait`` and ``redeliver_report`` no longer exist).

The task always offers a unit and never ends the Episode: its bounded yield controller stops it.

BLOCKED-ON-JOB-SERVICE: ``estimate_table``. The old decision showed the execution expectations of role ``launch``
(timing information of earlier runs). Wanted call, in ``decide``:
``ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')``. No such service exists yet, so a run
cannot be linked until the caller supplies one."""
from copy import deepcopy
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting

CHILD_SLOTS = {
    'api': ('structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
            'api_job_execution'),
    'local': ('structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
              'local_job_execution'),
    'hpc': ('structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
            'hpc_job_execution'),
}
SLOT_OF_KIND = {'api': 'api', 'local': 'local', 'hpc': 'hpc'}
SERVICES = ('estimate_table',)
MODEL_ROLE = 'REASONING'
CAPABILITIES = 'execution_capabilities'
COMMISSION = 'commission:'

INSTRUCTIONS = (
    'Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
    'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
    'constraints and pinned instructions: a request is commissioned exactly as the assignment states it. A '
    'resource child owns iterative execution in the shared loop; it returns the typed handoff this launch '
    'requested, and no infrastructure chooses an approach. Answer with one selection: '
    + CAPABILITIES + ' reads the actual caller-bound resource configuration and the already recorded inventory '
    '(no discovery, no selection); ' + COMMISSION + '<resource_id> commissions the resource child of that '
    'resource for its request. A received usable handoff for each permitted request completes this launch '
    'endpoint with exact zero future credit. The episode iterator decides continuation from credit; add no '
    'stopping budget.')


def capabilities(settings, resource_ids):
    """The configured values and the recorded inventory of each bound resource: the old ``execution.capabilities``
    (configured values, availability ``unknown``, no probe, no discovery, no selection)."""
    resources, inventory = settings['resources'], settings['initial_information']
    return [{'resource_id': resource_id, 'availability': 'unknown', 'configuration': deepcopy(resources[resource_id]),
             'inventory_snapshot': deepcopy(inventory.get(resource_id))} for resource_id in resource_ids]


def execution_capabilities(arguments, ctx):
    """Read the caller-bound resource configuration and the already recorded inventory of the named resources."""
    return {'resources': capabilities(ctx.settings, arguments['resource_ids'])}


TOOLS = {CAPABILITIES: execution_capabilities}


def offered(summary):
    """The selections this decision offers: the capabilities read, and one commission per permitted resource."""
    return [CAPABILITIES] + [COMMISSION + resource_id for resource_id in summary['permitted_resource_ids']]


def output_schema(summary):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'type': 'string', 'enum': offered(summary),
                                         'description': 'The one action of this decision.'}}}


def request_of(summary, resource_id):
    return next(request for request in summary['requests'] if request['resource_id'] == resource_id)


def selected_execution_task(summary):
    """The scientific parent's question and selected tool information with the requests, when every request is a
    local native protein-structure job (the old ``selected_execution_task_v1`` of ``internal_summary``)."""
    task = summary['scientific_task']
    requests = summary['requests']
    if task is None or not all(request['version'] == 'practical_assignment_v1' and request['resource_kind'] == 'local'
                               and 'native_protein_structure' in request['requested_job'] for request in requests):
        return None
    return {'version': 'selected_execution_task_v1', **task, 'requests': deepcopy(requests)}


def decide(summary, feedback, ctx):
    settings = ctx.settings
    directory = settings.get('launch_instruction_directory')
    if directory is None and summary['launch_instructions'] is not None:
        raise ValueError('launch_instruction_directory_required_for_a_launch_instruction_selection')
    context = {
        'execution_assignment': {name: summary[name] for name in ('requests', 'immutable_input_versions', 'constraints',
                                                                  'launch_instructions')},
        'permitted_resource_ids': summary['permitted_resource_ids'],
        'execution_progress': summary['progress'],
        'handoff_unit': summary['handoff_unit'],
        'feedback': feedback,
        'time_accounting': time_accounting(ctx.clock.progress_time),
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: the read below. No such service exists.
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'launch'),
        'actions': [{'selection': name} for name in offered(summary)],
    }
    if summary['action_yields'] is not None:
        context['action_yields'] = summary['action_yields']
    if directory is not None:
        library = LaunchInstructions(directory)
        context['launch_instruction_library'] = library.context()
        context['selected_launch_instructions'] = library.materialize(summary['launch_instructions'])
    if summary['units_consumed'] == 0:
        context['execution_resource_capabilities'] = capabilities(settings, summary['permitted_resource_ids'])
        if summary['hpc_execution_job'] is not None:
            context['hpc_execution_job'] = summary['hpc_execution_job']
        task = selected_execution_task(summary)
        if task is not None:
            context['selected_execution_task'] = task
    return ModelRequest(MODEL_ROLE, INSTRUCTIONS, context, output_schema(summary))


def action(response, summary, records, ctx):
    """Admit the model's selection. A selection outside the offered ones creates no unit: the model decides again
    with the feedback."""
    try:
        Draft202012Validator(output_schema(summary)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = response['selection']
    if selection == CAPABILITIES:
        return ToolCall(CAPABILITIES, {'resource_ids': list(summary['permitted_resource_ids'])})
    resource_id = selection[len(COMMISSION):]
    request = request_of(summary, resource_id)
    kind = 'api' if request['version'] != 'practical_assignment_v1' else request['resource_kind']
    return ChildCall(SLOT_OF_KIND[kind], {'resource_id': resource_id})
