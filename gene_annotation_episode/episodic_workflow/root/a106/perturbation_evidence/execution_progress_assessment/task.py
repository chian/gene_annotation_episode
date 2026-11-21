"""The task: one selected action per unit on the job the commissioner handed over.

The model is the router: it picks one defined action with controlled arguments (a probability, a held check
reference, a log name with a byte window, a number of seconds, a dependency handle); code carries it out through the
job services. The model writes and runs no command.

| Action | Code | Service |
|---|---|---|
| ``progress_observe`` | one check of the job: ``job_access.check`` on the held handoff row, read by ``job_progress.status_reading``; the expectation of the check is recorded in the estimate table before the status request and resolved after it | ``job_access``, ``estimate_table`` |
| ``progress_read`` | a check row the Episode holds, read again through custody | none |
| ``progress_log`` | one byte window of a log of the job: ``job_access.window``; offered while the commissioner asked for log windows and the job's route keeps logs (a local or a PBS job; an API job has none) | ``job_access`` |
| ``progress_wait`` | a wait for the job's end event or a reconsideration time: ``native_events.wait``; offered while the handoff names an event target and no end event was received | ``native_events`` |
| ``monitor_dependency`` | a monitor of this episode's own kind for one job the target directly depends on (slot ``monitor``); offered while the commissioner passed dependencies | |

Carried from the old ``task.py`` (``ProgressMonitoringTask``), ``task_decision.py``, ``task_instructions.py``,
``progress_operations.py`` (``progress.observe``, ``progress.read``, ``progress.log``) and ``waiting.py`` (the wait
on native event targets). The old progress provider (``describe_progress_target``, ``observe_progress``,
``read_progress``) is the job service now; a request the job service cannot answer is a returned ``failed`` outcome
of its unit, with its credit like any other. The task always offers ``progress_observe`` and never ends the
Episode. Not carried: the decision exchange, the report update the model wrote with each decision, the launch
instruction and tool knowledge libraries in the request (a monitor launches nothing and runs no tool of those
libraries), the progress-time receipt of the Episode's own units, the selection of fields per observation (one
status request answers all of them; the assignment's ``requested_fields`` limits what is kept of it).

The request is written for the kind of route of the job at hand (``JOB_KINDS``, by the ``kind`` of the handoff
row): a command the route runs (``local``, ``pbs``: return code, duration, elapsed seconds, logs) or a job a public
web service works on (``api``: the service's status word, whether the finished job found hits, no log). For an API
job ``decide`` reads the service's spacing between two status requests of one job from the route
(``job_access.read('describe', resource_id)``) and shows it with the job: a check that comes earlier is not sent
and is the returned ``failed`` outcome ``provider_spacing_required`` of its unit. A106's own jobs are BV-BRC
application-service jobs, and the API route has no protocol for that service (``api_job_route.PROTOCOLS`` holds
``ncbi_blast``): the request of an API job was run on a BLAST job of the protocol test service
(``tests/test_monitor_api_job.py``), not on a BV-BRC job.

Settings this episode reads (``ctx.settings``): ``cost`` (the cost of one unit, also the cost of a check in the
estimate table) and ``parameters`` (``yield_estimator.py``)."""
from datetime import datetime, timedelta, timezone

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import (
    check_expectation, check_resolution, check_view, progress_information, status_reading)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)

from . import goal as goal_file

CHILD_SLOTS = {'monitor': goal_file.BINDING_PATH}
SERVICES = ('job_access', 'estimate_table', 'native_events')
# The kind of action a check of this monitor is in the estimate table.
CHECK_KIND = 'A106 job progress check'
# The largest log window one unit reads: its text is shown to the model in the next request.
LOG_WINDOW_BYTES = 4000
MODEL_ROLE = 'REASONING'

# What the request says of a job by the kind of its route: what a check shows beside the state and the availability
# of results, which facts earn credit, and what earns none.
COMMAND_JOB = {
    'check_shows': 'its return code and duration once it has ended, its elapsed seconds while it runs and the size '
                   'of its logs',
    'facts': 'a state, the availability of results, a return code, a final duration, the availability of a log',
    'no_credit': 'reading a check again, a log window, a wait, timestamps, the elapsed time of an unfinished job or '
                 'growing log sizes'}
SERVICE_JOB = {
    'check_shows': "the web service's own status word (provider_status) and, once the job has finished, whether it "
                   'found hits (has_hits). The job runs on a public web service: an unfinished job is reported as '
                   'queued, because the service does not say whether it has begun, and the job has no return code, '
                   'duration or log. The service asks for a minimum time between two status requests of one job '
                   '(seconds_between_status_requests in job). A check that comes earlier is not sent: it writes no '
                   'check record and returns failed with provider_spacing_required and retry_after_seconds, the '
                   'seconds until a check can be sent',
    'facts': "a state, the availability of results, the service's status word, whether the finished job found hits",
    'no_credit': 'reading a check again, a check that was not sent or timestamps'}
JOB_KINDS = {'local': COMMAND_JOB, 'pbs': COMMAND_JOB, 'api': SERVICE_JOB}

ACTIONS = {
    'progress_observe':
        'Check the job: one fresh status request to its resource through the job service. It writes a check '
        "record: the job's state (queued, running, finished, failed, cancelled or unknown), whether its results "
        'are available, {check_shows}. Give informative_probability: your probability (0 to 1) that this check '
        'shows a fact the checks before it do not. It is recorded before the request is made and compared with '
        'what the check showed.',
    'progress_read':
        'Read again one check record you hold (check_ref, from checks). No request is made to the job.',
    'progress_log':
        "Read one byte window of the job's stdout.log or stderr.log as it is now: limit bytes from offset. The "
        'text is shown to you with that unit in units. The sizes of the logs are in the latest check.',
    'progress_wait':
        "Wait for the job's end event, or until reconsider_after_seconds have passed, whichever comes first. The "
        "event means the job's process has ended and its exit was recorded; it does not establish that results "
        'are ready, so check the job afterwards. Waiting only reports readiness and earns nothing. The whole wait '
        'is spent inside this episode: your commissioner receives nothing until the episode ends, and it can wait '
        'for the job itself after your return. Wait only when you expect the job to end within the seconds you '
        'give.',
    'monitor_dependency':
        'Commission a monitor of your own kind for one job in dependencies (a job your target directly depends '
        'on). It returns its credit, what it found and its check records. No descendant traversal, fanout, '
        'cadence or depth is prescribed.',
}
CONTEXT_GUIDE = (
    'In the context: job is the job you were handed (launch_estimates is what its launch expected of it); now is '
    'the UTC time of this decision; checks are the check records of the job you hold, the earliest first '
    '(made_by says whether your commissioner handed it to you or you made it); units are your actions so far, in '
    'order, with the credit each earned (the last one also shows the text of a log window or the detail of a '
    'failed request); credit is your credit now, the unit of one informative check and the cost of one action; '
    'earlier_checks_of_this_kind counts the checks of this kind made so far, in this and earlier runs (resolved: '
    'compared with what the check showed; open: not answered), the credit they were expected to earn, the credit '
    'they earned and the ratio of the two (correction); dependencies, when present, are the jobs your target '
    'directly depends on; feedback, when present, says why your last answer was not accepted.\n')
CREDIT_GUIDANCE = (
    'Credit: you earn one information_unit for each check that shows a fact about its job which the checks before '
    'it, including those your commissioner handed you, do not show: {facts}. A check that shows nothing new earns '
    'nothing. Neither do {no_credit}. Repeated observation identities and read timestamps alone earn no new '
    'information. Credit measures monitoring information, not scientific progress.\n')
ACTION_BOUNDARY = (
    'You cannot end this episode: its yield controller ends it when further actions are not expected to earn more '
    'than they cost, and only then does your commissioner receive your return. When you expect no new fact soon, '
    'select an action that takes no time (a check, or reading a check again): the controller then ends the episode '
    'with what you have found. Do not emit a stop action or invent a turn budget, approval review, quality gate, '
    'experiment, term or observation. Do not execute native provider tools or write commands. The host executes '
    'your selected action.\n')
RETURN_GUIDANCE = (
    "What returns to your commissioner is your credit and the facts code reads from your latest check (the job's "
    'state, whether results are available, when it was observed, the measurements your commissioner asked for) '
    'with the references of your check records. No text of yours and no log text is returned.\n')


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


# -- the tools ---------------------------------------------------------------------------------------------------
def progress_observe(arguments, ctx):
    """One check of the job. What is expected of it is recorded before the status request; what it gave (whether
    it showed a new fact, in this monitor's credit units) after it. A request the route could not answer is the
    returned outcome ``failed``: no check row, and the expectation stays open."""
    table, expectation = ctx.services['estimate_table'], arguments['expectation']
    held = (arguments['known_progress_refs'], arguments['requested_fields'], arguments['information_unit'])
    before = progress_information(ctx.store, *held)['credit']
    table.expect(CHECK_KIND, expectation, key=ctx.operation_key, at=datetime.now(timezone.utc).isoformat())
    outcome = ctx.services['job_access'].check(ctx, arguments['handoff_ref'], assess=status_reading)
    if outcome['status'] != 'completed':
        return outcome
    # Informative: the information credit of the held check rows rose. (An API route answers the status of an
    # ended job from its record, with the time it was observed: that check is the row already held, not a new one.)
    informative = progress_information(ctx.store, *held)['credit'] > before
    table.resolve(ctx.operation_key, check_resolution(informative, expectation, outcome['state']),
                  at=outcome['observed_at'])
    return {**outcome, 'informative': informative}


def progress_read(arguments, ctx):
    """A check row the Episode holds, read again through custody."""
    row = ctx.store.table(JOB_LEDGER).get(arguments['check_ref'])
    return {'status': 'completed', **check_view(row, arguments['requested_fields'])}


def progress_log(arguments, ctx):
    """One byte window of a log of the job; the bytes come into custody and their text is returned."""
    outcome = ctx.services['job_access'].window(ctx, arguments['handoff_ref'], arguments['log'],
                                                offset=arguments['offset'], limit=arguments['limit'])
    if outcome['status'] != 'completed':
        return outcome
    return {**outcome, 'text': ctx.store.get_artifact(outcome['content_ref']).decode('utf-8', 'replace')}


async def progress_wait(arguments, ctx):
    """Wait for the job's end event after the cursor last seen, or for the reconsideration time. The receipt of
    the event comes into custody."""
    outcome = await ctx.services['native_events'].wait(ctx, {
        'version': 'event_condition_v1', 'reconsider_at': arguments['reconsider_at'],
        'events': [{'handle': arguments['event_target'], 'event': 'state_changed',
                    'after_cursor': arguments['after_cursor']}]})
    if outcome['status'] != 'completed':
        return {'status': 'failed', 'failure': {'code': outcome['feedback']['code'],
                                                'detail': outcome['feedback']['detail']}}
    wake = outcome['result']
    return {'status': 'completed', 'woke_on': wake['reason'], 'observed_at': wake['observed_at'],
            'reconsider_at': wake['reconsider_at'],
            'event_cursor': max([arguments['after_cursor'], *(event['cursor'] for event in wake['events'])]),
            'receipt_refs': outcome['record_refs']}


TOOLS = {'progress_observe': progress_observe, 'progress_read': progress_read, 'progress_log': progress_log,
         'progress_wait': progress_wait}


# -- the decision ------------------------------------------------------------------------------------------------
def offered(summary):
    """The actions this decision offers. A check is always offered, so a unit can always be accepted. A log window
    and a wait are offered only for a job that has a log or an end event: an API job has neither."""
    names = ['progress_observe']
    if summary['checks']:
        names.append('progress_read')
    if 'log_windows' in summary['requested_fields'] and summary['job']['log_names']:
        names.append('progress_log')
    if summary['job']['event_target'] is not None and summary['event_cursor'] == 0:
        names.append('progress_wait')
    if summary['dependencies']:
        names.append('monitor_dependency')
    return names


def selection_schema(summary):
    """The closed decision form: exactly one of the offered actions, each with its controlled arguments."""
    arguments = {
        'progress_observe': {'informative_probability': {'type': 'number', 'minimum': 0, 'maximum': 1}},
        'progress_read': {'check_ref': {'enum': [check['check_ref'] for check in summary['checks']]}},
        'progress_log': {'log': {'enum': summary['job']['log_names']}, 'offset': {'type': 'integer', 'minimum': 0},
                         'limit': {'type': 'integer', 'minimum': 1, 'maximum': LOG_WINDOW_BYTES}},
        'progress_wait': {'reconsider_after_seconds': {'type': 'number', 'minimum': 0}}}
    options = []
    for name in offered(summary):
        if name == 'monitor_dependency':
            options.append(_object({'kind': {'const': 'monitor_dependency'}, 'dependency_handle': {
                'enum': [row['handle'] for row in summary['dependencies']]}}))
        else:
            options.append(_object({'kind': {'const': 'tool'}, 'tool': {'const': name},
                                    'arguments': _object(arguments[name])}))
    return _object({'selection': {'anyOf': options}})


def instructions(summary):
    kind = JOB_KINDS[summary['job']['resource_kind']]
    actions = ''.join('- ' + name + ': ' + ACTIONS[name].format(**kind) + '\n' for name in offered(summary))
    return (goal_file.GOAL + '\n'
            + 'Each decision selects exactly one action; the host carries it out and the next decision shows you '
              'its outcome. The actions you can select now:\n' + actions
            + CONTEXT_GUIDE + CREDIT_GUIDANCE.format(**kind) + RETURN_GUIDANCE + ACTION_BOUNDARY)


def decision_context(summary, feedback, ctx):
    """What the decision needs, and nothing of the controller's internals."""
    job, information = summary['job'], summary['monitoring_information']
    history = ctx.services['estimate_table'].read('kind_statistics', CHECK_KIND)
    context = {
        'job': {'handle': job['handle'], 'resource': job['resource_id'], 'resource_kind': job['resource_kind'],
                'submitted_at': job['submitted_at'], 'launch_estimates': job['launch_estimates']},
        'now': ctx.clock.now,
        'checks': summary['checks'],
        'units': summary['units'],
        'credit': {'current': information['credit'], 'information_unit': information['information_unit'],
                   'cost_of_one_action': ctx.settings['cost']},
        'earlier_checks_of_this_kind': {name: history[name] for name in (
            'resolved', 'open', 'expected_gain', 'obtained_gain', 'correction')}}
    if job['resource_kind'] == 'api':
        context['job']['seconds_between_status_requests'] = ctx.services['job_access'].read(
            'describe', job['resource_id'])['poll_spacing_seconds']
    if summary['dependencies']:
        context['dependencies'] = [{name: row[name] for name in ('handle', 'resource_kind', 'submitted_at',
                                                                 'latest_check')}
                                   for row in summary['dependencies']]
    if feedback is not None:
        context['feedback'] = feedback
    return context


def decide(summary, feedback, ctx):
    return ModelRequest(MODEL_ROLE, instructions(summary), decision_context(summary, feedback, ctx),
                        generation_schema(selection_schema(summary)))


def action(response, summary, records, ctx):
    schema = selection_schema(summary)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    selected = decoded['selection']
    if selected['kind'] == 'monitor_dependency':
        return ChildCall('monitor', {'dependency_handle': selected['dependency_handle']})
    name, arguments = selected['tool'], selected['arguments']
    if name == 'progress_observe':
        return ToolCall(name, {
            'handoff_ref': summary['handoff_ref'], 'known_progress_refs': summary['known_progress_refs'],
            'requested_fields': summary['requested_fields'], 'information_unit': summary['information_unit'],
            'expectation': check_expectation(arguments['informative_probability'], summary['information_unit'],
                                             ctx.settings['cost'])})
    if name == 'progress_read':
        return ToolCall(name, {'check_ref': arguments['check_ref'],
                               'requested_fields': summary['requested_fields']})
    if name == 'progress_log':
        return ToolCall(name, {'handoff_ref': summary['handoff_ref'], **arguments})
    reconsider = datetime.fromisoformat(ctx.clock.now) + timedelta(seconds=arguments['reconsider_after_seconds'])
    return ToolCall(name, {'event_target': summary['job']['event_target'], 'after_cursor': summary['event_cursor'],
                           'reconsider_at': reconsider.isoformat()})
