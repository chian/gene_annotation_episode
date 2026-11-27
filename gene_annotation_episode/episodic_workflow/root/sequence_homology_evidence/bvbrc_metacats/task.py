"""The task: one MetaCATS analysis of a held graded alignment, done in one loop. The model is the router: it answers with
one defined action as JSON (``bvbrc_job_child.output_schema``); each action has ONE deterministic check over the filled JSON
and what the episode holds (``bvbrc_job_child.check_*``, and the requirement that the commission's alignment is a held
data product of kind ``multiple_sequence_alignment``); a check with problems makes ``action`` raise ``Rejected`` (no unit).
A passed check runs as one unit by one library function:

* ``estimate``: the expected seconds with the basis; code records it as the expectation of the launch.
* ``launch``: submit the ``MetaCATS`` job (code builds the groups from the held alignment, writes the group file and the
  alignment without the target's row under the job's own folder). Gated: refused unless an estimate is held, unless the
  alignment is a held product of its kind, and when the report of the same groups is held (the p-value is one fixed value, not a field).
* ``fix`` (after a failure), ``monitor`` and ``extract`` as in ``bvbrc_job_child``.

The decision shows the commission, the state, the held estimate, the planned size of the job (sequences, groups, columns and
each candidate group's size) and what the ledger has learned of this kind of job, the seconds since the launch, the minimum
wait and each earlier unit. The task never ends the Episode; the yield controller does. Settings (``ctx.settings``):
``cost`` and ``parameters`` (``yield_estimator.py``)."""
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
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_metacats_search import (
    APPLICATION, requirement_problems, reusable_report)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

INSTRUCTIONS = common_instructions(
    'test the assigned held alignment with MetaCATS (the target\'s sequence is in the alignment and is what is being placed). '
    'Code, not you, builds the groups: one group per product candidate of the alignment, its members that candidate\'s '
    'reference sequences; the target is in no group. The job is the MetaCATS application on protein sequences; the p-value '
    'is one fixed value, not your choice. planned shows the size of the job '
    '(sequences, groups, columns and the size of each candidate group).',
    'the service\'s table of the positions that differ between the groups at the fixed p-value is read and, for each such '
    'position, the residue counts per group and the target\'s residue are saved; a candidate\'s conserved site of the alignment '
    'whose column is significant is confirmed, and the head\'s credit counts each candidate\'s regions of the target '
    'with a confirmed site that no earlier analysis confirmed; '
    'when no position is significant the sheet says so; nothing more '
    'is needed for the result to count.')


def _resource(summary):
    request = summary['state_facts']['request']
    return summary['fields']['resource_id'] if request is None else request['resource_id']


def _trend(summary, ctx):
    return learned(ctx.services['estimate_table'], APPLICATION, summary['fields'], summary['planned'], ctx.clock.now)


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names in the answer schema ``decide`` sends (``output_schema``), which
    are the tool names: ``fix`` only while a failure waits."""
    schema = output_schema(APPLICATION, summary['state'])
    return [option['properties']['name']['enum'][0] for option in schema['properties']['action']['anyOf']]


def decide(summary, feedback, ctx):
    fields, job, facts = summary['fields'], summary['job'], summary['state_facts']
    description = ctx.services['job_access'].read('describe', _resource(summary))
    context = {
        'commission': {**fields, **summary['commission'], 'until': summary['until'], 'resumed': summary['resumed'],
                       'known_ended': summary['known_ended']},
        'planned': summary['planned'],
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


def action(response, summary, records, ctx):
    """The model's JSON to a unit; the action's one check runs here, before anything runs."""
    try:
        Draft202012Validator(output_schema(APPLICATION, summary['state'])).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    name, fields, facts = chosen['name'], summary['fields'], summary['state_facts']
    commission = {'query_ref': summary['commission']['query_ref'], 'alignment_ref': summary['commission']['alignment_ref']}
    needed = requirement_problems(records, commission)
    job = job_view(records, APPLICATION)
    if name == 'estimate':
        problems = needed + check_estimate(APPLICATION, chosen, state=facts, learned_trend=_trend(summary, ctx),
                                           commission=commission)
    elif name == 'launch':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        reusable = None if needed else reusable_report(records, commission['alignment_ref'])
        problems = needed + check_launch(APPLICATION, chosen, state=facts, fields=fields, resources=resources,
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
        return ToolCall('estimate', {'estimate': {key: chosen[key] for key in ('expected_seconds', 'basis')}})
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
    """The fetch of the result table and its grading into the sheet, then the settling of the annotations
    (``settle_annotations``), as one unit."""
    graded = APPLICATION.extract(ctx, arguments['handoff_ref'], arguments['request'], arguments['commission'])
    if graded['status'] != 'completed':
        return graded
    settled = await settle_annotations(ctx, scope=arguments['scope'], organism=arguments['organism'])
    return {**graded, 'graded_refs': [*graded['graded_refs'], *settled],
            'record_refs': [*graded['record_refs'], *settled]}


TOOLS = {'estimate': estimate, 'launch': launch, 'fix': fix, 'monitor': monitor, 'extract': extract}
