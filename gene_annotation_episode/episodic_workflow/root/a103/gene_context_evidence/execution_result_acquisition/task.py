"""The task: the model chooses one bounded acquisition per unit (an observation of the handed-off attempt, or a read
of requested file windows) and the episode retains each result as a source record in custody.

The task always offers a unit and never ends the Episode: the Episode ends when its yield controller stops it. After
the requested acquisition is complete a further action is an ordinary unit that returns an ``invalid`` outcome
(``execution_results_assignment_already_completed``) and enters the iterator with its credit unchanged. The wait
action of an API target is not carried (API targets are not carried, see ``messages/read_from_parent.py``).

Wanted of the ``job_access`` service, which the system does not provide yet (BLOCKED-ON-JOB-SERVICE):
reads for ``decide``: ``target(handoff_ref)`` and ``target_description(handoff_ref, selector)`` (the old
``job_progress_provider.targets.read_target`` and ``describe_target``); calls for the tools:
``observe_target(target, key=...)`` and ``read_file(target, path=, offset=, limit=, key=...)``, idempotent on the key
(the old ``observe_target`` and ``read_file``). The job record kinds (handoff row) and their work table are not
defined either: the handoff is read at ``_read_target``, which raises."""
import base64

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    canonical, digest)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v2'
FILE_LIMIT_BYTES = 1024 * 1024
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

INSTRUCTIONS = (
    'Acquire the original selected execution results through the original handoff. Choose bounded status or '
    'requested file/page reads using actual preceding outcomes. Preserve partial bytes and native scores. Native '
    'paths expose the current resource filesystem: the exact attempt observation does not establish that current '
    'file bytes were produced by that attempt. Separate read windows are not an atomic file snapshot. The '
    'scientific parent interprets the returned records. Original work, resource and selector stay fixed. Only '
    'actual complete acquisition establishes this endpoint. Every action is one unit whose actual result and earned '
    'credit enter the iterator, including an invalid or failed one. Credit is the newly covered fraction of the '
    'requested byte positions; the episode iterator decides continuation from credit, add no stopping budget.')

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
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def _windows(tool_name, operation, requested, settings):
    """The windows one operation reads, within the requested ones."""
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
    """Retain the result: its artifact and an ``episode.execution_result`` source, produced by this unit."""
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
        return _outcome(body, references=[_publish(ctx, body)])
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
    """Ask the model for the next acquisition, with the assignment, the target, the progress and the last outcome."""
    access = ctx.services['job_access']
    selector = summary['assignment']['selector']
    context = {
        'execution_assignment': summary['assignment'],
        'execution_target': access.read('target', summary['handoff_refs'][0]),
        'execution_target_description': access.read('target_description', summary['handoff_refs'][0], selector),
        'selected_execution_task': {'version': 'selected_execution_task_v1',
                                    'scientific_task': summary['scientific_task'], 'selector': selector,
                                    'requested_paths': summary['requested_paths']},
        'execution_progress': {'result_refs': summary['result_refs'], 'completed': summary['completed'],
                               'window_count': summary['window_count'], 'failure_count': summary['failure_count'],
                               'observations': summary['observation_states'], 'own_results': summary['own']},
        'actions': summary['actions'], 'feedback': feedback, 'tools': CATALOG}
    if 'controller' in summary:
        context['controller'] = summary['controller']
    return ModelRequest('REASONING', INSTRUCTIONS, context, generation_schema(ACTION_SCHEMA))


def action(response, summary, records, ctx):
    """The one operation the model chose; an answer that does not fit the schema is rejected with its diagnostic."""
    try:
        selection = decode_response(response, ACTION_SCHEMA)['selection']
        Draft202012Validator(SELECTION_SCHEMA).validate(selection)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(selection['tool'], {'operation': selection['arguments'], 'handoff_refs': summary['handoff_refs'],
                                        'requested': summary['requested'], 'completed': summary['completed']})
