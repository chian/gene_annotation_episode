"""The task: acquire the results of the original handoff.

The model chooses one native result operation from what preceded it: a status observation of the exact handed-off
attempt, or a bounded read window inside the original requested paths and interval (the old
``execution.results.status``, ``execution.results.collect`` and ``execution.results.read``; tool names are
lowercase identifiers now). The acquisition itself is done through the ``job_access`` service, which observes the
attempt and reads the requested files on the resource. Each tool keeps what it acquired as a retained result record
the Episode holds: an artifact with the information body and a ``source`` record of provider
``episode.execution_result`` over it. The task always offers a unit and never ends the Episode; the yield controller
stops it. A tool that was selected, executed and returned an invalid outcome still returns it as its outcome (the old
``_outcome(code=...)``): it enters the iterator with its credit, which is zero for it.

``wait`` is the old selected wait of an API service assignment (``api_service_assignment_v1``): an ``async`` tool
that awaits the native event ledger through the job service. A wait earns what its summary earns: nothing.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet"). The tools name it and call it; each raises where the call is made.

Only the generic native byte-window family is placed. The old typed result families (masking, utility, standard
BLAST database, BLAST database, HMMER preparation, HMMER, BLAST pairwise), the API service results (AppService, BV-BRC
data, UniProt, the HMMER API) and the local file sources were classes of the old shared root and of this folder that
are in no place now: ``decide`` raises ``NotImplementedError('unplaced:<family>...')`` where their catalog would have
been read.

Settings (``ctx.settings``): ``log_window_bytes`` (the old bounded first window of ``collect``),
``launch_instructions_directory`` and ``tool_knowledge_directory``."""
import base64
import inspect
import json

from episode_runtime import ModelRequest, Rejected, ToolCall

from . import goal as goal_file
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.execution_contracts import (
    TEXT, canonical, digest, obj)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    ContractError, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v2'
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
BODY_FIELDS = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments',
               'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
FILE_LIMIT = 1024 * 1024
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}

# The old ``native_result_operation_catalog()`` (result_operations.py).
CATALOG = [
    {'name': 'execution_results_status',
     'description': 'Observe the exact handed-off physical attempt once (old execution.results.status).',
     'input_schema': obj({})},
    {'name': 'execution_results_collect',
     'description': 'Observe the original attempt and acquire bounded first windows of the requested paths (old '
                    'execution.results.collect).',
     'input_schema': obj({})},
    {'name': 'execution_results_read',
     'description': 'Acquire one selected bounded byte window within the original requested paths and interval (old '
                    'execution.results.read).',
     'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': {**LIMIT, 'maximum': FILE_LIMIT}})}]
# The old ``wait`` selection of an API service assignment: an event_condition_v1 over registered native event targets.
WAIT = {'name': 'wait',
        'description': 'Wait for native job events of the targets this episode owns or received (an '
                       'event_condition_v1 condition).',
        'input_schema': obj({'condition': {'type': 'object'}})}

# The old results goal text replaced the default instructions (``replaces_default_instructions``); the old composer
# added the tool-knowledge and launch-instruction library texts, and the native-event wait text when ``wait`` is
# permitted. The pending-child-delivery repair text, the in-process wait text and the exchange-history text describe
# actions that no longer exist (redelivery, pending children, the request_context exchange): not carried.
ANSWER_INSTRUCTION = (' Answer with one tool and its operands as one JSON object in arguments_json (an empty object '
                      'for execution_results_status and execution_results_collect).')
NATIVE_EVENT_INSTRUCTION = (
    '\nThe separate native_event_targets input names native notification targets assigned or actually received by '
    'this episode. A target is registration metadata, not proof that submission succeeded. Its state_changed event '
    'means the original service exit receipt was committed; the service may still be closing, so this does not '
    'establish result readiness or a child episode return. after_cursor records an event cursor actually received, '
    'initially zero. Select your own wait condition and subsequent status/monitor/result work. No event probability, '
    'gain or scientific credit follows from registration or passing time alone.')


def _outcome(result=None, *, references=(), code=None):
    """The old ``_outcome``: the outcome of an acquisition, or an invalid one with its code."""
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def _service_call(ctx, member, wanted, *arguments, **keywords):
    service = ctx.services['job_access']
    if not hasattr(service, member):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member + '; wanted call: ' + wanted)
    return getattr(service, member)(*arguments, **keywords)


async def _settled(reply):
    return await reply if inspect.isawaitable(reply) else reply


def _validate_result_body(body, arguments, ctx):
    """The episode's check of its own acquisition (old ``_validate_result_body``): the closed body, and every
    window inside the original requested windows with the bytes it claims."""
    if (not isinstance(body, dict) or set(body) != BODY_FIELDS or body['version'] != RESULT_VERSION
            or body['run_id'] != ctx.run_id or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
        raise ValueError('invalid_execution_result_information')
    requested = arguments['requested']
    for window in body['windows']:
        if window['path'] not in requested:
            raise ValueError('execution_result_selector_conflict')
        raw = base64.b64decode(window['bytes_base64'], validate=True)
        start, length = requested[window['path']]
        if (window['offset'] < start or window['returned_bytes'] != len(raw)
                or (length is not None and window['offset'] + len(raw) > start + length)
                or window['size_bytes'] < 0):
            raise ValueError('execution_result_window_conflict')


def _publish_result(body, ctx):
    """Keep the acquisition as an artifact and a ``source`` record over it (old ``_publish_result``)."""
    artifact = ctx.store.artifact(canonical(body), 'application/json')
    payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id,
                                                                                         body['operation_key']]),
               'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
               'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    return ctx.store.put('source', payload, origin='tool')['id'], artifact


def _windows(tool_name, arguments):
    """The windows one operation reads (old ``_execute_native_results``)."""
    requested, model = arguments['requested'], arguments['arguments']
    if tool_name == 'execution_results_read':
        if model['path'] not in requested:
            raise ValueError('execution_results_selector_conflict')
        start, length = requested[model['path']]
        if model['offset'] < start or (length is not None and model['offset'] + model['limit'] > start + length):
            raise ValueError('execution_results_selector_conflict')
        return [model]
    if tool_name == 'execution_results_collect':
        bound = min(arguments['log_window_bytes'], FILE_LIMIT)
        return [{'path': path, 'offset': start, 'limit': min(bound, length) if length is not None else bound}
                for path, (start, length) in requested.items()]
    return []


async def _execute_native_results(tool_name, arguments, ctx):
    try:
        if arguments['completed']:
            raise ValueError('execution_results_assignment_already_completed')
        windows = _windows(tool_name, arguments)
        target = arguments['target']
        observation = await _settled(_service_call(
            ctx, 'observe_target', 'await ctx.services["job_access"].observe_target(arguments["target"], '
                                   'key=ctx.operation_key)', target, key=ctx.operation_key))
        acquired, failures = [], []
        for index, window in enumerate(windows):
            try:
                data = await _settled(_service_call(
                    ctx, 'read_file', 'await ctx.services["job_access"].read_file(arguments["target"], path=, '
                                      'offset=, limit=, key=ctx.operation_key + ":file:<index>")',
                    target, **window, key=ctx.operation_key + ':file:' + str(index)))
                acquired.append(data)
            except (ValueError, OSError) as error:
                failures.append({'path': window['path'],
                                 'code': str(error) if isinstance(error, ValueError)
                                 else 'execution_result_file_unavailable',
                                 'exception_type': type(error).__name__})
        body = {'version': RESULT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                'scope': target['scope'], 'assignment': arguments['assignment'], 'operation_key': ctx.operation_key,
                'tool_name': tool_name, 'arguments': arguments['arguments'], 'target': target,
                'observation': observation, 'windows': acquired, 'failures': failures,
                'acquisition_origin': dict(NATIVE_RESULT_ORIGIN)}
        _validate_result_body(body, arguments, ctx)
        source_ref, artifact_ref = _publish_result(body, ctx)
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))
    return {**_outcome(body, references=[source_ref]), 'artifact_ref': artifact_ref}


async def execution_results_status(arguments, ctx):
    return await _execute_native_results('execution_results_status', arguments, ctx)


async def execution_results_collect(arguments, ctx):
    return await _execute_native_results('execution_results_collect', arguments, ctx)


async def execution_results_read(arguments, ctx):
    return await _execute_native_results('execution_results_read', arguments, ctx)


async def wait(arguments, ctx):
    """The old ``_execute_selected_wait``: await the native event ledger; an unusable target is a failed outcome that
    enters the iterator (``selected_wait`` returns it)."""
    service = ctx.services['job_access']
    if not (hasattr(service, 'validate_event_targets') and hasattr(service, 'wait_events')):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.validate_event_targets and wait_events (the '
                                  'native event ledger); wanted call: await selected_wait(ctx.services["job_access"], '
                                  'arguments["condition"])')
    return await selected_wait(service, arguments['condition'])


TOOLS = {'execution_results_status': execution_results_status, 'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read, 'wait': wait}


def _catalog(summary):
    """The operations offered for the original target (the old ``catalog`` branches)."""
    family = summary['family']
    if family == 'native_bytes':
        return CATALOG
    # old: the family's operation_catalog(), api_execution.catalog(context) (with ``wait`` for an API service
    # assignment), local_file_sources.execute
    raise NotImplementedError('unplaced:' + family + '.operation_catalog')


def _instructions(settings, catalog):
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = goal_file.GOAL + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS
    if any(entry['name'] == 'wait' for entry in catalog):
        text += NATIVE_EVENT_INSTRUCTION
    return text + ANSWER_INSTRUCTION, library


def _task_text(summary):
    """The old selected-execution presentation (``present_execution_context``) over this episode's own summary: the
    assignment, the target, what was acquired so far and the progress."""
    parts = ['TASK', '', 'Acquire the selected results of the original handoff.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True), '', 'Execution target', '',
             json.dumps(summary['target'], indent=1, sort_keys=True)]
    if summary['selected_execution_task'] is not None:
        parts.extend(['', 'Selected execution task', '',
                      json.dumps(summary['selected_execution_task'], indent=1, sort_keys=True)])
    if summary['acquisitions']:
        parts.extend(['', 'Acquisitions so far', '', json.dumps(summary['acquisitions'], indent=1, sort_keys=True)])
    parts.extend(['', 'Progress', '', json.dumps({'execution_progress': summary['execution_progress']},
                                                 indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _output_schema(catalog):
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': [entry['name'] for entry in catalog]},
                           'arguments_json': {'type': 'string',
                                              'description': 'The operands as one JSON object: ' + json.dumps(
                                                  {entry['name']: entry['input_schema'] for entry in catalog},
                                                  sort_keys=True)}}}


def decide(summary, feedback, ctx):
    """One acquisition: the model chooses it from the assignment, the target, the acquisitions so far and their
    credit."""
    catalog = _catalog(summary)
    instructions, library = _instructions(ctx.settings, catalog)
    knowledge = ToolKnowledge(ctx.settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'execution_assignment': summary['assignment'],
               'execution_progress': summary['execution_progress'], 'execution_target': summary['target'],
               'acquisitions': summary['acquisitions'], 'launch_instruction_library': library.context(),
               'tool_knowledge': knowledge.context(), 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    if summary['selected_execution_task'] is not None:
        context['selected_execution_task'] = summary['selected_execution_task']
    return ModelRequest('REASONING', instructions, context, _output_schema(catalog))


def action(response, summary, records, ctx):
    """The one operation the answer selects, or a rejection: it names an offered tool and operands that fit its
    schema."""
    entries = {entry['name']: entry for entry in _catalog(summary)}
    try:
        if response['tool'] not in entries:
            raise ValueError('execution_operation_not_available')
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        validate_schema(arguments, entries[response['tool']]['input_schema'])
    except (KeyError, TypeError, ValueError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    return ToolCall(response['tool'], {'arguments': arguments, 'assignment': summary['assignment'],
                                       'target': summary['target'], 'requested': summary['requested'],
                                       'completed': summary['execution_completed'],
                                       'log_window_bytes': ctx.settings['log_window_bytes']})
