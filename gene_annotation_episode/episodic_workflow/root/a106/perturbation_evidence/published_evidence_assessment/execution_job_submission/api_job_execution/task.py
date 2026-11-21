"""The task: carry out the assigned API job through the job-access service, one selected operation per unit.

Carried from the old ``task.py`` (``OperationalTask``), ``task_decision.py``, ``task_instructions.py``,
``decision_inputs.py``, ``decision_state.py``, ``decision_presentation.py``, ``execution_operations.py``
(``_api_operation_catalog``, ``capabilities``, ``_resource_information``, ``catalog``, ``execute``),
``execution_state.py`` (``initialize``) and ``waiting.py`` (``_execute_selected_wait``). One unit is one tool
call: the first is the lookup of the bound resource's capabilities and initial inventory (``api_capabilities``,
offered by the task itself); after it the model selects one operation each turn. The task always offers a unit
and never ends the Episode: only the yield controller does. The episode has no child. The old ``wait`` (permitted
by ``permitted_common_actions``) is the ``wait_for_service_job`` tool. The old decision exchange, report update,
redelivery, restore and checkpoint code are system machinery and are not carried. This file is a private copy:
it imports nothing from another episode.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service. The old ``APIServiceExecution`` (``api_execution``) lived in
the old shared root; the library has no copy and no service wraps it. The calls the episode wants are named in the
tools below."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .messages.read_from_parent import OLD_PROPERTIES

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TEXT = {'type': 'string', 'minLength': 1}
OPEN_RECORD = {'type': 'object'}
INSTRUCTION_TEMPLATE = (
    'Carry out the assigned work through {service} using one selected operation each turn. Keep the original '
    'inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, '
    'observations or repair from the actual available operations and received outcomes. Distinguish an immediate '
    'returned response from a service job that continues remotely. Preserve the actual request or job identity and '
    'submission uncertainty; a missing reply does not establish that no job was created. Establish the requested '
    'usable monitoring/results handoff from recorded service facts. The configured controller governs continuation; '
    'verified original handoff completion gives exact zero future credit.')
DESCRIPTIONS = {
    'api_capabilities': ('Read the actual caller-bound configuration of the bound API resource and its already '
                         'recorded inventory; no discovery or selection.'),
    'api_operation': ('Perform one operation of the assigned API service (name starting with api.), over the '
                      'original assignment: a preparation, a service request, an observation or a repair. '
                      'Returns the recorded service facts, the handoff, support and result records.'),
    'wait_for_service_job': ('Give a service job that continues remotely time to change state. Waiting earns no '
                             'credit by itself; it only reports what the service then records.'),
    'knowledge_lookup': 'Look into the run-frozen tool-instruction library (knowledge.search, entry, read).',
    'launch_instruction_lookup': ('Look into the run-frozen launch instruction library (launch.instructions.search, '
                                  'entry, read, select).'),
}
ARGUMENTS = {
    'api_capabilities': {'type': 'object', 'additionalProperties': False, 'required': ['resource_id'],
                         'properties': {'resource_id': TEXT}},
    'api_operation': {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments'],
                      'properties': {'operation': {**TEXT, 'pattern': '^api\\.'}, 'arguments': OPEN_RECORD}},
    'wait_for_service_job': {'type': 'object', 'additionalProperties': False,
                             'required': ['handle', 'after_cursor', 'reconsider_at'],
                             'properties': {'handle': TEXT, 'after_cursor': {'type': 'integer', 'minimum': 0},
                                            'reconsider_at': {'type': ['string', 'null']}}},
    'knowledge_lookup': {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments'],
                         'properties': {'operation': {'type': 'string',
                                                      'enum': [item['name'] for item in knowledge_catalog()]},
                                        'arguments': OPEN_RECORD}},
    'launch_instruction_lookup': {'type': 'object', 'additionalProperties': False,
                                  'required': ['operation', 'arguments'],
                                  'properties': {'operation': {'type': 'string',
                                                               'enum': [item['name'] for item in launch_catalog()]},
                                                 'arguments': OPEN_RECORD}},
}
OFFERED = ('api_operation', 'wait_for_service_job', 'knowledge_lookup', 'launch_instruction_lookup')


def _assignment(summary):
    return {name: summary[name] for name in OLD_PROPERTIES if name in summary}


def _artifact_refs(items, ctx):
    return [ctx.store.artifact(item['content'], item['media_type']) for item in items]


def _outcome(reply, ctx):
    """One unit's outcome from a job-access reply: the reply's facts and identities, the records it produced
    written through custody, and the credit units the episode's credit reads from the summary (credit has no
    settings, no services)."""
    return {'status': reply['status'], 'result': reply['result'], 'feedback': reply['feedback'],
            'facts': reply['facts'], 'events': reply['events'],
            'handoff_refs': _artifact_refs(reply['handoffs'], ctx),
            'support_refs': _artifact_refs(reply['support_receipts'], ctx),
            'result_refs': _artifact_refs(reply['artifacts'], ctx),
            'handoff_established': reply['handoff_established'],
            'execution_completed': reply['execution_completed'], 'job_identity': reply['job_identity'],
            'request_identity': reply['request_identity'], 'submission_outcome': reply['submission_outcome'],
            'credit_units': {'handoff_unit': ctx.settings['handoff_unit'],
                             'acquired_record_unit': ctx.settings['acquired_record_unit']}}


def _held(arguments, ctx):
    """The held records the operation reads: the ones the parent passed and the ones the model named."""
    refs = list(dict.fromkeys([*arguments['input_refs'], *_named_refs(arguments['arguments'])]))
    return {ref: ctx.store.get(ref) for ref in refs}


def api_capabilities(arguments, ctx):
    """Wanted call: ``ctx.services['job_access'].api_capabilities(resource_id)`` (old ``capabilities`` and
    ``_resource_information``: availability, tool names, service, base_url of the configured API resource, no
    probe). The initial inventory is the episode's setting ``initial_information`` (old ``initial_information``)."""
    resource_id = arguments['resource_id']
    return {'capabilities': ctx.services['job_access'].api_capabilities(resource_id),
            'inventory_snapshot': ctx.settings['initial_information'].get(resource_id)}


def api_operation(arguments, ctx):
    """Wanted call: ``ctx.services['job_access'].api_operation(assignment, operation, operation_arguments,
    held, key=ctx.operation_key)`` (old ``api_execution.execute``). It must be idempotent on the key: a
    submission that was made under the key is returned, not made again (``ctx.resumed`` says an earlier attempt
    began). A failed, invalid or unavailable reply is a returned outcome and enters the iterator like any other."""
    reply = ctx.services['job_access'].api_operation(arguments['assignment'], arguments['operation'],
                                                     arguments['arguments'], _held(arguments, ctx),
                                                     key=ctx.operation_key)
    return _outcome(reply, ctx)


async def wait_for_service_job(arguments, ctx):
    """Wanted call: ``await ctx.services['job_access'].api_wait(assignment, handle, after_cursor,
    reconsider_at)`` (old ``perform_selected_wait``: the service's state change or its reconsideration time)."""
    reply = await ctx.services['job_access'].api_wait(arguments['assignment'], arguments['arguments']['handle'],
                                                      arguments['arguments']['after_cursor'],
                                                      arguments['arguments']['reconsider_at'])
    return _outcome(reply, ctx)


def knowledge_lookup(arguments, ctx):
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                    arguments['arguments'])


TOOLS = {'api_capabilities': api_capabilities, 'api_operation': api_operation,
         'wait_for_service_job': wait_for_service_job, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _arguments_schema(name, summary):
    """The arguments of a tool now. ``api_operation`` also names which of the input list's unconsumed records it
    hands to the service (nano-graphrag input list: an item handed out is consumed and offered no more); a consumed
    record cannot be named."""
    schema = deepcopy(ARGUMENTS[name])
    if name == 'api_operation':
        unconsumed = list(summary['input_list'])
        schema['required'] = [*schema['required'], 'input_refs']
        schema['properties']['input_refs'] = (
            {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': unconsumed}} if unconsumed
            else {'type': 'array', 'maxItems': 0})
    return schema


def _schema(summary):
    branches = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                 'properties': {'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _arguments_schema(name, summary)}} for name in OFFERED]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def _instructions(summary):
    return INSTRUCTION_TEMPLATE.format(service=summary['service']) + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS


def _context(summary, feedback, ctx):
    """The old decision context of this episode as named sections of one mapping."""
    context = {
        'goal': INSTRUCTION_TEMPLATE.format(service=summary['service']),
        'execution_assignment': _assignment(summary),
        'assigned_job': summary['message'],
        'execution_resource_capabilities': summary['capabilities'],
        'execution_initial_information': summary['inventory_snapshot'],
        'execution_progress': summary['facts'],
        'api_service': summary['service'],
        'api_request': summary['request'],
        'api_received_progress': summary['api_received_progress'],
        'api_execution_completed': summary['execution_completed'],
        'callable_operations': [{'name': name, 'description': DESCRIPTIONS[name], 'arguments_schema': _arguments_schema(name, summary)}
                                for name in OFFERED],
        'input_list': summary['input_list'],
        'consumed_input_refs': summary['consumed_input_refs'],
        'selected_launch_instructions': summary.get('launch_instructions'),
        'action_yields': summary.get('action_yields'),
        'last_local_outcome': summary['last_local_outcome'],
        'returned_feedback': summary['feedback'],
        'requested_information': summary['lookups'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
        'rejection_feedback': feedback,
        'tool_knowledge': ToolKnowledge(ctx.settings['tool_knowledge_directory']).context(),
        'launch_instruction_library': LaunchInstructions(ctx.settings['launch_instructions_directory']).context()}
    return context


def decide(summary, feedback, ctx):
    if summary['capabilities'] is None:
        return ToolCall('api_capabilities', {'resource_id': summary['resource_id']})
    return ModelRequest('REASONING', _instructions(summary), _context(summary, feedback, ctx),
                        generation_schema(_schema(summary)))


def _named_refs(value):
    """The record references a model-built value names: values under ``ref``, ``..._ref`` and ``..._refs``."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                found.append(child)
            elif name.endswith('_refs'):
                found.extend(child)
            else:
                found.extend(_named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_named_refs(child))
    return found


def action(response, summary, records, ctx):
    schema = _schema(summary)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
        selection = decoded['selection']
        unheld = [ref for ref in _named_refs(selection['arguments']) if not records.holds(ref)]
        if unheld:
            raise ValueError('record_not_held:' + ','.join(unheld))
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    tool, given = selection['tool'], selection['arguments']
    # The tool is handed no summary: the original assignment and the passed records ride in its arguments.
    # The records handed to the service are the unconsumed input records the operation names: they are consumed.
    envelope = {'assignment': _assignment(summary)}
    if tool == 'api_operation':
        return ToolCall(tool, {**envelope, 'input_refs': given['input_refs'], 'operation': given['operation'],
                               'arguments': given['arguments']})
    if tool == 'wait_for_service_job':
        return ToolCall(tool, {**envelope, 'input_refs': [], 'arguments': given})
    return ToolCall(tool, given)
