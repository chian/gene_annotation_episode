"""Where the investigation stands, as a pure function of the loop's view: the assignment, the provider search run for the
query handed over, the hits of its result list and Jev's measurement of them, the pages commissioned (their credit and
the controlled features of their findings) and the sheet the latest page holds.

The search step's Jev measurement (nano-graphrag ``web_search_binding``: ``assess_page_candidate`` and
``SearchPageProposer``): the assignment names ONE query (``search_query_ref``: a record of the strategy that holds a
provider search request, read through custody); code runs it (the ``run_search`` unit, the operation of
``public.literature.search``) and the retained Europe PMC search response it returns is the result list. A search
result is ONE HIT of that list: its PMCID, provider rank (its position among the distinct publications of the list),
title and a description (journal, year and the abstract the provider returned). Two hits of the same publication are one
result, and an article a page has examined (``examined_article_refs`` of the assignment: the articles the pages of
earlier runs examined and returned, plus this episode's own pages) is not a result any more. ``jev_search_goal`` is the
immutable Search Goal Jev measures them against (the runner's goal record of this episode, as nano-graphrag's
``goal.as_record()``, with the commissioned task and the subject of the claim); ``search_assessment_ref`` is the
assessment the automatic ``assess_search_results`` unit holds, and ``search_planner_context`` is that assessment over the
unprocessed results only with the measured outcomes of the prior pages (``prior_page_outcomes``).

The model picks an unprocessed hit; code obtains its paper (``fetch_search_hit``, the operation of
``public.literature.read``; an article already held is opened without a new fetch) and, when that completed,
commissions the page on the paper (``pending_page``). A hit is done by its pick; a hit whose fetch failed is reported in
``hit_fetches`` with the provider status and is never opened."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    relevant_lead_sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    article_sources, hit_candidate, ranked_hits, search_planner_context, source_kind)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_record_publications import (
    PARTIAL_LIST, listed_without_full_text, merge_listed)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import BINDING_PATH, PLANNING_QUESTION, RESULT, UNIT

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
UNITS = ('run_search', 'list_record_publications', 'assess_search_results', 'fetch_search_hit')
RUN_SEARCH = 'run_search'
LIST = 'list_record_publications'
ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'


def search_run(outcomes):
    """Whether the provider search of this episode's query has run: a ``run_search`` unit was made."""
    return any(outcome['kind'] == 'tool' and outcome['tool'] == RUN_SEARCH for outcome in outcomes)


def next_search(parent, outcomes):
    """The query code runs next (nano-graphrag ``web_search_binding``: the search level runs the provider search for the
    query it was handed): the one query of the assignment while no ``run_search`` unit was made; None after."""
    return None if search_run(outcomes) else parent['search']['search_query_ref']


def listing_subjects(parent, records):
    """The subjects whose own records' listed papers are looked up: the protein subjects of the proposed annotation
    that carry a sequence (the sequence is what finds the records equal to the target's)."""
    subjects = records.get(parent['proposed_annotation_ref'])['subject_refs']
    return [ref for ref in subjects if records.subject_molecule(ref) == 'protein' and records.get(ref).get('sequence_ref')]


def next_listing(parent, outcomes, records):
    """The subjects code looks up next: those of the proposed annotation while no ``list_record_publications`` unit was
    made and the search has run; None after, and None when no subject has a sequence to look up."""
    if not search_run(outcomes) or any(outcome['kind'] == 'tool' and outcome['tool'] == LIST for outcome in outcomes):
        return None
    return listing_subjects(parent, records) or None


def listed_hits(outcomes, records):
    """The papers the database lists for the target's own records, held by the ``list_record_publications`` unit (every
    listed paper, with its PMCID when Europe PMC gave one); empty when the unit did not complete or was not made."""
    listed = []
    for outcome in outcomes:
        if outcome['kind'] == 'tool' and outcome['tool'] == LIST and outcome['outcome']['status'] == 'completed':
            listed += json.loads(records.get_artifact(outcome['outcome']['publications_ref']))['listed']
    return listed


def result_response(outcomes):
    """The retained search response the search this episode ran returned (the sources its unit produced)."""
    return list(dict.fromkeys(ref for outcome in outcomes
                              if outcome['kind'] == 'tool' and outcome['tool'] == RUN_SEARCH
                              for ref in outcome['outcome']['record_refs']))


def consumed_results(outcomes):
    """The search results picked, in the order picked (nano-graphrag ``web_search_binding``: a result taken up is done
    and no longer offered): the hits this episode fetched, whether the fetch completed or failed."""
    return list(dict.fromkeys(outcome['arguments']['arguments']['hit'] for outcome in outcomes
                              if outcome['kind'] == 'tool' and outcome['tool'] == FETCH))


def search_hits(response_refs, records):
    """The distinct hits of the result list the search this episode ran returned, each with its provider rank
    (``ranked_hits``). A result list that is not a retained search response fails."""
    contents = []
    for ref in response_refs:
        source = records.get(ref)
        if source_kind(source) != 'search_response':
            raise ValueError('search_result_is_not_a_search_response:' + ref)
        contents.append(records.get_artifact(source['artifact_ref']))
    return ranked_hits(contents)


def hit_fetches(outcomes):
    """What each fetch of a hit came to, for the model: the hit, the unit's status and, when the provider refused,
    its status code; a hit whose fetch did not complete is never opened."""
    return [{'hit': outcome['arguments']['arguments']['hit'], 'status': outcome['outcome']['status'],
             'provider_status': (outcome['outcome']['feedback'] or {}).get('code')}
            for outcome in outcomes if outcome['kind'] == 'tool' and outcome['tool'] == FETCH]


def page_of(records, source_ref):
    """The page the child is commissioned on, from the source record alone: its text representation when the source
    holds one, else its original bytes, with that representation's artifact; no earlier delivery is held for a source
    the search just returned. The model does not type any of these."""
    source = records.get(source_ref)
    representation = 'text' if source.get('text_ref') is not None else 'original'
    return {'source_ref': source_ref, 'representation': representation,
            'artifact_ref': source['text_ref' if representation == 'text' else 'artifact_ref'],
            'prior_delivery_refs': []}


def pending_page(last, records):
    """The page commission code makes straight after a fetch that completed: the paper that was fetched for the hit the
    model picked; None at every other point."""
    if last is None or last['kind'] != 'tool' or last['tool'] != FETCH or last['outcome']['status'] != 'completed':
        return None
    return {'hit': last['arguments']['arguments']['hit'],
            'page': page_of(records, last['outcome']['result']['source_ref'])}


def label_of(records, ref):
    return records.get(ref).get('label') or ref


def search_goal(view, task, task_key, proposed, records):
    """The immutable Search Goal Jev measures every result against (nano-graphrag: ``EpisodeGoal.for_grain(search_grain,
    parent=strategy goal, objective=...)`` and ``goal.as_record()``). The runner already built this episode's goal as
    the child of its commissioner's goal with the commission's objective (``view.goal``); its record is carried as it is
    (goal id, parent goal id, objective, result contract, root task context), with this episode's grain (binding path,
    unit, result) and what the commission requests: the commissioned task and the subject of the proposed annotation
    (its predicate and the labels of its records)."""
    hypothesis = records.get(proposed)
    value = hypothesis['value']
    return {**view.goal.as_record(), 'grain': {'binding_path': BINDING_PATH, 'unit': UNIT, 'result': RESULT},
            'requested_results': {'task_key': task_key, 'task_kind': task['kind']},
            'subject': {'predicate': hypothesis['predicate'],
                        'subjects': [label_of(records, ref) for ref in hypothesis['subject_refs']],
                        'partner': (label_of(records, value['ref']) if value.get('type') in ('term_ref', 'reference')
                                    else value)}}


def prior_page_outcomes(children, ranks):
    """The compact measured outcome of each page, in the order commissioned (nano-graphrag ``record_page_outcome``): the
    result it was handed and its provider rank, how it ended, its units, its credit and the counts of its finding."""
    return [{'result_id': outcome['arguments']['hit'], 'provider_rank': ranks.get(outcome['arguments']['hit']),
             'ended_by': outcome['completion']['ended_by'],
             'units_consumed': outcome['completion']['units_consumed'], 'credit': outcome['report']['credit'],
             'distinct_findings': len(outcome['report']['features']), 'scores': len(outcome['report']['scores']),
             'lead_sources': len(outcome['report']['lead_source_refs'])}
            for outcome in children]


def internal_summary(view):
    parent = view.parent_input
    search, task = parent['search'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The input list (nano-graphrag's input-list paradigm): the hits of the result list of the query, in the order the
    # search returned them, that this episode has not picked and whose article no page has examined (a page of an
    # earlier run, named by ``examined_article_refs`` of the assignment, or a page of this episode). A hit picked is
    # done; the list shrinks by one per hit picked, and once it is empty no hit is offered (``task.offered_actions``).
    # The yield estimator does not pass it as items (``items=None``), so an empty list ends no episode: the
    # accumulation controller (``ADAPTIVE_CONTROL``, no cost) stops after 4 flat units in a row (expected next credit's
    # upper bound at or below the adaptive gamma, once W = 8 attempted, m = 4 observed).
    consumed = consumed_results(view.outcomes)
    # The hit list is the provider search's hits and then the papers the database lists for the target's own records
    # that can be opened, each paper once (a paper that shares a PMCID, PMID or DOI with an earlier hit is that hit).
    listed = listed_hits(view.outcomes, records)
    hits = merge_listed(search_hits(result_response(view.outcomes), records), listed)
    examined = set(parent['examined_article_refs']) | {outcome['arguments']['page']['source_ref']
                                                      for outcome in children}
    held = article_sources(records)
    candidates = [hit_candidate(hit) for hit in hits if not examined.intersection(held.get(hit['pmcid'], ()))]
    input_list = [item['result_id'] for item in candidates if item['result_id'] not in consumed]
    # Jev's measurement of the search results (nano-graphrag ``SearchPageProposer``): held once by the automatic
    # ``assess_search_results`` unit; the planner sees it for the unprocessed results only.
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    page_outcomes = prior_page_outcomes(children, {hit['pmcid']: hit['provider_rank'] for hit in hits})
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {**search, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    return {
        'literature_assignment': assignment, 'search': search,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=UNITS, tool_of=lambda outcome: outcome.get('tool')),
        'literature_goal_plan': {'objective': view.goal.as_record()['objective'],
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task,
                                 'progress_definition': credit_binding(parent['task_key'], task),
                                 'planning_question': PLANNING_QUESTION},
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'input_list': input_list, 'consumed_inputs': consumed,
        'hit_fetches': hit_fetches(view.outcomes), 'pending_page': pending_page(last, records),
        'pending_search': next_search(parent, view.outcomes),
        'pending_listing': next_listing(parent, view.outcomes, records),
        'listed_publications': {'source': 'database_list_for_records_of_the_target_sequence', 'partial': True,
                                'meaning': PARTIAL_LIST,
                                'result_ids': [hit['pmcid'] for hit in hits if hit.get('listed_by')],
                                'listed_without_full_text': listed_without_full_text(listed)},
        'examined_article_refs': [outcome['arguments']['page']['source_ref'] for outcome in children],
        'search_result_candidates': candidates,
        'jev_search_goal': search_goal(view, task, parent['task_key'], parent['proposed_annotation_ref'], records),
        'search_assessment_ref': assessment_ref,
        'prior_page_outcomes': page_outcomes,
        'search_planner_context': (None if assessment is None
                                   else search_planner_context(assessment, input_list, page_outcomes)),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'credit': outcome['report']['credit'],
                           'scores': outcome['report']['scores'], 'features': outcome['report']['features']}
                          for outcome in children],
        # The page child returns the whole subscoring sheet as it stands after it, starting from the states this episode
        # passed to it: the latest page's states, scores and features are the current sheet. Before any page returned,
        # the sheet is the one this episode was given (the states its commissioner passed, no scores, no features).
        'sheet_state_refs': children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs'],
        'given_sheet_state_refs': list(parent['sheet_state_refs']),
        # A child that changed nothing returns the sheet it was given and no finding, so the finding of the sheet as it
        # stands is the one of the latest child return that carries one (none before any child changed the sheet).
        'scores': next((child['report']['scores'] for child in reversed(children) if child['report']['features']), []),
        'features': next((child['report']['features'] for child in reversed(children) if child['report']['features']), []),
        'lead_source_refs': relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records),
    }
