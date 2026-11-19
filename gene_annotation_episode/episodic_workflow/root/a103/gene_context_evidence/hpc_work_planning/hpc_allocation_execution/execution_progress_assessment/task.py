"""The task: observe the assigned execution target, read what was delivered, read one retained log window, wait for
native job events, or commission a monitor for one exposed direct dependency. One unit is one such action.

Carried from the old ``progress_operations.py`` (``ProgressOperations.catalog`` and ``execute``), ``task.py``,
``task_decision.py``, ``decision_inputs.py``, ``task_instructions.py`` and ``waiting.py``. The task always offers a
unit and never ends the Episode: only the yield controller does. The old ``wait`` on pending in-process children,
``redeliver_report``, the report update the model wrote and the decision-exchange lookups are not carried (the
return's facts are recorded facts: ``messages/final_to_parent.py``). The old wait on native job events is the tool
``wait_for_events``.

The old tool names ``progress.observe``, ``progress.read`` and ``progress.log`` are ``progress_observe``,
``progress_read`` and ``progress_log`` (a tool name is a lowercase identifier).

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``),
``launch_instructions_directory`` and ``knowledge_library_directory`` (optional, the old workflow's launch and
tool-knowledge libraries), ``execution_expectations`` (the old execution-expectation binding; when present the
estimate table is needed, see ``execution_expectations``).

BLOCKED-ON-JOB-SERVICE: the progress provider (``observe_progress``, ``read_progress``,
``describe_progress_target``) and the native event ledger are not wrapped as services. ``observe_target``,
``describe_target`` and ``snapshot_read`` name the service and the call they want and raise where they are
reached."""
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.readers.gene_context_evidence.source_bytes import (
    source_window)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import BINDING_PATH, GOAL
from .messages.read_from_parent import FIELD_OPTIONS

CHILD_SLOTS = {'monitor': BINDING_PATH}
SERVICES = ('job_access', 'native_events')

ACTION_BOUNDARY = """Do not emit a stop action or invent a
turn budget, approval review, quality gate, experiment, term or observation.
"""

RESOURCE_ESTIMATE_GUIDANCE = """resource_tool_estimates, when supplied, describe expected execution time and
configured resources for the declared execution classes. Use these expectations
with your own yield estimate and prior outcomes to choose useful work. A timing
experiment earns monitoring credit for timing information learned and updates
execution expectations. Missing history means duration is unknown. Job elapsed
time and the duration of an own monitoring action are distinct measurements.
"""

HOST_EXECUTION_GUIDANCE = """Do not execute native provider tools. The host executes your selected action.
"""

NATIVE_EVENT_GUIDANCE = """
Select wait_for_events to wait for a native notification target assigned or actually received by this episode. A
target is registration metadata, not proof that submission succeeded. Its state_changed event means the original
service exit receipt was committed; the service may still be closing, so this does not establish result readiness.
after_cursor records an event cursor actually received, initially zero. Waiting only reports readiness and earns no
credit. No event probability, gain or scientific credit follows from registration or passing time alone."""

_TEXT = {'type': 'string', 'minLength': 1}
_FIELDS = {'type': 'array', 'items': {'enum': list(FIELD_OPTIONS)}, 'uniqueItems': True}
_TYPES = {'type': 'array', 'uniqueItems': True, 'items': {'enum': sorted(RECORD_SCHEMAS)}}
EVENT_CONDITION = obj({'version': {'const': 'event_condition_v1'},
                       'events': {'type': 'array', 'items': obj({'handle': _TEXT, 'event': _TEXT,
                                                                  'after_cursor': {'type': 'integer', 'minimum': 0}})},
                       'reconsider_at': {'type': ['string', 'null']}})


def describe_target(ctx, target_handle):
    """What the progress provider says of the assigned target (the old ``describe_progress_target``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read('describe_progress_target',
    target_handle)`` (a recorded read of a decision)."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              ".read('describe_progress_target', target_handle)")


def execution_expectations(ctx):
    """The old ``decision_inputs`` execution expectations and resource estimates for role ``monitor``, which the old
    workflow added only when an execution-expectation binding was configured.

    BLOCKED-ON-JOB-SERVICE: estimate_table (README 5 item 19, not built); wanted call:
    ``ctx.services['estimate_table'].read('execution_expectations', 'monitor')``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ctx.services['estimate_table']"
                              ".read('execution_expectations', 'monitor')")


async def observe_target(ctx, assignment, fields):
    """One observation of the assigned target (the old ``services.observe_progress``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_progress(
    target_handle, fields, permitted_committed_record_types=..., operation_key=ctx.operation_key)``, idempotent on
    ``ctx.operation_key``; it returns the ``progress_snapshot_v1`` record of the delivered observation."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await ctx.services['job_access']"
                              '.observe_progress(assignment[\'target_handle\'], fields, '
                              "permitted_committed_record_types=assignment['permitted_committed_record_types'], "
                              'operation_key=ctx.operation_key)')


def snapshot_read(ctx, reference):
    """A received observation the summary holds no snapshot of (the old ``services.read_progress``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read_progress(reference)``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              '.read_progress(reference)')


def _invalid(error):
    detail = getattr(error, 'detail', None)
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'progress_refs': [],
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': detail} if detail else {})}}


def _committed(ctx, assignment, snapshot):
    """The committed records of an observation whose type the parent permitted."""
    return [ref for ref in snapshot['committed_record_refs']
            if ctx.store.get(ref)['record_type'] in assignment['permitted_committed_record_types']]


def _received_snapshot(ctx, arguments):
    if not arguments['received']:
        raise ContractError('monitor_progress_not_received')
    return snapshot_read(ctx, arguments['progress_ref']) if arguments['snapshot'] is None else arguments['snapshot']


async def progress_observe(arguments, ctx):
    assignment, fields = arguments['assignment'], arguments['requested_fields']
    try:
        if not set(fields) <= set(assignment['requested_fields']):
            raise ContractError('monitor_observation_expands_requested_fields')
        if 'native_operation' in arguments:
            raise NotImplementedError('native_observation_options_not_placed: the old shared-root '
                                      'native_observation_options(native_operation, context) has no copy')
        snapshot = await observe_target(ctx, assignment, fields)
        committed = _committed(ctx, assignment, snapshot)
    except ContractError as error:
        return _invalid(error)
    model_arguments = {key: value for key, value in arguments.items() if key != 'assignment'}
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': 'progress_observe',
                                                    'arguments': model_arguments}),
            'record_refs': committed, 'changed_record_refs': [], 'progress_refs': [snapshot['progress_ref']],
            'snapshot': snapshot}


def progress_read(arguments, ctx):
    assignment = arguments['assignment']
    try:
        snapshot = _received_snapshot(ctx, arguments)
        committed = _committed(ctx, assignment, snapshot)
    except ContractError as error:
        return _invalid(error)
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': 'progress_read',
                                                    'arguments': {'progress_ref': arguments['progress_ref']}}),
            'record_refs': committed, 'changed_record_refs': [], 'progress_refs': [snapshot['progress_ref']],
            'snapshot': snapshot}


def progress_log(arguments, ctx):
    try:
        snapshot = _received_snapshot(ctx, arguments)
        if arguments['log_index'] >= len(snapshot['log_windows']):
            raise ContractError('monitor_log_window_unavailable')
        window = snapshot['log_windows'][arguments['log_index']]
        source = ctx.store.get(window['source_ref'])
        representation = next((name for name, key in (('original', 'artifact_ref'), ('text', 'text_ref'),
                                                      ('stdout', 'stdout_ref'), ('stderr', 'stderr_ref'))
                               if source.get(key) == window['artifact_ref']), None)
        if representation is None:
            raise ContractError('progress_log_source_artifact_mismatch')
        if window['start_byte'] == window['end_byte']:
            read = {'source_ref': window['source_ref'], 'artifact_ref': window['artifact_ref'],
                    'start': window['start_byte'], 'end': window['end_byte'], 'text': ''}
        else:
            # The old route was the registry's ``source.read`` tool over the Store; the library function behind it
            # is handed ``ctx.store`` (see the carry-over record: library not carried).
            read = source_window(ctx.store, source_ref=window['source_ref'], representation=representation,
                                 offset=window['start_byte'], limit=window['end_byte'] - window['start_byte'])
    except ContractError as error:
        return _invalid(error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': [snapshot['progress_ref']], 'result': read}


async def wait_for_events(arguments, ctx):
    """The old selected wait on native job events (``waiting.MonitorWaiting`` and ``jobs.waiting.selected_wait``):
    it earns no credit; an event target the ledger cannot use is a failed outcome that enters the iterator."""
    outcome = await selected_wait(ctx.services['native_events'], arguments['condition'])
    return {**outcome, 'progress_refs': []}


TOOLS = {'progress_observe': progress_observe, 'progress_read': progress_read, 'progress_log': progress_log,
         'wait_for_events': wait_for_events}


def tool_catalog(descriptor):
    """The old ``ProgressOperations.catalog``; ``native_operation`` appears only when the target descriptor
    supplies a ``selected_observation_schema``."""
    properties = {'requested_fields': deepcopy(_FIELDS)}
    selected_schema = (descriptor or {}).get('selected_observation_schema')
    if selected_schema is not None:
        if (selected_schema.get('type') != 'object' or selected_schema.get('additionalProperties') is not False
                or set(selected_schema.get('properties', {})) != {'native_operation'}
                or selected_schema.get('required') != ['native_operation']):
            raise ContractError('progress_selected_observation_schema_invalid')
        properties.update(deepcopy(selected_schema['properties']))
    return [{'name': 'progress_observe',
             'description': 'Observe selected exposed fields of your assigned target. Retain the original '
                            'observation identity when facts are unchanged. This operation never traverses '
                            'dependent work.', 'input_schema': obj(properties)},
            {'name': 'progress_read', 'description': 'Read an already delivered exact progress observation.',
             'input_schema': obj({'progress_ref': REF})},
            {'name': 'progress_log',
             'description': 'Read one exact retained log window from an already delivered progress observation, '
                            'preserving source/artifact byte custody.',
             'input_schema': obj({'progress_ref': REF, 'log_index': {'type': 'integer', 'minimum': 0}})},
            {'name': 'wait_for_events',
             'description': 'Wait for native job events named by registered targets this episode owns or received, '
                            'or until a reconsideration time. Waiting reports readiness only and earns no credit.',
             'input_schema': obj({'condition': EVENT_CONDITION})}]


def selection_schema(descriptor, has_dependencies):
    """What the model answers with: one tool and its arguments, or (when the assigned target exposes direct
    dependencies) a monitor child for one of them (the old action schema over the tool and child kinds)."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
               for entry in tool_catalog(descriptor)]
    if has_dependencies:
        options.append(obj({'kind': {'const': 'child'}, 'slot': {'const': 'monitor'},
                            'arguments': obj({'dependency_handle': _TEXT, 'requested_fields': deepcopy(_FIELDS),
                                              'permitted_committed_record_types': deepcopy(_TYPES)})}))
    return obj({'selection': {'anyOf': options}})


def instructions(*, knowledge, launch_library):
    """The old composition (goal, action boundary, resource estimates, host execution, tool-knowledge and launch
    library texts, native events); the credit-component, report, history, repair and pending-child paragraphs
    describe fields and actions this episode no longer has."""
    text = GOAL + '\n' + ACTION_BOUNDARY + RESOURCE_ESTIMATE_GUIDANCE + HOST_EXECUTION_GUIDANCE
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text + NATIVE_EVENT_GUIDANCE


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the assignment, the target, the delivered observations, the
    information credit and its meaning, the outcomes, the tools, the measured time, the yield table and the library
    listings (the old decision state and inputs, over this episode's summary)."""
    settings = ctx.settings
    descriptor = describe_target(ctx, summary['target_handle'])
    if settings.get('execution_expectations') is not None:
        execution_expectations(ctx)
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    has_dependencies = bool(summary['monitor_direct_dependencies'])
    context = {'goal': {'objective': summary['monitor_goal']['objective']},
               'tools': tool_catalog(descriptor),
               'current_credit': summary['monitoring_information_credit'],
               'credit_binding': summary['monitoring_information_binding'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'visible_record_refs': summary['committed_record_refs'],
               'monitor_assignment': summary['monitor_assignment'],
               'monitor_target_description': descriptor,
               'monitor_direct_dependencies': summary['monitor_direct_dependencies'],
               'monitor_received_progress_refs': summary['monitor_received_progress_refs'],
               'monitor_information_meaning': summary['monitor_information_meaning'],
               'monitor_goal': {**summary['monitor_goal'],
                                'yield_settings': {'kind': 'information_accumulation', 'cutoff': settings['cost'],
                                                   'uncertainty_alpha': settings['parameters']['uncertainty_alpha']}},
               'outcome_history': summary['outcome_history'],
               'last_local_outcome': summary['last_local_outcome']}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'child_options': ('monitor: commission an ordinary monitor for one exposed direct dependency of the '
                          'assigned target; dependency_handle must be one of monitor_direct_dependencies.'
                          if has_dependencies else None),
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema(descriptor, has_dependencies)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one monitor commission, or reject it (no unit). A tool is
    handed no summary, so the call carries the assignment slice and the delivered snapshot it works from. An
    observation that expands the requested fields, an unreceived progress reference or an unavailable log window is
    not rejected here: as before, it is an executed unit whose invalid outcome enters the iterator."""
    descriptor = describe_target(ctx, summary['target_handle'])
    schema = selection_schema(descriptor, bool(summary['monitor_direct_dependencies']))
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = value['selection']
    if selection['kind'] == 'child':
        return ChildCall(selection['slot'], selection['arguments'])
    name, arguments = selection['tool'], selection['arguments']
    assignment = {key: summary[key] for key in ('target_handle', 'requested_fields',
                                                'permitted_committed_record_types')}
    if name == 'wait_for_events':
        return ToolCall(name, {'condition': arguments['condition']})
    if name == 'progress_observe':
        return ToolCall(name, {'assignment': assignment, **arguments})
    reference = arguments['progress_ref']
    received = reference in summary['received_progress_refs']
    return ToolCall(name, {'assignment': assignment, **arguments, 'received': received,
                           'snapshot': summary['progress_snapshots'].get(reference) if received else None})
