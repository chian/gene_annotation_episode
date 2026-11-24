"""The task: nano-graphrag's web search. It receives ONE query (by reference), runs the provider search, has Jev score
every hit once, the model picks ONE unprocessed hit, code obtains the paper when its page is built and commissions the
page. A hit picked is done. It cannot read or extract, offers no read tool and commits no reasoning (grading is
automatic, far below).

Units. Each is one unit of the episode's iterator with its own outcome:

* ``run_search`` (automatic, code attached to the unit): the provider search for the query the strategy handed over
  (nano-graphrag ``web_search_binding``: the search level runs the provider search for the query it was handed). The
  query is not in the commission: ``search_query_ref`` names a record of the strategy, which holds the request in its
  ``request_ref`` artifact, read here through custody. The unit is the operation of ``public.literature.search``; its
  outcome is the unit's outcome like any other, and the retained response it produced is the result list the hits are
  read from (``messages/internal_summary.py``).
* ``list_record_publications`` (automatic, only when the proposed annotation's subject is a protein with a sequence):
  the papers a database lists for the target's own records (owner's goal for this arm, 2026-11-21: find the exact
  sequence the experimental data belong to; "some dbs will have a partial list of papers"). Code runs the sequence-
  identity lookup of the target (the operation ``public.literature.sequence_identity``), holds the records whose
  complete sequence equals the target's (``target_record_refs``), reads the papers the database lists for each
  (``record_publications``) and has Europe PMC give the PMCID of the listed papers (the operation
  ``public.literature.search``). The list is held as an artifact; ``messages/internal_summary.py`` adds the listed
  papers that can be opened to the hit list, each once and marked with where it came from. The database's list is
  partial and says so to the model.
* ``assess_search_results`` (automatic): the search step's Jev measurement (nano-graphrag ``web_search_binding``,
  ``SEARCH_PAGE_SELECTION_VERSION`` ``model_planned_from_jev_evidence``): a search result is ONE HIT of the provider's
  result list (its PMCID, rank, title, journal, year and the abstract the provider returned), not a fetched document.
  Jev measures every hit once, from its description, against the immutable Search Goal and the assessment is held as an
  artifact.
* ``fetch_search_hit`` (the model's pick): every later decision shows the model nano-graphrag's candidate view for the
  UNPROCESSED hits only (``context.page_candidates``: each hit's Jev probability, provider rank, title and
  description, and the measured outcomes of the prior pages); the model picks one hit. Code obtains that hit's paper
  (the operation of ``public.literature.read``; an article already held is opened without a new fetch: no second
  record of it) and, when that completed, commissions the page on the paper with no model call. A hit is done by its
  pick; a hit whose fetch failed is shown in ``context.hit_fetches`` with the provider status and is never opened. Jev
  is planning evidence, not the selection policy.

Child. The slot below is the old ``_CHILDREN['literature_search']`` (the page) under the name of its folder. A child is
a unit like any other: what it earns in this episode is this episode's own credit. The task never ends the Episode:
only the yield controller does."""
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    articles_held_with_text, assess_search_results as assess_results, source_kind)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_record_publications import (
    PARTIAL_LIST, record_publications, resolve_queries, target_record_refs, with_full_text)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_sequence_discovery import (
    identity_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import JevDecisionClient
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from .goal import GOAL

CHILD_SLOTS = {
    'page': 'experimental_activity_evidence/literature/strategy/web_search/page',
}
SERVICES = ()

# The provider operations this episode's code runs for its units (they are not offered to the model).
SEARCH_OPERATION = 'public.literature.search'
READ_OPERATION = 'public.literature.read'
IDENTITY_OPERATION = 'public.literature.sequence_identity'
OPERATION_DEFINITIONS = {name: access_library._DEFINITIONS[name] for name in (SEARCH_OPERATION, READ_OPERATION)}
OPERATION_DEFINITIONS[IDENTITY_OPERATION] = (access_library._SEQUENCE_IDENTITY_DESCRIPTION, identity_schema())

RUN_SEARCH = 'run_search'
LIST = 'list_record_publications'
ASSESS = 'assess_search_results'
# The tool the model picks a hit with. Code obtains the hit's paper and commissions the page on it.
FETCH = 'fetch_search_hit'
FETCH_DESCRIPTION = (
    'Pick one UNPROCESSED hit of the search results (input_list: PMCIDs) to have examined. Choose the hit from '
    'context.page_candidates (its Jev probability, provider rank, title, description and the measured outcomes of the '
    'previous pages). Code then obtains the hit\'s paper (the operation of public_literature_read; an article already '
    'held is opened without a new fetch) and, when that completes, commissions the page on the paper with no further '
    'choice of yours; a hit whose fetch fails is done, is shown in context.hit_fetches with the provider status and is '
    'never opened. A hit picked is done: it is not offered again. The page is where the paper is examined; the sheet '
    'states and the credit come back to you. You read nothing yourself and extract nothing.')


def fetch_entry(input_list):
    """The hit-picking tool the model is shown, over the unprocessed hits (the input list)."""
    return {'name': FETCH, 'description': FETCH_DESCRIPTION,
            'input_schema': obj({'hit': {'enum': list(input_list)}})}


def hit_tools(input_list):
    """The hit-picking tool while an unprocessed hit remains."""
    return [fetch_entry(input_list)] if input_list else []


# The declared shape of the page child's commission (code builds it; the model only picks the hit), kept for the
# binding test: the hit and the page (the source, its representation and artifact, filled from the source record).
CHILD_ARGUMENTS = {'page': ('The page on the paper of the hit the model picked, commissioned by code.',
                            obj({'hit': {'type': 'string', 'minLength': 1},
                                 'page': obj({'source_ref': {'type': 'string', 'minLength': 1},
                                              'representation': {'enum': ['text', 'original']},
                                              'artifact_ref': {'type': 'string', 'minLength': 1},
                                              'prior_delivery_refs': {'type': 'array'}})}))}

INSTRUCTIONS = (
    'You own an iterative scientific annotation improvement, not a tool itinerary. The provider search for your query '
    'has been run and Jev has scored every hit once. You pick ONE unprocessed hit per decision (fetch_search_hit); code '
    'obtains its paper and the page examines it. You read nothing and extract nothing, and nothing is assessed by a '
    'reasoning commit: grading of what the leaves extract is automatic and its results come back as child_returns. '
    'Only the numerical controller decides when you stop.\n')
CHILD_GUIDANCE = ('\nA search result is one hit of a provider\'s result list (its PMCID, title, journal, year and '
                  'abstract). Jev has measured every hit once against the Search Goal. context.page_candidates shows, '
                  'for the UNPROCESSED hits only, each one\'s provider rank, title, description and Jev assessment '
                  '(relevance_probability: Jev\'s probability that the hit can contribute to the Search Goal), and the '
                  'measured results of the previous pages (previous_page_children). These are measurements for your '
                  'planning, not a rule that the largest probability must be selected: use them and the realized '
                  'results of previous pages to choose the next hit worth examining. context.hit_fetches shows which '
                  'hits were fetched and the provider status of a fetch that failed (that hit is never opened). One '
                  'page takes one hit; a publication is one hit however many lists returned it, and an article a page '
                  'has already examined is not offered again; the numerical controller alone decides whether the '
                  'search continues. Some hits are not provider search results but papers a database lists for a '
                  'record of the target\'s sequence (their description begins "[Listed by"): ' + PARTIAL_LIST + ' '
                  'context.listed_publications names them. A child earns credit in this episode only through the records it returns.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading sheets '
                   'your pages returned (evidence type, quantity kind, measured effect, variance, log evidence '
                   'ratio, prediction model, criterion statuses); no prose of yours is returned.')


def instructions():
    return INSTRUCTIONS + '\n' + GOAL + CHILD_GUIDANCE + RETURN_GUIDANCE


def selection_schema(summary):
    """What the model answers with: one unprocessed hit to pick (the old action schema: kind ``tool``)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in hit_tools(summary['input_list'])]
    return obj({'selection': {'anyOf': tools}})


def invalid(name, arguments, ctx, error):
    """A contract error of the arguments of a unit: an ``invalid`` outcome with feedback."""
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_operation(name, arguments, scope, ctx):
    """Execute one provider operation of the library for a unit of this episode. A contract error is returned as an
    ``invalid`` outcome with ``arguments_or_reference`` feedback; a failed provider call is the unit's outcome like any
    other."""
    try:
        validate_schema(arguments, source_location_inputs(OPERATION_DEFINITIONS[name][1]))
    except (ContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)
    registry = access_library.A105ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def run_search(arguments, ctx):
    """The provider search of the one query the strategy handed over: ``search_query_ref`` names a record of the
    strategy, which holds the request in its ``request_ref`` artifact, read here through custody."""
    source = ctx.store.require(arguments['search_query_ref'], {'source'})
    request = json.loads(ctx.store.get_artifact(source['request_ref']))
    return await run_operation(SEARCH_OPERATION, request, arguments['scope'], ctx)


async def list_record_publications(arguments, ctx):
    """The papers a database lists for the target's own records. For each protein subject of the proposed annotation:
    the sequence-identity lookup (one UniProt checksum page), the records whose complete sequence equals the
    subject's, and the papers the database lists for each. The listed papers that have a PubMed identifier and no PMCID
    are looked up in Europe PMC for their PMCID and abstract. An operation that does not complete is the unit's
    outcome. The unit holds the list as an artifact (``publications_ref``)."""
    produced, listed, record_refs = [], [], []
    for subject_ref in arguments['subject_refs']:
        lookup = await run_operation(IDENTITY_OPERATION, {'subject_ref': subject_ref}, arguments['scope'], ctx)
        if lookup['status'] != 'completed':
            return lookup
        produced += lookup['record_refs']
        for record_ref in target_record_refs(ctx.store, subject_ref=subject_ref):
            record_refs.append(record_ref)
            listed += record_publications(ctx.store, record_ref=record_ref)
    contents = []
    for request in resolve_queries(listed):
        resolved = await run_operation(SEARCH_OPERATION, request, arguments['scope'], ctx)
        if resolved['status'] != 'completed':
            return resolved
        produced += resolved['record_refs']
        contents += [ctx.store.get_artifact(ctx.store.get(ref)['artifact_ref']) for ref in resolved['record_refs']
                     if source_kind(ctx.store.get(ref)) == 'search_response']
    listed = with_full_text(listed, contents)
    publications = ctx.store.artifact(canonical({'listed': listed, 'record_refs': record_refs}), 'application/json')
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': LIST, 'arguments': arguments}),
            'record_refs': list(dict.fromkeys([*produced, *record_refs])), 'changed_record_refs': [],
            'result': {'target_record_count': len(record_refs), 'listed_count': len(listed)},
            'feedback': None, 'publications_ref': publications}


async def assess_search_results(arguments, ctx):
    """The search step's Jev measurement (nano-graphrag ``SearchPageProposer._issue`` with ``assess_page_candidate``):
    Jev measures each hit once against the Search Goal, from its description (the journal, year and abstract the
    provider returned: a hit holds no other text, as in nano-graphrag), and this unit holds the assessment as an
    artifact the episode keeps (``search_assessment_ref``). The library function is pure; this unit alone writes. The
    Jev client reads its key (``TYPESAFE_API_KEY``) from the repository's ``.env`` at run time (``jev_client``); a
    missing key or a failed call raises."""
    results = arguments['results']
    assessment = await assess_results(JevDecisionClient.from_repository_env(), goal=arguments['goal'],
                                      results=results)
    ref = ctx.store.artifact(canonical(assessment), 'application/json')
    return {'status': 'completed', 'assessment_ref': ref, 'result_count': len(results),
            'window_count': sum(len(item['window_probabilities']) for item in assessment['assessments']),
            'request_count': sum(item['attempts'] for item in assessment['assessments'])}


async def fetch_search_hit(arguments, ctx):
    """The paper of the picked hit: the operation of ``public.literature.read`` on the hit's PMCID, run by code for the
    model's pick. Its outcome is the unit's outcome like any other, whatever the provider answered: a failed fetch is an
    outcome that completes the hit and is reported to the model with the provider status. An article this episode
    already holds with its text (an earlier fetch whose records it was given) is not fetched again: the unit completes
    on the held source, so the article has one record. A source record held without its text is fetched: the page
    reads the text. The page is commissioned by code once this unit completed (``decide``)."""
    pmcid = arguments['arguments']['hit']
    held = articles_held_with_text(ctx.store).get(pmcid)
    if held:
        return {'status': 'completed',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': FETCH, 'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': {'source_ref': held[0]}, 'feedback': None}
    return await run_operation(READ_OPERATION, {'pmcid': pmcid}, arguments['scope'], ctx)


TOOLS = {RUN_SEARCH: run_search, LIST: list_record_publications, ASSESS: assess_search_results,
         FETCH: fetch_search_hit}


def decide(summary, feedback, ctx):
    """The next unit. Before the provider search has run, the decision is that search; before Jev has measured the
    results, the decision is that measurement; straight after the fetch of a picked hit completed, the decision is the
    page on the paper; these are code attached to the units, with no model call (nano-graphrag runs the search and
    assesses every buffered result before its page proposer is asked). Otherwise the model picks one unprocessed hit,
    shown the assignment, its own outcomes, the credit definition, the candidates and their Jev assessment, the pages'
    returns, the measured time and the yield table."""
    if summary['pending_search'] is not None:
        return ToolCall(RUN_SEARCH, {'search_query_ref': summary['pending_search'], 'scope': summary['scope']})
    if summary['pending_listing'] is not None:
        return ToolCall(LIST, {'subject_refs': summary['pending_listing'], 'scope': summary['scope']})
    if assessment_pending(summary):
        return ToolCall(ASSESS, {'goal': summary['jev_search_goal'], 'results': summary['search_result_candidates']})
    if summary['pending_page'] is not None:
        return ChildCall('page', summary['pending_page'])
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'],
               'child_returns': summary['child_returns'], 'input_list': summary['input_list'],
               'consumed_inputs': summary['consumed_inputs'],
               'page_candidates': summary['search_planner_context'], 'hit_fetches': summary['hit_fetches'],
               'listed_publications': summary['listed_publications'],
               'tools': hit_tools(summary['input_list']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context, generation_schema(selection_schema(summary)))


def action(response, summary, records, ctx):
    """Turn the model's answer into the pick of one hit, or reject it (no unit): an answer that selects no offered hit
    or arguments that do not fit the schema is invalid (validation of the model's own answer)."""
    schema = selection_schema(summary)
    try:
        decoded = decode_response(response, schema)
        validate_schema(decoded, schema)
        selection = decoded['selection']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(selection['tool'], {'arguments': selection['arguments'], 'scope': summary['scope']})


def assessment_pending(summary):
    """Whether Jev has yet to measure the search results: there are results and no held assessment."""
    return summary['search_assessment_ref'] is None and bool(summary['search_result_candidates'])


def offered_actions(summary, ctx):
    """The action types offered at this decision: before the provider search ran the one action is ``run_search``;
    before Jev measured the results it is ``assess_search_results``; straight after a fetched hit it is the page;
    otherwise the hit-picking tool while an unprocessed hit remains."""
    if summary['pending_search'] is not None:
        return [RUN_SEARCH]
    if summary['pending_listing'] is not None:
        return [LIST]
    if assessment_pending(summary):
        return [ASSESS]
    if summary['pending_page'] is not None:
        return list(CHILD_SLOTS)
    return [entry['name'] for entry in hit_tools(summary['input_list'])]
