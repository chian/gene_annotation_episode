"""The task: one BV-BRC multiple sequence alignment of the assigned target with chosen candidates' sequences, done in one
loop. The model is the router: it answers with one defined action as JSON (``bvbrc_job_child.output_schema``); each action
has ONE deterministic check over the filled JSON and what the episode holds (``bvbrc_job_child.check_*``); a check with
problems makes ``action`` raise ``Rejected`` (no unit). A passed check runs as one unit by one library function:

* ``estimate``: ``per_candidate`` (how many sequences of each candidate; the job's size) and the expected seconds with the
  basis; code records it as the expectation of the launch.
* ``launch``: submit the ``MSA`` job (code fetches the sequences it chose, keeps them, labels them as a data product).
  Gated: refused unless an estimate is held, and refused when the alignment of the same inputs and settings is held.
* ``fix`` (after a failure), ``monitor`` and ``extract`` as in ``bvbrc_job_child``.

The decision shows the commission, the state, the held estimate, the planned size of the job and what the ledger has
learned of this kind of job, the seconds since the launch, the minimum wait and each earlier unit. The task never ends the
Episode; the yield controller does. Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.annotation_settling import (
    settle_annotations)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    ESTIMATE_RANGE, FAILURE_CODES, WAIT_RANGE_MAX, check_estimate, check_extract, check_fix, check_launch, check_monitor,
    common_instructions, job_view, launch_job, learned, minimum_wait, monitor_job, output_schema, record_estimate,
    search_facts, timing)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    APPLICATION, PER_CANDIDATE_RANGE, reusable_alignment)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

INSTRUCTIONS = common_instructions(
    'align the assigned target protein with sequences of candidates of a graded BV-BRC database search (the search, the '
    'candidates and the number of sequences per candidate are the commission\'s, in commission). Code, not you, chooses '
    'the sequences: for each candidate its hits with the highest values in the search, one per distinct sequence, the '
    'first per_candidate of them; the target is always in the alignment. The job is the MSA application with the Muscle '
    'aligner on protein sequences. In the estimate and the launch, per_candidate is the commission\'s number; planned shows '
    'the size of the job it gives (sequences, residues, longest).',
    'the alignment is read, each sequence is checked against what was given, and for each reference sequence the columns '
    'where it and the target both have a residue, how many of those are identical, and the value (identical columns over '
    'the target\'s length) are saved; the head\'s credit counts the values as one more test of the candidates; nothing more '
    'is needed for the result to count.')


def _resource(summary):
    request = summary['state_facts']['request']
    return summary['fields']['resource_id'] if request is None else request['resource_id']


def _trend(summary, ctx):
    return learned(ctx.services['estimate_table'], APPLICATION, summary['fields'], summary['planned']['residues'])


def decide(summary, feedback, ctx):
    fields, job, facts = summary['fields'], summary['job'], summary['state_facts']
    description = ctx.services['job_access'].read('describe', _resource(summary))
    context = {
        'commission': {**fields, **summary['commission'], 'until': summary['until'], 'resumed': summary['resumed'],
                       'known_ended': summary['known_ended']},
        'planned': summary['planned'], 'per_candidate_range': list(PER_CANDIDATE_RANGE),
        'credit': {**summary['units'],
                   'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
        'state': summary['state'], 'held_estimate': facts['estimate'], 'last_failure_code': summary['last_failure_code'],
        'failed_request': facts['failed_request'], 'fixed_field': facts['fixed_field'],
        'learned_durations': _trend(summary, ctx), 'unit_rows': summary['unit_rows'],
        'service': {'request_spacing_seconds': description['request_spacing_seconds'],
                    'poll_spacing_seconds': description['poll_spacing_seconds']},
        'wait_seconds_range': {'maximum': WAIT_RANGE_MAX}, 'estimate_seconds_range': list(ESTIMATE_RANGE),
        'failure_codes': list(FAILURE_CODES), 'yield_table': summary['yield_table'], 'feedback': feedback}
    if job is not None:
        context['job'] = job
        context['timing'] = timing(job, ctx.clock.now)
        context['minimum_wait_seconds'] = minimum_wait(description, job, ctx.clock.now)
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        output_schema(APPLICATION, summary['state']))


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the options of the schema ``decide`` asks the model with."""
    schema = output_schema(APPLICATION, summary['state'])
    return [option['properties']['name']['enum'][0] for option in schema['properties']['action']['anyOf']]


def action(response, summary, records, ctx):
    """The model's JSON to a unit; the action's one check runs here, before anything runs."""
    try:
        Draft202012Validator(output_schema(APPLICATION, summary['state'])).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    name, fields, facts = chosen['name'], summary['fields'], summary['state_facts']
    commission = {'query_ref': summary['commission']['query_ref'], 'search_ref': summary['commission']['search_ref'],
                  'candidates': summary['commission']['candidates']}
    job = job_view(records, APPLICATION)
    if name == 'estimate':
        problems = check_estimate(APPLICATION, chosen, state=facts, learned_trend=_trend(summary, ctx), commission=commission)
    elif name == 'launch':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        reusable = reusable_alignment(records, commission, chosen['per_candidate'])
        problems = check_launch(APPLICATION, chosen, state=facts, fields=fields, resources=resources,
                                commission=commission, reusable=reusable)
    elif name == 'fix':
        problems = check_fix(APPLICATION, chosen, state=facts)
    elif name == 'monitor':
        description = ctx.services['job_access'].read('describe', _resource(summary))
        minimum = 0 if job is None else minimum_wait(description, search_facts(job), ctx.clock.now)
        problems = check_monitor(chosen, state=facts, job=job, minimum=minimum)
    else:
        problems = check_extract(chosen, state=facts, job=job)
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    if name == 'estimate':
        return ToolCall('estimate', {'estimate': {key: chosen[key] for key in ('per_candidate', 'expected_seconds',
                                                                               'basis')}})
    if name == 'launch':
        return ToolCall('launch', {'request': {key: chosen[key] for key in APPLICATION.request_fields},
                                   'estimate': facts['estimate'], 'commission': commission})
    if name == 'fix':
        return ToolCall('fix', {'fix': {'failure_code': chosen['failure_code'], 'field': chosen['field']}})
    if name == 'monitor':
        return ToolCall('monitor', {'handoff_ref': chosen['handoff_ref'], 'wait_seconds': chosen['wait_seconds'],
                                    'expected_remaining_seconds': chosen['expected_remaining_seconds']})
    return ToolCall('extract', {'handoff_ref': chosen['handoff_ref'], 'request': facts['request'],
                                'commission': commission, 'scope': summary['scope'], 'organism': summary['organism']})


def estimate(arguments, ctx):
    return record_estimate(ctx, estimate=arguments['estimate'])


def launch(arguments, ctx):
    return launch_job(ctx, APPLICATION, request=arguments['request'], estimate=arguments['estimate'],
                      commission=arguments['commission'])


def fix(arguments, ctx):
    """The reasoning about a failure, as the controlled values the model chose: nothing is run."""
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'record_refs': [], 'fix': arguments['fix']}


async def monitor(arguments, ctx):
    return await monitor_job(ctx, APPLICATION, handoff_ref=arguments['handoff_ref'],
                             wait_seconds=arguments['wait_seconds'],
                             expected_remaining_seconds=arguments['expected_remaining_seconds'])


async def extract(arguments, ctx):
    """The fetch of the alignment and its grading into the sheet, then the settling of the annotations
    (``settle_annotations``), as one unit."""
    graded = APPLICATION.extract(ctx, arguments['handoff_ref'], arguments['request'], arguments['commission'])
    if graded['status'] != 'completed':
        return graded
    settled = await settle_annotations(ctx, scope=arguments['scope'], organism=arguments['organism'])
    return {**graded, 'graded_refs': [*graded['graded_refs'], *settled],
            'record_refs': [*graded['record_refs'], *settled]}


TOOLS = {'estimate': estimate, 'launch': launch, 'fix': fix, 'monitor': monitor, 'extract': extract}
