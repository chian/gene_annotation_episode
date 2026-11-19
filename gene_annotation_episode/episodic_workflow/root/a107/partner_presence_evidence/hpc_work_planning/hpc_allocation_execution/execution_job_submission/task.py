"""The task: the launch of one planned computation. The first unit is the lookup of the configured resource
capabilities (the old ``execution.capabilities``, the one operation of ``work_operations.py`` and
``resource_information.py``: ``execution_capabilities`` here); after it the model chooses either a lookup in the
run-frozen tool-knowledge or launch-instruction library, or which permitted concrete request to commission on an
explicit ``resource_id``. A commission is a ``ChildCall`` on the launch child that owns the resource's kind
(``launch_api``, ``launch_local`` or ``launch_hpc``). The task always offers a unit and never ends the Episode: no
stopping budget is added, and the yield controller (``yield_estimator.py``) alone stops it.

The old decision machine (``LaunchTask.next``, ``apply_response``, ``execute``, ``LaunchTaskDecision``, the decision
exchange, the ``wait`` and ``redeliver_report`` actions, the saved-request checks, the conversation state) is the
system's loop now. The old ``reason`` action was permitted only outside an ``hpc`` path
(``permitted_common_actions``); this episode runs under the HPC allocation parent, so it never had it. What stays of
``task_instructions.instructions`` is the goal text (it replaced the default instructions), the tool-knowledge text
and the launch-instruction text; the repair, pending-child, wait, native-event and decision-exchange paragraphs
described actions that no longer exist.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). This episode names it for the two things the old ``api_execution`` did for
an API resource: the configured operations of the resource (``capabilities(resource_id)``) and the service's own
validation of an API request (``validate_assignment(request)``); each raises where it is called.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id, old ``resources``),
``initial_information`` (the recorded inventory by resource id), ``coordinator_workspace``,
``launch_instructions_directory`` and ``tool_knowledge_directory`` (the old ``directory`` of the two libraries) and
``task_yield_profiles`` (read by ``yield_estimator.py``)."""
from copy import deepcopy
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

CHILD_SLOTS = {
    'launch_api': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution',
    'launch_hpc': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution',
    'launch_local': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution',
}
SERVICES = ('job_access',)

# The old ``binding_roles.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
# The one general capability of a local or HPC resource (the tool of the practical execution children).
PRACTICAL_TOOL_NAMES = ['exec_command']
# The old ``_with_selected_execution_task``: the native job families whose scientific view it presented.
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation',
                         'native_expression_nmf')
TRANSPORT_ERROR = 'a107_execution_job_submission_selection_has_no_argument_transport'
ANSWER_INSTRUCTION = (' Answer with one selection: commission one permitted request on its explicit resource_id '
                      '(kind child, with the launch child slot that owns the resource), or look into a library '
                      '(kind tool).')
DESCRIPTIONS = {
    'knowledge_lookup': 'Look into the run-frozen tool-instruction library (knowledge.search, entry, read).',
    'launch_instruction_lookup': ('Look into the run-frozen launch instruction library (launch.instructions.search, '
                                  'entry, read, select).'),
}
LOOKUP_ARGUMENTS = {
    name: {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments'],
           'properties': {'operation': {'type': 'string', 'enum': [item['name'] for item in catalog()]},
                          'arguments': {'type': 'object'}}}
    for name, catalog in (('knowledge_lookup', knowledge_catalog), ('launch_instruction_lookup', launch_catalog))}


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: each request names a bound resource of its
    kind, and the transport (or the API service) accepts the request. A configuration or request it refuses raises
    and fails the run: it is not a model answer."""
    settings = ctx.settings
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        kind = 'api' if request['version'] != 'practical_assignment_v1' else request['resource_kind']
        if KINDS[config['kind']] != kind:
            raise ValueError('execution_resource_kind_conflict')
        if kind == 'api':
            try:
                ctx.services['job_access'].read('validate_assignment', request)
            except AttributeError:
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: '
                    'ctx.services["job_access"].read("validate_assignment", request)') from None
        else:
            TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace']
                              ).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities``: the caller-bound resource configuration and the already recorded
    inventory, with no discovery, authentication probe or selection. A resource of the API kind also lists its
    configured operations, which only the job-access service knows."""
    settings = ctx.settings
    information = []
    for resource_id, config in settings['resources'].items():
        kind = KINDS[config['kind']]
        value = {'resource_id': resource_id, 'resource_kind': kind, 'configuration': deepcopy(config)}
        if resource_id in settings['initial_information']:
            value['recorded_inventory'] = settings['initial_information'][resource_id]
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
        else:
            value['tool_names'] = list(PRACTICAL_TOOL_NAMES)
        information.append(value)
    return {'execution_capability_information': information,
            'execution_initial_information': deepcopy(settings['initial_information'])}


def knowledge_lookup(arguments, ctx):
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                    arguments['arguments'])


TOOLS = {'execution_capabilities': execution_capabilities, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _selected_execution_task(summary, resources):
    """The old ``LaunchInternalSummary._with_selected_execution_task``: the scientific question and tool
    information of the parent task, and each request with its resource information, constraints and job. It
    presented nothing when the request of some resource was not of a supported shape."""
    task = summary['scientific_task']
    if task is None:
        return None
    selected = []
    for resource_id, request in summary['assignment']['requests'].items():
        if resource_id not in resources:
            return None
        if request['version'] != 'practical_assignment_v1':
            if request.get('service') != 'ebi_hmmer':
                return None
            kind, job = 'api', deepcopy(request)
        else:
            jobs = request['requested_job']
            chosen = [name for name in SUPPORTED_NATIVE_JOBS if isinstance(jobs.get(name), dict)]
            if len(chosen) != 1:
                return None
            kind, job = request['resource_kind'], deepcopy(jobs[chosen[0]])
            if chosen[0] == 'native_expression_nmf':
                # old: expression_nmf_presentation.expression_nmf_scientific_job_view(job), in no place now
                raise NotImplementedError('unplaced:expression_nmf_scientific_job_view')
            if chosen[0] in ('native_hmmer', 'native_hmmer_preparation'):
                # old: native_profile_presentation.native_profile_scientific_job_view(job), in no place now
                raise NotImplementedError('unplaced:native_profile_scientific_job_view')
        selected.append({'resource_id': resource_id, 'resource_kind': kind, 'endpoint': request.get('endpoint'),
                         'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                         'resource': resources[resource_id]})
    return {'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': deepcopy(summary['assignment']['constraints']), 'selector': None,
            'result_description': None}


def _task_text(summary, selected):
    parts = ['TASK', '', 'Choose which permitted concrete execution request to commission on an explicit resource_id.']
    if selected is not None:
        parts.extend(['', 'Selected execution task', '', json.dumps(selected, indent=1, sort_keys=True)])
    parts.extend(['', 'Permitted requests', '', json.dumps(summary['permitted'], indent=1, sort_keys=True),
                  '', 'Launches so far', '', json.dumps(summary['launches'], indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _schema(summary):
    commissions = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'resource_id'],
                    'properties': {'kind': {'type': 'string', 'const': 'child'},
                                   'slot': {'type': 'string', 'const': entry['slot']},
                                   'resource_id': {'type': 'string', 'const': resource_id}}}
                   for resource_id, entry in sorted(summary['permitted'].items())]
    lookups = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                'properties': {'kind': {'type': 'string', 'const': 'tool'},
                               'tool': {'type': 'string', 'const': name},
                               'arguments': deepcopy(LOOKUP_ARGUMENTS[name])}} for name in sorted(LOOKUP_ARGUMENTS)]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': commissions + lookups}}}


def _context(summary, feedback, ctx, selected, resources):
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary, selected), 'feedback': feedback,
               'execution_assignment': summary['assignment'], 'execution_progress': summary['progress'],
               'execution_capability_information': summary['capabilities']['execution_capability_information'],
               'execution_initial_information': summary['capabilities']['execution_initial_information'],
               'callable_lookups': [{'name': name, 'description': DESCRIPTIONS[name],
                                     'arguments_schema': LOOKUP_ARGUMENTS[name]} for name in sorted(DESCRIPTIONS)],
               'requested_information': summary['lookups'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(summary['assignment'].get('launch_instructions')),
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if selected is not None:
        context['selected_execution_task'] = selected
    return context


def decide(summary, feedback, ctx):
    """The lookup of the capabilities first (after the configured resources accepted the requests); then one
    selection: a library lookup or a commission of one permitted request, chosen from the capabilities, the
    inventory, the handoffs received so far and their credit."""
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    resources = {value['resource_id']: value for value in summary['capabilities']['execution_capability_information']}
    selected = _selected_execution_task(summary, resources)
    instructions = GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION
    schema = strict_output_schema(_schema(summary), open_records_as_text=True,
                                  argument_transport_error=TRANSPORT_ERROR)
    return ModelRequest('REASONING', instructions, _context(summary, feedback, ctx, selected, resources), schema)


def action(response, summary, records, ctx):
    """The one unit the answer selects, or a rejection: a lookup of a library, or the commission of a permitted
    request on the launch child that owns the resource's kind."""
    schema = _schema(summary)
    try:
        decoded = decode_strict_output(response, schema, open_records_as_text=True,
                                       argument_transport_error=TRANSPORT_ERROR)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    if selection['kind'] == 'child':
        return ChildCall(selection['slot'], {'resource_id': selection['resource_id']})
    return ToolCall(selection['tool'], selection['arguments'])
