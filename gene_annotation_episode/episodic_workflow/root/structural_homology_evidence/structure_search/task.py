"""The task: one structure search of the assigned target against one structure database, done in one loop. The model is the
router: it answers with one defined action as JSON (``structure_search_child.output_schema``); each action has ONE
deterministic check over the filled JSON and what the episode holds (``structure_search_child.check_*``); a check with
problems makes ``action`` raise ``Rejected`` (no unit). A passed check runs as one unit by one library function:

* ``get_model``: a model of the target from one source (``alphafold_db`` or ``esmfold``), offered only while no model is held
  and the source was not tried; ``not_found`` is a completed unit that holds nothing and earns nothing.
* ``estimate``: the database and the expected seconds with the basis, exactly the ledger's figure; code records it as the
  expectation of the launch.
* ``launch``: submit the ``StructureSearch`` job with the model file. Gated: refused unless an estimate and a model are held,
  and refused when the search of the same model file and database is held.
* ``fix`` (after a failure), ``monitor`` and ``extract`` as in ``structure_search_child``.

The decision shows the commission, the state, the model held, the tries of each model source, the held estimate and what the
ledger has learned of this kind of job, the seconds since the launch, the minimum wait and each earlier unit; never a protein
name. The task never ends the Episode; the yield controller does. Settings (``ctx.settings``): ``cost`` and ``parameters``
(``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    APPLICATION, model_problems, obtain_model, reusable_search, target_sequence)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ESTIMATE_RANGE, FAILURE_CODES, WAIT_RANGE_MAX, check_estimate, check_extract, check_fix, check_get_model, check_launch,
    check_monitor, common_instructions, job_view, launch_job, learned, minimum_wait, monitor_job, output_schema,
    record_estimate, search_facts, timing)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')

INSTRUCTIONS = common_instructions(
    'compare the assigned target protein with the structures of one structure database through one model of the target (the '
    'database and the resource are the commission\'s, in commission; the target is shown by its record, molecule and '
    'length). The search mode is fixed (tmalign, a global TM-align alignment). The result is a ranked list of hits, each '
    'with its aligned residue pairs and its structure statistics.',
    'the hits are parsed, the superposition and the index B of every hit are computed from the aligned pairs, the hits are '
    'named in rank order from UniProt (the names are looked up, never asked of you), and the sheet is saved: per hit the '
    'aligned pairs, the RMSD and B, per product candidate its hits and its mean B. A hit that is the model itself (an '
    'AlphaFold DB model searched against its own database) is a control and gives no value to any candidate. The head\'s '
    'credit counts the values as one more test of the candidates; nothing more is needed for the result to count.')


def _resource(summary):
    request = summary['state_facts']['request']
    return summary['fields']['resource_id'] if request is None else request['resource_id']


def _size(summary):
    """The job's size, the field the ledger's duration is fitted against: the residues of the model held, else of the target
    (a model found covers the whole target)."""
    return summary['query']['length'] if summary['model'] is None else summary['model']['residues']


def _trend(summary, ctx, database):
    return learned(ctx.services['estimate_table'], APPLICATION, {'database': database}, _size(summary))


def _schema(summary):
    return output_schema(APPLICATION, summary['state'], summary['sources'])


def decide(summary, feedback, ctx):
    fields, job, facts, model = summary['fields'], summary['job'], summary['state_facts'], summary['model']
    description = ctx.services['job_access'].read('describe', _resource(summary))
    context = {
        'commission': {**fields, 'until': summary['until'], 'resumed': summary['resumed'],
                       'known_ended': summary['known_ended'], 'model_passed': summary['model_passed'],
                       'target': {'record': summary['query']['subject_ref'], 'molecule': summary['query']['molecule'],
                                  'length': summary['query']['length']}},
        'credit': {**summary['units'],
                   'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
        'state': summary['state'],
        'model': None if model is None else {name: model[name] for name in ('origin', 'residues', 'mean_plddt')},
        'sources': summary['sources'], 'model_tries': summary['model_tries'],
        'held_estimate': facts['estimate'], 'last_failure_code': summary['last_failure_code'],
        'failed_request': facts['failed_request'], 'fixed_field': facts['fixed_field'],
        'learned_durations': {database: _trend(summary, ctx, database) for database in DATABASES},
        'unit_rows': summary['unit_rows'],
        'service': {'request_spacing_seconds': description['request_spacing_seconds'],
                    'poll_spacing_seconds': description['poll_spacing_seconds']},
        'wait_seconds_range': {'maximum': WAIT_RANGE_MAX}, 'estimate_seconds_range': list(ESTIMATE_RANGE),
        'failure_codes': list(FAILURE_CODES), 'yield_table': summary['yield_table'], 'feedback': feedback}
    if job is not None:
        context['job'] = job
        context['timing'] = timing(job, ctx.clock.now)
        context['minimum_wait_seconds'] = minimum_wait(description, job, ctx.clock.now)
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
    name, fields, facts, model = chosen['name'], summary['fields'], summary['state_facts'], summary['model']
    query_ref = summary['query']['subject_ref']
    commission = {'query_ref': query_ref}
    job = job_view(records, APPLICATION)
    if name == 'get_model':
        problems = check_get_model(chosen, rows=summary['unit_rows'], model_held=model is not None,
                                   sequence=target_sequence(records, query_ref))
    elif name == 'estimate':
        problems = check_estimate(APPLICATION, chosen, state=facts, learned_trend=_trend(summary, ctx, chosen['database']),
                                  commission=commission)
    elif name == 'launch':
        resources = {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}
        reusable = None if model is None else reusable_search(records, model['artifact_ref'], chosen['database'])
        problems = check_launch(APPLICATION, chosen, state=facts, fields=fields, resources=resources,
                                commission=commission, model=model, reusable=reusable)
        if model is not None:
            problems.extend(model_problems(model, records, target_sequence(records, query_ref)))
    elif name == 'fix':
        problems = check_fix(APPLICATION, chosen, state=facts)
    elif name == 'monitor':
        description = ctx.services['job_access'].read('describe', _resource(summary))
        minimum = 0 if job is None else minimum_wait(description, search_facts(APPLICATION, job), ctx.clock.now)
        problems = check_monitor(chosen, state=facts, job=job, minimum=minimum)
    else:
        problems = check_extract(chosen, state=facts, job=job)
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    if name == 'get_model':
        return ToolCall('get_model', {'source': chosen['source'], 'query_ref': query_ref})
    if name == 'estimate':
        return ToolCall('estimate', {'estimate': {key: chosen[key] for key in ('database', 'expected_seconds', 'basis')}})
    if name == 'launch':
        return ToolCall('launch', {'request': {key: chosen[key] for key in APPLICATION.request_fields},
                                   'estimate': facts['estimate'], 'commission': {**commission, 'model': model}})
    if name == 'fix':
        return ToolCall('fix', {'fix': {'failure_code': chosen['failure_code'], 'field': chosen['field']}})
    if name == 'monitor':
        return ToolCall('monitor', {'handoff_ref': chosen['handoff_ref'], 'wait_seconds': chosen['wait_seconds'],
                                    'expected_remaining_seconds': chosen['expected_remaining_seconds']})
    return ToolCall('extract', {'handoff_ref': chosen['handoff_ref'], 'request': facts['request'],
                                'commission': commission})


def get_model(arguments, ctx):
    """The model of the target from one source, by the library's one function."""
    return obtain_model(ctx, source=arguments['source'], query_ref=arguments['query_ref'])


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
    """The fetch of the result and its grading into the sheet, as one unit."""
    return APPLICATION.extract(ctx, arguments['handoff_ref'], arguments['request'], arguments['commission'])


TOOLS = {'get_model': get_model, 'estimate': estimate, 'launch': launch, 'fix': fix, 'monitor': monitor, 'extract': extract}
