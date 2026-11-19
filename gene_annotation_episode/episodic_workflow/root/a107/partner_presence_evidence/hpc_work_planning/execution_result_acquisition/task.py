"""The task: the model chooses one bounded acquisition per unit (an observation of the handed-off attempt, or a read of
requested file windows) and the episode retains each result as a source record in custody.

Carried from the old ``work_operations.py`` (``ResultsWorkOperations.catalog``, ``execute``),
``result_records.py`` (``native_result_operation_catalog``), ``action_outcome.py`` (``_outcome``),
``native_file_acquisition.py`` (``_execute_native_results``), ``result_publication.py`` (``_publish_result``),
``task_instructions.py`` and ``instructions.py``, ``goal.py`` (the permitted actions: ``tool``; the ``wait`` action
of an API target is wait/suspension machinery and API targets are not carried), ``initial_information.py``,
``task_decision.py`` (the results decision inputs) and ``task.py`` (``apply_response``: an answer that does not fit
the schema is rejected with its diagnostic). The old reasoning-commit, job-child, ``reads.map`` and report-update
branches of ``task.py`` and the decision-exchange loop (``exchange_decision``) are not carried: ``reason`` is never
permitted here, and a lookup is a tool.

The task always offers a unit and never ends the Episode: the Episode ends when its yield controller stops it. After
the requested acquisition is complete a further action is an ordinary unit that returns an ``invalid`` outcome
(``execution_results_assignment_already_completed``, the old refusal) and enters the iterator with its credit
unchanged.

Tool names are ``[a-z][a-z0-9_]*`` now: the old ``execution.results.status``, ``.collect`` and ``.read`` are
``execution_results_status``, ``execution_results_collect`` and ``execution_results_read``.

Settings this episode reads (``ctx.settings``; the old ``configuration.py`` values): ``log_window_bytes`` (tools),
``knowledge_library_directory`` and ``launch_instructions_directory`` (optional) and the yield profiles
(``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: the service ``job_access`` and the job record kind of the handoff are not provided. Wanted of
``job_access``: reads for ``decide`` ``target(handoff_ref)`` and ``target_description(handoff_ref, selector)`` (the
old ``job_progress_provider.targets.read_target`` and ``describe_target``); calls for the tools
``observe_target(target, key=, resumed=)`` and ``read_file(target, path=, offset=, limit=, key=, resumed=)``,
idempotent on the key (the old ``observe_target`` and ``read_file``). The handoff row is read at ``_read_target``,
which raises."""
import base64
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    ContractError, canonical, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TRANSPORT_ERROR = 'a107_execution_result_acquisition_selection_has_no_argument_transport'
RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v3'
MEBIBYTE = 1024 * 1024
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

_TEXT = {'type': 'string', 'minLength': 1}
_OFFSET = {'type': 'integer', 'minimum': 0}
_FILE_LIMIT = {'type': 'integer', 'minimum': 1, 'maximum': MEBIBYTE}

# The old native result operation catalog (``native_result_operation_catalog``), under the new tool names.
CATALOG = {
    'execution_results_status': {
        'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})},
    'execution_results_collect': {
        'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.',
        'input_schema': obj({})},
    'execution_results_read': {
        'description': 'Acquire one selected bounded byte window within the original requested paths and interval.',
        'input_schema': obj({'path': _TEXT, 'offset': _OFFSET, 'limit': _FILE_LIMIT})},
}


def operation_catalog():
    return [{'name': name, **deepcopy(entry)} for name, entry in CATALOG.items()]


def _outcome(result=None, *, references=(), code=None):
    """The old ``_outcome``: the outcome shape of a result operation, ``invalid`` when it carries a code."""
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def requested_windows(tool, window, requested, log_window_bytes):
    """The windows one result action reads (the old ``_execute_native_results``): ``read`` one window that lies
    inside a requested path and interval; ``collect`` the first window of every requested path, each up to
    ``min(log_window_bytes, 1 MiB, length)``; ``status`` none."""
    if tool == 'execution_results_read':
        if window['path'] not in requested:
            raise ValueError('execution_results_selector_conflict')
        start, length = requested[window['path']]
        if window['offset'] < start or (length is not None and window['offset'] + window['limit'] > start + length):
            raise ValueError('execution_results_selector_conflict')
        return [dict(window)]
    if tool == 'execution_results_collect':
        return [{'path': path, 'offset': start,
                 'limit': min(log_window_bytes, MEBIBYTE, length) if length is not None
                 else min(log_window_bytes, MEBIBYTE)} for path, (start, length) in requested.items()]
    return []


def validate_result_body(body, *, requested):
    """The old ``_validate_result_body`` content checks: the closed field set, the origin and every window inside the
    requested paths and intervals with bytes of the declared length. (The checks against the old journal, the saved
    action row and the receipt files are the system's.)"""
    fields = {'version', 'run_id', 'episode_id', 'assignment', 'handoff_refs', 'requested', 'operation_key',
              'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
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


def _read_target(ctx, handoff_refs):
    """The execution target (handle, resource, workspace, assignment) the held handoff record names: the old
    ``job_progress_provider.targets.read_target(handoff_ref, scope)``.

    BLOCKED-ON-JOB-SERVICE: the job record kind of the handoff (the row the launching child writes and returns; no
    job record kind or work table is declared); wanted call: ``row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0])``
    then ``ctx.services['job_access'].read_target(row)`` (``JOB_LEDGER`` is the job library's work table, not
    written yet)."""
    raise NotImplementedError(
        'BLOCKED-ON-JOB-SERVICE: the handoff record kind and its work table (JOB_LEDGER); wanted call: '
        "row = ctx.store.table(JOB_LEDGER).get(handoff_refs[0]); target = ctx.services['job_access']"
        '.read_target(row)')


def _publish(ctx, body):
    """Retain the result (the old ``_publish_result``): its artifact and an ``episode.execution_result`` source,
    both produced by this unit; the references are the source and its artifact."""
    artifact = ctx.store.artifact(canonical(body).encode('utf-8'), 'application/json')
    payload = {'provider': RESULT_PROVIDER,
               'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id, body['operation_key']]),
               'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
               'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    return [ctx.store.put('source', payload, origin='tool')['id'], artifact]


async def acquire(tool, arguments, ctx):
    """Observe the attempt once and read the selected windows; retain the result as records held as produced.

    The old ``_execute_native_results``. An argument or reference error is an ``invalid`` outcome (the old
    ``execute`` returned it so); an unavailable file is recorded in ``failures``. The old immutable intent,
    observation, window and receipt files are machinery: the system journals the unit and the job-access calls are
    idempotent on ``ctx.operation_key``."""
    operation, requested = arguments['operation'], {path: tuple(window) for path, window in
                                                    arguments['requested'].items()}
    try:
        validate_schema(operation, CATALOG[tool]['input_schema'])
        if arguments['completed']:
            raise ValueError('execution_results_assignment_already_completed')
        windows = requested_windows(tool, operation, requested, ctx.settings['log_window_bytes'])
        target = _read_target(ctx, arguments['handoff_refs'])
    except (ValueError, TypeError, ContractError) as error:
        return _outcome(code=str(error))
    access = ctx.services['job_access']
    observation = await access.observe_target(target, key=ctx.operation_key, resumed=ctx.resumed)
    acquired, failures = [], []
    for index, window in enumerate(windows):
        try:
            acquired.append(await access.read_file(target, **window, key=ctx.operation_key + ':file:' + str(index),
                                                   resumed=ctx.resumed))
        except (ValueError, OSError) as error:
            failures.append({'path': window['path'],
                             'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable',
                             'exception_type': type(error).__name__})
    body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
            'assignment': arguments['assignment'], 'handoff_refs': arguments['handoff_refs'],
            'requested': arguments['requested'], 'operation_key': ctx.operation_key, 'tool_name': tool,
            'arguments': operation, 'target': target, 'observation': observation, 'windows': acquired,
            'failures': failures, 'acquisition_origin': deepcopy(NATIVE_RESULT_ORIGIN)}
    validate_result_body(body, requested=requested)
    return _outcome(body, references=_publish(ctx, body))


async def execution_results_status(arguments, ctx):
    return await acquire('execution_results_status', arguments, ctx)


async def execution_results_collect(arguments, ctx):
    return await acquire('execution_results_collect', arguments, ctx)


async def execution_results_read(arguments, ctx):
    return await acquire('execution_results_read', arguments, ctx)


TOOLS = {'execution_results_status': execution_results_status,
         'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read}


def selection_schema():
    """What the model answers with: one of the three tools and its arguments (the old action schema, tool kind
    only)."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'tool'}, 'tool': {'const': name}, 'arguments': entry['input_schema']})
        for name, entry in CATALOG.items()]}})


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def instructions(*, knowledge, launch_library):
    """The old composition (the goal text, then the tool-knowledge and launch-library texts when those libraries are
    present in the context). The reasoning-commit paragraph (``reason`` is never permitted), the report-repair
    paragraph, the decision-exchange wording and the wait and native-event paragraphs (the ``wait`` action, API
    targets only) describe actions this episode does not have."""
    text = GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    """Ask the model for the next acquisition, shown the assignment, the target and its description, the selected
    execution task, the progress so far, the last outcomes, the tools, the measured time and the yield table."""
    access = ctx.services['job_access']
    selector = summary['assignment']['selector']
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    launch_directory = ctx.settings.get('launch_instructions_directory')
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    launch = None if launch_directory is None else LaunchInstructions(launch_directory).context()
    context = {
        'goal': GOAL,
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
        'last_local_outcome': None if not summary['actions'] else summary['actions'][-1],
        'actions': summary['actions'], 'tools': operation_catalog(),
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields'],
                                       'tool_knowledge': knowledge, 'launch_instruction_library': launch},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge, launch_library=launch), context,
                        generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """The one operation the model chose, or a rejection (no unit). An answer that does not fit the schema is
    invalid. The tool travels with the assignment, the handoff, the requested windows and whether the acquisition
    is already complete, because a tool is handed no summary; an unusable window (outside the requested paths and
    intervals) is an ``invalid`` outcome of the unit, as the old ``execute`` returned it."""
    schema = selection_schema()
    try:
        value = decode_response(response, schema)
        Draft202012Validator(schema).validate(value)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(selection['tool'], {'operation': selection['arguments'], 'assignment': summary['assignment'],
                                        'handoff_refs': summary['handoff_refs'], 'requested': summary['requested'],
                                        'completed': summary['completed']})
