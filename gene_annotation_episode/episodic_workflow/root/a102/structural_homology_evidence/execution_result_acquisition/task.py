"""The task: observe the handed-off attempt and read windows of the requested result files, one action per unit.

Carried from the old ``acquisition_operations.py`` (``catalog``, ``execute``), ``execution_contracts.py``
(``native_result_operation_catalog``, ``_outcome``), ``retained_result_acquisition.py`` (``_execute_native_results``),
``retained_result_publication.py`` (``_publish_result``, ``_validate_result_body``), ``instructions.py``,
``action_policy.py`` (the model selects the ``tool`` action only; the ``wait`` action for an API target is a
wait/suspension and the API target is not carried), ``decision_state.py``, ``decision_inputs.py``,
``decision_provider.py`` and ``task.py``. One unit is one tool call. The task always offers a unit and never ends
the Episode: only the yield controller does (the old refusal of a result action after a verified completion,
``execution_results_assignment_already_completed``, was a stop rule and is deleted). The model's old
``report_update`` is not carried: the return's facts are recorded facts (``messages/final_to_parent.py``).

Tool names are ``[a-z][a-z0-9_]*`` now: the old ``execution.results.status``, ``.collect`` and ``.read`` are
``execution_results_status``, ``execution_results_collect`` and ``execution_results_read``.

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``log_window_bytes`` (tools),
``resource`` (the configured resource, shown to the model; optional), ``initial_information`` (the recorded
inventory of that resource, optional), ``launch_instructions_directory`` and ``knowledge_library_directory``
(optional) and the yield profiles (``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: the handoff record (the job ledger row the launching child wrote) and the job-access calls
that observe the attempt and read a result file are not provided. ``handoff_target`` and ``read_window`` name the
record and the calls they want and raise where they are reached."""
import base64
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.execution_contracts import (
    canonical, obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.structural_homology_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TRANSPORT_ERROR = 'a102_execution_result_acquisition_selection_has_no_argument_transport'
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


def handoff_target(reader, handoff_ref):
    """The execution target (handle, resource, workspace, assignment) the held handoff record names: the old
    ``job_progress_provider.targets.read_target(handoff_ref, scope)``.

    BLOCKED-ON-JOB-SERVICE: job ledger handoff record (the handoff row the launching child writes and returns;
    no job record kind is declared); wanted call: ``reader.table(JOB_LEDGER).get(handoff_ref)`` (``JOB_LEDGER``
    is the job library's work table, not written yet) read as the execution target."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job ledger handoff record; wanted call: '
                              'ctx.store.table(JOB_LEDGER).get(handoff_ref) as the execution target')
    return reader.table(None).get(handoff_ref)


async def observe_target(target, ctx):
    """One observation of the exact handed-off attempt: the old ``targets.observe_target(target, operation_key=...)``
    (``{'state', 'returncode', 'observed_at', ...}``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].observe_target(target,
    key=ctx.operation_key, resumed=ctx.resumed)``, idempotent on ``ctx.operation_key``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].observe_target(target, key=ctx.operation_key, "
                              'resumed=ctx.resumed)')
    return await ctx.services['job_access'].observe_target(target, key=ctx.operation_key, resumed=ctx.resumed)


async def read_window(target, window, key, ctx):
    """One bounded read of a result file: the old ``targets.read_file(target, **window, operation_key=...)``
    (``{'path', 'offset', 'returned_bytes', 'size_bytes', 'bytes_base64', ...}``).

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].read_file(target,
    path=window['path'], offset=window['offset'], limit=window['limit'], key=key, resumed=ctx.resumed)``,
    idempotent on ``key``."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].read_file(target, path=window['path'], "
                              "offset=window['offset'], limit=window['limit'], key=key, resumed=ctx.resumed)")
    return await ctx.services['job_access'].read_file(target, **window, key=key, resumed=ctx.resumed)


def validate_result_body(body, *, run_id, assignment, requested):
    """The old ``_validate_result_body`` over what this episode still holds: the body's fields, identity, the
    original assignment and every window inside the requested paths and intervals. The checks against the old
    runner's tables (the scope, the saved action row, the episode row, the receipt file) are machinery."""
    fields = {'version', 'run_id', 'episode_id', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target',
              'observation', 'windows', 'failures', 'acquisition_origin'}
    if (not isinstance(body, dict) or set(body) != fields or body['version'] != RESULT_VERSION
            or body['run_id'] != run_id or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
        raise ValueError('invalid_execution_result_information')
    if body['assignment'] != assignment:
        raise ValueError('execution_result_original_assignment_conflict')
    for window in body['windows']:
        if window['path'] not in requested:
            raise ValueError('execution_result_selector_conflict')
        raw = base64.b64decode(window['bytes_base64'], validate=True)
        start, length = requested[window['path']]
        if (window['offset'] < start or window['returned_bytes'] != len(raw)
                or (length is not None and window['offset'] + len(raw) > start + length)
                or window['size_bytes'] < 0):
            raise ValueError('execution_result_window_conflict')


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


async def acquire(tool, arguments, ctx):
    """Observe the attempt once and read the selected windows; keep the result as one record held as produced.

    The old ``_execute_native_results``. An argument or reference error is an ``invalid`` outcome (the old
    ``execute`` returned it so); an unavailable file is recorded in ``failures``. The old immutable intent,
    observation, window and receipt files, the saved selected action row and the refusal after completion are
    machinery or stop rules and are not carried: the system journals the unit and a rerun is idempotent on
    ``ctx.operation_key``."""
    assignment = arguments['assignment']
    requested = {path: tuple(window) for path, window in arguments['requested'].items()}
    try:
        windows = requested_windows(tool, arguments.get('window'), requested, ctx.settings['log_window_bytes'])
        target = handoff_target(ctx.store, assignment['handoff_ref'])
        for path in requested:
            confined(path, target['assignment']['workspace'])
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))
    observation = await observe_target(target, ctx)
    acquired, failures = [], []
    for index, window in enumerate(windows):
        try:
            acquired.append(await read_window(target, window, ctx.operation_key + ':file:' + str(index), ctx))
        except (ValueError, OSError) as error:
            failures.append({'path': window['path'],
                             'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable',
                             'exception_type': type(error).__name__})
    body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id, 'assignment': assignment,
            'operation_key': ctx.operation_key, 'tool_name': tool, 'arguments': arguments.get('window') or {},
            'target': target, 'observation': observation, 'windows': acquired, 'failures': failures,
            'acquisition_origin': deepcopy(NATIVE_RESULT_ORIGIN)}
    validate_result_body(body, run_id=ctx.run_id, assignment=assignment, requested=requested)
    reference = ctx.store.artifact(canonical(body), 'application/json')
    return _outcome(body, references=[reference])


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


def resource_information(settings):
    """The old ``initial_decision_context`` (``execution_resource_capabilities``, ``execution_initial_information``)
    for the one configured resource, when the settings name it."""
    configuration = settings.get('resource')
    if configuration is None:
        return None
    return {'resource_kind': 'hpc' if configuration['kind'] == 'pbs_ssh' else configuration['kind'],
            'tool_names': list(CATALOG),
            **{name: deepcopy(configuration[name])
               for name in ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
               if name in configuration},
            'inventory_snapshot': deepcopy(settings.get('initial_information'))}


def instructions(*, knowledge, launch_library):
    """The old composition (``ResultsGoal.instructions`` then ``instructions.instructions``) for what the episode
    offers: the goal text, then the tool-knowledge and launch-library texts when those libraries are present. The
    reasoning-commit paragraph (``reason`` is never permitted), the report-repair paragraph and the decision
    exchange wording describe actions this episode does not have, and the wait and native-event paragraphs
    belong to the ``wait`` action (API targets only)."""
    text = GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the assignment, the facts so far, the acquired target, the origin of
    acquired bytes, the credit rule, the last outcome, the tools, the measured time, the yield table and the library
    listings (the old decision state and inputs, over this episode's summary)."""
    settings = ctx.settings
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    yields = summary['action_yields']
    capabilities = resource_information(settings)
    context = {'goal': GOAL, 'execution_assignment': summary['assignment'], 'execution_progress': summary['facts'],
               'execution_target': summary['target'], 'acquisition_provenance': NATIVE_RESULT_ORIGIN,
               'current_credit': None if yields is None else yields['current_credit'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_outcome'],
               'tools': operation_catalog(), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': yields, 'tool_knowledge': knowledge,
        'execution_resource_capabilities': None if capabilities is None else [capabilities],
        'launch_instruction_library': None if launch is None else launch.context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge, launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that does not fit the schema
    is invalid. The tool travels with the assignment and the requested windows, because a tool is handed no
    summary; an unusable window (outside the requested paths and intervals) is an ``invalid`` outcome of the unit,
    as the old ``execute`` returned it."""
    schema = selection_schema()
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    arguments = {'assignment': summary['assignment'], 'requested': summary['requested']}
    if selection['tool'] == 'execution_results_read':
        arguments['window'] = selection['arguments']
    return ToolCall(selection['tool'], arguments)
