"""The task: one all-vs-all of the assigned target with the sequences of chosen candidates of a graded BV-BRC search, done in
one loop of three one-shot tools. The model is the router: it answers with one defined action as JSON (``output_schema``); each
tool has ONE deterministic check over the filled JSON and what the episode holds (``all_vs_all_run.check_*``); a check with
problems makes ``action`` raise ``Rejected`` (no unit). A passed check runs as one unit by one library function:

* ``prepare_database`` (``resource_id``): fetch the set's sequences once (the target and the chosen candidates' hits), build the
  BLAST database on the local resource and keep both as labelled data products.
* ``all_vs_all_blast`` (``resource_id``, ``database_ref``): REQUIRES the database product; ``blastp`` of every sequence of the set
  against it; the matrix of bit scores is kept as a labelled data product.
* ``cluster`` (``resource_id``, ``matrix_ref``, ``inflation``): REQUIRES the matrix product; MCL at an inflation of the
  commission's fixed set; the clusters are kept and graded into the cluster sheet (a graded source of the head's credit). The
  same matrix at the same inflation is refused.
* ``hold`` (a reason): nothing is run; always a valid answer, so a model with no valid tool is never stuck in rejections.

The decision shows the commission, the planned set, the held products, the clusterings graded so far (each candidate's share of
its sequences in the target's cluster), the credit units and each earlier unit. The task never ends the Episode; the yield
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
    'every ordered pair, and each graded clustering.\n'
    '\n'
    'You do not write a command. You answer with one action as JSON; code checks it before anything runs and runs the job.\n'
    '- prepare_database, with resource_id (a bound local resource, local_resources): fetches the set\'s sequences, builds the BLAST '
    'database and keeps both.\n'
    '- all_vs_all_blast, with resource_id and database_ref (a held blast_protein_database product, products): runs blastp of every '
    'sequence of the set against the database and keeps the matrix of bit scores (the best alignment of each ordered pair). It '
    'is offered only when a database is held.\n'
    '- cluster, with resource_id, matrix_ref (a held sequence_similarity_matrix product) and inflation (one of the commission\'s '
    'allowed values, lower is coarser clusters, higher finer): clusters the matrix with MCL on the bit-score ratio (a pair\'s bit '
    'score over the smaller of the two sequences\' scores against themselves, 0 to 1) and grades the clustering: for each '
    'candidate, the share of its sequences in the target\'s cluster. The same matrix at the same inflation is not clustered again.\n'
    '- hold, with a reason: do nothing now.\n'
    'If a check finds something wrong you are told each problem as a code with its field (feedback.problems) and nothing has run. '
    'A call that passed its check works; a failure after it is the environment\'s, is reported once as failed and is never '
    'retryable. The yield table shows what each unit earned. You cannot end the episode; the yield controller does.')


def local_resources(ctx):
    """The bound resources, ``{resource_id: kind}`` (read through the service's read handle, so the read is recorded)."""
    return {item['resource_id']: item['kind'] for item in ctx.services['job_access'].read('resources')}


def remaining_inflations(summary):
    """The inflations of the commission not yet clustered for the held matrix and not failed."""
    held = {row['settings']['inflation'] for row in summary['products'] if row['kind'] == run.CLUSTERS_KIND}
    failed = {inflation for _, inflation in summary['failed']['cluster']}
    return [value for value in summary['commission']['inflations'] if value not in held and value not in failed]


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
    if matrices and remaining_inflations(summary):
        options.append(one('cluster', resource_id=local, matrix_ref={'type': 'string', 'enum': matrices},
                           inflation={'type': 'number', 'enum': remaining_inflations(summary)}))
    options.append(one('hold', reason={'type': 'string', 'enum': list(run.HOLD_REASONS)}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'], 'properties': {'action': {'anyOf': options}}}


def decide(summary, feedback, ctx):
    resources = local_resources(ctx)
    context = {'commission': summary['commission'], 'planned_set': summary['planned'],
               'credit': {**summary['units'], 'target': summary['target'],
                          'now': None if summary['yield_table'] is None else summary['yield_table']['current_credit']},
               'state': summary['state'], 'local_resources': sorted(name for name, kind in resources.items() if kind == 'local'),
               'products': summary['products'], 'clusterings': summary['clusterings'], 'failed': summary['failed'],
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
    else:
        problems = run.check_cluster(chosen, commission=commission, reader=records, resources=resources,
                                     failed={tuple(pair) for pair in failed['cluster']},
                                     mcl_directory=settings['mcl_executable_directory'])
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
                             arguments['call']['inflation'], arguments['commission'], arguments['commission']['per_candidate'])


def hold(arguments, ctx):
    """Nothing is run: the unit's outcome is the reason."""
    return {'status': 'held', 'reason': arguments['reason'], 'failure_code': None, 'retryable': False, 'record_refs': [],
            'graded_refs': [], 'handoff_refs': [], 'closure_refs': []}


TOOLS = {'prepare_database': prepare_database, 'all_vs_all_blast': all_vs_all_blast, 'cluster': cluster, 'hold': hold}
