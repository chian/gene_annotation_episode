"""The task: acquire the original selected execution results through the original handoff, one operation per unit.

Carried from the old ``task.py`` (``OperationalTask``), ``task_decision.py``, ``task_instructions.py``,
``decision_inputs.py``, ``decision_state.py``, ``decision_presentation.py``, ``execution_operations.py``
(``_api_operation_catalog`` (the result catalog because a target exists), ``catalog``, ``execute`` (the local
name and argument check before the service call), ``capabilities``), ``execution_state.py`` (``initialize``,
``_target``) and ``waiting.py`` (``_execute_selected_wait``). One unit is one tool call: the first is the lookup
of the original target and the result catalog (``result_catalog``, offered by the task itself: the old
``catalog(context)`` re-validated the selector against the target and returned the service's real status and
result read operations); after it the model selects one operation each turn. The task always offers a unit and
never ends the Episode: only the yield controller does. The episode has no child. The old ``wait`` (permitted by
``permitted_common_actions``) is the ``wait_for_service_job`` tool. The old decision exchange, report update,
redelivery, restore and checkpoint code are system machinery and are not carried. This file is a private copy:
it imports nothing from another episode.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service and the job ledger handoff record. The old
``APIServiceExecution`` (``api_execution``) and ``ExecutionProgressProvider`` (``job_progress_provider``) lived
in the old shared root; the library has no copy and no service wraps them, and the handoff row the launching
child writes has no declared table. The calls the episode wants are named in the tools below; the target read
(``handoff_target``) raises where it is reached."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import (
    checked)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import (
    time_accounting, yield_table)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TEXT = {'type': 'string', 'minLength': 1}
OPEN_RECORD = {'type': 'object'}
DESCRIPTIONS = {
    'result_catalog': ('Read the original target behind the handoff and the status and result read operations the '
                       'original service offers for the selector; no discovery or selection.'),
    'api_result_operation': ('Perform one status or result read operation of the original service, named in the '
                             'result catalog, with arguments that satisfy its input schema. Returns the recorded '
                             'service facts and the acquired result records, partial bytes and native scores kept.'),
    'wait_for_service_job': ('Give the original service job time to change state. Waiting earns no credit by '
                             'itself; it only reports what the service then records.'),
    'knowledge_lookup': 'Look into the run-frozen tool-instruction library (knowledge.search, entry, read).',
    'launch_instruction_lookup': ('Look into the run-frozen launch instruction library (launch.instructions.search, '
                                  'entry, read, select).'),
}
ARGUMENTS = {
    'api_result_operation': {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments'],
                             'properties': {'operation': TEXT, 'arguments': OPEN_RECORD}},
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
OFFERED = ('api_result_operation', 'wait_for_service_job', 'knowledge_lookup', 'launch_instruction_lookup')


def handoff_target(handoff_ref, ctx):
    """The original target behind the handoff the launching child wrote (old
    ``job_progress_provider.targets.read_target(handoff_ref, scope)``).

    BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call:
    ``ctx.store.table(JOB_LEDGER).get(handoff_ref)`` read as the execution target (handle, resource_id,
    resource_kind, execution_id, assignment). No job record kind or work table is declared yet."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call: '
                              'ctx.store.table(JOB_LEDGER).get(' + repr(handoff_ref) + ')')


def _artifact_refs(items, ctx):
    return [ctx.store.artifact(item['content'], item['media_type']) for item in items]


def _credit_units(ctx):
    return {'handoff_unit': ctx.settings['handoff_unit'],
            'acquired_record_unit': ctx.settings['acquired_record_unit']}


def _outcome(reply, ctx):
    """One unit's outcome from a job-access reply: the reply's facts and identities, the records it produced
    written through custody, and the credit units the episode's credit reads from the summary (credit has no
    settings, no services). An invalid, failed or unavailable reply is an outcome like any other."""
    return {'status': reply['status'], 'result': reply['result'], 'feedback': reply['feedback'],
            'facts': reply['facts'],
            'handoff_refs': _artifact_refs(reply['handoffs'], ctx),
            'support_refs': _artifact_refs(reply['support_receipts'], ctx),
            'result_refs': _artifact_refs(reply['artifacts'], ctx),
            'handoff_identities': reply['handoff_identities'], 'result_identities': reply['result_identities'],
            'execution_completed': reply['execution_completed'], 'credit_units': _credit_units(ctx)}


def _invalid(code, ctx):
    """The old ``_outcome(code=...)``: a selection or arguments the catalog does not admit."""
    return {'status': 'invalid', 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': code}, 'facts': {},
            'handoff_refs': [], 'support_refs': [], 'result_refs': [], 'handoff_identities': [],
            'result_identities': [], 'execution_completed': False, 'credit_units': _credit_units(ctx)}


def result_catalog(arguments, ctx):
    """Wanted calls: ``ctx.services['job_access'].api_result_catalog(target, selector)`` (old
    ``service.result_catalog(request, selector)`` through ``api_execution.catalog``; it validates the selector
    against the target, old ``validate_result_selector``), ``.api_describe_target(target, selector)`` (old
    ``targets.describe_target``), ``.api_capabilities(resource_id)`` (old ``capabilities``) and
    ``.api_handoff_identity(target)`` (the identity of the original handoff, which earns nothing)."""
    target = handoff_target(arguments['handoff_ref'], ctx)
    job = ctx.services['job_access']
    selector = arguments['selector']
    return {'target': target, 'catalog': job.api_result_catalog(target, selector),
            'target_description': job.api_describe_target(target, selector),
            'capabilities': job.api_capabilities(target['resource_id']),
            'initial_handoff_identities': [job.api_handoff_identity(target)],
            'inventory_snapshot': ctx.settings['initial_information'], 'credit_units': _credit_units(ctx)}


def api_result_operation(arguments, ctx):
    """Wanted call: ``ctx.services['job_access'].api_result_operation(target, selector, operation,
    operation_arguments, key=ctx.operation_key)`` (old ``api_execution.execute``). It must be idempotent on the
    key. As in the old ``execute``, the name is checked against the catalog (``execution_operation_not_available``)
    and the arguments against its input schema (``invalid_execution_operation_arguments``) before the call, and a
    ``ValueError`` or ``TypeError`` is an invalid outcome."""
    target = handoff_target(arguments['handoff_ref'], ctx)
    job = ctx.services['job_access']
    try:
        catalog = {entry['name']: entry for entry in job.api_result_catalog(target, arguments['selector'])}
        if arguments['operation'] not in catalog:
            raise ValueError('execution_operation_not_available')
        given = checked(arguments['arguments'], catalog[arguments['operation']]['input_schema'],
                        'invalid_execution_operation_arguments')
        reply = job.api_result_operation(target, arguments['selector'], arguments['operation'], given,
                                         key=ctx.operation_key)
    except (ValueError, TypeError) as error:
        return _invalid(str(error), ctx)
    return _outcome(reply, ctx)


async def wait_for_service_job(arguments, ctx):
    """Wanted call: ``await ctx.services['job_access'].api_wait(target, handle, after_cursor, reconsider_at)``
    (old ``perform_selected_wait``: the service's state change or its reconsideration time)."""
    target = handoff_target(arguments['handoff_ref'], ctx)
    reply = await ctx.services['job_access'].api_wait(target, arguments['arguments']['handle'],
                                                      arguments['arguments']['after_cursor'],
                                                      arguments['arguments']['reconsider_at'])
    return _outcome(reply, ctx)


def knowledge_lookup(arguments, ctx):
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                    arguments['arguments'])


TOOLS = {'result_catalog': result_catalog, 'api_result_operation': api_result_operation,
         'wait_for_service_job': wait_for_service_job, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _schema(summary):
    branches = []
    for name in OFFERED:
        arguments = deepcopy(ARGUMENTS[name])
        if name == 'api_result_operation':
            arguments['properties']['operation'] = {'type': 'string',
                                                    'enum': [entry['name'] for entry in summary['catalog']]}
        branches.append({'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                         'properties': {'kind': {'type': 'string', 'const': 'tool'},
                                        'tool': {'type': 'string', 'const': name}, 'arguments': arguments}})
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def _instructions():
    return GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS


def _context(summary, feedback, ctx):
    """The old decision context of this episode as named sections of one mapping."""
    return {
        'goal': GOAL,
        'execution_assignment': {name: summary[name] for name in ('version', 'handoff_ref', 'selector')},
        'execution_resource_capabilities': summary['capabilities'],
        'execution_initial_information': summary['inventory_snapshot'],
        'execution_progress': summary['facts'],
        'execution_target': summary['target'],
        'execution_target_description': summary['target_description'],
        'execution_completed': summary['execution_completed'],
        'callable_operations': [{'name': name, 'description': DESCRIPTIONS[name], 'arguments_schema': ARGUMENTS[name]}
                                for name in OFFERED],
        'result_catalog': summary['catalog'],
        'action_yields': summary.get('action_yields'),
        'last_local_outcome': summary['last_local_outcome'],
        'returned_feedback': summary['feedback'],
        'requested_information': summary['lookups'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
        'rejection_feedback': feedback,
        'tool_knowledge': ToolKnowledge(ctx.settings['tool_knowledge_directory']).context(),
        'launch_instruction_library': LaunchInstructions(ctx.settings['launch_instructions_directory']).context()}


def decide(summary, feedback, ctx):
    if summary['catalog'] is None:
        return ToolCall('result_catalog', {'handoff_ref': summary['handoff_ref'], 'selector': summary['selector']})
    return ModelRequest('REASONING', _instructions(), _context(summary, feedback, ctx),
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
    # The tool is handed no summary: the original handoff and selector ride in its arguments.
    envelope = {'handoff_ref': summary['handoff_ref'], 'selector': summary['selector']}
    if tool == 'api_result_operation':
        return ToolCall(tool, {**envelope, 'operation': given['operation'], 'arguments': given['arguments']})
    if tool == 'wait_for_service_job':
        return ToolCall(tool, {**envelope, 'arguments': given})
    return ToolCall(tool, given)
