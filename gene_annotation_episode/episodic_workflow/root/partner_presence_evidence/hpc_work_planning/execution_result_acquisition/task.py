"""The task: acquire the requested result files of the handed-off A107 job through the job service.

The model is the router: at each decision it selects one defined operation with controlled operands, and code
carries it out. No operation runs a command the model wrote.

The operations, on the ``job_access`` service and the Episode's store:

- ``execution_results_status``: one status request for the job of the held handoff row (``JobAccess.check``); the
  service writes the check row.
- ``execution_results_collect``: the fetch of the requested result files (``JobAccess.fetch`` with the job service's
  names of the requested paths): each file becomes an artifact this Episode holds and the service writes the
  closure row; the bounded first window of each requested path (``min(log_window_bytes, 1 MiB, length)``) is then
  read from the fetched artifact through custody (``ctx.store.open_artifact``) and retained.
- ``execution_results_read``: one further bounded window of a fetched file, inside the requested interval of its
  path, read from the held artifact in the same way.

A window names the fetched artifact it lies in, where it lies, how many bytes it holds and their digest; the bytes
stay in the fetched artifact. Each collect and read keeps its windows as a result record the Episode holds: an
artifact with the information body and a ``source`` record of provider ``episode.execution_result`` over it. A
request the job service refuses (the job has not ended: ``results_not_available``; a requested file the job did not
leave: ``result_not_in_catalog``; the transport is down) is the ``failed`` outcome the service returns: it is an
outcome of the unit and earns what the summary earns, nothing.

The task always offers a unit and never ends the Episode; the yield controller stops it. This episode does not wait
for a job: a status request stays available when nothing else is.

Settings (``ctx.settings``): ``log_window_bytes`` (the bound of the first window ``execution_results_collect``
retains of each requested path) and the yield profiles (``yield_estimator.py``)."""
import hashlib

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    ContractError, canonical, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    digest)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TRANSPORT_ERROR = 'a107_execution_result_acquisition_selection_has_no_argument_transport'
RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information'
MEBIBYTE = 1024 * 1024

_OFFSET = {'type': 'integer', 'minimum': 0}
_FILE_LIMIT = {'type': 'integer', 'minimum': 1, 'maximum': MEBIBYTE}

STATUS = {'name': 'execution_results_status',
          'description': 'Ask the job service once for the state of the handed-off job (queued, running, finished, '
                         'failed, cancelled or unknown) and whether its results are available. The check is '
                         'recorded; no bytes are acquired.',
          'input_schema': obj({})}
COLLECT = {'name': 'execution_results_collect',
           'description': 'Fetch the requested result files of the job through the job service. Each fetched file '
                          'is kept whole, the job is closed, and the first window of each requested path (at most '
                          'first_window_bytes) is retained. The job service refuses while the job has not ended '
                          '(failure code results_not_available).',
           'input_schema': obj({})}


def execution_results_status(arguments, ctx):
    """One status request for the handed-off job. The job service writes the check row, with the route's reply as
    its artifact, through the Episode's store: that row is the record of the observation. A request that fails is
    the ``failed`` outcome the service returns."""
    return ctx.services['job_access'].check(ctx, arguments['handoff_ref'])


def _window(store, path, file, offset, limit):
    """One byte window of a fetched result file, read through custody: the artifact it lies in, where it lies, the
    bytes it holds and their digest."""
    with store.open_artifact(file['ref']) as stream:
        stream.seek(offset)
        data = stream.read(limit)
    return {'path': path, 'artifact_ref': file['ref'], 'offset': offset, 'returned_bytes': len(data),
            'size_bytes': file['bytes'], 'sha256': hashlib.sha256(data).hexdigest()}


def _retain(ctx, tool_name, arguments, windows):
    """Keep one acquisition as a result record this Episode holds: an artifact with its information body (the
    assignment it serves, the closure row of the fetch and the windows) and a ``source`` record over it."""
    closure = arguments['closure']
    body = {'version': RESULT_VERSION, 'assignment': arguments['assignment'], 'tool_name': tool_name,
            'closure_ref': closure['ref'], 'windows': windows}
    with ctx.store.transaction():
        artifact = ctx.store.artifact(canonical(body).encode('utf-8'), 'application/json')
        source = ctx.store.put('source', {
            'provider': RESULT_PROVIDER,
            'accession': 'execution_result_' + digest([ctx.run_id, ctx.episode_id, ctx.operation_key]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': RESULT_VERSION, 'retrieved_at': closure['at']}, origin='tool')
    return {'status': 'completed', 'result_ref': source['id'], 'artifact_ref': artifact}


def execution_results_collect(arguments, ctx):
    """Fetch the requested result files of the handed-off job and retain the bounded first window of each requested
    path. The job service fetches each file whole as an artifact this Episode holds and writes the closure row; a
    request it refuses is the ``failed`` outcome it returns."""
    requested, names = arguments['requested'], arguments['names']
    fetched = ctx.services['job_access'].fetch(ctx, arguments['assignment']['handoff_ref'],
                                               names=[names[path] for path in requested])
    if fetched['status'] != 'completed':
        return fetched
    files = {item['name']: item for item in fetched['results']}
    bound = min(ctx.settings['log_window_bytes'], MEBIBYTE)
    windows = [_window(ctx.store, path, files[names[path]], start, bound if length is None else min(bound, length))
               for path, (start, length) in requested.items()]
    closure = {'ref': fetched['closure_ref'], 'at': fetched['closed_at']}
    return _retain(ctx, 'execution_results_collect', {**arguments, 'closure': closure}, windows)


def execution_results_read(arguments, ctx):
    """Retain one selected byte window of a fetched result file. A window outside the requested interval of its path
    is an invalid outcome."""
    window = arguments['window']
    start, length = arguments['requested'][window['path']]
    if window['offset'] < start or (length is not None and window['offset'] + window['limit'] > start + length):
        return {'status': 'invalid', 'feedback': {'category': 'arguments_or_reference',
                                                  'code': 'execution_results_selector_conflict'}}
    return _retain(ctx, 'execution_results_read', arguments,
                   [_window(ctx.store, window['path'], arguments['file'], window['offset'], window['limit'])])


TOOLS = {'execution_results_status': execution_results_status,
         'execution_results_collect': execution_results_collect,
         'execution_results_read': execution_results_read}

RESULT_INSTRUCTIONS = (
    '\n\nThe context shows the job (its last observed state and whether its results were fetched), the requested '
    'paths with their byte intervals, and the outcome of every operation so far. The job service fetches the result '
    'files of a job only once the job has ended: before that it refuses with the failure code '
    'results_not_available, nothing is acquired and the job stays open for a later acquisition. This episode does '
    'not wait for a job. A fetched file is the file of the job\'s directory as it stood at the fetch, kept whole '
    'with its digest; a window is a part of that one fetched file. The state of the job does not establish that '
    'the bytes are the output of that attempt.'
    '\n\nCredit. The credit is the credit unit times the fraction of the requested bytes that the retained windows '
    'cover, each byte position counted once whatever the read boundaries, averaged over the requested paths. Bytes '
    'an earlier acquisition of this job already retained, a status request, a refused fetch and a window of bytes '
    'already retained earn nothing. When the results are not available, or when every requested byte is retained, '
    'select execution_results_status.')
ANSWER_INSTRUCTION = (
    '\n\nAnswer with one selection: kind "tool", the name of one of these operations in tool and its operands in '
    'arguments (an empty object for an operation without operands). You select the operation; code carries it out. '
    'No operation ends the episode: it ends when further operations no longer earn credit.')


def operation_catalog(summary):
    """The operations offered now: a status request always, the fetch while the job is not closed, and a further
    window once files are fetched."""
    catalog = [STATUS]
    if not summary['job']['closed']:
        catalog.append(COLLECT)
    if summary['fetched_files']:
        catalog.append({'name': 'execution_results_read',
                        'description': 'Retain one further byte window (path, offset, limit) of a fetched file, '
                                       'inside the requested interval of that path.',
                        'input_schema': obj({'path': {'type': 'string', 'enum': sorted(summary['fetched_files'])},
                                             'offset': _OFFSET, 'limit': _FILE_LIMIT})})
    return catalog


def selection_schema(catalog):
    """What the model answers with: one of the offered operations and its operands."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
        for entry in catalog]}})


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def instructions(catalog):
    """What the episode is for, what a result acquisition means and earns, and the operations available now."""
    operations = ''.join('\n- ' + entry['name'] + ': ' + entry['description'] for entry in catalog)
    return GOAL + RESULT_INSTRUCTIONS + '\n\nOperations available now:' + operations + ANSWER_INSTRUCTION


def decision_context(summary, feedback, settings):
    """What the decision needs: the job, what was requested, what was acquired so far and the credit."""
    job, fetched = summary['job'], summary['fetched_files']
    return {'feedback': feedback,
            'job': {'handoff_ref': summary['assignment']['handoff_ref'], 'job': job['job'],
                    'resource_id': job['resource_id'], 'kind': job['kind'], 'submitted_at': job['submitted_at'],
                    'last_observed_state': job['last_observed_state'] or 'not_observed',
                    'last_observed_at': job['last_observed_at'], 'results_fetched': job['closed']},
            'requested': [{'path': path, 'offset': start, 'limit': length,
                           'fetched_file_bytes': fetched[path]['bytes'] if path in fetched else None}
                          for path, (start, length) in summary['requested'].items()],
            'first_window_bytes': min(settings['log_window_bytes'], MEBIBYTE),
            'acquisitions': summary['acquisitions'], 'complete': summary['completed'],
            'credit': summary['credit_view']}


def decide(summary, feedback, ctx):
    """One operation: the model selects it from the job, what was requested, what was acquired so far and the
    credit."""
    catalog = operation_catalog(summary)
    return ModelRequest('REASONING', instructions(catalog), decision_context(summary, feedback, ctx.settings),
                        generation_schema(selection_schema(catalog)))


def action(response, summary, records, ctx):
    """The one operation the answer selects, or a rejection (no unit): it names an offered operation with operands
    that fit its schema. Every operand of the tool call that is not the model's own choice is taken from the
    summary, because a tool is handed no summary; a window outside the requested interval is an ``invalid``
    outcome of the unit."""
    schema = selection_schema(operation_catalog(summary))
    try:
        value = decode_response(response, schema)
        Draft202012Validator(schema).validate(value)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    tool, assignment = selection['tool'], summary['assignment']
    if tool == 'execution_results_status':
        return ToolCall(tool, {'handoff_ref': assignment['handoff_ref']})
    if tool == 'execution_results_collect':
        return ToolCall(tool, {'assignment': assignment, 'requested': summary['requested'],
                               'names': summary['result_names']})
    return ToolCall(tool, {'window': selection['arguments'],
                           'file': summary['fetched_files'][selection['arguments']['path']],
                           'closure': {'ref': summary['job']['closure_ref'], 'at': summary['job']['closed_at']},
                           'assignment': assignment, 'requested': summary['requested']})
