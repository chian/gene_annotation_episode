"""The task: one BV-BRC database search of the assigned query, done in one loop.

The model is the router. It answers with one defined action as JSON, each with ONE deterministic check over the filled
JSON and what the episode holds (``bvbrc_blast_search.check_*``): if the check names problems ``action`` raises
``Rejected`` with them (each a field and a code, and what to choose from): no unit is made and the model answers again.
A passed check runs as one unit, by one library function; a fault after a passed check is the environment's, reported
once as failed and not retried.

* ``estimate``: the expected duration of the coming search (seconds) and the basis it rests on, made before anything is
  launched and again to revise it; code records it on the estimate table as the expectation of the launch.
* ``launch``: submit the ``Homology`` search. Gated: refused unless an estimate is held.
* ``fix``: offered after a failure: the failure code addressed and the request field that will change. After it a launch
  is accepted, one whose request differs from the failed one in that field.
* ``monitor``: one status request after a wait the model chooses (its lower end is what the service's spacing needs);
  the model gives with it the expected remaining seconds, recorded while the search is not finished; the first request
  that shows the search ended resolves the estimate with the measured duration.
* ``extract``: only when the latest monitor shows the search finished: fetch the result files and grade them in the same
  unit; the head's credit counts it with no further call.

The decision shows, as controlled facts: the commission, the state, the held estimate and what the estimate table has
learned of each kind of search, the seconds since the launch and how far past the estimate (facts, never a deadline), the
minimum wait of a status request, and each earlier unit. The task never ends the Episode; the yield controller does.

Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.annotation_settling import (
    settle_annotations)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.blast_claim_keeping import (
    keep_taxon_claims)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_blast_search import (
    DATABASES, ESTIMATE_BASES, ESTIMATE_RANGE, FAILURE_CODES, REQUEST_FIELDS, WAIT_RANGE_MAX, check_estimate,
    check_extract, check_fix, check_launch, check_monitor, fetch_and_grade_search, launch_search,
    learned_statistics, minimum_wait, monitor_search, record_estimate, search_facts, search_view, timing)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

INSTRUCTIONS = (
    'You are the database search agent for one assigned query sequence. This episode exists to search that query '
    'against one precomputed BV-BRC database through the BV-BRC application service (the program, database and '
    'resource are the commission\'s, in commission), to follow the search to its end and to return what it established '
    'to the parent: the estimate, the handoff, what the status requests showed and the graded result.\n'
    '\n'
    'The commission\'s until says where this commission ends. launched: estimate and launch, and the episode ends the '
    'moment the launch completes (the search keeps running at the service and the parent is told how long to expect; a '
    'later commission resumes it). extracted: follow the search to its graded result; when resumed is true the search was '
    'launched by an earlier commission (state launched or finished): do not estimate or launch, monitor it and extract. '
    'The episode ends by itself when its credit reaches the target of the commission; you cannot end it.\n'
    '\n'
    'You do not write a request. You answer with one action as JSON; code checks your JSON before anything runs and runs '
    'the job.\n'
    '- estimate: before anything is launched, the program and database you will search, and the seconds the search is '
    'expected to take (expected_seconds) and their basis, both exactly as learned_durations gives them for that '
    'program:database in ledger_estimate: the estimate comes from the ledger. With measured searches of that kind '
    '(measured is how many, typical_seconds their median, latest_seconds the newest first, duration_curve, when present, '
    'the curve of seconds against query length they make, with its seconds for this query) the basis is '
    'duration_curve_of_earlier_jobs and the seconds are duration_curve.seconds when the curve is present, else '
    'learned_from_earlier_searches and typical_seconds; with none the basis is no_earlier_measurement and the seconds are '
    'the fixed first figure. Any other figure is refused.\n'
    '- launch: the search, with program, database and resource_id as the commission gives them. Refused unless an '
    'estimate is held (state estimated). One launch per estimate.\n'
    '- monitor: one status request of the launched search (handoff_ref: the handoff record in search). wait_seconds is '
    'how long the unit waits before it asks: at least minimum_wait_seconds (the service allows a status request only a '
    'set time after the last contact) and at most the maximum shown. expected_remaining_seconds is your revised '
    'expectation of the time left, recorded while the search is not finished. The first request that shows the search '
    'ended records the measured duration, which the next estimate learns from. There is no deadline and no cancel.\n'
    '- extract: only when the latest monitor shows the search finished (state finished). Code fetches the result files '
    'and grades them in the same unit; nothing more is needed for the result to count.\n'
    '- fix: only after a failure (state failed): the failure code you address (last_failure_code) and the request field '
    'you will change (program, database or resource_id). Only after a fix does a launch pass, with a request that '
    'differs from the failed one in that field, after a new estimate.\n'
    'If your JSON is wrong you are told each problem as a code with the field it concerns (`problems` in each entry of feedback) and '
    'nothing has run; fix those fields and answer again. A correct action works on the first try.\n'
    '\n'
    'What you are shown. state: no_estimate, estimated, launched, finished, extracted or failed. unit_rows: each earlier '
    'action with its status, failure_code (a fixed vocabulary) and retryable. timing: the seconds since the launch, the '
    'seconds you estimated and how far past it the search is (negative: before it): facts, not a deadline. A search far '
    'past its estimate may still finish.\n'
    '\n'
    'Credit is the measure of this episode, bounded, and only for what is new in this commission: four things, each '
    'worth its unit once: an estimate held (credit.information_unit), the search launched (credit.handoff_unit), the '
    'search known ended (credit.information_unit: the first status that shows finished or failed; queued or running earns '
    'nothing) and the graded result (credit.graded_unit). The target is what is still obtainable under until. When the '
    'target cannot be reached (the search failed, or it keeps running) a few actions that earn nothing follow and the '
    'yield controller ends the episode. You cannot end it.')


def output_schema(state):
    """The answer: one defined action with its controlled fields. ``fix`` is offered only while a failure waits for it."""
    def one(name, **fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'enum': [name]}, **fields}}
    handoff = {'type': 'string', 'minLength': 1}
    seconds = {'type': 'number', 'minimum': 0, 'maximum': ESTIMATE_RANGE[1]}
    options = [
        one('estimate', program={'type': 'string', 'enum': sorted(PROGRAM_UNITS)},
            database={'type': 'string', 'enum': list(DATABASES)},
            expected_seconds={'type': 'number', 'minimum': ESTIMATE_RANGE[0], 'maximum': ESTIMATE_RANGE[1]},
            basis={'type': 'string', 'enum': list(ESTIMATE_BASES)}),
        one('launch', program={'type': 'string', 'enum': sorted(PROGRAM_UNITS)},
            database={'type': 'string', 'enum': list(DATABASES)}, resource_id={'type': 'string', 'minLength': 1}),
        one('monitor', handoff_ref=handoff, wait_seconds={'type': 'number', 'minimum': 0, 'maximum': WAIT_RANGE_MAX},
            expected_remaining_seconds=seconds),
        one('extract', handoff_ref=handoff)]
    if state == 'failed':
        options.append(one('fix', failure_code={'type': 'string', 'enum': list(FAILURE_CODES)},
                           field={'type': 'string', 'enum': list(REQUEST_FIELDS)}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': options}}}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the options of ``output_schema`` (as ``decide`` offers them;
    ``fix`` only while a failure waits for it). The names are the tool names."""
    return [option['properties']['name']['enum'][0] for option in output_schema(summary['state'])['properties']['action']['anyOf']]


def _resource(summary):
    request = summary['state_facts']['request']
    return summary['fields']['resource_id'] if request is None else request['resource_id']


def decide(summary, feedback, ctx):
    fields, search, facts = summary['fields'], summary['search'], summary['state_facts']
    description = ctx.services['job_access'].read('describe', _resource(summary))
    context = {
        'commission': {**fields, 'until': summary['until'], 'resumed': summary['resumed'],
                       'known_ended': summary['known_ended'], 'query': {'record': summary['query']['subject_ref'],
                                           'molecule': summary['query']['molecule'],
                                           'length': summary['query']['length']}},
        'credit': {**summary['units'],
                   'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
        'state': summary['state'], 'held_estimate': facts['estimate'], 'last_failure_code': summary['last_failure_code'],
        'failed_request': facts['failed_request'], 'fixed_field': facts['fixed_field'],
        'learned_durations': learned_statistics(ctx.services['estimate_table'], summary['query']['length'],
                                                ctx.clock.now),
        'unit_rows': summary['unit_rows'],
        'service': {'request_spacing_seconds': description['request_spacing_seconds'],
                    'poll_spacing_seconds': description['poll_spacing_seconds']},
        'wait_seconds_range': {'maximum': WAIT_RANGE_MAX}, 'estimate_seconds_range': list(ESTIMATE_RANGE),
        'failure_codes': list(FAILURE_CODES), 'yield_table': summary['yield_table'], 'feedback': feedback}
    if search is not None:
        context['search'] = search
        context['timing'] = timing(search, ctx.clock.now)
        context['minimum_wait_seconds'] = minimum_wait(description, search, ctx.clock.now)
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        output_schema(summary['state']))


def action(response, summary, records, ctx):
    """The model's JSON to a unit. The action's one check runs here, before anything runs; an action with problems is
    rejected with the list of them (no unit, no observation)."""
    try:
        Draft202012Validator(output_schema(summary['state'])).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    name, fields, query, facts = chosen['name'], summary['fields'], summary['query'], summary['state_facts']
    search = search_view(records)
    if name == 'estimate':
        learned = learned_statistics(ctx.services['estimate_table'], query['length'], ctx.clock.now)
        problems = check_estimate(chosen, state=facts, learned=learned, query_molecule=query['molecule'])
    elif name == 'launch':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        problems = check_launch(chosen, state=facts, fields=fields, query_molecule=query['molecule'],
                                resources=resources)
    elif name == 'fix':
        problems = check_fix(chosen, state=facts)
    elif name == 'monitor':
        problems = []
        if search is not None:
            description = ctx.services['job_access'].read('describe', _resource(summary))
            minimum = minimum_wait(description, search_facts(search), ctx.clock.now)
            problems = check_monitor(chosen, state=facts, search=search, minimum=minimum)
        else:
            problems = check_monitor(chosen, state=facts, search=None, minimum=0)
    else:
        problems = check_extract(chosen, state=facts, search=search)
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    if name == 'estimate':
        return ToolCall('estimate', {'estimate': {key: chosen[key] for key in ('program', 'database', 'expected_seconds',
                                                                               'basis')}})
    if name == 'launch':
        return ToolCall('launch', {'request': {key: chosen[key] for key in ('program', 'database', 'resource_id')},
                                   'estimate': facts['estimate'], 'sequence_ref': query['sequence_ref']})
    if name == 'fix':
        return ToolCall('fix', {'fix': {'failure_code': chosen['failure_code'], 'field': chosen['field']}})
    if name == 'monitor':
        return ToolCall('monitor', {'handoff_ref': chosen['handoff_ref'], 'wait_seconds': chosen['wait_seconds'],
                                    'expected_remaining_seconds': chosen['expected_remaining_seconds']})
    return ToolCall('extract', {'handoff_ref': chosen['handoff_ref'], 'request': facts['request'],
                                'query_ref': query['subject_ref'], 'scope': summary['scope'],
                                'organism': summary['organism']})


def estimate(arguments, ctx):
    """The estimate recorded on the estimate table before the launch, by the library's one function."""
    return record_estimate(ctx, estimate=arguments['estimate'])


def launch(arguments, ctx):
    """The one submission of the estimated search, by the library's one function."""
    return launch_search(ctx, request=arguments['request'], estimate=arguments['estimate'],
                         sequence_ref=arguments['sequence_ref'])


def fix(arguments, ctx):
    """The reasoning about a failure, as the controlled values the model chose: nothing is run."""
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [], 'fix': arguments['fix']}


async def monitor(arguments, ctx):
    """One status request after the wait, updating the estimate, by the library's one function."""
    return await monitor_search(ctx, handoff_ref=arguments['handoff_ref'], wait_seconds=arguments['wait_seconds'],
                                expected_remaining_seconds=arguments['expected_remaining_seconds'])


async def extract(arguments, ctx):
    """The fetch of the report and its grading into the database sheet, then the settling of the annotations
    (``settle_annotations``), as one unit."""
    graded = fetch_and_grade_search(ctx, handoff_ref=arguments['handoff_ref'], fields=arguments['request'],
                                    query_ref=arguments['query_ref'])
    if graded['status'] != 'completed':
        return graded
    taxa = keep_taxon_claims(ctx.store, search_source_ref=graded['graded_refs'][0], searched_ref=arguments['query_ref'])
    settled = await settle_annotations(ctx, scope=arguments['scope'], organism=arguments['organism'])
    return {**graded, 'graded_refs': [*graded['graded_refs'], *taxa, *settled],
            'record_refs': [*graded['record_refs'], *taxa, *settled]}


TOOLS = {'estimate': estimate, 'launch': launch, 'fix': fix, 'monitor': monitor, 'extract': extract}
