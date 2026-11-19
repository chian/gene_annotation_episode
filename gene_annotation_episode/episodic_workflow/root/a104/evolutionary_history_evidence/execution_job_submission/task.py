"""The task: the launch of one evolutionary-history job. The first unit is the lookup of the configured resource
capabilities (the old ``execution.capabilities``, the one operation of ``launch_operation_catalog`` and the only branch
of ``LaunchWorkOperations.execute`` that was reachable for the launch role, which returned ``initial_decision_context``
as the tool result: ``execution_capabilities`` here, a tool name cannot contain a dot); after it the model chooses
either a lookup in the run-frozen tool-knowledge or launch-instruction library (the old decision-exchange lookups,
which are tools now), or which permitted concrete request to commission on an explicit ``resource_id``. A commission
is a ``ChildCall`` on the launch child that owns the resource's kind (``launch_api``, ``launch_local`` or
``launch_hpc``). The task always offers a unit and never ends the Episode: no stopping budget is added, and the yield
controller (``yield_estimator.py``) alone stops it.

The old decision machine (``LaunchTask.next``, ``apply_response``, ``execute``, ``LaunchTaskDecision.call``,
``exchange_decision`` and its saved-request checks, the ``wait`` and ``redeliver_report`` actions, the conversation
state) is the system's loop now. The old ``permitted_common_actions`` offered ``tool``, ``reason``, ``child``, ``wait``
and ``redeliver_report``, and without ``reason`` and ``wait`` when any ancestor was ``hpc``; the reasoning path
(``reason``) is a tool that commits through ``ctx.store.commit_reasoning`` and this episode, which has no reasoning
content of its own to commit (it commissions launches), declares none: the old action offered nothing the launch could
use it for (contract_misfits). What stays of ``instructions.instructions`` is the goal text (it replaced the default
instructions), the tool-knowledge text and the launch-instruction text; the reasoning-commit, ``pending_child_
delivery``, wait, native-event and decision-exchange paragraphs described actions that no longer exist.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). This episode names it for what the old ``api_execution`` did for an API
resource: the operations and configuration facts of the resource (``capabilities(resource_id)``), the BV-BRC values
already received (``received_bvbrc_context()``) and the service's own validation of an API request
(``validate_assignment(request)``); each raises where it is called.

Not carried into the model's context (their sources are old-runner services, not episode functions): the old
``resource_context``, ``shared_information_context``, ``execution_expectations``, ``resource_tool_estimates``,
``native_execution_expectations``, ``pending_work``, ``waiting_support``, ``native_event_targets``,
``job_execution_options`` and ``completed_action_reports`` of ``decision_inputs``; the ``resource_tool_contracts`` of
``LaunchResourceInformation`` (the per-resource launch and results operation contracts with commission routes) need
``api_execution.operation_contracts``, ``homology_api_contracts`` and the native ``*_tool_info`` modules, which have no
library module; the model is shown the permitted requests and the resource capabilities instead. The old prompt
renderers (``render_selected_execution_prompt``, ``render_api_launch_prompt``) have no module in the library: the task
text is rendered here.

Settings (``ctx.settings``, the old ``configuration.py`` values): ``resources`` (the configured resources by resource
id, each with ``kind`` ``local``, ``pbs_ssh``, ``hmmer_api`` or ``api``), ``initial_information`` (the recorded
inventory by resource id), ``coordinator_workspace`` (the run directory the resource validators work in),
``launch_instructions_directory`` and ``tool_knowledge_directory`` (the old ``directory`` of the two libraries) and
``task_yield_profiles`` (read by ``yield_estimator.py``)."""
from copy import deepcopy
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_terminal_transport import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import BINDING_PATH, GOAL

CHILD_SLOTS = {'launch_api': BINDING_PATH + '/api_job_execution', 'launch_hpc': BINDING_PATH + '/hpc_job_execution',
               'launch_local': BINDING_PATH + '/local_job_execution'}
SERVICES = ('job_access',)

# The old ``binding_roles.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
# The old ``LaunchResourceInformation._resource_information`` keys copied from the configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
# The old ``terminal_execution.operation_catalog``: the one general capability of a local or HPC resource.
PRACTICAL_TOOL_NAMES = ['exec_command']
# The old ``LaunchInternalSummary._with_selected_execution_task``: the native job families whose scientific view it
# presented.
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation')
# The old ``LaunchConfiguration.__init__`` allowance of ``native_*`` bindings on a configured resource.
ALLOWED_NATIVE = set(SUPPORTED_NATIVE_JOBS)
ANSWER_INSTRUCTION = (' Answer with one selection: commission one permitted request on its explicit resource_id '
                      '(kind child, with the launch child slot that owns the resource), or look into a library '
                      '(kind tool, one operation of the library).')
LIBRARIES = {'knowledge_lookup': ('Look into the run-frozen tool-instruction library: ', knowledge_catalog),
             'launch_instruction_lookup': ('Look into the run-frozen launch instruction library: ', launch_catalog)}
# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; no '
                            'discovery or selection.')


def _resources(settings):
    """The old ``LaunchConfiguration.__init__`` checks of the configured resources."""
    resources, information = settings['resources'], settings['initial_information']
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    for configuration in resources.values():
        if {name for name in configuration if name.startswith('native_') and name not in ALLOWED_NATIVE}:
            raise ValueError('a104_execution_resource_binding_conflict')
    return resources


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: each request names a bound resource of its
    kind, and the transport (or the API service) accepts the request. A configuration or request it refuses raises
    and fails the run: it is not a model answer. (The old ``validate_primary_resource_bindings`` and
    ``validate_preparation_resource_binding`` have no module in the library.)"""
    settings = ctx.settings
    _resources(settings)
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
            TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                              artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities`` (``LaunchWorkOperations.execute`` returning ``initial_decision_context``):
    the caller-bound resource configuration and the already recorded inventory, with no discovery, authentication
    probe or selection. A resource of the API kind also lists its configured operations and configuration facts, and
    the BV-BRC values already received, which only the job-access service knows."""
    settings = ctx.settings
    information = []
    api_resources = False
    for resource_id, config in settings['resources'].items():
        kind = KINDS[config['kind']]
        value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
                 **{key: deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
                 'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))}
        if kind == 'api':
            api_resources = True
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
    received = []
    if api_resources:
        service = ctx.services['job_access']
        if not hasattr(service, 'received_bvbrc_context'):
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: job_access.received_bvbrc_context(); wanted call: '
                'ctx.services["job_access"].received_bvbrc_context()')
        received = service.received_bvbrc_context()
        if inspect.isawaitable(received):
            received = await received
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings['initial_information']),
            'received_bvbrc_values': received}


def knowledge_lookup(arguments, ctx):
    """One operation of the run-frozen tool-instruction library (the old ``knowledge.*`` exchange lookups)."""
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    """One operation of the run-frozen launch-instruction library (the old ``launch.instructions.*`` lookups)."""
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                    arguments['arguments'])


TOOLS = {'execution_capabilities': execution_capabilities, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _selected_execution_task(summary, resources):
    """The old ``LaunchInternalSummary._with_selected_execution_task``: the scientific question and tool information of
    the parent task, and each request with its resource information, constraints and job. It presented nothing when
    the request of some resource was not an EBI HMMER API request or exactly one supported native job family."""
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
            if chosen[0] in ('native_hmmer', 'native_hmmer_preparation'):
                # old: native_profile_presentation.native_profile_scientific_job_view(job): no module in the library
                raise NotImplementedError('unplaced:native_profile_scientific_job_view')
        selected.append({'resource_id': resource_id, 'resource_kind': kind,
                         'endpoint': deepcopy(request.get('endpoint')),
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
    """What the model answers with: the commission of one permitted request, or one operation of a library."""
    commissions = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'resource_id'],
                    'properties': {'kind': {'type': 'string', 'const': 'child'},
                                   'slot': {'type': 'string', 'const': entry['slot']},
                                   'resource_id': {'type': 'string', 'const': resource_id}}}
                   for resource_id, entry in sorted(summary['permitted'].items())]
    lookups = [{'type': 'object', 'additionalProperties': False,
                'required': ['kind', 'tool', 'operation', 'arguments'],
                'properties': {'kind': {'type': 'string', 'const': 'tool'},
                               'tool': {'type': 'string', 'const': name},
                               'operation': {'type': 'string', 'const': operation['name']},
                               'arguments': deepcopy(operation['input_schema'])}}
               for name, (_, catalog) in sorted(LIBRARIES.items()) for operation in catalog()]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': commissions + lookups}}}


def _context(summary, feedback, ctx, selected):
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary, selected), 'feedback': feedback,
               'execution_assignment': summary['assignment'], 'execution_progress': summary['progress'],
               'execution_resource_capabilities': summary['capabilities']['execution_resource_capabilities'],
               'execution_initial_information': summary['capabilities']['execution_initial_information'],
               'received_bvbrc_values': summary['capabilities']['received_bvbrc_values'],
               'callable_lookups': [{'name': name, 'description': description + ', '.join(
                   operation['name'] for operation in catalog())} for name, (description, catalog) in
                   sorted(LIBRARIES.items())],
               'requested_information': summary['lookups'], 'completed_action_reports': summary['launches'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(summary['assignment'].get('launch_instructions')),
               'tools': [{'name': 'execution_capabilities', 'description': CAPABILITIES_DESCRIPTION}],
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if selected is not None:
        context['selected_execution_task'] = selected
    return context


def decide(summary, feedback, ctx):
    """The lookup of the capabilities first (after the configured resources accepted the requests); then one
    selection: a library lookup or the commission of one permitted request, chosen from the capabilities, the
    inventory, the handoffs received so far and their credit."""
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    resources = {value['resource_id']: value for value in summary['capabilities']['execution_resource_capabilities']}
    selected = _selected_execution_task(summary, resources)
    instructions = GOAL + '\n' + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION
    return ModelRequest('REASONING', instructions, _context(summary, feedback, ctx, selected),
                        generation_schema(_schema(summary)))


def action(response, summary, records, ctx):
    """The one unit the answer selects, or a rejection: a lookup of a library, or the commission of a permitted
    request on the launch child that owns the resource's kind. The lookups are always acceptable, so a unit is
    always offered."""
    schema = _schema(summary)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    if selection['kind'] == 'child':
        return ChildCall(selection['slot'], {'resource_id': selection['resource_id']})
    return ToolCall(selection['tool'], {'operation': selection['operation'], 'arguments': selection['arguments']})
