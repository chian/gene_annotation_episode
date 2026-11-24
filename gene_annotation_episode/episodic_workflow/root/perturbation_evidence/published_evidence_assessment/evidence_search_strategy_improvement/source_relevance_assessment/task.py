"""The task: run the one query the strategy handed over, measure its hits, pick one hit at a time and have its paper
examined.

This is nano-graphrag's web search (``web_search_binding``): it receives a query; the provider search runs
automatically; Jev scores every hit once, automatically; the model picks ONE unprocessed hit; the paper is obtained
when its page is built; a hit picked is done. It cannot read a paper or extract from one, commits no reasoning and
grades nothing: the sheets are graded automatically below, where a leaf extracts what it finds, and what returns here
is the credit and the controlled features of those sheets, with the sources the pages verified as leads.

One unit is one of: ``run_search`` (the provider search of the handed query, decided by code; the operation of
``public.literature.search`` through the same access path as the tool), ``assess_search_results`` (Jev's measurement of
the hits not yet measured, decided by code, no model call), ``fetch_search_hit`` (the model's pick of one unprocessed
hit; code obtains its paper, the operation of ``public.literature.read``, or opens the article it already holds) or
``literature_page`` (the page on the paper just obtained, commissioned by code straight after a completed pick). The
model is asked once per hit, at the pick; the other units follow from the state. A failed search, measurement or
paper fetch is an outcome like any other and enters the iterator. When every hit is processed the next unit is the
next page of the same provider search (the cursor the last response named): the task always offers a unit and never
ends the Episode, only the yield controller does.

The query is not in the commission: ``search_query_ref`` names a record of the strategy, which holds the request in its
``request_ref`` artifact, read here through custody (no query text travels between episodes).

Carried from the old task.py, task_decision.py, task_action.py, task_instructions.py, source_contracts.py of
``literature_search`` at 97308b94c. The old ``wait`` and ``redeliver_report`` actions are not carried (a child
completes inside the unit that commissioned it).

Not carried, and the reason: the access and acquisition tools the model was offered (reading or acquiring a paper
belongs to the levels below; the search level obtains a paper only when it builds the page), the reasoning commit and
the population route with the automatic score judgment (assessment is not a reasoning commit and the sheets are saved
by the leaves), the model's own choice of the page's source, representation and artifact (code fills them from the
source record), the commission of a page over a held source that is not a hit, and every task kind but
``verified_source_leads``."""
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    article_sources, assess_search_results as assess_results)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import JevDecisionClient
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    canonical, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The old role of ``_CHILDREN['literature_search']``, under its old name.
CHILD_SLOTS = {
    'literature_page': ('perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                        'source_relevance_assessment/source_evidence_examination'),
}
SERVICES = ()

POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
SEARCH = 'public.literature.search'
READ = 'public.literature.read'
# The library's input schemas of the two provider operations this episode runs by code.
INPUT_SCHEMAS = {SEARCH: obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query']),
                 READ: obj({'pmcid': TEXT})}

RUN_SEARCH = 'run_search'
ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'
PAGE = 'literature_page'
FETCH_DESCRIPTION = (
    'Pick one unprocessed hit of the search (the PMCID of an entry of input_list). Its paper is obtained for you and '
    'examined as a page: you do not read it. A hit you pick is done: it is not offered again, whatever the paper '
    'gives. page_candidates shows, for the unprocessed hits only, each one\'s provider rank, title, description and '
    'Jev assessment (relevance_probability: Jev\'s probability that the hit can contribute to the Search Goal) and the '
    'measured results of the previous pages (previous_page_children): these are measurements for your planning, not a '
    'rule that the largest probability must be picked.')
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_literature_outcomes; that page creates no new '
                    'action and does not execute or credit the historical work again.')
COMMISSION_GUIDANCE = ('\nThe search of the query you were handed has run and Jev has measured every hit once '
                       'against the Search Goal. Pick the next unprocessed hit worth examining (fetch_search_hit); '
                       'its paper is obtained and examined for you, and what it earns comes back as credit and the '
                       'controlled features of the A106 sheets graded below. You cannot read a paper, extract from '
                       'one or assess evidence: grading is automatic. The numerical controller alone decides '
                       'whether the search continues.')


def instructions():
    """The investigation text this episode shows: its goal, the history paragraph and the commission guidance. The
    library's reasoning-commit, acquisition and read texts are not carried: this episode has no such action."""
    return GOAL + '\n' + HISTORY_GUIDANCE + COMMISSION_GUIDANCE


def fetch_entry(input_list):
    """The one tool the model is shown: the pick of an unprocessed hit (only an entry of the input list)."""
    return {'name': FETCH, 'description': FETCH_DESCRIPTION,
            'input_schema': obj({'hit': {'enum': list(input_list)}})}


def selection_schema(input_list):
    """What the model answers with: the one pick of an unprocessed hit (the old action schema)."""
    entry = fetch_entry(input_list)
    return obj({'selection': obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                  'arguments': entry['input_schema']})})


async def run_provider(name, arguments, scope, ctx):
    """Run one provider operation through the registry. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other,
    whatever the provider answered."""
    try:
        validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    except (ContractError, ValidationError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name,
                                                        'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def run_search(arguments, ctx):
    """The provider search of the one query the strategy handed over (nano-graphrag ``web_search_binding``: the search
    level runs the provider search for the query it was handed): the request the query record holds, read through
    custody, with the cursor of the next page when the search runs again. Its outcome is the unit's outcome like any
    other, whatever the provider answered, and the retained response it produced is the result list the hits are read
    from (``messages/internal_summary.py``)."""
    envelope = arguments
    arguments = envelope['arguments']
    source = ctx.store.require(arguments['search_query_ref'], {'source'})
    request = json.loads(ctx.store.get_artifact(source['request_ref']))
    if arguments['cursor'] is not None:
        request = {**request, 'cursor': arguments['cursor']}
    return await run_provider(SEARCH, request, envelope['scope'], ctx)


async def assess_search_results(arguments, ctx):
    """The search step's Jev measurement (nano-graphrag ``SearchPageProposer._issue`` with ``assess_page_candidate``):
    Jev measures each hit once against the Search Goal, from its description (the journal, year and abstract the
    provider returned: a hit holds no other text, as in nano-graphrag), and this unit holds the assessment as an
    artifact the episode keeps (``search_assessment_refs``). The library function is pure; this unit alone writes. The
    Jev client reads its key from the repository's ``.env`` at run time (``jev_client``); a missing key or a failed
    call raises."""
    results = arguments['results']
    assessment = await assess_results(JevDecisionClient.from_repository_env(), goal=arguments['goal'],
                                      results=results)
    ref = ctx.store.artifact(canonical(assessment), 'application/json')
    return {'status': 'completed', 'assessment_ref': ref, 'result_count': len(results),
            'window_count': sum(len(item['window_probabilities']) for item in assessment['assessments']),
            'request_count': sum(item['attempts'] for item in assessment['assessments'])}


async def fetch_search_hit(arguments, ctx):
    """The paper of the picked hit: the operation of ``public.literature.read`` on the hit's PMCID, run by code for the
    model's pick. Its outcome is the unit's outcome like any other, whatever the provider answered: a failed fetch is
    an outcome that consumes the hit and is reported to the model with the provider status. An article this episode
    already holds in full is not fetched again: the unit completes on the held source, so the article has one record.
    The page on the paper is commissioned by code once this unit completed (``decide``)."""
    envelope = arguments
    pmcid = envelope['arguments']['hit']
    held = article_sources(ctx.store).get(pmcid)
    if held:
        return {'status': 'completed',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': FETCH,
                                                        'arguments': envelope['arguments']}),
                'record_refs': [], 'changed_record_refs': [], 'result': {'source_ref': held[0]}, 'feedback': None}
    return await run_provider(READ, {'pmcid': pmcid}, envelope['scope'], ctx)


TOOLS = {RUN_SEARCH: run_search, ASSESS: assess_search_results, FETCH: fetch_search_hit}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, or decide it by code. Straight after a pick whose paper was obtained the
    decision is the page on that paper (no model call). The first decision is the provider search of the handed query,
    and the one after every hit is processed is the next page of it (no model call). Before Jev has measured the new
    hits the decision is that measurement (no model call: nano-graphrag assesses every buffered result before its page
    proposer is asked). Otherwise the model is asked for the one hit to pick, shown the assignment, its own outcomes,
    the controlled features of the A106 sheets saved below, the unprocessed hits with Jev's measurement, the measured
    time and the yield table (the old decision state and inputs, over this episode's summary)."""
    if summary['pending_page'] is not None:
        return ChildCall(PAGE, summary['pending_page'])
    if summary['pending_search']:
        return ToolCall(RUN_SEARCH, {'arguments': {'search_query_ref': summary['search']['search_query_ref'],
                                                   'cursor': summary['search_cursor']},
                                     'scope': summary['scope']})
    if summary['unassessed_candidates']:
        return ToolCall(ASSESS, {'goal': summary['jev_search_goal'], 'results': summary['unassessed_candidates']})
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'a106_findings': summary['a106_findings'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'child_reports': summary['child_reports'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'page_candidates': summary['search_planner_context'], 'hit_fetches': summary['hit_fetches'],
               'tools': [fetch_entry(summary['input_list'])],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context,
                        generation_schema(selection_schema(summary['input_list'])))


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into the one pick of an unprocessed hit, or reject it (no unit). An answer that selects
    no offered tool, or a hit that is not an unprocessed hit of the input list, is invalid."""
    schema = selection_schema(summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(FETCH, {'arguments': selection['arguments'], 'scope': summary['scope']})


def offered_actions(summary, ctx):
    """The action types offered at this decision: straight after a pick whose paper was obtained it is the page; before
    the search ran, or once every hit is processed, the provider search; before Jev has measured the new hits that
    measurement; otherwise the pick of a hit."""
    if summary['pending_page'] is not None:
        return [PAGE]
    if summary['pending_search']:
        return [RUN_SEARCH]
    if summary['unassessed_candidates']:
        return [ASSESS]
    return [FETCH]
