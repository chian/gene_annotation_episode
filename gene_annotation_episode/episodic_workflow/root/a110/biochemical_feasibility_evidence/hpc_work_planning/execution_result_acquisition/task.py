"""The task: one acquisition action per unit: observe the exact handed-off attempt once, collect the first windows
of every requested path, or read one window inside the requested path and interval.

Carried from the old ``task.py`` (``ResultsTask``), ``task_decision.py``, ``task_instructions.py``,
``work_operations.py`` (``ResultsWorkOperations.catalog`` and ``execute``), ``result_records.py``
(``native_result_operation_catalog``), ``native_file_acquisition.py`` (``_execute_native_results``),
``result_publication.py`` (``_publish_result``), ``action_outcome.py`` and ``schema_fields.py``. Only the ``tool``
action was permitted (``ResultsGoal.permitted_common_actions``), and there are no children. The old decision-exchange
loop, the report redelivery, the ``report_update`` the model wrote with each decision, the immutable intent /
observation / window files and their receipt replay (the system's attempts journal and ``ctx.operation_key``
replace them) and the refusal read from ``runtime_actions`` are not carried (README 3a, 3b R2, 3e). The task always
offers a unit and never ends the Episode: ``action`` accepts one of the three tools at every decision, and a
selection that names none is rejected with feedback and no unit. After the endpoint is complete a further tool call
is still a unit: it returns the old ``invalid`` outcome ``execution_results_assignment_already_completed``
(``action`` passes whether the endpoint is complete in the arguments, a tool is handed no summary).

A tool call whose arguments break the assignment (a path outside the requested paths, a window outside the
requested interval) returns an ``invalid`` outcome, which is a unit like any other (the old ``ValueError`` ->
``_outcome(code=...)``). A failed read of one window is kept as a failure of the receipt; the receipt is written
through ``ctx.store`` (an artifact and a Source of provider ``episode.execution_result``).

BLOCKED-ON-JOB-SERVICE (each raises ``NotImplementedError`` where it is reached): the handoff record and its target
(``_read_target``), the observation of the attempt (``_observe_target``) and one file window (``_read_window``) are
the old ``job_progress_provider.targets`` over A110's execution job provider; no service wraps it and the handoff
record kind is not defined. ``decide`` makes the recorded read ``describe_result_target`` of the same service (old
``describe_target``). Settings this episode reads (``ctx.settings``): ``log_window_bytes`` (old configuration, a
positive integer), ``launch_instructions_directory`` and ``knowledge_library_directory`` (optional: the libraries
whose context is shown to the model), and the yield profiles (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.execution_contracts import (
    canonical, checked, digest, obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import ToolKnowledge

from . import goal as goal_file

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v2'
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
MODEL_ROLE = 'REASONING'
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'results_argument_transport_not_carried'}

TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024 * 1024}

CATALOG = [
    {'name': 'execution_results_status',
     'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})},
    {'name': 'execution_results_collect',
     'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.',
     'input_schema': obj({})},
    {'name': 'execution_results_read',
     'description': 'Acquire one selected bounded byte window within the original requested paths and interval.',
     'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})},
]
_CATALOG = {entry['name']: entry for entry in CATALOG}


def _outcome(result=None, *, references=(), artifacts=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'artifact_refs': list(artifacts), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def _read_target(ctx, handoff_ref):
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: the handoff job record (execution_target_v1, record kind not defined); wanted '
        'call: ctx.store.get(handoff_ref) read as the execution target, validated by validate_target and matched '
        'to the commissioned assignment (old job_progress_provider.targets.read_target and _context_target), or '
        "ctx.services['job_access'].read_target(handoff_ref)")


def _observe_target(ctx, target):
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services[\'job_access\'].observe_target(target, '
        'key=ctx.operation_key), returning the observation of the exact attempt (state, returncode, observed_at; '
        'old job_progress_provider.targets.observe_target)')


def _read_window(ctx, target, window, index):
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ctx.services[\'job_access\'].read_file(target, '
        "path=window['path'], offset=window['offset'], limit=window['limit'], key=ctx.operation_key + ':file:' + "
        'str(index)), returning the acquired window (path, offset, returned_bytes, size_bytes; old '
        'job_progress_provider.targets.read_file)')


def _window_requests(tool_name, arguments, requested, log_window_bytes):
    """The windows one tool call reads (old ``_execute_native_results``); a window outside the original selector is
    a ``ValueError`` (an invalid outcome)."""
    by_path = {row['path']: (row['start'], row['length']) for row in requested}
    if tool_name == 'execution_results_read':
        if arguments['path'] not in by_path:
            raise ValueError('execution_results_selector_conflict')
        start, length = by_path[arguments['path']]
        if arguments['offset'] < start or (length is not None
                                           and arguments['offset'] + arguments['limit'] > start + length):
            raise ValueError('execution_results_selector_conflict')
        return [dict(arguments)]
    if tool_name == 'execution_results_collect':
        return [{'path': path, 'offset': start,
                 'limit': min(log_window_bytes, 1024 * 1024, length) if length is not None
                 else min(log_window_bytes, 1024 * 1024)} for path, (start, length) in by_path.items()]
    return []


def _publish_result(ctx, body):
    """Publish a result receipt as a Source of provider ``episode.execution_result`` (old ``_publish_result``)."""
    artifact = ctx.store.artifact(canonical(body), 'application/json')
    payload = {'provider': RESULT_PROVIDER,
               'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id, body['operation_key']]),
               'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
               'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    return ctx.store.put('source', payload, origin='tool')['id'], artifact


def _acquire(tool_name, arguments, ctx):
    try:
        if tool_name not in _CATALOG:
            raise ValueError('execution_operation_not_available')
        model_arguments = checked(arguments['arguments'], _CATALOG[tool_name]['input_schema'],
                                  'invalid_execution_operation_arguments')
        requests = _window_requests(tool_name, model_arguments, arguments['windows'],
                                    ctx.settings['log_window_bytes'])
        if arguments['already_completed']:
            raise ValueError('execution_results_assignment_already_completed')
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))
    target = _read_target(ctx, arguments['handoff_ref'])
    observation = _observe_target(ctx, target)
    acquired, failures = [], []
    for index, window in enumerate(requests):
        try:
            acquired.append(_read_window(ctx, target, window, index))
        except (ValueError, OSError) as error:
            failures.append({'path': window['path'],
                             'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable',
                             'exception_type': type(error).__name__})
    body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
            'assignment': arguments['assignment'], 'operation_key': ctx.operation_key, 'tool_name': tool_name,
            'arguments': model_arguments, 'target': target, 'observation': observation, 'windows': acquired,
            'failures': failures, 'acquisition_origin': dict(NATIVE_RESULT_ORIGIN)}
    reference, artifact = _publish_result(ctx, body)
    return _outcome(body, references=[reference], artifacts=[artifact])


def execution_results_status(arguments, ctx):
    return _acquire('execution_results_status', arguments, ctx)


def execution_results_collect(arguments, ctx):
    return _acquire('execution_results_collect', arguments, ctx)


def execution_results_read(arguments, ctx):
    return _acquire('execution_results_read', arguments, ctx)


TOOLS = {'execution_results_status': execution_results_status,
         'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read}


def selection_schema():
    """The closed decision form: one acquisition tool with its arguments."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
               for entry in CATALOG]
    return obj({'selection': {'anyOf': options}})


def decide(summary, feedback, ctx):
    description = ctx.services['job_access'].read('describe_result_target', summary['handoff_ref'],
                                                  summary['selector'])
    context = {
        'goal': summary['goal'],
        'execution_assignment': summary['execution_assignment'],
        'execution_progress': summary['execution_progress'],
        'execution_target_description': description,
        'visible_record_refs': [*summary['handoff_refs'], *summary['result_refs'],
                                *summary['result_artifact_refs']],
        'tools': CATALOG,
        'last_local_outcome': summary['last_local_outcome'],
        'feedback': feedback,
        'current_credit': summary['current_credit'],
        'acquired_selector_fraction': summary['acquired_selector_fraction'],
        'credit_binding': summary['credit_binding'],
        'controller': summary['controller'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
    }
    library = ctx.settings.get('launch_instructions_directory')
    if library is not None:
        launch = LaunchInstructions(library)
        context = extend_context(context, {'launch_instruction_library': launch.context()},
                                 conflict='initial_binding_context_field_conflict')
    knowledge = ctx.settings.get('knowledge_library_directory')
    if knowledge is not None:
        context = extend_context(context, {'tool_knowledge': ToolKnowledge(knowledge).context()},
                                 conflict='initial_binding_context_field_conflict')
    return ModelRequest(MODEL_ROLE, goal_file.GOAL, context, strict_output_schema(selection_schema(), **TRANSPORT))


def action(response, summary, records, ctx):
    schema = selection_schema()
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    return ToolCall(selected['tool'], {'arguments': selected['arguments'], 'handoff_ref': summary['handoff_ref'],
                                       'windows': summary['windows'],
                                       'assignment': {key: summary[key] for key in (
                                           'handoff_refs', 'selector', 'windows', 'constraints', 'resource_kind',
                                           'acquired_record_unit')},
                                       'already_completed': summary['execution_progress']['execution_completed']})
