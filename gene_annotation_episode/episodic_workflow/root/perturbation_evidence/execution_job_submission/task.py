"""The task: the launch of one perturbation (BV-BRC AppService) job. The first unit is the lookup of the configured
resource capabilities (the old ``execution.capabilities``, the one operation of ``launch_operation_catalog``, whose
``OperationalOperations.execute`` returned ``initial_decision_context``: ``execution_capabilities`` here, a tool name
cannot contain a dot); after it the model chooses either a lookup in the run-frozen tool-knowledge or
launch-instruction library (the old decision-exchange lookups, which are tools now), or which permitted concrete
request to commission on an explicit ``resource_id``. A commission is a ``ChildCall`` on the API launch child
(``launch_api``, the only child role). The task always offers a unit and never ends the Episode: no stopping budget
is added, and the yield controller (``yield_estimator.py``) alone stops it.

The old decision machine (``OperationalTask.next``, ``apply_response``, ``execute``, ``OperationalTaskDecision.call``,
``exchange_decision`` and its saved-request checks, the ``wait`` and ``redeliver_report`` actions, the conversation
state) is the system's loop now. The old ``permitted_common_actions`` offered ``tool``, ``reason``, ``child``,
``wait`` and ``redeliver_report``; the reasoning path (``reason``) is a tool that commits through
``ctx.store.commit_reasoning`` and this episode, which has no reasoning content of its own to commit (it commissions
launches), declares none: the old action offered nothing the launch could use it for (contract_misfits). What stays of
``task_instructions.instructions`` is the goal text (it replaced the default instructions), the tool-knowledge text
and the launch-instruction text; the reasoning-commit, ``pending_child_delivery``, wait, native-event and
decision-exchange paragraphs described actions that no longer exist.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). This episode names it for what the old ``api_execution``
(``APIServiceExecution``) did for an API resource: the configured operations of the resource
(``capabilities(resource_id)``) and the service's own validation of an API request (``validate_assignment(request)``);
each raises where it is called.

Not carried into the model's context (their sources are old-runner services, not episode functions): the old
``resource_context``, ``shared_information_context``, ``execution_expectations``, ``resource_tool_estimates``,
``native_execution_expectations``, ``pending_work`` and ``waiting_support`` of ``decision_inputs``; the model is
shown the permitted requests and the resource capabilities instead.

Settings (``ctx.settings``, the old ``configuration.py`` values): ``resources`` (the configured resources by resource
id, each with ``kind`` ``api``), ``initial_information`` (the recorded inventory by resource id),
``launch_instructions_directory`` and ``tool_knowledge_directory`` (the old ``directory`` of the two libraries) and
``task_yield_profiles`` (read by ``yield_estimator.py``)."""
from copy import deepcopy
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import BINDING_PATH, GOAL

CHILD_SLOTS = {'launch_api': BINDING_PATH + '/api_job_execution'}
SERVICES = ('job_access',)

# The old ``execution_contracts.KINDS``: the kind of each configured resource.
KINDS = {'api': 'api'}
# The old ``OperationalOperations._resource_information`` keys copied from the configured resource.
RESOURCE_KEYS = ('service', 'base_url')
ANSWER_INSTRUCTION = (' Answer with one selection: commission one permitted request on its explicit resource_id '
                      '(kind child, with the launch child slot that owns the resource), or look into a library '
                      '(kind tool, one operation of the library).')
LIBRARIES = {'knowledge_lookup': ('Look into the run-frozen tool-instruction library: ', knowledge_catalog),
             'launch_instruction_lookup': ('Look into the run-frozen launch instruction library: ', launch_catalog)}
# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; no '
                            'discovery or selection.')


def _resources(settings):
    """The old ``OperationalConfiguration.__init__`` checks of the configured resources."""
    resources, information = settings['resources'], settings['initial_information']
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    return resources


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: each request names a bound resource and the API
    service accepts the request. A configuration or request it refuses raises and fails the run: it is not a model
    answer."""
    _resources(ctx.settings)
    for resource_id, request in summary['assignment']['requests'].items():
        if resource_id not in ctx.settings['resources']:
            raise ValueError('execution_resource_not_bound')
        try:
            ctx.services['job_access'].read('validate_assignment', request)
        except AttributeError:
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: '
                'ctx.services["job_access"].read("validate_assignment", request)') from None


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities`` (``OperationalOperations.execute`` returning ``initial_decision_context``):
    the caller-bound resource configuration and the already recorded inventory, with no discovery or selection. Each
    resource lists its configured operations, which only the job-access service knows."""
    settings = ctx.settings
    service = ctx.services['job_access']
    information = []
    for resource_id, config in _resources(settings).items():
        if not hasattr(service, 'capabilities'):
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: '
                'await ctx.services["job_access"].capabilities(resource_id)')
        entries = service.capabilities(resource_id)
        if inspect.isawaitable(entries):
            entries = await entries
        information.append({'resource_id': resource_id, 'resource_kind': 'api', 'availability': 'unknown',
                            'tool_names': [entry['name'] for entry in entries],
                            **{key: deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
                            'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))})
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings['initial_information'])}


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


def _task_text(summary):
    parts = ['TASK', '', 'Choose which permitted concrete execution request to commission on an explicit resource_id.',
             '', 'Permitted requests', '', json.dumps(summary['permitted'], indent=1, sort_keys=True),
             '', 'Launches so far', '', json.dumps(summary['launches'], indent=1, sort_keys=True)]
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


def _context(summary, feedback, ctx):
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    return {'task': _task_text(summary), 'feedback': feedback,
            'execution_assignment': summary['assignment'], 'execution_progress': summary['progress'],
            'execution_resource_capabilities': summary['capabilities']['execution_resource_capabilities'],
            'execution_initial_information': summary['capabilities']['execution_initial_information'],
            'callable_lookups': [{'name': name, 'description': description + ', '.join(
                operation['name'] for operation in catalog())} for name, (description, catalog) in
                sorted(LIBRARIES.items())],
            'requested_information': summary['lookups'], 'completed_action_reports': summary['launches'],
            'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
            'selected_launch_instructions': library.materialize(summary['assignment'].get('launch_instructions')),
            'tools': [{'name': 'execution_capabilities', 'description': CAPABILITIES_DESCRIPTION}],
            'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}


def decide(summary, feedback, ctx):
    """The lookup of the capabilities first (after the configured resources accepted the requests); then one
    selection: a library lookup or the commission of one permitted request, chosen from the capabilities, the
    inventory, the handoffs received so far and their credit."""
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    instructions = GOAL + '\n' + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION
    return ModelRequest('REASONING', instructions, _context(summary, feedback, ctx),
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
