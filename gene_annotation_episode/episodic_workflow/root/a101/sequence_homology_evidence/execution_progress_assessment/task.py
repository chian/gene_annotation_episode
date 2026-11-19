"""The task: one selected action per unit: a progress tool (observe the assigned target, read a delivered
observation, read one retained log window) or one commissioned monitor for an exposed direct dependency.

Carried from the old ``task.py`` (``ProgressMonitoringTask``), ``task_decision.py``, ``task_instructions.py``,
``progress_operations.py`` (``ProgressOperations.catalog`` and ``execute``), ``decision_state.py`` and
``decision_inputs.py``; the old decision-exchange loop, the ``report_update`` the model wrote with each decision,
the wait and the report redelivery are not carried (README 3a, 3b R2, 3e). The task always offers a unit and never
ends the Episode: ``action`` accepts a progress tool at every decision, so a selection that names none is rejected
with feedback and no unit; the commissioned monitor is offered only while the target exposes direct dependencies.

A tool call that breaks the assignment's limits (more fields than the assignment's ``requested_fields``, a
progress ref that was not received, a log window that does not exist) returns an ``invalid`` outcome, which is a
unit with its credit like any other. ``action`` copies what a tool needs of the assignment and of the received
progress into the tool's arguments (a tool is handed no summary).

Settings this episode reads (``ctx.settings``): ``launch_instructions_directory`` and ``knowledge_library_directory``
(optional: the libraries whose context is shown to the model); ``cost`` and ``parameters``
(``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: observing the target is the old ``ProgressProvider.observe`` over A101's execution job
provider; no service wraps it. ``progress_observe`` names the service and the call it wants and raises where it is
reached. The description of the target the model is shown is a recorded read of the same service.

Unplaced: the ``native_operation`` argument of the observation (``native_observation_options`` of the old shared
root ``episode_bindings``) has no home now: ``progress_observe`` raises ``NotImplementedError`` for it."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    ContractError)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from . import goal as goal_file

FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
          'result_available')
CHILD_SLOTS = {'monitor': goal_file.BINDING_PATH}
SERVICES = ('job_access',)

ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
CREDIT_COMPONENT_GUIDANCE = ('monitoring_information_credit is the projector\'s credit from the same projection as '
                             'current_credit; monitoring_information_binding says how it is counted. They describe '
                             'the progress proxy, not biological truth. Repeated observation identities and read '
                             'timestamps alone earn no new information.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'
MODEL_ROLE = 'REASONING'


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


_TEXT = {'type': 'string', 'minLength': 1}


def catalog(description):
    """The old ``ProgressOperations.catalog``: the three progress tools; the observation takes the target's own
    selected-observation property (``native_operation``) when its description declares one."""
    properties = {'requested_fields': {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}}
    selected_schema = (description or {}).get('selected_observation_schema')
    if selected_schema is not None:
        if (selected_schema.get('type') != 'object' or selected_schema.get('additionalProperties') is not False
                or set(selected_schema.get('properties', {})) != {'native_operation'}
                or selected_schema.get('required') != ['native_operation']):
            raise ContractError('progress_selected_observation_schema_invalid')
        properties.update(deepcopy(selected_schema['properties']))
    return [
        {'name': 'progress_observe',
         'description': 'Observe selected exposed fields of your assigned target. Retain the original observation '
                        'identity when facts are unchanged. This operation never traverses dependent work.',
         'input_schema': _object(properties)},
        {'name': 'progress_read', 'description': 'Read an already delivered exact progress observation.',
         'input_schema': _object({'progress_ref': _TEXT})},
        {'name': 'progress_log',
         'description': 'Read one exact retained log window from an already delivered progress observation, '
                        'preserving source/artifact byte custody.',
         'input_schema': _object({'progress_ref': _TEXT, 'log_index': {'type': 'integer', 'minimum': 0}})},
    ]


def _invalid(code, detail=None):
    return {'status': 'invalid', 'kind': 'tool', 'record_refs': [], 'changed_record_refs': [], 'progress_refs': [],
            'feedback': {'category': 'arguments_or_reference', 'code': code, **({'detail': detail} if detail else {})}}


def _delivered(store, snapshot, permitted):
    """The outcome of a delivered observation: its identity and its parent-permitted committed records."""
    committed = [ref for ref in snapshot['committed_record_refs'] if store.get(ref)['record_type'] in permitted]
    return {'status': 'completed', 'kind': 'tool', 'record_refs': committed, 'changed_record_refs': [],
            'progress_refs': [snapshot['progress_ref']], 'snapshot': snapshot}


def _observe_progress(ctx, arguments):
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services[\'job_access\'].observe_progress('
        'arguments[\'target_handle\'], arguments[\'requested_fields\'], '
        'permitted_committed_record_types=arguments[\'permitted_committed_record_types\'], '
        'key=ctx.operation_key), returning the progress_snapshot_v1 of the observation, with the original '
        'identity of an unchanged observation (the old ProgressProvider.observe)')


def progress_observe(arguments, ctx):
    if not set(arguments['requested_fields']) <= set(arguments['permitted_fields']):
        return _invalid('monitor_observation_expands_requested_fields')
    if 'native_operation' in arguments:
        raise NotImplementedError('unplaced:native_observation_options: the selected native_operation of the '
                                  'observation (old episode_bindings.native_observation_options) has no home now')
    snapshot = _observe_progress(ctx, arguments)
    return _delivered(ctx.store, snapshot, set(arguments['permitted_committed_record_types']))


def progress_read(arguments, ctx):
    snapshot = arguments['snapshot']
    if snapshot is None:
        return _invalid('monitor_progress_not_received')
    return _delivered(ctx.store, snapshot, set(arguments['permitted_committed_record_types']))


def progress_log(arguments, ctx):
    snapshot = arguments['snapshot']
    if snapshot is None:
        return _invalid('monitor_progress_not_received')
    if arguments['log_index'] >= len(snapshot['log_windows']):
        return _invalid('monitor_log_window_unavailable')
    window = snapshot['log_windows'][arguments['log_index']]
    source = ctx.store.get(window['source_ref'])
    if window['artifact_ref'] not in [source.get(field) for field in ('artifact_ref', 'text_ref', 'stdout_ref',
                                                                      'stderr_ref')]:
        return _invalid('progress_log_source_artifact_mismatch')
    text = ''
    if window['start_byte'] != window['end_byte']:
        # The exact byte window of the held artifact, read through custody (old: the registry's ``source.read``).
        with ctx.store.open_artifact(window['artifact_ref']) as handle:
            handle.seek(window['start_byte'])
            text = handle.read(window['end_byte'] - window['start_byte']).decode('utf-8')
    return {'status': 'completed', 'kind': 'tool', 'record_refs': [], 'changed_record_refs': [],
            'progress_refs': [snapshot['progress_ref']],
            'result': {'source_ref': window['source_ref'], 'artifact_ref': window['artifact_ref'],
                       'start': window['start_byte'], 'end': window['end_byte'], 'text': text}}


TOOLS = {'progress_observe': progress_observe, 'progress_read': progress_read, 'progress_log': progress_log}


def selection_schema(summary, description):
    """The closed decision form: one progress tool with its arguments, or one dependency monitor commission."""
    options = [_object({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                        'arguments': entry['input_schema']}) for entry in catalog(description)]
    handles = [row['handle'] for row in summary['monitor_direct_dependencies']]
    if handles:
        options.append(_object({'kind': {'const': 'monitor_dependency'}, 'dependency_handle': {'enum': handles}}))
    return _object({'selection': {'anyOf': options}})


def instructions(summary, *, has_knowledge, has_launch):
    """The old ``task_instructions.instructions``: the goal, the action boundary, the credit-component and host
    execution guidance, then the tool-knowledge and launch-instruction texts when those libraries are shown."""
    text = goal_file.GOAL + '\n' + ACTION_BOUNDARY + CREDIT_COMPONENT_GUIDANCE + HOST_EXECUTION_GUIDANCE
    if summary['monitor_direct_dependencies']:
        text += ('You may commission an ordinary monitor (kind monitor_dependency) for one of the '
                 'monitor_direct_dependencies; the child returns the progress it delivered.\n')
    if has_knowledge:
        text += KNOWLEDGE_INSTRUCTIONS
    if has_launch:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    description = ctx.services['job_access'].read('describe_progress_target', summary['target_handle'])
    goal = {**summary['monitor_goal'],
            'yield_settings': {'cost': ctx.settings.get('cost'), 'parameters': ctx.settings.get('parameters')}}
    context = {
        'goal': goal,
        'monitor_assignment': summary['monitor_assignment'],
        'monitor_target_description': description,
        'monitor_direct_dependencies': summary['monitor_direct_dependencies'],
        'monitor_received_progress_refs': summary['monitor_received_progress_refs'],
        'monitor_information_meaning': summary['monitor_information_meaning'],
        'tools': catalog(description),
        'last_local_outcome': summary['last_local_outcome'],
        'feedback': feedback,
        'current_credit': summary['monitoring_information_credit'],
        'monitoring_information_credit': summary['monitoring_information_credit'],
        'monitoring_information_binding': summary['monitoring_information_binding'],
        'controller': summary['controller'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
    }
    library = ctx.settings.get('launch_instructions_directory')
    if library is not None:
        launch = LaunchInstructions(library)
        context = extend_context(context, {
            'launch_instruction_library': launch.context(),
            'selected_launch_instructions': launch.materialize(summary['launch_instructions'])},
            conflict='initial_binding_context_field_conflict')
    knowledge = ctx.settings.get('knowledge_library_directory')
    if knowledge is not None:
        context = extend_context(context, {'tool_knowledge': ToolKnowledge(knowledge).context()},
                                 conflict='initial_binding_context_field_conflict')
    schema = selection_schema(summary, description)
    return ModelRequest(MODEL_ROLE, instructions(summary, has_knowledge=knowledge is not None,
                                                 has_launch=library is not None), context,
                        generation_schema(schema))


def _tool_call(name, selected, summary):
    """The tool call with what the tool needs of the assignment and of the received progress."""
    arguments = {**selected, 'permitted_committed_record_types': list(summary['permitted_committed_record_types'])}
    if name == 'progress_observe':
        return ToolCall(name, {**arguments, 'target_handle': summary['target_handle'],
                               'permitted_fields': list(summary['requested_fields'])})
    reference = selected['progress_ref']
    return ToolCall(name, {**arguments, 'snapshot': summary['progress_snapshots'].get(reference)
                           if reference in summary['monitor_received_progress_refs'] else None})


def action(response, summary, records, ctx):
    description = ctx.services['job_access'].read('describe_progress_target', summary['target_handle'])
    schema = selection_schema(summary, description)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    if selected['kind'] == 'monitor_dependency':
        return ChildCall('monitor', {'dependency_handle': selected['dependency_handle']})
    return _tool_call(selected['tool'], selected['arguments'], summary)
