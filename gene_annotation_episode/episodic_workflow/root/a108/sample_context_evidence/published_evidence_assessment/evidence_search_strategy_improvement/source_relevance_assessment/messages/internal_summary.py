"""Where the search stands, as a pure function of the loop's view: the search assignment (ONE search, the record of the
query the strategy wrote), the provider search this episode ran for it, the hits that search returned (each one a
provider hit with its rank, title and description, not a fetched document), Jev's measurement of each hit, the hits
picked and what became of them, what the page children returned, the investigation findings of the sheets saved below
and the typed answer the commissioned task asks for.

Carried from nano-graphrag's ``web_search_binding`` (the search level receives a query, runs the provider search, has
Jev score every hit once, lets the model pick ONE unprocessed hit, obtains the paper when its page is built and
processes no hit twice) and from the old ``internal_summary.py`` of ``literature_search`` at 97308b94c. The search
cannot read or extract, so the source custody of the held sources, the received-fact display, the population contexts,
the visual evidence and the reasoning outcomes of the old context are gone.

The input list: the hits of the result list this search returned, in the order the provider returned them, that this
episode has not picked. A hit picked is consumed by its fetch (a hit whose fetch failed is consumed too and shown in
``hit_fetches``); the list shrinks by one per hit picked and, once it is empty, no hit is offered. The yield estimator
does not pass it as items (``items=None``).

Straight after a fetch that completed the next unit is the page on the fetched article (``pending_page``), commissioned
by code with no model call: the model picked the hit, and the page is built from the source record alone."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    article_sources, hit_candidate, ranked_hits, search_planner_context, source_kind)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis, merged_findings, own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_return
from ..goal import BINDING_PATH, GOAL, RESULT, UNIT
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
SEARCH_ASSIGNMENT = 'search_assignment'
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. The provider search, Jev\'s measurement and each hit picked are shown '
                   'in the candidate view and hit_fetches.')
GRADING_NAMESPACE = 'literature_a108_grading_cells'
AGGREGATION_NAMESPACE = 'literature_a108_aggregation_cells'
RUN_SEARCH = 'run_search'
ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'
PLANNING_QUESTION = ('Which of the unprocessed hits of this search is worth having examined for the assigned question? '
                     'Pick one.')


def source_custody(records, held):
    """The custody of each held source: its version, artifacts and the sources it derives from."""
    return {reference: {key: records.get(reference).get(key) for key in CUSTODY_KEYS}
            for reference in held if reference.startswith('source_')}


def search_run(parent, outcomes):
    """The unit that ran the provider search of the assignment, or None before it ran."""
    return next((outcome for outcome in outcomes if outcome['kind'] == 'tool' and outcome['tool'] == RUN_SEARCH), None)


def search_hits(run, records):
    """The distinct hits of the result list the search returned, each with its provider rank (``ranked_hits``). The
    retained response the provider search produced must be a search response. A search that did not complete returned
    no result list: there is no hit."""
    if run is None or run['outcome']['status'] != 'completed':
        return []
    contents = []
    for ref in run['outcome']['record_refs']:
        source = records.get(ref)
        if source_kind(source) != 'search_response':
            raise ValueError('search_result_is_not_a_search_response:' + ref)
        contents.append(records.get_artifact(source['artifact_ref']))
    return ranked_hits(contents)


def consumed_hits(outcomes):
    """The hits picked, in the order picked (nano-graphrag: a hit picked is done): the hits this episode fetched,
    whether the fetch completed or failed."""
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
    holds one, else its original bytes, with that representation's artifact; no earlier delivery is held for a source
    the search just returned. The model does not type any of these."""
    source = records.get(source_ref)
    representation = 'text' if source.get('text_ref') is not None else 'original'
    return {'source_ref': source_ref, 'representation': representation,
            'artifact_ref': source['text_ref' if representation == 'text' else 'artifact_ref'],
            'prior_delivery_refs': []}


def pending_page(last, records):
    """The page commission code makes straight after a fetch that completed (the commission of the hit the model
    picked, on the article that was fetched); None at every other point."""
    if last is None or last['kind'] != 'tool' or last['tool'] != FETCH or last['outcome']['status'] != 'completed':
        return None
    return {'hit': last['arguments']['arguments']['hit'],
            'page': page_of(records, last['outcome']['result']['source_ref'])}


def label_of(records, ref):
    record = records.get(ref)
    return record.get('label') or record.get('name') or ref


def question_context(records, ref):
    """One record giving the assigned question its context, as the Search Goal names it: its record type, its context
    type and its name or label, where it has them."""
    record = records.get(ref)
    entry = {'record_type': record.get('record_type'), 'context_type': record.get('context_type'),
             'name': record.get('name') or record.get('label')}
    return {key: value for key, value in entry.items() if value is not None}


def search_goal(view, parent, records):
    """The immutable Search Goal Jev measures every hit against (nano-graphrag: ``EpisodeGoal.for_grain(search_grain,
    parent=strategy goal, objective=...)`` and ``goal.as_record()``), derived from the commission. The runner already
    built this episode's goal as the child of its commissioner's goal with the commission's objective (``view.goal``);
    its record is carried as it is, with this episode's grain (binding path, unit, result) and what the commission
    requests: the commissioned A108 task (its key and kind), the A108 grading and aggregation components the parent
    wants returned, the records giving the question its context, and the subject of the proposed annotation (its
    predicate, the labels of its subjects and its value)."""
    task = parent['task']
    hypothesis = records.get(parent['proposed_annotation_ref'])
    value = hypothesis['value']
    requested = {'task_key': parent['task_key'], 'task_kind': task['kind'],
                 REQUESTED_GRADING: parent[REQUESTED_GRADING], REQUESTED_AGGREGATION: parent[REQUESTED_AGGREGATION],
                 'question_context': [question_context(records, ref) for ref in parent['question_context_refs']]}
    return {**view.goal.as_record(), 'grain': {'binding_path': BINDING_PATH, 'unit': UNIT, 'result': RESULT},
            'requested_results': {key: item for key, item in requested.items() if item not in (None, [])},
            'subject': {'predicate': hypothesis['predicate'],
                        'subjects': [label_of(records, ref) for ref in hypothesis['subject_refs']],
                        'partner': (label_of(records, value['ref']) if value.get('type') in ('term_ref', 'reference')
                                    else value)}}


def prior_page_outcomes(children, ranks):
    """The compact measured outcome of each page child, in the order commissioned (nano-graphrag
    ``record_page_outcome``): the hit it was handed and its provider rank, how it ended, its units, its credit and the
    counts of its finding."""
    return [{'result_id': outcome['arguments']['hit'], 'provider_rank': ranks.get(outcome['arguments']['hit']),
             'ended_by': outcome['completion']['ended_by'],
             'units_consumed': outcome['completion']['units_consumed'], 'credit': outcome['report']['credit'],
             'grading_sheets': len(outcome['report']['finding']['grading_sheets']),
             'aggregation_cells': len(outcome['report']['finding']['aggregation_cells']),
             'assessments': len(outcome['report']['finding']['assessment_refs']),
             'lead_sources': (len(outcome['report']['leads']['lead_source_refs']) if 'leads' in outcome['report']
                              else 0)}
            for outcome in children]


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    records = view.records
    held = sorted(records.refs())
    custody = source_custody(records, held)
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    run = search_run(parent, view.outcomes)
    hits = search_hits(run, records)
    consumed = consumed_hits(view.outcomes)
    candidates = [hit_candidate(hit) for hit in hits]
    input_list = [item['result_id'] for item in candidates if item['result_id'] not in consumed]
    # Jev's measurement of the hits (nano-graphrag ``SearchPageProposer``): held once by the code-decided
    # ``assess_search_results`` unit; the planner sees it for the unconsumed hits only.
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    page_outcomes = prior_page_outcomes(children, {hit['pmcid']: hit['provider_rank'] for hit in hits})
    child_reports = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                      'hit': outcome['arguments']['hit'], **outcome['report']} for outcome in children]
    tools = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {'version': SEARCH_ASSIGNMENT, 'question_context_refs': parent['question_context_refs'],
                  'search_query_ref': parent['search_query_ref'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'question_context_refs': parent['question_context_refs'],
        'held_source_custody': custody,
        'proposed_annotation_subject_refs': records.get(parent['proposed_annotation_ref'])['subject_refs'],
        'pending_search': None if run is not None else parent['search_query_ref'],
        'input_list': input_list, 'consumed_inputs': consumed, 'hit_fetches': hit_fetches(view.outcomes),
        'pending_page': pending_page(last, records),
        'search_result_candidates': candidates,
        'jev_search_goal': search_goal(view, parent, records),
        'search_assessment_ref': assessment_ref,
        'prior_page_outcomes': page_outcomes,
        'search_planner_context': (None if assessment is None
                                   else search_planner_context(assessment, input_list, page_outcomes)),
        'own_literature_outcomes': outcome_page(tools, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(RUN_SEARCH, ASSESS, FETCH),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_goal_plan': {'objective': view.goal.as_record(),
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task, 'progress_definition': binding,
                                 'planning_question': PLANNING_QUESTION},
        'credit_binding': binding,
        'held_record_refs': held,
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_reports': child_reports,
        'finding': {**merged_findings(own_findings(records), [child['finding'] for child in child_reports]),
                    'assessment_refs': list(dict.fromkeys(
                        ref for child in child_reports for ref in child['finding']['assessment_refs']))},
        'grading_cell_refs': list(dict.fromkeys(
            ref for child in child_reports for ref in child.get(GRADING_NAMESPACE, ()))),
        'aggregation_cell_refs': list(dict.fromkeys(
            ref for child in child_reports for ref in child.get(AGGREGATION_NAMESPACE, ()))),
        'returned_lead_source_refs': [ref for child in child_reports if 'leads' in child
                                      for ref in child['leads']['lead_source_refs']],
    }
    summary['lead_return'] = lead_return(summary, records)
    summary['finding']['observation_refs'] = assessment_basis(view.records, summary['finding']['assessment_refs'])
    return summary
