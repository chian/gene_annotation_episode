"""The A102 monitor's task: observe the assigned execution target, read what was delivered, read one retained log
window, wait for native job events, or commission a monitor for one exposed direct dependency. One unit is one such
action.

Carried from the old ``progress_operations.py`` (``ProgressOperations.catalog`` and ``execute``), ``task.py``,
``task_decision.py``, ``decision_inputs.py``, ``decision_state.py``, ``task_instructions.py``, ``goal.py`` (the goal
instruction text) and ``waiting.py``. The task always offers a unit and never ends the Episode: only the yield
controller does. The old ``redeliver_report`` and the wait on pending in-process children, the report update the
model wrote, the decision-exchange loop and the saved-exchange checks are not carried (the return's facts are
recorded facts: ``messages/final_to_parent.py``). The old wait on native job events is the tool ``wait_for_events``.

The old tool names ``progress.observe``, ``progress.read`` and ``progress.log`` are ``progress_observe``,
``progress_read`` and ``progress_log`` (a tool name is a lowercase identifier).

An executed tool that returns an invalid outcome (an observation that expands the assigned fields, an unreceived
progress reference, an unavailable log window) is still one unit: as before, it is a returned ``status: invalid``
outcome that enters the iterator. A model answer that is malformed, or that commissions a child outside the
exposed direct dependencies, is rejected in ``action`` (no unit).

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``), and
optionally ``launch_instructions_directory``, ``knowledge_library_directory`` (the old workflow's launch and
tool-knowledge libraries) and ``execution_expectations`` (the old execution-expectation binding; when present the
estimate table is needed).

BLOCKED-ON-JOB-SERVICE: the progress provider (``observe_progress``, ``read_progress``, ``describe_progress_target``,
``direct_dependencies``, ``resolve``) is not wrapped as a service, nor is the native event ledger. The functions
``describe_target``, ``direct_dependencies``, ``target_in_scope``, ``observe_target`` and ``snapshot_read`` name the
service and the call they want and raise where they are reached.
"""
from __future__ import annotations

from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.progress_provider import (
    FIELDS, PROGRESS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, identity, obj, plain, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import BINDING_PATH

CHILD_SLOTS = {'monitor': BINDING_PATH}
SERVICES = ('job_access', 'native_events')
TRANSPORT_ERROR = 'a102_monitor_tool_argument_transport_unsupported'

GOAL_INSTRUCTIONS = (
    'Investigate which further exposed progress information is useful for the assigned target. Use actual '
    'status, measured quantities, committed references and source-bound logs. Liveness establishes process '
    'presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information '
    'stays unknown. Earlier outcomes and your admitted child forms inform later decisions. You may explicitly '
    'commission an ordinary monitor for one exposed direct dependency; no descendant traversal, fanout, '
    "cadence or depth is prescribed. Return the original parent's typed form at your closure even while the "
    'target remains active. Do not report private reasoning, intentions or unrestricted findings. Recorded '
    'facts use saved delivered observations; closure does not poll or compose another report with a model. '
    "The monitor's information-credit projector and bound yield rule govern continuation. "
    'Repeated observation identities and read timestamps alone earn no new information.')
ACTION_BOUNDARY = """Do not emit a stop action or invent a
turn budget, approval review, quality gate, experiment, term or observation.
"""
CREDIT_COMPONENT_GUIDANCE = """current_credit is the monitoring information credit of the current projection, with the
projector recorded in credit_binding; it describes the progress proxy, not biological truth.
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
_FIELDS = {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}
_TYPES = {'type': 'array', 'uniqueItems': True, 'items': {'enum': sorted(RECORD_SCHEMAS)}}
_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
EVENT_CONDITION = obj({'version': {'const': 'event_condition_v1'},
                       'events': {'type': 'array', 'items': obj({'handle': _TEXT, 'event': _TEXT,
                                                                  'after_cursor': {'type': 'integer', 'minimum': 0}})},
                       'reconsider_at': {'type': ['string', 'null']}})


# ---------------------------------------------------------------------------------------------------------------
# What the job-access service is asked (BLOCKED-ON-JOB-SERVICE: no such service is built).

def target_in_scope(ctx, summary):
    """Whether the assigned target is an execution handle inside the scope (the old ``reference_in_scope``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read('resolve', target_handle,
    scope, 'execution_handle')`` (a recorded read of a decision)."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              ".read('resolve', summary['target_handle'], summary['scope'], 'execution_handle')")


def describe_target(ctx, summary):
    """What the progress provider says of the assigned target (the old ``describe_progress_target``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read('describe_progress_target',
    target_handle, scope)`` (a recorded read of a decision)."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              ".read('describe_progress_target', summary['target_handle'], summary['scope'])")


def direct_dependencies(ctx, summary):
    """The exposed direct dependencies of the assigned target (the old ``services.dependencies``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read('direct_dependencies',
    target_handle, scope)`` (a recorded read of a decision)."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              ".read('direct_dependencies', summary['target_handle'], summary['scope'])")


def execution_expectations(ctx):
    """The old ``decision_inputs`` execution expectations and resource estimates for role ``monitor``, which the old
    workflow added only when an execution-expectation binding was configured.

    BLOCKED-ON-JOB-SERVICE: estimate_table (README 5 item 19, not built); wanted call:
    ``ctx.services['estimate_table'].read('execution_expectations', 'monitor')``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: ctx.services['estimate_table']"
                              ".read('execution_expectations', 'monitor')")


async def observe_target(ctx, arguments):
    """One observation of the assigned target (the old ``services.observe_progress``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_progress(
    target_handle, requested_fields, scope, permitted_committed_record_types=..., operation_key=ctx.operation_key)``,
    idempotent on ``ctx.operation_key``; it returns the ``progress_snapshot_v1`` record of the delivered
    observation (its ``progress_ref`` is the observation's identity, an unchanged observation keeping its
    original one)."""
    raise NotImplementedError(
        "BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await ctx.services['job_access'].observe_progress("
        "arguments['target_handle'], arguments['requested_fields'], arguments['scope'], "
        "permitted_committed_record_types=arguments['permitted_committed_record_types'], "
        'operation_key=ctx.operation_key)')


def snapshot_read(ctx, reference):
    """A received observation the summary holds no snapshot of (the old ``services.read_progress``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``ctx.services['job_access'].read_progress(reference,
    scope)``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services['job_access']"
                              '.read_progress(reference, scope)')


# ---------------------------------------------------------------------------------------------------------------
# The tools.

def _invalid(error):
    detail = getattr(error, 'detail', None)
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'progress_refs': [],
            'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                         **({'detail': detail} if detail else {})}}


def _committed(ctx, arguments, snapshot):
    """The committed records of an observation whose type the parent permitted (each must be held)."""
    return [reference for reference in snapshot['committed_record_refs']
            if ctx.store.get(reference)['record_type'] in arguments['permitted_committed_record_types']]


def _received_snapshot(ctx, arguments):
    if not arguments['received']:
        raise ContractError('monitor_progress_not_received')
    if arguments['snapshot'] is None:
        return snapshot_read(ctx, arguments['progress_ref'])
    return arguments['snapshot']


def _delivery(ctx, name, arguments, snapshot, operation):
    committed = _committed(ctx, arguments, snapshot)
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': operation}),
            'record_refs': committed, 'changed_record_refs': [], 'progress_refs': [snapshot['progress_ref']],
            'snapshot': snapshot}


async def progress_observe(arguments, ctx):
    try:
        if not set(arguments['requested_fields']) <= set(arguments['assigned_fields']):
            raise ContractError('monitor_observation_expands_requested_fields')
        if 'native_operation' in arguments:
            raise NotImplementedError('native_observation_options_not_placed: the old shared-root '
                                      'native_observation_options(native_operation, context) has no copy; its '
                                      'result was passed as options of the observation')
        snapshot = plain(await observe_target(ctx, arguments))
        if snapshot['version'] != PROGRESS_VERSION or snapshot['target_handle'] != arguments['target_handle']:
            raise ContractError('progress_job_target_mismatch')
        operation = {key: arguments[key] for key in ('requested_fields', 'native_operation') if key in arguments}
        return _delivery(ctx, 'progress_observe', arguments, snapshot, operation)
    except ContractError as error:
        return _invalid(error)


def progress_read(arguments, ctx):
    try:
        snapshot = _received_snapshot(ctx, arguments)
        return _delivery(ctx, 'progress_read', arguments, snapshot, {'progress_ref': arguments['progress_ref']})
    except ContractError as error:
        return _invalid(error)


def progress_log(arguments, ctx):
    """One retained log window of a received observation, read through the held source and artifact."""
    try:
        snapshot = _received_snapshot(ctx, arguments)
        if arguments['log_index'] >= len(snapshot['log_windows']):
            raise ContractError('monitor_log_window_unavailable')
        window = snapshot['log_windows'][arguments['log_index']]
        if not ctx.store.holds(window['source_ref']) or not ctx.store.holds(window['artifact_ref']):
            raise ContractError('monitor_log_source_not_held')
        source = ctx.store.get(window['source_ref'])
        if not any(source.get(key) == window['artifact_ref']
                   for key in ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')):
            raise ContractError('progress_log_source_artifact_mismatch')
        text = ''
        if window['start_byte'] != window['end_byte']:
            with ctx.store.open_artifact(window['artifact_ref']) as stream:
                stream.seek(window['start_byte'])
                data = stream.read(window['end_byte'] - window['start_byte'])
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                raise ContractError('progress_log_window_not_utf8') from None
    except ContractError as error:
        return _invalid(error)
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': [snapshot['progress_ref']],
            'result': {'source_ref': window['source_ref'], 'artifact_ref': window['artifact_ref'],
                       'start': window['start_byte'], 'end': window['end_byte'], 'text': text}}


async def wait_for_events(arguments, ctx):
    """The old selected wait on native job events (``waiting.MonitorWaiting`` and ``jobs.waiting.selected_wait``):
    it earns no credit; an event target the ledger cannot use is a failed outcome that enters the iterator."""
    outcome = await selected_wait(ctx.services['native_events'], plain(arguments['condition']))
    return {**outcome, 'progress_refs': []}


TOOLS = {'progress_observe': progress_observe, 'progress_read': progress_read, 'progress_log': progress_log,
         'wait_for_events': wait_for_events}


# ---------------------------------------------------------------------------------------------------------------
# Deciding.

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
             'input_schema': obj({'progress_ref': _TEXT})},
            {'name': 'progress_log',
             'description': 'Read one exact retained log window from an already delivered progress observation, '
                            'preserving source/artifact byte custody.',
             'input_schema': obj({'progress_ref': _TEXT, 'log_index': {'type': 'integer', 'minimum': 0}})},
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
                                              'known_progress_refs': deepcopy(_REFS),
                                              'permitted_committed_record_types': deepcopy(_TYPES)})}))
    return obj({'selection': {'anyOf': options}})


def instructions(*, knowledge, launch_library):
    """The old composition (goal, action boundary, credit components, host execution, tool-knowledge and launch
    library texts, native events); the resource-estimate, report, history, repair and pending-child paragraphs
    describe inputs and actions this episode no longer has."""
    text = GOAL_INSTRUCTIONS + '\n' + ACTION_BOUNDARY + CREDIT_COMPONENT_GUIDANCE + HOST_EXECUTION_GUIDANCE
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text + NATIVE_EVENT_GUIDANCE


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the assignment, the target, the delivered observations, the
    information credit and its meaning, the outcomes, the tools, the measured time, the yield table and the library
    listings (the old decision state and inputs, over this episode's summary and the recorded service reads)."""
    settings = ctx.settings
    if not target_in_scope(ctx, summary):
        raise ContractError('progress_target_unavailable_or_outside_scope')
    descriptor = describe_target(ctx, summary)
    dependencies = direct_dependencies(ctx, summary)
    if settings.get('execution_expectations') is not None:
        execution_expectations(ctx)
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    assignment = {key: summary[key] for key in ('version', 'target_handle', 'requested_fields',
                                                'known_progress_refs', 'permitted_committed_record_types')}
    context = {'goal': {'objective': summary['goal']['objective']},
               'scope': summary['scope'],
               'tools': tool_catalog(descriptor),
               'visible_record_refs': summary['committed_record_refs'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'monitor_assignment': assignment,
               'monitor_target_description': plain(descriptor),
               'monitor_direct_dependencies': plain(dependencies),
               'monitor_received_progress_refs': summary['received_progress_refs'],
               'monitor_information_meaning': summary['information_meaning'],
               'monitor_goal': {**summary['goal'],
                                'yield_settings': {'kind': 'information_accumulation', 'cutoff': settings['cost'],
                                                   'uncertainty_alpha': settings['parameters']['uncertainty_alpha']}},
               'outcome_history': summary['outcome_history'],
               'last_local_outcome': summary['last_outcome']}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['controller'], 'tool_knowledge': knowledge,
        'child_options': ('monitor: commission an ordinary monitor for one exposed direct dependency of the '
                          'assigned target; dependency_handle must be one of monitor_direct_dependencies.'
                          if dependencies else None),
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    schema = selection_schema(descriptor, bool(dependencies))
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, strict_output_schema(schema, open_records_as_text=False,
                                                      argument_transport_error=TRANSPORT_ERROR))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one monitor commission, or reject it (no unit). A tool is
    handed no summary, so its call carries the assignment slice and the delivered snapshot it works from. A child
    outside the exposed direct dependencies, a baseline the monitor does not hold or a record type beyond its own
    are rejected here: the old runner refused them inside the child's preparation, before any child existed."""
    dependencies = direct_dependencies(ctx, summary)
    schema = selection_schema(describe_target(ctx, summary), bool(dependencies))
    try:
        value = decode_strict_output(response, schema, open_records_as_text=False,
                                     argument_transport_error=TRANSPORT_ERROR)
        validate_schema(value, schema)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = value['selection']
    arguments = selection['arguments']
    if selection['kind'] == 'child':
        if arguments['dependency_handle'] not in [row['handle'] for row in dependencies]:
            raise Rejected(rejection_feedback('monitor_child_target_not_exposed_direct_dependency',
                                              category='action_contract'))
        if not set(arguments['permitted_committed_record_types']) <= set(summary['permitted_committed_record_types']):
            raise Rejected(rejection_feedback('monitor_child_expands_permitted_record_types',
                                              category='action_contract'))
        if any(reference not in summary['progress_snapshots'] for reference in arguments['known_progress_refs']):
            raise Rejected(rejection_feedback('monitor_child_known_progress_not_received',
                                              category='action_contract'))
        return ChildCall(selection['slot'], {
            'target_handle': arguments['dependency_handle'], 'requested_fields': arguments['requested_fields'],
            'known_progress_refs': arguments['known_progress_refs'],
            'permitted_committed_record_types': arguments['permitted_committed_record_types']})
    name = selection['tool']
    if name == 'wait_for_events':
        return ToolCall(name, {'condition': arguments['condition']})
    carried = {'target_handle': summary['target_handle'], 'scope': summary['scope'],
               'permitted_committed_record_types': summary['permitted_committed_record_types']}
    if name == 'progress_observe':
        return ToolCall(name, {**carried, 'assigned_fields': summary['requested_fields'], **arguments})
    reference = arguments['progress_ref']
    received = reference in summary['received_progress_refs']
    return ToolCall(name, {**carried, **arguments, 'received': received,
                           'snapshot': summary['progress_snapshots'].get(reference) if received else None})
