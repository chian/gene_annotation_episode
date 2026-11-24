"""Where the search stands, as a pure function of the loop's view: the assignment, the hits the provider search of the
handed query returned (each with its provider rank), Jev's measurement of them, the hits picked and the page children
commissioned on their papers, the controlled features of the A106 sheets the pages saved and returned, and the typed
answer the commissioned task asks for (carried from the old ``internal_summary.py``: ``literature_assignment``,
``own_literature_outcomes``, ``literature_history_meaning``; the old reads of ``runtime_actions`` are the unit outcomes
of ``view``, and the old ``completed_action_reports`` are the child reports ``read_from_child`` made).

The search step (nano-graphrag ``web_search_binding``: ``assess_page_candidate`` and ``SearchPageProposer``). The
assignment names ONE query (``search_query_ref``: a record of the strategy that holds a provider search request, read
through custody); code runs it (the ``run_search`` unit, the operation of ``public.literature.search`` through the
same access path) and the retained Europe PMC search response it returns is the result list. A search result is ONE HIT
of such a list: its PMCID, provider rank (its position among the distinct publications of the lists, in the order they
were returned), title and a description (journal, year and the abstract the provider returned). Two hits of the same
publication are one result. ``jev_search_goal`` is the immutable Search Goal Jev measures them against (the runner's
goal record of this episode, as nano-graphrag's ``goal.as_record()``, with the task and subject the commission
requests); ``search_assessment_refs`` are the assessments the code-decided ``assess_search_results`` units hold (one
per list of hits, each hit measured once), and ``search_planner_context`` is those assessments over the unprocessed
hits only, with the measured outcomes of the prior page children (``prior_page_outcomes``).

The model picks an unprocessed hit (``fetch_search_hit``); code obtains its paper (the operation of
``public.literature.read``; an article already held is opened without a new fetch) and, when that completed,
commissions the page on it (``pending_page``): the paper's representation and artifact are filled by code from its
source record. A hit is consumed by its pick; a hit whose fetch failed is reported in ``hit_fetches`` with the
provider status and is never opened.

When every hit of the lists is processed the next unit is the next page of the same provider search (``pending_search``,
the cursor the last response named), run by code: the episode always offers a unit, and only its yield controller
stops it (nano-graphrag ends a search whose list is empty).

The old display contexts of the population route are replaced by the controlled features of the G1 and G2 sheets
(``a106_findings``), which this episode only receives from its pages: it saves no sheet itself."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    hit_candidate, ranked_hits, search_planner_context, source_kind)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions
from ..goal import BINDING_PATH, RESULT, UNIT

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
RUN_SEARCH = 'run_search'
ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'
PAGE = 'literature_page'
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. A hit '
                   'delivered does not establish scientific understanding, absence or resolved science.')
NO_FINDING = {'intervention_assessments': [], 'a106_subscores': []}


def result_responses(outcomes):
    """The retained search responses the searches this episode ran returned, in the order run (the sources their
    units produced)."""
    return list(dict.fromkeys(ref for outcome in outcomes
                              if outcome['kind'] == 'tool' and outcome['tool'] == RUN_SEARCH
                              for ref in outcome['outcome']['record_refs']))


def search_hits(response_refs, records):
    """The distinct hits of the result lists the searches this episode ran returned, each with its provider rank
    (``ranked_hits``). A result list that is not a retained search response fails."""
    contents = []
    for ref in response_refs:
        source = records.get(ref)
        if source_kind(source) != 'search_response':
            raise ValueError('search_result_is_not_a_search_response:' + ref)
        contents.append(records.get_artifact(source['artifact_ref']))
    return ranked_hits(contents)


def next_cursor(response_refs, records):
    """The cursor the last retained search response names for the next page of the same search, or None."""
    if not response_refs:
        return None
    last = records.get(response_refs[-1])
    return json.loads(records.get_artifact(last['artifact_ref'])).get('nextCursorMark')


def consumed_hits(outcomes):
    """The hits handed out, in the order handed out (nano-graphrag ``_processed_ranks``: a hit taken up is done and
    no longer offered): the hits this episode picked, whether the fetch of the paper completed or failed."""
    return list(dict.fromkeys(outcome['arguments']['arguments']['hit'] for outcome in outcomes
                              if outcome['kind'] == 'tool' and outcome['tool'] == FETCH))


def hit_fetches(outcomes):
    """What each fetch of a hit came to, for the model: the hit, the unit's status and, when the provider refused,
    its status code; a hit whose fetch did not complete is never opened."""
    return [{'hit': outcome['arguments']['arguments']['hit'], 'status': outcome['outcome']['status'],
             'provider_status': (outcome['outcome']['feedback'] or {}).get('code')}
            for outcome in outcomes if outcome['kind'] == 'tool' and outcome['tool'] == FETCH]


def page_of(records, source_ref):
    """The page the child is commissioned on, from the source record alone: its text representation when the source
    holds one, else its original bytes, with that representation's artifact; no earlier delivery is held for a paper
    the search just obtained; and the records the child is passed in custody (the paper and its artifacts). The
    model does not type any of these."""
    source = records.get(source_ref)
    representation = 'text' if source.get('text_ref') is not None else 'original'
    return {'source_ref': source_ref, 'representation': representation,
            'artifact_ref': source['text_ref' if representation == 'text' else 'artifact_ref'],
            'prior_delivery_refs': [],
            'custody': [source_ref, *[source[key] for key in ARTIFACT_KEYS if source.get(key) is not None]]}


def pending_page(last, records):
    """The page commission code makes straight after a pick whose paper was obtained: the page on that paper; None at
    every other point."""
    if last is None or last['kind'] != 'tool' or last['tool'] != FETCH or last['outcome']['status'] != 'completed':
        return None
    return {'hit': last['arguments']['arguments']['hit'],
            'page': page_of(records, last['outcome']['result']['source_ref'])}


def label_of(records, ref):
    return records.get(ref).get('label') or ref


def search_goal(view, parent, records):
    """The immutable Search Goal Jev measures every result against, derived from the commission (nano-graphrag:
    ``EpisodeGoal.for_grain(search_grain, parent=strategy goal, objective=...)`` and ``goal.as_record()``). The runner
    already built this episode's goal as the child of its commissioner's goal with the commission's objective
    (``view.goal``); its record is carried as it is, with this episode's grain (binding path, unit, result) and what
    the commission requests: the commissioned task (its key and kind), the labels of the question-context records and
    the subject of the proposed annotation (its predicate and the labels of its records)."""
    task = parent['task']
    hypothesis = records.get(parent['proposed_annotation_ref'])
    value = hypothesis['value']
    requested = {'task_key': parent['task_key'], 'task_kind': task['kind'], 'evidence_axis': task['evidence_axis']}
    return {**view.goal.as_record(), 'grain': {'binding_path': BINDING_PATH, 'unit': UNIT, 'result': RESULT},
            'requested_results': requested,
            'question_context': [label_of(records, ref) for ref in parent['search']['question_context_refs']],
            'subject': {'predicate': hypothesis['predicate'],
                        'subjects': [label_of(records, ref) for ref in hypothesis['subject_refs']],
                        'partner': (label_of(records, value['ref']) if value.get('type') in ('term_ref', 'reference')
                                    else value)}}


def prior_page_outcomes(children, ranks):
    """The compact measured outcome of each page child, in the order commissioned (nano-graphrag
    ``record_page_outcome``): the hit it was handed and its provider rank, how it ended, its units, its credit and the
    counts of its finding and of the lead sources it returned."""
    return [{'result_id': outcome['arguments']['hit'], 'provider_rank': ranks.get(outcome['arguments']['hit']),
             'ended_by': outcome['completion']['ended_by'],
             'units_consumed': outcome['completion']['units_consumed'], 'credit': outcome['report']['credit'],
             'intervention_assessments': len(outcome['report']['finding']['intervention_assessments']),
             'a106_subscores': len(outcome['report']['finding']['a106_subscores']),
             'lead_sources': len(outcome['report'].get('lead_source_refs', ()))}
            for outcome in children]


def assessments_held(outcomes, records):
    """The Jev assessments this episode holds: the references of its ``assess_search_results`` units and the
    assessment of each hit they measured, by hit."""
    refs = [outcome['outcome']['assessment_ref'] for outcome in outcomes
            if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    held = [json.loads(records.get_artifact(ref)) for ref in refs]
    return refs, held, {item['result_id']: item for assessment in held for item in assessment['assessments']}


def internal_summary(view):
    parent = view.parent_input
    search, task = parent['search'], parent['task']
    records = view.records
    outcomes = view.outcomes
    children = [outcome for outcome in outcomes if outcome['kind'] == 'child']
    last = outcomes[-1] if outcomes else None
    responses = result_responses(outcomes)
    hits = search_hits(responses, records)
    consumed = consumed_hits(outcomes)
    # The input list (nano-graphrag's input-list paradigm): the hits of the result lists in the order the search returned
    # them that this episode has not picked. A hit leaves the list when it is picked (its work is handed to a page), not
    # when its paper is held. The yield estimator does not pass it as items (``items=None``): the hits are known only
    # once the search ran, and an empty list ends no episode (the next provider page is run instead).
    candidates = [hit_candidate(hit) for hit in hits]
    input_list = [item['result_id'] for item in candidates if item['result_id'] not in consumed]
    # Jev's measurement of the hits (nano-graphrag ``SearchPageProposer``): held once per hit by the code-decided
    # ``assess_search_results`` units; the planner sees it for the unprocessed hits only.
    refs, assessments, by_hit = assessments_held(outcomes, records)
    unassessed = [item for item in candidates if item['result_id'] not in by_hit and item['result_id'] in input_list]
    page_outcomes = prior_page_outcomes(children, {hit['pmcid']: hit['provider_rank'] for hit in hits})
    merged = (None if not assessments or unassessed else
              {**assessments[0], 'assessments': sorted(by_hit.values(), key=lambda item: item['provider_rank'])})
    searched = [outcome for outcome in outcomes if outcome['kind'] == 'tool' and outcome['tool'] == RUN_SEARCH]
    # The leads in the order of the units: each relevant lead source an admitted page return names (the old
    # ``lead_dispositions`` merged them by decision order).
    leads = [{'source_ref': ref, 'disposition': 'relevant', 'proposed_annotation_ref': parent['proposed_annotation_ref']}
             for outcome in children for ref in outcome['report'].get('lead_source_refs', ())]
    assignment = {**search, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment, 'search': search,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(RUN_SEARCH, ASSESS, FETCH),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'input_list': input_list, 'consumed_inputs': consumed,
        'hit_fetches': hit_fetches(outcomes),
        'pending_page': pending_page(last, records),
        'pending_search': not searched or (not input_list and not unassessed),
        'search_cursor': next_cursor(responses, records),
        'search_result_candidates': candidates, 'unassessed_candidates': unassessed,
        'jev_search_goal': search_goal(view, parent, records),
        'search_assessment_refs': refs,
        'prior_page_outcomes': page_outcomes,
        'search_planner_context': (None if merged is None
                                   else search_planner_context(merged, input_list, page_outcomes)),
        'child_reports': [{'slot': outcome['slot'], 'arguments': outcome['arguments'], 'report': outcome['report']}
                          for outcome in children],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': merged_findings(NO_FINDING, [outcome['report']['finding'] for outcome in children]),
        'source_leads': leads,
    }
    summary['source_lead_dispositions'] = lead_dispositions(summary, records)
    return summary
