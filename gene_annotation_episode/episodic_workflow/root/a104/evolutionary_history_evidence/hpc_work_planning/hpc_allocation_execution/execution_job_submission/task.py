"""The task: the launch of one job. The episode's first unit is the lookup of the configured resource capabilities
(its one tool, ``execution_capabilities``: the old ``execution.capabilities``); after it the model chooses which
permitted concrete request to commission on an explicit ``resource_id``, and the commission is a ``ChildCall`` on
the launch child that owns the resource's kind (``launch_api``, ``launch_local`` or ``launch_hpc``). The task always
offers a unit and never ends the Episode: no stopping budget is added; the yield controller stops it when the
requests still without a usable handoff are exhausted or the forecast no longer pays for another commission.

The old decision machine (``LaunchTask.next``, ``call``, ``apply_response``, ``execute``, the decision exchange, the
``reason`` and ``wait`` and ``redeliver_report`` actions) is the system's loop now; the old report and history
guidance of ``task_instructions`` described actions that no longer exist and is not carried. What stays of
``task_instructions`` is the action boundary and the host-execution text.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). This episode names it for the two things the old ``api_execution`` did for
an API resource: the operation names and configuration facts of the resource (``capabilities(resource_id)``) and
the service's own validation of an API request (``validate_assignment(request)``); each raises where it is called.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id), ``initial_information`` (the
recorded inventory by resource id), ``coordinator_workspace``, ``launch_instructions_directory``,
``tool_knowledge_directory`` and ``task_yield_profiles`` (read by ``yield_estimator.py``)."""
import inspect
import json

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_terminal_transport import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

_ROOT = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
CHILD_SLOTS = {'launch_api': _ROOT + 'api_job_execution', 'launch_local': _ROOT + 'local_job_execution',
               'launch_hpc': _ROOT + 'hpc_job_execution'}
SERVICES = ('job_access',)

# The old ``contracts.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
# The old ``resource_information._resource_information`` keys copied from the configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
# The old ``terminal_validation.operation_catalog``: the one general capability of a local or HPC resource.
PRACTICAL_TOOL_NAMES = ['exec_command']

ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'
ANSWER_INSTRUCTION = (' Answer with slot (the launch child that owns the resource: launch_api, launch_local or '
                      'launch_hpc) and the resource_id of one permitted request.')


def _kind(request):
    return 'api' if request['version'] != 'practical_assignment' else request['resource_kind']


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: the request names a bound resource of its
    kind, and the transport (or the API service) accepts the request. A configuration or request it refuses raises
    and fails the run: it is not a model answer."""
    settings = ctx.settings
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        if KINDS[config['kind']] != _kind(request):
            raise ValueError('execution_resource_kind_conflict')
        if _kind(request) == 'api':
            try:
                ctx.services['job_access'].read('validate_assignment', request)
            except AttributeError:
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: '
                    'ctx.services["job_access"].read("validate_assignment", request)') from None
        else:
            TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                              artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The old ``LaunchCapabilities.execute`` / ``initial_decision_context``: the caller-bound resource
    configuration and the recorded inventory, with no discovery, authentication probe or selection."""
    settings = ctx.settings
    information = []
    for resource_id, config in settings['resources'].items():
        kind = KINDS[config['kind']]
        value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
                 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [],
                 **{key: config[key] for key in RESOURCE_KEYS if key in config},
                 'inventory_snapshot': settings['initial_information'].get(resource_id)}
        if kind == 'api':
            service = ctx.services['job_access']
            if not hasattr(service, 'capabilities'):
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: '
                    'await ctx.services["job_access"].capabilities(resource_id)')
            entries = service.capabilities(resource_id)
            if inspect.isawaitable(entries):
                entries = await entries
            value['tool_names'] = [entry['name'] for entry in entries]
            facts = {}
            for entry in entries:
                reported = entry.get('configuration', {})
                for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                    if name not in reported:
                        continue
                    actual = reported[name]
                    if type(actual) is not bool:
                        raise ValueError('api_configuration_fact_must_be_boolean')
                    if name in facts and facts[name] != actual:
                        raise ValueError('api_configuration_fact_conflict')
                    facts[name] = actual
            if facts:
                value['api_configuration_facts'] = facts
        else:
            value['tool_names'] = list(PRACTICAL_TOOL_NAMES)
        information.append(value)
    return {'execution_resource_capabilities': information,
            'execution_initial_information': settings['initial_information']}


TOOLS = {'execution_capabilities': execution_capabilities}


def _selected_execution_task(summary, resources):
    """The old ``LaunchSummary._with_selected_execution_task``: the scientific question and tool information of the
    parent task, and the permitted requests with their resource information, constraints and job."""
    task = summary['scientific_task']
    if task is None:
        return None
    selected = []
    for resource_id, entry in summary['permitted'].items():
        request = summary['assignment']['requests'][resource_id]
        selected.append({'resource_id': resource_id, 'resource_kind': entry['kind'],
                         'endpoint': request.get('endpoint'), 'constraints': request.get('constraints', {}),
                         'job': request if entry['kind'] == 'api' else request['requested_job'],
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
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    resources = {value['resource_id']: value for value in summary['capabilities']['execution_resource_capabilities']}
    selected = _selected_execution_task(summary, resources)
    instructions = (GOAL + '\n' + ACTION_BOUNDARY + HOST_EXECUTION_GUIDANCE + KNOWLEDGE_INSTRUCTIONS
                    + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION)
    context = {'task': _task_text(summary, selected), 'feedback': feedback,
               'execution_assignment': summary['assignment'], 'execution_progress': {
                   'handoff_resources': summary['handoff_resources'], 'handoff_refs': summary['handoff_refs'],
                   'received_handoff_resources': summary['received_handoff_resources']},
               'execution_resource_capabilities': summary['capabilities']['execution_resource_capabilities'],
               'execution_initial_information': summary['capabilities']['execution_initial_information'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(summary['assignment'].get('launch_instructions')),
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if selected is not None:
        context['selected_execution_task'] = selected
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
