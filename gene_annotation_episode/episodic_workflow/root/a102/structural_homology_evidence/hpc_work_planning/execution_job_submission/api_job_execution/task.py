"""The task: one selected action per unit on the one assigned API service (carried from ``task.py``,
``task_decision.py``, ``instructions.py``, ``action_policy.py``, ``api_operations.py``, ``resource_information.py``,
``decision_inputs.py``, ``execution_contracts.py`` and ``waiting.py``).

Each decision the model selects one of: ``service_operation`` (one operation of the API service's catalog),
``capabilities`` (the caller-bound resource configuration), ``wait`` (only for a service job that continues
remotely: assignment version ``api_service_assignment_v1``), and, when the settings name the libraries,
``launch_instructions`` and ``tool_knowledge`` lookups. The model's ``report_update`` (its current interpretation
for the parent) rides in the arguments of the unit it selects. A selection that fails admission is rejected and
creates no unit. The task offers a unit at every decision and never ends the Episode: the yield controller does.

BLOCKED-ON-JOB-SERVICE. The API service executor (its operation catalog, its execution of one operation with the
credit view and facts it returns, and a wait on a service job) was not in the episode trees; it is the ``job_access``
service of ``LAUNCH_MONITOR_EXTRACT_MECHANICS.md`` and the system does not provide it yet. This file names the
service and the calls it wants (``read('api_catalog', ...)``, ``api_execute(...)``, ``wait_for_job(...)``) and
raises ``NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`` where the service does not offer them. The job
records (the handoff row of a declared job work table) are not defined either: ``write_handoff_record`` raises.
"""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

CHILD_SLOTS = {}
SERVICES = ('job_access',)
WAIT_VERSION = 'api_service_assignment_v1'

GOAL_TEXT = (
    'Carry out the assigned work through {service} using one selected operation each turn. Keep the original '
    'inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, '
    'observations or repair from the actual available operations and received outcomes. Distinguish an immediate '
    'returned response from a service job that continues remotely. Preserve the actual request or job identity and '
    'submission uncertainty; a missing reply does not establish that no job was created. Establish the requested '
    'usable monitoring/results handoff from recorded service facts. The configured controller governs '
    'continuation; verified original handoff completion gives exact zero future credit.')
ACTION_TEXT = (
    ' Each answer selects one action: action=service_operation with operation (a name of the catalog) and '
    'arguments_json (the operation arguments as JSON text); action=capabilities to read the caller-bound resource '
    'configuration and recorded inventory (no discovery, no selection); action=wait with arguments_json naming the '
    'service job and condition, only when a wait is offered. Give report_update, your current interpretation for '
    'the parent, with every answer.')
WAIT_TEXT = (' A wait is offered because this assignment is a service job that continues remotely: use it to let '
             'the job run; it does not establish the job state.')
LOOKUP_ACTIONS = {'launch_instructions': ('launch_instructions_directory', LAUNCH_INSTRUCTIONS, LaunchInstructions),
                  'tool_knowledge': ('tool_knowledge_directory', KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)}
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; '
                            'no discovery or selection.')


def wait_permitted(summary):
    """Old ``action_policy``: ``tool`` always; ``wait`` only for ``api_service_assignment_v1``."""
    return summary['version'] == WAIT_VERSION


def offered_actions(summary, settings):
    names = ['service_operation', 'capabilities']
    if wait_permitted(summary):
        names.append('wait')
    return names + [name for name, (key, _text, _library) in LOOKUP_ACTIONS.items() if key in settings]


def resource_capabilities(settings, resource_id, service):
    """The old first-decision ``execution_resource_capabilities`` for the one assigned resource (no probe)."""
    resource = settings['resources'][resource_id]
    return {'resource_id': resource_id, 'resource_kind': 'api', 'availability': 'unknown', 'service': service,
            'configuration': resource, 'inventory_snapshot': settings['initial_information'][resource_id]}


def output_schema(actions):
    return {'type': 'object', 'additionalProperties': False,
            'required': ['action', 'operation', 'arguments_json', 'report_update'],
            'properties': {'action': {'enum': list(actions)}, 'operation': {'type': 'string'},
                           'arguments_json': {'type': 'string'}, 'report_update': {'type': 'string'}}}


def instructions(summary, settings):
    text = GOAL_TEXT.format(service=summary['service']) + ACTION_TEXT
    if wait_permitted(summary):
        text += WAIT_TEXT
    for name, (key, library_text, _library) in LOOKUP_ACTIONS.items():
        if key in settings:
            text += library_text
    return text


def catalog_of(summary, ctx):
    """The API service executor's operation catalog for this assignment: a recorded read of the service."""
    catalog = ctx.services['job_access'].read('api_catalog', summary['service'], summary['algorithm'],
                                              summary['database'])
    if not isinstance(catalog, dict):
        raise TypeError('api_catalog_must_be_a_mapping_of_operation_to_contract')
    return catalog


def decide(summary, feedback, ctx):
    context = {'goal': GOAL_TEXT.format(service=summary['service']), 'execution_assignment': {
                   name: summary[name] for name in ('version', 'service', 'algorithm', 'database', 'resource_id',
                                                    'request', 'immutable_input_versions')},
               'execution_resource_capabilities': resource_capabilities(ctx.settings, summary['resource_id'],
                                                                        summary['service']),
               'tools': catalog_of(summary, ctx), 'offered_actions': offered_actions(summary, ctx.settings),
               'execution_progress': {'steps': summary['steps'], 'handoff_refs': summary['handoff_refs'],
                                      'result_refs': summary['result_refs'], 'completed': summary['completed']},
               'current_credit': summary['credit'], 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'current_report_update': summary['report_update'], 'feedback': feedback}
    if 'launch_instructions_directory' in ctx.settings:
        library = LaunchInstructions(ctx.settings['launch_instructions_directory'])
        context['launch_instruction_library'] = library.context()
        context['selected_launch_instructions'] = library.materialize(summary['launch_instructions'])
    elif summary['launch_instructions'] is not None:
        raise ValueError('selected_launch_instructions_require_the_launch_instructions_directory_setting')
    if 'tool_knowledge_directory' in ctx.settings:
        context['tool_knowledge'] = ToolKnowledge(ctx.settings['tool_knowledge_directory']).context()
    return ModelRequest('REASONING', instructions(summary, ctx.settings), context,
                        output_schema(offered_actions(summary, ctx.settings)))


def action(response, summary, records, ctx):
    """Admit the model's selection (old ``apply_response`` for a tool or wait): a rejection creates no unit."""
    try:
        Draft202012Validator(output_schema(offered_actions(summary, ctx.settings))).validate(response)
        selected = response['action']
        arguments = json.loads(response['arguments_json']) if response['arguments_json'] else {}
        if selected == 'service_operation':
            if response['operation'] not in catalog_of(summary, ctx):
                raise ValueError('operation_not_in_the_service_catalog:' + response['operation'])
        elif selected in LOOKUP_ACTIONS and not response['operation']:
            raise ValueError('lookup_requires_the_operation_name')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    report = {'report_update': response['report_update']}
    if selected == 'service_operation':
        return ToolCall('service_operation', {
            'operation': response['operation'], 'arguments': arguments, 'resource_id': summary['resource_id'],
            'service': summary['service'], 'algorithm': summary['algorithm'], 'database': summary['database'],
            'scope': summary['scope'], 'request': summary['request'], 'input_refs': summary['input_refs'],
            'immutable_input_versions': summary['immutable_input_versions'], **report})
    if selected == 'capabilities':
        return ToolCall('capabilities', {'resource_id': summary['resource_id'], 'service': summary['service'],
                                         **report})
    if selected == 'wait':
        return ToolCall('wait', {'resource_id': summary['resource_id'], 'service': summary['service'],
                                 'condition': arguments, 'handoff_refs': summary['handoff_refs'], **report})
    return ToolCall(selected, {'name': response['operation'], 'lookup': arguments, **report})


def required_member(service, member):
    """The service's operation, or the explicit block when the system does not provide it yet."""
    call = getattr(service, member, None)
    if call is None:
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member)
    return call


def write_handoff_record(store, reply, operation_key):
    """The handoff record of the job: a row of a declared job ledger work table, written through ``store``.

    Wanted call: ``store.table(JOB_LEDGER).put({'job': ..., 'event': 'handoff', 'at': ..., 'detail': ...,
    'source_ref': ...})`` and ``api_job_receipts.ApiJobReceipts(...).publish(...)`` for the retained response.
    Neither the job record kind nor a custody-aware receipts library exists yet.
    """
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of a declared job ledger '
                              'work table)')


def service_operation(arguments, ctx):
    """One operation of the API service, through the ``job_access`` service, idempotent on the operation key."""
    execute = required_member(ctx.services['job_access'], 'api_execute')
    try:
        reply = execute(resource_id=arguments['resource_id'], service=arguments['service'],
                        algorithm=arguments['algorithm'], database=arguments['database'],
                        operation=arguments['operation'], arguments=arguments['arguments'],
                        request=arguments['request'], scope=arguments['scope'],
                        input_refs=arguments['input_refs'],
                        immutable_input_versions=arguments['immutable_input_versions'],
                        handoff_unit=ctx.settings['handoff_unit'],
                        acquired_record_unit=ctx.settings['acquired_record_unit'], key=ctx.operation_key)
    except NotImplementedError:
        raise
    except Exception as error:      # noqa: BLE001 - an operation that raised is a failed outcome that still earns
        return {**failure_outcome(ctx.store, error, category='service_operation',
                                  cause_code='api_operation_raised'), 'operation': arguments['operation'],
                'event': None, 'credit': None, 'completed': False, 'handoff_refs': [], 'result_refs': []}
    event = reply['event']
    handoff_refs = write_handoff_record(ctx.store, reply, ctx.operation_key) \
        if event['handoff_ready'] or event['native_handle'] is not None else []
    return {'operation': arguments['operation'], 'status': reply['status'], 'event': event,
            'feedback': reply['feedback'], 'credit': reply['credit'], 'completed': reply['facts']['execution_completed'],
            'handoff_refs': handoff_refs, 'result_refs': list(reply['facts']['execution_result_refs'])}


def capabilities(arguments, ctx):
    """The old ``execution.capabilities`` operation: the resource configuration and recorded inventory."""
    return {'operation': 'execution.capabilities', 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False,
            'capabilities': resource_capabilities(ctx.settings, arguments['resource_id'], arguments['service'])}


async def wait(arguments, ctx):
    """Wait on the service job (old ``waiting.py`` / the ``wait`` action), through the ``job_access`` service."""
    wait_for_job = required_member(ctx.services['job_access'], 'wait_for_job')
    reply = await wait_for_job(resource_id=arguments['resource_id'], service=arguments['service'],
                               condition=arguments['condition'], handoff_refs=arguments['handoff_refs'],
                               key=ctx.operation_key)
    return {'operation': 'wait', 'status': reply['status'], 'event': reply['event'], 'feedback': None,
            'credit': None, 'completed': False}


def launch_instructions(arguments, ctx):
    """A lookup in the run-frozen launch instruction library (old ``launch.instructions.*`` operations)."""
    result = LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['name'],
                                                                                       arguments['lookup'])
    return {'operation': arguments['name'], 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False, 'result': result}


def tool_knowledge(arguments, ctx):
    """A lookup in the run-frozen tool knowledge library (old ``knowledge.*`` operations)."""
    result = ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['name'],
                                                                           arguments['lookup'])
    return {'operation': arguments['name'], 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False, 'result': result}


TOOLS = {'service_operation': service_operation, 'capabilities': capabilities, 'wait': wait,
         'launch_instructions': launch_instructions, 'tool_knowledge': tool_knowledge}
