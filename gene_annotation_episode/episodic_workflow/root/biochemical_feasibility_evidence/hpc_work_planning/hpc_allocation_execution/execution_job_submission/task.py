"""The task: the launch of one job. The episode's first unit is the lookup of the configured resource capabilities
(its one tool, ``execution_capabilities``: the old ``execution.capabilities``, ``LaunchWorkOperations``); after it
the model chooses which permitted concrete request to commission on an explicit ``resource_id``, and the
commission is a ``ChildCall`` on the launch child that owns the resource's kind (``launch_local`` or
``launch_hpc``). The task always offers a unit and never ends the Episode: no stopping budget is added; the yield
controller stops it when the requests still without a usable handoff are exhausted or the forecast no longer pays
for another commission.

The old decision machine (``LaunchTask.next``, ``call``, ``apply_response``, ``execute``, the decision exchange, the
``reason``, ``wait`` and ``redeliver_report`` actions) is the system's loop now; the old report, pending-child,
native-event and decision-exchange guidance of ``task_instructions`` described actions that no longer exist and is
not carried. What stays of ``task_instructions`` is the action boundary, the host-execution text and the
tool-knowledge and launch-library texts.

This episode submits, checks and fetches nothing itself: its children carry the job access (their own blocked
files). The capabilities lookup reads the configured resources and the recorded inventory from the settings, as the
old ``execution_capability_information`` did.

BLOCKED-ON-JOB-SERVICE: ``estimate_table`` (MECHANICS section 5; no service exists). The old decision context carried
the timing information of earlier runs (``execution_expectations('launch')`` and the ``resource_tool_estimates``
made from them: "timing information inform the choice", the goal text). ``decide`` names the service and reads
``ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')`` and raises where the service has no such
member.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id), ``initial_information`` (the
recorded inventory by resource id, optional per resource), ``coordinator_workspace``,
``launch_instructions_directory``, ``tool_knowledge_directory`` (optional: the old workflow-level libraries) and
``task_yield_profiles`` (read by ``yield_estimator.py``)."""
import json

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

_ROOT = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
CHILD_SLOTS = {'launch_local': _ROOT + 'local_job_execution', 'launch_hpc': _ROOT + 'hpc_job_execution'}
SERVICES = ('estimate_table',)

# The old ``binding_roles.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}
# The old resource information keys copied from the configured resource (the keys of the configured transport).
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')
# The old ``operation_catalog`` of a local or HPC resource: the one general capability.
PRACTICAL_TOOL_NAMES = ['exec_command']

ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'
ANSWER_INSTRUCTION = (' Answer with slot (the launch child that owns the resource: launch_local or launch_hpc) and '
                      'the resource_id of one permitted request.')


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: the request names a bound resource of its
    kind, and the transport accepts the request. A configuration or request it refuses raises and fails the run:
    it is not a model answer."""
    settings = ctx.settings
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        if KINDS[config['kind']] != request['resource_kind']:
            raise ValueError('execution_resource_kind_conflict')
        TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                          artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities`` / ``execution_capability_information``: the caller-bound resource
    configuration and the recorded inventory, with no discovery, authentication probe or selection."""
    settings = ctx.settings
    information = []
    for resource_id, config in settings['resources'].items():
        information.append({'resource_id': resource_id, 'resource_kind': KINDS[config['kind']],
                            'availability': 'unknown', 'observed_at': 'caller_configuration',
                            'provenance_refs': [], 'knowledge_entry_ids': [],
                            **{key: config[key] for key in RESOURCE_KEYS if key in config},
                            'tool_names': list(PRACTICAL_TOOL_NAMES),
                            'inventory_snapshot': settings.get('initial_information', {}).get(resource_id)})
    return {'execution_resource_capabilities': information,
            'execution_initial_information': settings.get('initial_information', {})}


TOOLS = {'execution_capabilities': execution_capabilities}


def _selected_execution_task(summary, resources):
    """The old ``LaunchInternalSummary._with_selected_execution_task``: only for native flux balance work (every
    request's job is a native flux balance job) and only when the parent task is known: the scientific question and
    tool information of the parent task, and the permitted requests with their resource information, constraints
    and job. The old ``scientific_job_view`` of the job has no placed home: the job is shown as the request has it."""
    task = summary['scientific_task']
    requests = summary['assignment']['requests']
    if task is None or any('native_flux_balance' not in request['requested_job'] for request in requests.values()):
        return None
    selected = []
    for resource_id in summary['permitted']:
        request = requests[resource_id]
        selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                         'endpoint': request['endpoint'], 'constraints': request['constraints'],
                         'job': request['requested_job']['native_flux_balance'],
                         'resource': resources.get(resource_id)})
    return {'version': 'selected_execution_task', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': summary['assignment']['constraints']}


def _task_text(summary, selected):
    parts = ['TASK', '', 'Choose which permitted concrete execution request to commission on an explicit resource_id.']
    if selected is not None:
        parts.extend(['', 'Selected execution task', '', json.dumps(selected, indent=1, sort_keys=True)])
    parts.extend(['', 'Launches so far', '', json.dumps(summary['launches'], indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _output_schema(summary):
    permitted = summary['permitted']
    slots = sorted({entry['slot'] for entry in permitted.values()})
    return {'type': 'object', 'additionalProperties': False, 'required': ['slot', 'resource_id'],
            'properties': {'slot': {'enum': slots}, 'resource_id': {'enum': sorted(permitted)}}}


def decide(summary, feedback, ctx):
    """The lookup of the capabilities first; then one commission: the model chooses the permitted request from the
    capabilities, the inventory, the handoffs received so far and their credit."""
    if not summary['permitted']:
        raise ValueError('execution_no_permitted_request')
    _bound(summary, ctx)
    if summary['capabilities'] is None:
        return ToolCall('execution_capabilities', {})
    try:
        estimates = ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')
    except AttributeError:
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: estimate_table.resource_tool_estimates(kind); wanted call: '
            "ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')") from None
    settings = ctx.settings
    library_directory = settings.get('launch_instructions_directory')
    knowledge_directory = settings.get('tool_knowledge_directory')
    library = None if library_directory is None else LaunchInstructions(library_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory)
    resources = {value['resource_id']: value for value in summary['capabilities']['execution_resource_capabilities']}
    selected = _selected_execution_task(summary, resources)
    instructions = (GOAL + '\n' + ACTION_BOUNDARY + HOST_EXECUTION_GUIDANCE
                    + ('' if knowledge is None else KNOWLEDGE_INSTRUCTIONS)
                    + ('' if library is None else LAUNCH_INSTRUCTIONS) + ANSWER_INSTRUCTION)
    context = {'task': _task_text(summary, selected), 'feedback': feedback,
               'execution_assignment': summary['assignment'],
               'execution_progress': {'handoff_resources': summary['handoff_resources'],
                                      'handoff_refs': summary['handoff_refs'],
                                      'received_handoff_resources': summary['received_handoff_resources']},
               'execution_resource_capabilities': summary['capabilities']['execution_resource_capabilities'],
               'execution_initial_information': summary['capabilities']['execution_initial_information'],
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'tool_knowledge': None if knowledge is None else knowledge.context(),
        'launch_instruction_library': None if library is None else library.context(),
        'selected_launch_instructions': (None if library is None or 'launch_instructions' not in summary['assignment']
                                         else library.materialize(summary['assignment']['launch_instructions'])),
        'selected_execution_task': selected, 'resource_tool_estimates': estimates},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions, context, _output_schema(summary))


def action(response, summary, records, ctx):
    """The one commission the answer selects, or a rejection: it names a permitted resource and the launch child
    that owns the resource's kind."""
    try:
        slot, resource_id = response['slot'], response['resource_id']
        entry = summary['permitted'].get(resource_id)
        if entry is None:
            raise ValueError('execution_resource_not_permitted')
        if entry['slot'] != slot:
            raise ValueError('execution_slot_does_not_own_the_resource_kind')
    except (KeyError, TypeError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    return ChildCall(slot, {'resource_id': resource_id})
