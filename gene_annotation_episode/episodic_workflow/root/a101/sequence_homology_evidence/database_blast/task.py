"""The task: one hosted database search of the assigned query, followed without waiting for it.

The model is the router. It answers with one defined action as JSON: ``submit`` (the search: program, database,
hit-list size and API resource, as the commission names them), ``check`` (one status request of the held search),
``fetch_and_grade`` (fetch the report of the finished search and grade it into the database sheet in the same unit) or
``hold`` (a reason from a fixed vocabulary). Each action has ONE deterministic check over the filled JSON and what the
episode holds (``database_blast_search.check_*``): if it names problems ``action`` raises ``Rejected`` with them (each a
code and the field it concerns): no unit is made and the model answers again. If it passes, the tool runs as one unit
(``submit_search``, ``check_search``, ``fetch_and_grade_search``: each one library call composing existing functions);
a fault after a passed check is the environment's, reported once as failed and not retried. Grading follows the fetch in
the same unit: no step of the model stands between a finished search's report and its being counted in credit.

The search runs at the service. This episode never sits waiting for it: a ``check`` waits only the spacing the service
requires between two status requests (and says so to the model beforehand), and an unfinished search is held. The
decision shows the duration predicted at the submission (learned from the measured durations of earlier searches of the
same kind, on the estimate table), the service's own estimate, the seconds since the submission and how far past each the
search is: facts, never a deadline. The task never ends the Episode; the yield controller does.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    DATABASES, FAILURE_CODES, HITLIST_RANGE, HOLD_REASONS, check_fetch_request, check_hold, check_search,
    check_status_request, check_submit, fetch_and_grade_search, search_kind, search_view, seconds_until_allowed,
    submit_search, timing)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

INSTRUCTIONS = (
    'You are the database search agent for one assigned query sequence. This episode exists to search that query '
    'against one hosted database through the public NCBI BLAST service (the program, database and hit-list size are the '
    'commission\'s, in commission), to follow the search to its end, and to return what it established to the parent: '
    'its handoff, what its status requests showed and, when the service has finished it, the graded result.\n'
    '\n'
    'You do not write a request. You answer with one action as JSON; code checks your JSON before anything runs and '
    'runs the job.\n'
    '- submit: the search, with program, database, hitlist_size and resource_id exactly as the commission gives them. '
    'One submission only: it is refused while a search is held.\n'
    '- check: one status request of the held search (handoff_ref: the handoff record in search). The service allows a '
    'status request only a set time after the last contact (seconds_until_next_status_request): if you check earlier, the '
    'unit waits that time (up to a minute) and then makes the one request, and this episode does not sit waiting for a '
    'search. When the latest check showed the search not finished and seconds_until_next_status_request is not 0, hold '
    '(search_not_finished): the parent comes back later with the records. Check when that time is 0 or when no check has '
    'been made yet.\n'
    '- fetch_and_grade: only when the latest check shows the search finished (state finished). Code fetches the '
    'report and grades it into the database sheet in the same unit; nothing more is needed for the result to count.\n'
    '- hold: do nothing now, with a reason: search_not_finished (the search is accepted and not finished), '
    'failure_not_retryable (a unit failed or the service reported the search failed or lost; the same call gives the same '
    'result) or graded_result_established (the work is done).\n'
    'If your JSON is wrong you are told each problem as a code with the field it concerns (feedback.problems) and nothing '
    'has run; fix those fields and answer again. A correct action works on the first try.\n'
    '\n'
    'What you are shown. state: not_submitted, outstanding, finished, graded or failed. unit_rows: each earlier action '
    'with its status, failure_code (a fixed vocabulary) and retryable. timing: the seconds since the submission, the '
    'duration predicted at the submission from the measured durations of earlier searches of this kind (absent when none '
    'was measured), the service\'s own estimate, and how far past each the search is (negative: before it); '
    'learned_durations: what earlier searches of this kind measured. These are facts for choosing between check and hold; '
    'there is no deadline and no cancel. A search far past its prediction may still finish. The service may be slow or '
    'down: a request it does not answer is a failed outcome with its code, not retried blindly.\n'
    '\n'
    'Credit is the measure of this episode, and only for what is new: the handoff (credit.handoff_unit) when a search is '
    'newly submitted, a status request that shows a fact the earlier ones did not (credit.information_unit: queued, then '
    'finished), and the graded result (credit.graded_unit). A repeat, a hold and a failure earn nothing. When nothing more '
    'can be gained, a few holds follow and the yield controller ends the episode. You cannot end it.')


def output_schema():
    """The answer: one defined action with its controlled fields."""
    def one(name, **fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'enum': [name]}, **fields}}
    handoff = {'type': 'string', 'minLength': 1}
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': [
                one('submit', program={'type': 'string', 'enum': sorted(PROGRAM_UNITS)},
                    database={'type': 'string', 'enum': list(DATABASES)},
                    hitlist_size={'type': 'integer', 'minimum': HITLIST_RANGE[0], 'maximum': HITLIST_RANGE[1]},
                    resource_id={'type': 'string', 'minLength': 1}),
                one('check', handoff_ref=handoff),
                one('fetch_and_grade', handoff_ref=handoff),
                one('hold', reason={'type': 'string', 'enum': list(HOLD_REASONS)})]}}}


def decide(summary, feedback, ctx):
    fields, search = summary['fields'], summary['search']
    description = ctx.services['job_access'].read('describe', fields['resource_id'])
    learned = ctx.services['estimate_table'].read('kind_statistics', search_kind(fields['program'], fields['database']))
    context = {
        'commission': {**fields, 'query': {'record': summary['query']['subject_ref'],
                                           'molecule': summary['query']['molecule'],
                                           'length': summary['query']['length']}},
        'credit': {**summary['units'],
                   'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
        'state': summary['state'], 'last_failure_code': summary['last_failure_code'],
        'search': search, 'unit_rows': summary['unit_rows'],
        'learned_durations': {'resolved': learned['resolved'], 'duration_seconds': learned['duration_seconds']},
        'service': {'request_spacing_seconds': description['request_spacing_seconds'],
                    'poll_spacing_seconds': description['poll_spacing_seconds']},
        'hold_reasons': list(HOLD_REASONS), 'failure_codes': list(FAILURE_CODES),
        'yield_table': summary['yield_table'], 'feedback': feedback}
    if search is not None:
        context['timing'] = timing(search, ctx.clock.now)
        context['seconds_until_next_status_request'] = seconds_until_allowed(description, search, ctx.clock.now)
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items()
                                                     if value is not None}, output_schema())


def action(response, summary, records, ctx):
    """The model's JSON to a unit. The action's one check runs here, before anything runs; an action with problems is
    rejected with the list of them (no unit, no observation)."""
    try:
        Draft202012Validator(output_schema()).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    name, fields, query = chosen['name'], summary['fields'], summary['query']
    search, state = search_view(records), summary['state']
    if name == 'submit':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        problems = check_submit(chosen, fields=fields, query_molecule=query['molecule'], resources=resources,
                                search=search, failures=summary['failures'])
    elif name == 'check':
        problems = check_status_request(chosen, search=search, state=state)
    elif name == 'fetch_and_grade':
        problems = check_fetch_request(chosen, search=search, state=state)
    else:
        problems = check_hold(chosen, state=state)
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    if name == 'submit':
        return ToolCall('submit', {'request': {key: chosen[key] for key in ('program', 'database', 'hitlist_size',
                                                                            'resource_id')},
                                   'fields': fields, 'sequence_ref': query['sequence_ref']})
    if name == 'check':
        return ToolCall('check', {'handoff_ref': chosen['handoff_ref'], 'resource_id': fields['resource_id']})
    if name == 'fetch_and_grade':
        return ToolCall('fetch_and_grade', {'handoff_ref': chosen['handoff_ref'], 'fields': fields,
                                            'query_ref': query['subject_ref']})
    return ToolCall('hold', {'reason': chosen['reason']})


def submit(arguments, ctx):
    """The one submission, with the duration predicted first, by the library's one function."""
    return submit_search(ctx, request=arguments['request'], fields=arguments['fields'],
                         sequence_ref=arguments['sequence_ref'])


async def check(arguments, ctx):
    """One status request (after the wait the spacing needs), by the library's one function."""
    description = ctx.services['job_access'].describe(arguments['resource_id'])
    return await check_search(ctx, handoff_ref=arguments['handoff_ref'], description=description)


def fetch_and_grade(arguments, ctx):
    """The fetch of the report and its grading into the database sheet, as one unit."""
    return fetch_and_grade_search(ctx, handoff_ref=arguments['handoff_ref'], fields=arguments['fields'],
                                  query_ref=arguments['query_ref'])


def hold(arguments, ctx):
    """Nothing is run: the unit's outcome is the reason."""
    return {'status': 'held', 'reason': arguments['reason']}


TOOLS = {'submit': submit, 'check': check, 'fetch_and_grade': fetch_and_grade, 'hold': hold}
