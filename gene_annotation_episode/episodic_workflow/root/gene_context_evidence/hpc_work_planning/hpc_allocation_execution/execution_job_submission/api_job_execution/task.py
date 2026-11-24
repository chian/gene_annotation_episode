"""The task: carry out the assigned API job through the job-access service, one selected operation per unit.

Carried from the old ``task.py``, ``task_state.py``, ``action_policy.py``, ``operations.py``, ``goal.py``,
``instructions.py``, ``decision_inputs.py``, ``decision_state.py``, ``decision_presentation.py`` (``_task`` and
``_steering``) and ``decision_contracts.py``. One unit is one tool call: the first is the lookup of the bound
resource's capabilities (``api_capabilities``, offered by the task itself); after it the model selects one
operation each turn. The task always offers a unit and never ends the Episode: only the yield controller does.
The episode has no child. The wait of the old ``action_policy`` (only for a remote service job,
``api_service_assignment``) is the ``wait_for_service_job`` tool. This file is a private copy: it imports
nothing from another episode.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service. The old ``APIServiceExecution`` (``api_execution``) is not in
the library and no service wraps it. The calls the episode wants are named in the tools below."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL
from .messages.read_from_parent import ASSIGNMENT_PROPERTIES

CHILD_SLOTS = {}
SERVICES = ('job_access',)
SERVICE_JOB = 'api_service_assignment'

TEXT = {'type': 'string', 'minLength': 1}
OPEN_RECORD = {'type': 'object'}
DESCRIPTIONS = {
    'api_capabilities': 'Read the actual configured operations of the bound API resource; no discovery or selection.',
    'api_operation': ('Perform one operation of the assigned API service (name starting with api.), over the '
                      'original assignment: a preparation, a service request, an observation or a repair. '
                      'Returns the recorded service facts, the handoff records and the acquired records.'),
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


def _assignment(summary):
    return {name: summary[name] for name in ASSIGNMENT_PROPERTIES if name in summary}


def _outcome(reply, ctx):
    """One unit's outcome from a job-access reply: the reply's facts and identities, the records it produced
    written through custody, and the credit units the episode's credit reads from the summary (credit has no
    settings)."""
    store = ctx.store
    handoff_refs = [store.artifact(json.dumps(handoff, sort_keys=True), 'application/json')
                    for handoff in reply['handoffs']]
    result_refs = [store.artifact(item['content'], item['media_type']) for item in reply['artifacts']]
    return {'status': reply['status'], 'result': reply['result'], 'feedback': reply['feedback'],
            'facts': reply['facts'], 'handoff_refs': handoff_refs, 'result_refs': result_refs,
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
    """Wanted call: ``ctx.services['job_access'].api_capabilities(resource_id)`` (the configured operations of the
    API resource, no probe)."""
    return {'capabilities': ctx.services['job_access'].api_capabilities(arguments['resource_id'])}


def api_operation(arguments, ctx):
    """Wanted call: ``ctx.services['job_access'].api_operation(assignment, operation, operation_arguments,
    held, key=ctx.operation_key)``. It must be idempotent on the key: a submission that was made under the key
    is returned, not made again (``ctx.resumed`` says an earlier attempt began). A failed, invalid or
    unavailable reply is a returned outcome and enters the iterator like any other."""
    reply = ctx.services['job_access'].api_operation(arguments['assignment'], arguments['operation'],
                                                     arguments['arguments'], _held(arguments, ctx),
                                                     key=ctx.operation_key)
    return _outcome(reply, ctx)


async def wait_for_service_job(arguments, ctx):
    """Wanted call: ``await ctx.services['job_access'].api_wait(assignment, handle, after_cursor,
    reconsider_at)`` (the service's state change or its reconsideration time)."""
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


def _offered(summary, settings):
    """The operations offered now. The wait only for a remote service job (the old ``permitted_common_actions``)."""
    names = ['api_operation']
    if summary['version'] == SERVICE_JOB:
        names.append('wait_for_service_job')
    if 'tool_knowledge_directory' in settings:
        names.append('knowledge_lookup')
    if 'launch_instructions_directory' in settings:
        names.append('launch_instruction_lookup')
    return names


def _schema(offered):
    branches = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                 'properties': {'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': deepcopy(ARGUMENTS[name])}} for name in offered]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def _instructions(settings):
    text = GOAL
    if 'tool_knowledge_directory' in settings:
        text += KNOWLEDGE_INSTRUCTIONS
    if 'launch_instructions_directory' in settings:
        text += LAUNCH_INSTRUCTIONS
    return text


def _context(summary, feedback, ctx):
    """The old TASK and STEERING presentation, as the named sections of one mapping."""
    offered = _offered(summary, ctx.settings)
    task = {'assigned_job': summary['message'],
            'selected_api_work': {name: summary[name] for name in ('resource_id', 'service', 'endpoint')},
            'parent_constraints': summary['constraints'],
            'configured_resource': summary['capabilities'],
            'exact_assigned_scientific_request': summary['request'] if 'request' in summary else {
                name: summary[name] for name in ('subject_ref', 'algorithm', 'database', 'parameters', 'page_size')
                if name in summary},
            'callable_operations': [{'name': name, 'description': DESCRIPTIONS[name],
                                     'arguments_schema': ARGUMENTS[name]} for name in offered],
            'selected_launch_instructions': summary.get('launch_instructions')}
    steering = {'own_action_yields': summary.get('action_yields'),
                'original_handoff_completion': summary['execution_completed'],
                'recorded_own_api_outcomes': summary['api_received_progress'],
                'latest_own_action': summary['last_local_outcome'],
                'returned_feedback': summary['feedback'],
                'requested_information': summary['lookups'],
                'time_accounting': time_accounting(ctx.clock.progress_time),
                'rejection_feedback': feedback}
    context = {'TASK': task, 'STEERING': steering}
    if 'tool_knowledge_directory' in ctx.settings:
        context['tool_knowledge'] = ToolKnowledge(ctx.settings['tool_knowledge_directory']).context()
    if 'launch_instructions_directory' in ctx.settings:
        context['launch_instruction_library'] = LaunchInstructions(ctx.settings['launch_instructions_directory']).context()
    return context


def decide(summary, feedback, ctx):
    if summary['capabilities'] is None:
        return ToolCall('api_capabilities', {'resource_id': summary['resource_id']})
    return ModelRequest('REASONING', _instructions(ctx.settings), _context(summary, feedback, ctx),
                        generation_schema(_schema(_offered(summary, ctx.settings))))


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
    schema = _schema(_offered(summary, ctx.settings))
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
    envelope = {'assignment': _assignment(summary), 'input_refs': summary['input_refs']}
    if tool == 'api_operation':
        return ToolCall(tool, {**envelope, 'operation': given['operation'], 'arguments': given['arguments']})
    if tool == 'wait_for_service_job':
        return ToolCall(tool, {**envelope, 'arguments': given})
    return ToolCall(tool, given)
