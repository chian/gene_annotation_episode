"""The task: the model chooses one bounded acquisition per unit (an observation of the handed-off attempt, or a read
of requested file windows) and the episode retains each result as a source record in custody.

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``work_operations.py``
(``ResultsWorkOperations.catalog`` and ``execute``), ``native_file_acquisition.py``, ``result_publication.py``,
``result_records.py``, ``schema_fields.py``, ``action_outcome.py`` and ``internal_summary.py``
(``decision_context``). The old decision-exchange loop, the ``report_update`` the model wrote with each decision, the
wait and the report redelivery are not carried (README 3a, 3b R2, 3e).

The task always offers a unit and never ends the Episode: the Episode ends when its yield controller stops it. After
the requested acquisition is complete a further action is an ordinary unit that returns an ``invalid`` outcome
(``execution_results_assignment_already_completed``) and enters the iterator with its credit unchanged. A tool
that returns an ``invalid`` outcome (an argument or reference error, a read outside the requested interval) is a
unit like any other. The wait action of an API target is not carried (API targets are not carried, see
``messages/read_from_parent.py``).

Wanted of the ``job_access`` service, which the system does not provide yet (BLOCKED-ON-JOB-SERVICE):
reads for ``decide``: ``target(handoff_ref)`` and ``target_description(handoff_ref, selector)`` (the old
``job_progress_provider.targets.read_target`` and ``describe_target``); calls for the tools:
``observe_target(target, key=...)`` and ``read_file(target, path=, offset=, limit=, key=...)``, idempotent on the key
(the old ``observe_target`` and ``read_file``). The job record kinds (handoff row, closure row) and their work table
(the job ledger) are not defined either: the handoff is read at ``_read_target`` and the closure is written at
``_close_job``; both raise. The estimate table service is named in ``_close_job`` only.

Settings this episode reads (``ctx.settings``): ``log_window_bytes`` (the size of the first window ``collect`` reads
of each requested path), ``knowledge_library_directory`` (optional: the tool-knowledge library whose context and
instructions are shown to the model), and ``cost``, ``parameters`` and the yield profiles (``yield_estimator.py``)."""
import base64

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    canonical, digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from . import goal as goal_file
from .messages.internal_summary import compact_result, native_results_complete

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v2'
FILE_LIMIT_BYTES = 1024 * 1024
MODEL_ROLE = 'REASONING'
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'results_argument_transport_not_carried'}
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

INSTRUCTIONS = (
    goal_file.GOAL + ' Every action is one unit whose actual result and earned credit enter the iterator, including '
    'an invalid or failed one. Credit is the newly covered fraction of the requested byte positions; the episode '
    'iterator decides continuation from credit, add no stopping budget. Do not execute native provider tools. The '
    'host executes your selected action.')

_TEXT = {'type': 'string', 'minLength': 1}
OPERATIONS = {
    'execution_results_status': {
        'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})},
    'execution_results_collect': {
        'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.',
        'input_schema': obj({})},
    'execution_results_read': {
        'description': 'Acquire one selected bounded byte window within the original requested paths and interval.',
        'input_schema': obj({'path': _TEXT, 'offset': {'type': 'integer', 'minimum': 0},
                             'limit': {'type': 'integer', 'minimum': 1, 'maximum': FILE_LIMIT_BYTES}})}}
CATALOG = [{'name': name, **value} for name, value in OPERATIONS.items()]

# What the model answers: one of the operations, with its arguments.
SELECTION_SCHEMA = {'anyOf': [
    obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
         'arguments': value['input_schema']}) for name, value in OPERATIONS.items()]}
ACTION_SCHEMA = obj({'selection': SELECTION_SCHEMA})


def _outcome(result=None, *, references=(), code=None):
    """The old ``_outcome``: a completed result, or an ``invalid`` one with the reason."""
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def _windows(tool_name, operation, requested, settings):
    """The windows one operation reads, within the requested ones (the old ``_execute_native_results``)."""
    if tool_name == 'execution_results_read':
        if operation['path'] not in requested:
            raise ValueError('execution_results_selector_conflict')
        start, length = requested[operation['path']]
        if operation['offset'] < start or (length is not None
                                           and operation['offset'] + operation['limit'] > start + length):
            raise ValueError('execution_results_selector_conflict')
        return [operation]
    if tool_name == 'execution_results_collect':
        size = min(settings['log_window_bytes'], FILE_LIMIT_BYTES)
        return [{'path': path, 'offset': start, 'limit': min(size, length) if length is not None else size}
                for path, (start, length) in requested.items()]
    return []


def _read_target(ctx, handoff_refs):
    """The target of the original handoff (resource kind, workspace, handle, assignment)."""
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: the handoff record kind and its work table (JOB_LEDGER); wanted call: '
        "row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0]); target = ctx.services['job_access']"
        '.read_target(row)')


def _close_job(ctx, handoff_refs, result_refs, observation):
    """The requested acquisition is complete: write the closure row and add the finished action to the estimate
    table (``LAUNCH_MONITOR_EXTRACT_MECHANICS.md`` sections 3 and 7)."""
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: the job closure record (JOB_LEDGER) and the estimate_table service; wanted call: '
        "ctx.store.table(JOB_LEDGER).put({'job': handle, 'event': 'closure', 'at': observation['observed_at'], "
        "'detail': {'outcome': 'results_acquired', 'result_refs': result_refs}, 'source_ref': result_refs[-1]}); "
        "ctx.services['estimate_table'].add(kind, key=ctx.operation_key, ...)")


def validate_result_body(body, requested):
    """The old ``_validate_result_body`` content checks: the closed field set, the origin, and every window inside the
    requested interval with bytes of the declared length. (The checks against the old journal and receipt files are
    the system's.)"""
    fields = {'version', 'run_id', 'episode_id', 'handoff_refs', 'requested', 'operation_key', 'tool_name',
              'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
    if (not isinstance(body, dict) or set(body) != fields or body['version'] != RESULT_VERSION
            or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
        raise ValueError('invalid_execution_result_information')
    for window in body['windows']:
        if window['path'] not in requested:
            raise ValueError('execution_result_selector_conflict')
        raw = base64.b64decode(window['bytes_base64'], validate=True)
        start, length = requested[window['path']]
        if (window['offset'] < start or window['returned_bytes'] != len(raw)
                or (length is not None and window['offset'] + len(raw) > start + length)
                or window['size_bytes'] < 0):
            raise ValueError('execution_result_window_conflict')


def _publish(ctx, body):
    """Retain the result: its artifact and an ``episode.execution_result`` source, produced by this unit (the old
    ``_publish_result``)."""
    artifact = ctx.store.artifact(canonical(body).encode('utf-8'), 'application/json')
    payload = {'provider': RESULT_PROVIDER,
               'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id, body['operation_key']]),
               'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
               'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    return ctx.store.put('source', payload, origin='tool')['id']


def _acquire(tool_name, arguments, ctx):
    operation, requested = arguments['operation'], arguments['requested']
    try:
        validate_schema(operation, OPERATIONS[tool_name]['input_schema'])
        if arguments['completed']:
            raise ValueError('execution_results_assignment_already_completed')
        windows = _windows(tool_name, operation, requested, ctx.settings)
        target = _read_target(ctx, arguments['handoff_refs'])
        access = ctx.services['job_access']
        observation = access.observe_target(target, key=ctx.operation_key)
        acquired, failures = [], []
        for index, window in enumerate(windows):
            try:
                acquired.append(access.read_file(target, **window, key=ctx.operation_key + ':file:%d' % index))
            except (ValueError, OSError) as error:
                failures.append({'path': window['path'],
                                 'code': str(error) if isinstance(error, ValueError)
                                 else 'execution_result_file_unavailable',
                                 'exception_type': type(error).__name__})
        body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                'handoff_refs': arguments['handoff_refs'], 'requested': requested,
                'operation_key': ctx.operation_key, 'tool_name': tool_name, 'arguments': operation,
                'target': target, 'observation': observation, 'windows': acquired, 'failures': failures,
                'acquisition_origin': dict(NATIVE_RESULT_ORIGIN)}
        validate_result_body(body, requested)
        reference = _publish(ctx, body)
        if native_results_complete([*arguments['prior_results'], compact_result(reference, body)], requested):
            _close_job(ctx, arguments['handoff_refs'], [reference], observation)
        return _outcome(body, references=[reference])
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))


def execution_results_status(arguments, ctx):
    return _acquire('execution_results_status', arguments, ctx)


def execution_results_collect(arguments, ctx):
    return _acquire('execution_results_collect', arguments, ctx)


def execution_results_read(arguments, ctx):
    return _acquire('execution_results_read', arguments, ctx)


TOOLS = {'execution_results_status': execution_results_status,
         'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read}


def decide(summary, feedback, ctx):
    """Ask the model for the next acquisition, with the assignment, the target, the progress and the last outcome
    (the old ``decision_context``: ``execution_assignment``, ``execution_progress``, ``execution_target``,
    ``execution_target_description`` and ``selected_execution_task``)."""
    access = ctx.services['job_access']
    selector = summary['assignment']['selector']
    context = {
        'execution_assignment': summary['assignment'],
        'execution_target': access.read('target', summary['handoff_refs'][0]),
        'execution_target_description': access.read('target_description', summary['handoff_refs'][0], selector),
        'selected_execution_task': {'version': 'selected_execution_task_v1',
                                    'scientific_task': summary['scientific_task'],
                                    'constraints': summary['assignment']['constraints'], 'selector': selector,
                                    'requested_paths': summary['requested_paths']},
        'execution_progress': {'result_refs': summary['result_refs'], 'completed': summary['completed'],
                               'window_count': summary['window_count'], 'failure_count': summary['failure_count'],
                               'observations': summary['observation_states'], 'own_results': summary['own']},
        'actions': summary['actions'], 'feedback': feedback, 'tools': CATALOG,
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    if 'controller' in summary:
        context['controller'] = summary['controller']
    instructions = INSTRUCTIONS
    knowledge = ctx.settings.get('knowledge_library_directory')
    if knowledge is not None:
        context = extend_context(context, {'tool_knowledge': ToolKnowledge(knowledge).context()},
                                 conflict='initial_binding_context_field_conflict')
        instructions += ToolKnowledge.instructions
    return ModelRequest(MODEL_ROLE, instructions, context, strict_output_schema(ACTION_SCHEMA, **TRANSPORT))


def action(response, summary, records, ctx):
    """The one operation the model chose; an answer that does not fit the schema is rejected with its diagnostic."""
    try:
        selection = decode_strict_output(response, ACTION_SCHEMA, **TRANSPORT)['selection']
        Draft202012Validator(SELECTION_SCHEMA).validate(selection)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    return ToolCall(selection['tool'], {'operation': selection['arguments'], 'handoff_refs': summary['handoff_refs'],
                                        'requested': summary['requested'], 'completed': summary['completed'],
                                        'prior_results': [*summary['initial'], *summary['own']]})
