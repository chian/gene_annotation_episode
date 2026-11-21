"""The task of the A102 head: one model-chosen unit per decision. In round 1 the head has one action, the commission of its
child ``structure_search``: the model chooses the controlled fields of the commission (the target, the structure database, the
Foldseek resource, the model of the target and where the commission ends) and code builds the child's assignment
(``messages/msg_to_child.py``). It never ends the Episode: only the yield controller does. The head has no tool of its own yet
(``TOOLS`` is empty) and no ``reason`` action.

The child. A slot is offered while its commission can be stated from what this episode holds: a protein sequence of the scope
(a target whose molecule is not protein gets no commission) and a bound Foldseek resource (``commission_fields``). ONE
deterministic check of the filled commission runs in ``action`` before any child exists (``COMMISSION_CHECKS``): a search of the
same query, database and model already graded or already commissioned is refused with its fix list, except the resume of the
parked job (the same fields, ``until`` ``extracted``). A Foldseek job a child launched and returned parked is always finished
(``resume_action``: the episode does not stop while one is parked, and once it is due, or when nothing else is worth its cost,
its resume is the unit; the rule is the system's, ``method_loop.episode_type``). The service ``job_access`` is read for the bound
resources a commission may name (``bound_resources``).

Settings: ``yield_bindings`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import (
    foldseek_search as foldseek)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ROUTE_KIND, UNTIL, _choose, seconds_between)

from .credit import OBTAIN, commissioned, queries
from .goal import GOAL

CHILD_SLOTS = {'structure_search': 'structural_homology_evidence/structure_search'}
TOOLS = {}
SERVICES = ('job_access',)
SLOT = 'structure_search'
LEADING = 10

INSTRUCTIONS = (
    GOAL + '\n\n'
    'You are the head of this investigation. At each decision you choose exactly one action, from the actions offered '
    '(child_options), by answering with the controlled fields of its commission; code builds everything the child is told. '
    'The child owns its own iterative work, and the configured yield controller owns continuation: you cannot end the '
    'episode. Recorded facts come from actual records and are shown to you as they are: the targets with their molecule and '
    'length, the models held (origin, residues, mean pLDDT: a model\'s own confidence, not similarity), the graded searches, '
    'the outstanding jobs with the seconds since their launch and the seconds still expected, the leading candidates with '
    'their scores and subscoring sheets, your earlier units and the yield table. A model that is not held is obtained by the '
    'child when the commission names obtain_one. Waiting and unchanged observations do not manufacture progress.')

# What the model is told of the child it may commission: what the child does, the controlled fields of its commission (the model
# chooses values; code builds the child's assignment) and what comes back. Facts the system enforces; no recommendation.
CREDIT_TEXT = ('Your credit counts possible annotations (candidates). A candidate found with positive evidence is admitted to the '
               'list and earns its score; a possible annotation with no positive evidence is not on the list. Applying the same '
               'test to candidates already on the list earns by how differently they respond: the size of the difference of the '
               'moves of their scores. A repeat earns nothing.')
PARKED_TEXT = ('A parked job is always finished: this episode does not end while one is parked; once its expected remaining '
               'seconds have passed, or when none of your other actions is worth its cost, code commissions its continuation '
               '(until extracted) as the next unit without asking you; before then you may do other work worth its cost.')
CHILD_DESCRIPTIONS = {
    SLOT: (
        'Search the structure of one protein sequence of your scope against one structure database on the Foldseek web server '
        '(the StructureSearch application; no key, no login), through one model of the target. The alignment mode is fixed '
        '(tmalign, a global TM-align alignment). The result is a ranked list of hits, each with its aligned residue pairs. For '
        'each hit code superposes the aligned C-alpha atoms and computes the index B = [2 n / (target length + hit length)] / '
        '[1 + (RMSD / 2 A)^2] (n the aligned pairs, RMSD in angstroms), looks up the hit\'s UniProt recommended protein name, and '
        'each distinct product name is a candidate (vocabulary product) whose value in the test is the mean B of its hits; the '
        'hit that is the target\'s own model in its own database is a control and gives no value to any candidate; a hit never '
        'asked about (the naming stops once the candidates settle) names no candidate. ' + CREDIT_TEXT + ' Fill the five fields '
        'of its commission: query_ref (a protein sequence of your scope; targets gives the molecule of each), database (the '
        'structure database; afdb-swissprot holds AlphaFold models of reviewed UniProt entries), resource_id (a foldseek '
        'resource of bound_resources), model_ref (a model of that target in held_models, passed to the child as it is, or '
        'obtain_one: the child then obtains a model itself, from a source of its own choosing) and until. Code checks the '
        'commission before the child is commissioned; if something is wrong it comes back in feedback with the things to fix and '
        'nothing was commissioned. While a child runs, you do nothing else: your next decision comes after it returns. What '
        'until means: with until launched the child estimates the duration, launches the search and returns at once; the search '
        'then keeps running at the service, you can use your other actions while it runs, and the child is said to be parked. '
        + PARKED_TEXT + ' With until extracted the child follows the search to its end, waiting between status requests for as '
        'long as the search takes, and extracts the result into the graded sheet; it is also how a parked search is continued: '
        'while structure_search_jobs shows a search of the target as outstanding, commissioning the child again with the same '
        'query, database and resource, the model that search was given and until extracted continues that search and submits '
        'nothing (code passes back the records the child returned). What comes back: the state of the search (no_model, '
        'model_held, estimated, launched, finished, extracted or failed), the model\'s origin, residues and mean pLDDT, the hit, '
        'named, not-asked and candidate counts, the seconds estimated and observed, the last failure code and the credit; the '
        'models and the graded sheet are kept as labelled data products. When the search is parked (parked true) the report is a '
        'wait notice: seconds_since_launch, estimated_seconds and expected_remaining_seconds (the estimate minus the seconds '
        'since the launch, not below zero, or the later revised figure of a status request), and structure_search_jobs keeps '
        'showing the search with the seconds since its launch and the seconds still expected as of each decision. A search of '
        'the same target, database and model that is graded, or that failed, is not commissioned again.'),
}


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a commission may name (read through the service's read
    handle, so the read is recorded with the decision)."""
    return {resource['resource_id']: resource['kind'] for resource in ctx.services['job_access'].read('resources')}


def commission_fields(slot, summary, resources):
    """What the model supplies to commission ``slot``, as ``(properties, required)``: controlled values only. ``None`` while
    this episode holds nothing the commission could be chosen from (no protein sequence in the scope, or no bound Foldseek
    resource): the slot is then not offered. The model is one of the held models of the targets, or ``obtain_one`` while a target
    has none."""
    targets = queries(summary)
    services = [name for name, kind in resources.items() if kind == ROUTE_KIND]
    if not targets or not services:
        return None
    models = [row['id'] for row in summary['model_rows'] if row['query_ref'] in targets]
    if any(all(row['query_ref'] != target for row in summary['model_rows']) for target in targets):
        models.append(OBTAIN)
    properties = {'query_ref': {'type': 'string', 'enum': targets}, 'database': {'type': 'string', 'enum': list(DATABASES)},
                  'resource_id': {'type': 'string', 'enum': services}, 'model_ref': {'type': 'string', 'enum': models},
                  'until': {'type': 'string', 'enum': list(UNTIL)}}
    return properties, list(properties)


def check_structure_search(commission, summary, resources, records):
    """The things to fix in a commission of ``structure_search``: the child's own commission check
    (``foldseek_search.check_commission``: the query is a protein sequence of the scope, the database is offered, the model is a
    held model product, the resource is a bound Foldseek service, an outstanding job of this search is continued with ``until``
    ``extracted`` and another one blocks it, a search of the same query, database and model graded, or commissioned and not
    outstanding, is not commissioned again), over the graded searches the credit's own reader gives (``held_searches``) and the
    jobs read from the job ledger rows the head holds; and that the model is of the query."""
    model_ref = None if commission['model_ref'] == OBTAIN else commission['model_ref']
    request = {'query_ref': commission['query_ref'], 'database': commission['database'],
               'resource_id': commission['resource_id'], 'until': commission['until'], 'model_ref': model_ref}
    searches = [{'query_ref': target, 'database': database, 'model_sha256': sha}
                for target, pairs in summary['held_searches'].items() for database, sha in pairs]
    problems = foldseek.check_commission(
        request, scope_subjects=summary['scope']['subject_refs'], sequences=summary['held_sequences'], resources=resources,
        jobs=summary['structure_search_jobs'],
        commissioned=[(query, database, None if model == OBTAIN else model) for query, database, model in commissioned(summary)],
        models={row['id']: row for row in summary['model_rows']}, searches=searches)
    mine = [row['id'] for row in summary['model_rows'] if row['query_ref'] == commission['query_ref']]
    if model_ref is not None and mine and model_ref not in mine:
        problems.append(_choose('model_ref', 'model_is_not_of_the_query', choose_from=mine))
    if model_ref is None and mine:
        problems.append(_choose('model_ref', 'a_model_of_the_query_is_held', choose_from=mine))
    return problems


COMMISSIONS = {SLOT: commission_fields}
COMMISSION_CHECKS = {SLOT: check_structure_search}


def jobs_view(jobs, now):
    """The searches this episode's child launched as the model sees them at ``now`` (the decision's recorded time): each with
    its state, whether it is outstanding, and for an outstanding one the seconds since its launch and the seconds still
    expected: the estimate recorded with its launch minus those seconds, not below zero. Facts, never a deadline."""
    shown = []
    for job in jobs:
        row = {'handoff_ref': job['handoff_ref'], 'query_ref': job['identity']['query_ref'],
               'database': job['identity']['database'], 'resource_id': job['resource_id'], 'latest_state': job['latest_state'],
               'outstanding': job['outstanding'], 'closed': job['closed'], 'estimated_seconds': job['estimated_seconds']}
        if job['outstanding']:
            elapsed = seconds_between(job['launched_at'], now)
            row.update(seconds_since_launch=elapsed, expected_remaining_seconds=max(job['estimated_seconds'] - elapsed, 0.0))
        shown.append(row)
    return shown


def offered_children(summary, resources):
    """The children this decision offers: those whose commission this episode can state now."""
    return [slot for slot in CHILD_SLOTS if COMMISSIONS[slot](summary, resources) is not None]


def child_option(slot, summary, resources):
    """One child the model may commission: its name and the controlled fields of its commission."""
    properties, required = COMMISSIONS[slot](summary, resources)
    properties = {'name': {'type': 'string', 'enum': [slot]}, **properties}
    return {'type': 'object', 'additionalProperties': False, 'required': ['name', *required], 'properties': properties}


def selection_schema(summary, resources):
    """What the model answers with: one commission of one offered child."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': [child_option(slot, summary, resources)
                                                for slot in offered_children(summary, resources)]}}}


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ChildCall.slot``): each child slot whose
    commission can be stated (``offered_children``, the function ``decide`` offers the model with)."""
    return offered_children(summary, bound_resources(ctx))


def parked_jobs(summary):
    """The jobs of this episode's child that are parked (outstanding: launched, no closure held, not shown failed or lost),
    from the summary's view of the job ledger rows."""
    return [job for job in summary['structure_search_jobs'] if job['outstanding']]


def resume_commission(job, summary):
    """The commission that resumes the parked ``job``: the job's own commission again with ``until`` ``extracted`` (the one
    commission of it the head's check accepts while it is outstanding; it submits nothing): the search's query, database and
    resource and the model the job was given (the held model row of its SHA-256)."""
    identity = job['identity']
    model = next(row['id'] for row in summary['model_rows'] if row['settings']['sha256'] == identity['model_sha256'])
    return {'query_ref': identity['query_ref'], 'database': identity['database'], 'resource_id': job['resource_id'],
            'model_ref': model, 'until': 'extracted'}


def resume_action(summary, records, ctx):
    """The resume this episode owes (``method_loop.episode_type``; the owner, 2026-11-21: "the head must finish parked jobs"):
    ``None`` while no job is parked, else the resume of one parked job as ``{'action_type': its slot, 'arguments':
    resume_commission(...), 'due': ...}``. ``due`` is True once the job's expected remaining seconds have passed: the estimate
    recorded with its launch minus the seconds from the launch to this decision's recorded time (the wait notice ``jobs_view``
    shows), at or below zero. The job chosen: the earliest launched among the due ones, else the earliest launched. The
    commission passes the head's own check (``COMMISSION_CHECKS``), else this raises: a resume the check refuses is a fault of
    the episode."""
    parked = parked_jobs(summary)
    if not parked:
        return None
    remaining = lambda job: job['estimated_seconds'] - seconds_between(job['launched_at'], ctx.clock.now)
    due = [job for job in parked if remaining(job) <= 0]
    job = min(due or parked, key=lambda item: item['launched_at'])
    arguments = resume_commission(job, summary)
    problems = COMMISSION_CHECKS[SLOT](arguments, summary, bound_resources(ctx), records)
    if problems:
        raise ContractError('a102_resume_commission_refused_by_its_check:' + SLOT + ':' + repr(problems))
    return {'action_type': SLOT, 'arguments': arguments, 'due': bool(due)}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the commission's scope (the targets), the resources, the models, the graded
    searches, the jobs, the leading candidates, its own outcomes, the child it may use, the measured time and the yield table."""
    resources = bound_resources(ctx)
    offered = offered_children(summary, resources)
    context = {
        'goal': GOAL, 'scope': summary['scope'], 'targets': summary['targets'], 'bound_resources': resources,
        'held_models': [{'row_ref': row['id'], 'query_ref': row['query_ref'], 'origin': row['settings']['origin'],
                         'residues': row['settings']['residues_covered'], 'mean_plddt': row['settings']['mean_plddt']}
                        for row in summary['model_rows']],
        'graded_searches': [{key: row[key] for key in ('source_ref', 'query_ref', 'database', 'hit_count', 'named_count',
                                                       'candidate_count')} for row in summary['graded_searches']],
        'structure_search_jobs': jobs_view(summary['structure_search_jobs'], ctx.clock.now),
        'candidates': [{'target_ref': ref, 'candidate_count': row['candidate_count'], 'leading': row['candidates']}
                       for ref, row in summary['credit_table'].items()],
        'own_outcomes': [{key: row[key] for key in ('position', 'slot', 'arguments', 'child_state', 'credit', 'parked')}
                         for row in summary['units']],
        'child_options': [{'slot': slot, 'binding_path': CHILD_SLOTS[slot], 'description': CHILD_DESCRIPTIONS[slot]}
                          for slot in offered],
        'yield_table': summary['yield_table'], 'time_accounting': time_accounting(ctx.clock.progress_time),
        'feedback': feedback}
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        selection_schema(summary, resources))


def action(response, summary, records, ctx):
    """Turn the model's answer into one commission, or reject it (no unit): an answer that does not fit the schema, or a
    commission the check finds something to fix in (rejected with the things to fix)."""
    resources = bound_resources(ctx)
    try:
        Draft202012Validator(selection_schema(summary, resources)).validate(response)
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    slot = chosen['name']
    commission = {key: value for key, value in chosen.items() if key != 'name'}
    problems = COMMISSION_CHECKS[slot](commission, summary, resources, records)
    if problems:
        raise Rejected({'status': 'invalid', 'category': slot + '_commission',
                        'detail': {'commission': commission, 'fix': problems}})
    return ChildCall(slot, commission)
