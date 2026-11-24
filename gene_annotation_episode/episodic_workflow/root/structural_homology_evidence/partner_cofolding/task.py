"""The task: one co-folding job of the assigned target with several held ligand candidates, done in one loop. The model is the router:
it answers with one defined action as JSON (``structure_search_child.output_schema``); each action has ONE deterministic check over the
filled JSON and what the episode holds (``structure_search_child.check_*``); a check with problems makes ``action`` raise ``Rejected``
(no unit). A passed check runs as one unit by one library function:

* ``estimate``: the ligands and the expected seconds with the basis, exactly the ledger's figure; code records it as the expectation of
  the launch.
* ``launch``: stage the target, the ligands' SMILES and the program, and submit the Chai-1 batch job under the run's allocation. Gated:
  refused unless an estimate is held, and refused when the co-folding of the same target and ligands is held.
* ``fix`` (after a failure), ``monitor`` and ``extract`` as in ``structure_search_child``.

There is no ``get_model``: the target's sequence is read from its subject record. The PBS resource describes no request spacing, so a
status request may be made at once (``NO_SPACING``). The decision shows the commission, the state, the held estimate and what the ledger
has learned of this kind of job, the seconds since the launch and each earlier unit. The task never ends the Episode; the yield
controller does. Settings (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``), and the job's own: ``allocation``
(account, queue, select, walltime, filesystems), ``chai_python_executable`` and ``chai_environment`` (the environment exports of the job)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    APPLICATION, LIGAND_COUNT, reusable_cofolding)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ESTIMATE_RANGE, FAILURE_CODES, WAIT_RANGE_MAX, check_estimate, check_extract, check_fix, check_launch, check_monitor,
    job_view, launch_job, learned, minimum_wait, monitor_job, output_schema, record_estimate, search_facts, timing)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')
NO_SPACING = {'request_spacing_seconds': 0, 'poll_spacing_seconds': 0}

INSTRUCTIONS = (
    'You are the agent for one job of Chai-1 on a PBS resource: co-fold the assigned target protein with each of the assigned ligand '
    'candidates, one ligand per GPU (the target and the ligands are the commission\'s, in commission; the target is shown by its record, '
    'molecule and length). The result is structural compatibility as the model predicts it, never measured binding. The commission\'s '
    'until says where this commission ends. launched: the episode ends the moment the launch completes (the job keeps running and the '
    'parent is told how long to expect; a later commission resumes it). extracted: the job is followed to its graded result; when '
    'resumed is true the job was launched by an earlier commission (state launched or finished): no estimate or launch is possible, the '
    'job is monitored and extracted. The episode ends by itself when its credit reaches the target of the commission; you cannot end '
    'it.\n\n'
    'You do not write a request. You answer with one action as JSON; code checks your JSON before anything runs and runs the job.\n'
    '- estimate: the seconds the job is expected to take (expected_seconds) and their basis, both exactly as learned_durations.'
    'ledger_estimate gives them: the estimate comes from the ledger, and the seconds the ledger holds for a job include the time it waited '
    'in the queue. With measured jobs of this kind (measured is how many, typical_seconds their median, latest_seconds the newest first, '
    'size_fit, when present, a line of seconds against the target\'s residue count) the basis is learned_from_earlier_jobs and the seconds '
    'are what size_fit gives for this job, else typical_seconds; with none the basis is no_earlier_measurement and the seconds are the '
    'fixed first figure. Any other figure is refused. The estimate names the ligands (the commission\'s).\n'
    '- launch: the job, with the fields of the commission. Refused unless an estimate is held (state estimated). One launch per estimate. '
    'Refused when the co-folding of this target with these ligands is already held.\n'
    '- monitor: one status request of the launched job (handoff_ref: the handoff record in job). wait_seconds is how long the unit waits '
    'before it asks: at most the maximum shown. expected_remaining_seconds is your revised expectation of the time left. The first '
    'request that shows the job ended records the measured duration, which the next estimate learns from. No deadline, no cancel.\n'
    '- extract: only when the latest monitor shows the job finished (state finished). Code fetches the scores and grades them in the same '
    'unit: per ligand the value of each of five samples (the interface score of the target and the ligand, 0 for a sample with an '
    'inter-chain clash) and the ligand\'s value, their mean; the sheet is saved. The head\'s credit counts the values as one more test of '
    'the ligand candidates; nothing more is needed for the result to count.\n'
    '- fix: only after a failure (state failed): the failure code you address (last_failure_code) and the request field you will change. '
    'Only after a fix does a launch pass, with a request that differs from the failed one in that field, after a new estimate.\n'
    'If your JSON is wrong you are told each problem as a code with the field it concerns (feedback.problems) and nothing has run; each '
    'problem is a field, a code and what to choose from.\n\n'
    'States: ready (nothing estimated), estimated (an estimate held), launched, finished, extracted, failed.\n\n'
    'Credit is bounded and only for what is new in this commission: an estimate held (credit.information_unit), the job launched '
    '(credit.handoff_unit), the job known ended (credit.information_unit: the first status that shows finished or failed) and the graded '
    'result (credit.graded_unit). When the job cannot finish a few actions that earn nothing follow and the yield controller ends the '
    'episode. You cannot end it.')


def _size(summary):
    """The job's size, the field the ledger's duration is fitted against: the residues of the target."""
    return summary['query']['length']


def _trend(summary, ctx, ligands):
    return learned(ctx.services['estimate_table'], APPLICATION, {'ligands': ligands}, _size(summary))


def _schema(summary):
    return output_schema(APPLICATION, summary['state'], [])


def decide(summary, feedback, ctx):
    fields, job, facts = summary['fields'], summary['job'], summary['state_facts']
    context = {
        'commission': {**fields, 'until': summary['until'], 'resumed': summary['resumed'],
                       'known_ended': summary['known_ended'],
                       'target': {'record': summary['query']['subject_ref'], 'molecule': summary['query']['molecule'],
                                  'length': summary['query']['length']}},
        'credit': {**summary['units'],
                   'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
        'state': summary['state'],
        'held_estimate': facts['estimate'], 'last_failure_code': summary['last_failure_code'],
        'failed_request': facts['failed_request'], 'fixed_field': facts['fixed_field'],
        'learned_durations': _trend(summary, ctx, fields['ligands']),
        'unit_rows': summary['unit_rows'],
        'wait_seconds_range': {'maximum': WAIT_RANGE_MAX}, 'estimate_seconds_range': list(ESTIMATE_RANGE),
        'ligand_count_range': list(LIGAND_COUNT),
        'failure_codes': list(FAILURE_CODES), 'yield_table': summary['yield_table'], 'feedback': feedback}
    if job is not None:
        context['job'] = job
        context['timing'] = timing(job, ctx.clock.now)
        context['minimum_wait_seconds'] = minimum_wait(NO_SPACING, job, ctx.clock.now)
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        _schema(summary))


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the options of the schema ``decide`` asks the model with."""
    return [option['properties']['name']['enum'][0] for option in _schema(summary)['properties']['action']['anyOf']]


def action(response, summary, records, ctx):
    """The model's JSON to a unit; the action's one check runs here, before anything runs."""
    try:
        Draft202012Validator(_schema(summary)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    name, fields, facts = chosen['name'], summary['fields'], summary['state_facts']
    query_ref = summary['query']['subject_ref']
    commission = {'query_ref': query_ref}
    job = job_view(records, APPLICATION)
    if name == 'estimate':
        problems = check_estimate(APPLICATION, chosen, state=facts, learned_trend=_trend(summary, ctx, chosen['ligands']),
                                  commission=commission)
    elif name == 'launch':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        problems = check_launch(APPLICATION, chosen, state=facts, fields=fields, resources=resources, commission=commission,
                                model=None, reusable=reusable_cofolding(records, query_ref, chosen['ligands']))
    elif name == 'fix':
        problems = check_fix(APPLICATION, chosen, state=facts)
    elif name == 'monitor':
        minimum = 0 if job is None else minimum_wait(NO_SPACING, search_facts(APPLICATION, job), ctx.clock.now)
        problems = check_monitor(chosen, state=facts, job=job, minimum=minimum)
    else:
        problems = check_extract(chosen, state=facts, job=job)
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    if name == 'estimate':
        return ToolCall('estimate', {'estimate': {key: chosen[key] for key in ('ligands', 'expected_seconds', 'basis')}})
    if name == 'launch':
        return ToolCall('launch', {'request': {key: chosen[key] for key in APPLICATION.request_fields},
                                   'estimate': facts['estimate'], 'commission': commission})
    if name == 'fix':
        return ToolCall('fix', {'fix': {'failure_code': chosen['failure_code'], 'field': chosen['field']}})
    if name == 'monitor':
        return ToolCall('monitor', {'handoff_ref': chosen['handoff_ref'], 'wait_seconds': chosen['wait_seconds'],
                                    'expected_remaining_seconds': chosen['expected_remaining_seconds']})
    return ToolCall('extract', {'handoff_ref': chosen['handoff_ref'], 'request': facts['request'], 'commission': commission})


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


def extract(arguments, ctx):
    """The fetch of the scores and their grading into the sheet, as one unit."""
    return APPLICATION.extract(ctx, arguments['handoff_ref'], arguments['request'], arguments['commission'])


TOOLS = {'estimate': estimate, 'launch': launch, 'fix': fix, 'monitor': monitor, 'extract': extract}
