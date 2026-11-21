"""The task: run the one search this episode was given, have Jev measure each hit, pick one unprocessed hit, and have the
paper that hit names examined by a page. This episode is nano-graphrag's web search: it receives a query (the record
``search_query_ref`` of the strategy that wrote it), the provider search runs automatically (``run_search``, decided by
code, no model call), Jev scores every hit once automatically (``assess_search_results``, decided by code, no model
call), the model picks ONE unprocessed hit (the tool ``fetch_search_hit``), code obtains that hit's paper (the
operation of ``public.literature.read``, or the held source when the article is already held) and, when the fetch
completed, commissions the page on it with no model call. A hit picked is done: it is not offered again. This episode
has no read tool, no reasoning commit and no other action: it cannot read or extract.

A search result is ONE HIT of the provider's result list (its PMCID, rank, title, journal, year and the abstract the
provider returned), not a fetched document. Every decision shows the model nano-graphrag's candidate view for the
UNCONSUMED hits only (``context.page_candidates``: each hit's Jev probability, provider rank, title and description,
and the measured outcomes of the prior page children). Jev is planning evidence, not the selection policy.

Carried from the old task.py, task_decision.py, task_instructions.py and source_contracts.py of ``literature_search``
at 97308b94c (the old child role ``literature_page`` is the slot below), and from nano-graphrag's
``web_search_binding`` (``SEARCH_PAGE_SELECTION_VERSION`` ``model_planned_from_jev_evidence_v5``). One unit is one
search, one measurement, one fetch of a picked hit or one page commission. The task always offers a unit and never ends
the Episode: only the yield controller does. A hit whose fetch failed is shown in ``context.hit_fetches`` with the
provider status and is never opened. When no hit is left there is no unit to offer and ``decide`` raises: the stopping
of an episode without a candidate belongs to its yield estimator alone, which this episode's cannot do before a unit.

Settings read (``ctx.settings``): ``tool_registry`` (the JSON keyword arguments of the library ``ToolRegistry``; its
``PublicClients`` are the declared service ``public_clients``). The Jev client reads its key from the repository's
``.env`` at run time (``jev_client``); a missing key or a failed call raises."""
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    article_sources, assess_search_results as assess_results)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import JevDecisionClient
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    canonical, identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The one child (the old ``_CHILDREN['literature_search']``: literature_page), by slot.
CHILD_SLOTS = {
    'source_evidence_examination': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
}
SERVICES = ('public_clients',)

RUN_SEARCH = 'run_search'
ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'
FETCH_DESCRIPTION = (
    'Pick ONE unprocessed hit of the search (hit: its id, the PMCID, from input_list; choose it from '
    'context.page_candidates: its Jev probability, provider rank, title, description and the measured outcomes of the '
    'previous page children). Code fetches that hit\'s full text and has the paper examined by a page; you read '
    'nothing yourself. A hit you pick is done and is not offered again.')
PAGE_CANDIDATE_GUIDANCE = (
    '\nJev has measured every hit of the search once against the Search Goal. context.page_candidates shows, for the '
    'UNPROCESSED hits only, each one\'s provider rank, title, description and Jev assessment (relevance_probability: '
    'Jev\'s probability that the hit can contribute to the Search Goal), and the measured results of the previous '
    'page children (previous_page_children). These are measurements for your planning, not a rule that the largest '
    'probability must be selected: use them and the realized results of previous children to choose the next hit worth '
    'examining. One page child takes one paper; the numerical controller alone decides whether the search continues.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets your '
                   'descendants saved, with their references; nothing you write in prose is returned. Selecting a '
                   'hit never ends your work: only the numerical controller does.')


def fetch_schema(input_list):
    """The hit the model may pick: only an unprocessed hit of the input list, so a hit already picked cannot be
    selected."""
    return obj({'hit': {'type': 'string', 'enum': list(input_list)}})


def instructions():
    return GOAL + PAGE_CANDIDATE_GUIDANCE + RETURN_GUIDANCE


def catalog(input_list):
    """The tool the model is shown while an unprocessed hit remains: name, description and input schema."""
    if not input_list:
        return []
    return [{'name': FETCH, 'description': FETCH_DESCRIPTION, 'input_schema': fetch_schema(input_list)}]


def selection_schema(input_list):
    """What the model answers with: the one hit it picks."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
        for entry in catalog(input_list)]}})


def offered_actions(summary, ctx):
    """The action types offered at this decision: before the provider search ran the one action is ``run_search``;
    before Jev measured the hits it is ``assess_search_results``; straight after a fetched hit it is the page;
    otherwise the hit-picking tool while an unprocessed hit remains."""
    if summary['pending_search'] is not None:
        return [RUN_SEARCH]
    if assessment_pending(summary):
        return [ASSESS]
    if summary['pending_page'] is not None:
        return list(CHILD_SLOTS)
    return [entry['name'] for entry in catalog(summary['input_list'])]


def assessment_pending(summary):
    """Whether Jev has yet to measure the hits: there are hits and no held assessment."""
    return summary['search_assessment_ref'] is None and bool(summary['search_result_candidates'])


async def run_registry(name, arguments, ctx, scope):
    """Execute one acquisition operation of the tool registry: a failed operation is an outcome like any other."""
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def run_search(arguments, ctx):
    """The provider search of the one search the strategy handed over (nano-graphrag ``web_search_binding``: the search
    level runs the provider search for the query it was handed). The query is not in the commission: ``search_query_ref``
    names a record of the strategy, which holds the request in its ``request_ref`` artifact, read here through custody.
    The unit is the operation of ``public.literature.search``; its outcome is the unit's outcome like any other,
    whatever the provider answered, and the retained response it produced is the result list the hits are read from
    (``messages/internal_summary.py``)."""
    source = ctx.store.require(arguments['arguments']['search_query_ref'], {'source'})
    request = json.loads(ctx.store.get_artifact(source['request_ref']))
    return await run_registry('public.literature.search', request, ctx, arguments['scope'])


async def assess_search_results(arguments, ctx):
    """The search step's Jev measurement (nano-graphrag ``SearchPageProposer._issue`` with ``assess_page_candidate``):
    Jev measures each hit once against the Search Goal, from its description (the journal, year and abstract the
    provider returned: a hit holds no other text, as in nano-graphrag), and this unit holds the assessment as an
    artifact the episode keeps (``search_assessment_ref``). The library function is pure; this unit alone writes."""
    results = arguments['results']
    assessment = await assess_results(JevDecisionClient.from_repository_env(), goal=arguments['goal'],
                                      results=results)
    ref = ctx.store.artifact(canonical(assessment), 'application/json')
    return {'status': 'completed', 'assessment_ref': ref, 'result_count': len(results),
            'window_count': sum(len(item['window_probabilities']) for item in assessment['assessments']),
            'request_count': sum(item['attempts'] for item in assessment['assessments'])}


async def fetch_search_hit(arguments, ctx):
    """The full text of the picked hit: the operation of ``public.literature.read`` on the hit's PMCID, run by code
    for the model's pick. Its outcome is the unit's outcome like any other, whatever the provider answered: a failed
    fetch is an outcome that consumes the hit and is reported to the model with the provider status. An article this
    episode already holds in full is not fetched again: the unit completes on the held source, so the article has one
    record. The page is commissioned by code once this unit completed (``decide``)."""
    pmcid = arguments['arguments']['hit']
    held = article_sources(ctx.store).get(pmcid)
    if held:
        return {'status': 'completed',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': FETCH,
                                                        'arguments': arguments['arguments']}),
                'record_refs': [], 'changed_record_refs': [], 'result': {'source_ref': held[0]}, 'feedback': None}
    return await run_registry('public.literature.read', {'pmcid': pmcid}, ctx, arguments['scope'])


TOOLS = {RUN_SEARCH: run_search, ASSESS: assess_search_results, FETCH: fetch_search_hit}


def decide(summary, feedback, ctx):
    """Before the provider search ran the decision is that search, made by code with no model call; before Jev has
    measured the hits it is that measurement, also by code (nano-graphrag assesses every buffered result before its page
    proposer is asked); straight after the fetch of a picked hit completed it is the page on the fetched article, also
    by code. Otherwise ask the model for the next hit, shown the assignment, the candidate view of the unprocessed hits,
    what the fetches came to, what the page children returned, the credit definition, the measured time and the yield
    table."""
    if summary['pending_search'] is not None:
        return ToolCall(RUN_SEARCH, {'arguments': {'search_query_ref': summary['pending_search']},
                                     'scope': summary['scope']})
    if assessment_pending(summary):
        return ToolCall(ASSESS, {'goal': summary['jev_search_goal'], 'results': summary['search_result_candidates']})
    if summary['pending_page'] is not None:
        return ChildCall(next(iter(CHILD_SLOTS)), summary['pending_page'])
    if not summary['input_list']:
        raise LookupError('no_hit_left_to_offer')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'child_returns': summary['child_reports'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'page_candidates': summary['search_planner_context'], 'hit_fetches': summary['hit_fetches'],
               'tools': catalog(summary['input_list']), 'feedback': feedback,
               'action_yields': summary['action_yields'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(), context,
                        generation_schema(selection_schema(summary['input_list'])))


def action(response, summary, records, ctx):
    """Turn the model's answer into the fetch of the one hit it picked, or reject it (no unit). An answer that selects
    no offered hit or arguments that do not fit the schema is invalid (validation of the model's own answer)."""
    schema = selection_schema(summary['input_list'])
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(selection['tool'], {'arguments': selection['arguments'], 'scope': summary['scope']})
