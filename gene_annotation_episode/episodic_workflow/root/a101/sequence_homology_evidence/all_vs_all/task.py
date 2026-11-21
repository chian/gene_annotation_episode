"""The task: one all-vs-all of the assigned target with the sequences of chosen candidates of a graded BV-BRC search, done in
one loop of three one-shot tools. The model is the router: it answers with one defined action as JSON (``output_schema``); each
tool has ONE deterministic check over the filled JSON and what the episode holds (``all_vs_all_run.check_*``); a check with
problems makes ``action`` raise ``Rejected`` (no unit). A passed check runs as one unit by one library function:

* ``prepare_database`` (``resource_id``): fetch the set's sequences once (the target and the chosen candidates' hits), build the
  BLAST database on the local resource and keep both as labelled data products.
* ``all_vs_all_blast`` (``resource_id``, ``database_ref``): REQUIRES the database product; ``blastp`` of every sequence of the set
  against it; the matrix of bit scores is kept as a labelled data product.
* ``cluster`` (``resource_id``, ``matrix_ref``, ``inflation``, ``contrast``): a TRY. REQUIRES the matrix product; MCL at an inflation
  and on a graph contrast of the fixed sets (the model's tuning); the clusters are kept as a working result and the model is shown
  controlled facts of them. Nothing is graded. The same tuning of the same matrix is refused.
* ``commit_clustering`` (``clusters_ref``): REQUIRES a held clustering, once: it is graded into the cluster sheet, the one graded
  source of the head's credit. Tries neither add to nor dilute that credit.
* ``hold`` (a reason): nothing is run; always a valid answer, so a model with no valid tool is never stuck in rejections.

The decision shows the commission, the planned set, the held products, the tries made (their controlled facts), the committed
clustering (each candidate's share of its sequences in the target's cluster), the credit units and each earlier unit. The task never ends the Episode; the yield
controller does. Settings (``ctx.settings``): ``blast_executable_directory``, ``mcl_executable_directory``, ``python_executable``,
``cost`` and ``parameters`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as run)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

INSTRUCTIONS = (
    'You are the all-vs-all agent for one commission: the assigned target protein and the sequences of the assigned candidates of '
    'a graded BV-BRC database search. The set is the target and, for each candidate, the hits with the highest values in that '
    'search (one per distinct sequence, per_candidate of them): code chooses them, fetches each sequence once and gives each an id '
    '(target, r1, r2 ...). Credit counts what you establish, once each: the prepared database, the matrix of bit scores of '
    'every ordered pair, and the committed clustering (tries earn nothing).\n'
    '\n'
    'You do not write a command. You answer with one action as JSON; code checks it before anything runs and runs the job.\n'
    '- prepare_database, with resource_id (a bound local resource, local_resources): fetches the set\'s sequences, builds the BLAST '
    'database and keeps both.\n'
    '- all_vs_all_blast, with resource_id and database_ref (a held blast_protein_database product, products): runs blastp of every '
    'sequence of the set against the database and keeps the matrix of bit scores (the best alignment of each ordered pair). It '
    'is offered only when a database is held.\n'
    '- cluster, with resource_id, matrix_ref (a held sequence_similarity_matrix product), inflation (lower is coarser clusters, higher '
    'finer) and contrast: a TRY of the clustering. It clusters the matrix with MCL on the bit-score ratio (a pair\'s bit score over the '
    'smaller of the two sequences\' scores against themselves, 0 to 1) as the contrast leaves it: none (as they are), rescale (each '
    'ratio rescaled to the set\'s own range) or percentile_25, _50, _75, _90 (only the edges at or above that percentile of the set\'s '
    'ratios are kept). Nothing is graded. You are shown the facts of each try (tries): the clusters, the target\'s cluster and, for each '
    'candidate, how many of its sequences are in the target\'s cluster and how many clusters they span. A set of one close family '
    'often comes out as one cluster at first: try another tuning until the clusters say something about the candidates. The same '
    'tuning of the same matrix is not tried again.\n'
    '- commit_clustering, with clusters_ref (a held sequence_clusters product): commits that clustering, once. It is graded: for each '
    'candidate the share of its sequences in the target\'s cluster, the one test the parent reads. Choose the try that best shows where '
    'the target falls among the candidates.\n'
    '- hold, with a reason: do nothing now.\n'
    'If a check finds something wrong you are told each problem as a code with its field (feedback.problems) and nothing has run. '
    'A call that passed its check works; a failure after it is the environment\'s, is reported once as failed and is never '
    'retryable. The yield table shows what each unit earned. You cannot end the episode; the yield controller does.')


def local_resources(ctx):
    """The bound resources, ``{resource_id: kind}`` (read through the service's read handle, so the read is recorded)."""
    return {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}


def output_schema(summary, resources):
    """The answer: one defined action with its controlled fields; only the tools that can pass their check now are offered."""
    def one(name, **fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'enum': [name]}, **fields}}
    local = {'type': 'string', 'enum': sorted(name for name, kind in resources.items() if kind == 'local')}
    databases = [row['row_ref'] for row in summary['products'] if row['kind'] == run.DATABASE_KIND]
    matrices = [row['row_ref'] for row in summary['products'] if row['kind'] == run.MATRIX_KIND]
    options = []
    if not databases and not summary['failed']['prepare']:
        options.append(one('prepare_database', resource_id=local))
    if databases and not matrices and not summary['failed']['blast']:
        options.append(one('all_vs_all_blast', resource_id=local, database_ref={'type': 'string', 'enum': databases}))
    clusterings = [row['row_ref'] for row in summary['products'] if row['kind'] == run.CLUSTERS_KIND]
    if matrices and not summary['committed']:
        options.append(one('cluster', resource_id=local, matrix_ref={'type': 'string', 'enum': matrices},
                           inflation={'type': 'number', 'enum': list(run.INFLATIONS)},
                           contrast={'type': 'string', 'enum': list(run.CONTRASTS)}))
    if clusterings and not summary['committed']:
        options.append(one('commit_clustering', clusters_ref={'type': 'string', 'enum': clusterings}))
    options.append(one('hold', reason={'type': 'string', 'enum': list(run.HOLD_REASONS)}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'], 'properties': {'action': {'anyOf': options}}}


def decide(summary, feedback, ctx):
    resources = local_resources(ctx)
    context = {'commission': summary['commission'], 'planned_set': summary['planned'],
               'credit': {**summary['units'], 'target': summary['target'],
                          'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
               'state': summary['state'], 'local_resources': sorted(name for name, kind in resources.items() if kind == 'local'),
               'products': summary['products'], 'tries': summary['tries'], 'clusterings': summary['clusterings'],
               'failed': summary['failed'],
               'unit_rows': summary['unit_rows'], 'yield_table': summary['yield_table'], 'feedback': feedback}
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        output_schema(summary, resources))


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the options of the schema ``decide`` asks the model with."""
    schema = output_schema(summary, local_resources(ctx))
    return [option['properties']['name']['enum'][0] for option in schema['properties']['action']['anyOf']]


def action(response, summary, records, ctx):
    """The model's JSON to a unit; the tool's one check runs here, before anything runs."""
    resources = local_resources(ctx)
    try:
        Draft202012Validator(output_schema(summary, resources)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen, commission, per_candidate = response['action'], summary['commission'], summary['commission']['per_candidate']
    name = chosen['name']
    if name == 'hold':
        return ToolCall('hold', {'reason': chosen['reason']})
    failed, settings = summary['failed'], ctx.settings
    if name == 'prepare_database':
        problems = run.check_prepare(chosen, commission=commission, per_candidate=per_candidate, reader=records,
                                     resources=resources, failed=failed['prepare'],
                                     blast_directory=settings['blast_executable_directory'],
                                     python=settings['python_executable'])
    elif name == 'all_vs_all_blast':
        problems = run.check_blast(chosen, commission=commission, per_candidate=per_candidate, reader=records,
                                   resources=resources, failed=failed['blast'],
                                   blast_directory=settings['blast_executable_directory'],
                                   python=settings['python_executable'])
    elif name == 'cluster':
        problems = run.check_cluster(chosen, reader=records, ids=summary['set_ids'], resources=resources,
                                     tried={tuple(pair) for pair in summary['tried']},
                                     mcl_directory=settings['mcl_executable_directory'])
    else:
        problems = run.check_commit(chosen, reader=records, committed=summary['committed'])
    if problems:
        raise Rejected({'status': 'invalid', 'category': name + '_check', 'problems': problems})
    return ToolCall(name, {'call': {key: value for key, value in chosen.items() if key != 'name'}, 'commission': commission})


async def prepare_database(arguments, ctx):
    return await run.prepare_database(ctx, arguments['call']['resource_id'], arguments['commission'],
                                      arguments['commission']['per_candidate'])


async def all_vs_all_blast(arguments, ctx):
    return await run.all_vs_all_blast(ctx, arguments['call']['resource_id'], arguments['call']['database_ref'],
                                      arguments['commission'], arguments['commission']['per_candidate'])


async def cluster(arguments, ctx):
    return await run.cluster(ctx, arguments['call']['resource_id'], arguments['call']['matrix_ref'],
                             arguments['call']['inflation'], arguments['call']['contrast'], arguments['commission'],
                             arguments['commission']['per_candidate'])


def commit_clustering(arguments, ctx):
    return run.commit_clustering(ctx, arguments['call']['clusters_ref'], arguments['commission'],
                                 arguments['commission']['per_candidate'])


def hold(arguments, ctx):
    """Nothing is run: the unit's outcome is the reason."""
    return {'status': 'held', 'reason': arguments['reason'], 'failure_code': None, 'retryable': False, 'record_refs': [],
            'graded_refs': []}


TOOLS = {'prepare_database': prepare_database, 'all_vs_all_blast': all_vs_all_blast, 'cluster': cluster,
         'commit_clustering': commit_clustering, 'hold': hold}
