"""Where the investigation stands, as a pure function of the loop's view: the assignment, custody of the assigned
sources, the first page of the episode's own read and acquisition outcomes, the goal plan, the controlled features of
the current grading and aggregation sheets it saved and its child returned (each sheet its own entry), the returns
of the children commissioned (their credit and the counts of their findings), and what the units answer for the
commissioned task.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``, ``literature_goal_plan``
from ``goal.planning_context``). The old reads of ``runtime_actions`` and ``runtime_report_attempts`` are the unit
outcomes of ``view``: a tool unit's outcome, and a child unit's ``report`` (what ``read_from_child`` made of the
admitted result).

The search step's Jev measurement (nano-graphrag ``web_search_binding``: ``assess_page_candidate`` and
``SearchPageProposer``): a search result is ONE HIT of a result list the assignment names (``search_result_refs`` are
retained Europe PMC search responses): its PMCID, provider rank (its position among the distinct publications of the
lists, in the order they were returned), title and a description (journal, year and the abstract the provider returned).
Two hits of the same publication are one result, and an article a page has examined (``examined_article_refs`` of the
assignment: the articles the pages of earlier runs examined and returned, plus this episode's own pages) is not a result
any more. An article that is merely held (a model fetched it with a read tool) stays a result: its work is not done.
``jev_search_goal`` is the immutable Search Goal Jev measures them against (the runner's goal record of this
episode, as nano-graphrag's ``goal.as_record()``, with the results and subject the commission requests);
``search_assessment_ref`` is the assessment the code-decided ``assess_search_results`` unit holds, and
``search_planner_context`` is that assessment over the unconsumed results only with the measured outcomes of the
prior page children (``prior_page_outcomes``).

The model picks an unconsumed hit; code fetches its full text (``fetch_search_hit``, the operation of
``public.literature.read``; an article already held is opened without a new fetch) and, when the fetch completed,
commissions the page on the article (``pending_page``). A hit is consumed by its fetch; a hit whose fetch failed is reported in ``hit_fetches`` with the
provider status and is never opened.

A task naming specific sources (``named_source_refs``: the ``source_answer`` kinds) has no hits to choose from: the page
of this commission can examine only the source the task names (the page refuses any other), so that source alone is the
page candidate, and only when the task names exactly one."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    article_sources, hit_candidate, ranked_hits, search_planner_context, source_kind)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    no_applicable_spans, relevant_lead_sources, screening_covered)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    current_aggregation_features, current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import BINDING_PATH, PLANNING_QUESTION, RESULT, UNIT

CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_experimental_records',
              'source_pdf_text')
ACQUISITION_TOOLS = ('public_literature_search', 'public_literature_read', 'public_literature_sequence_identity',
                     'public_ncbi_search', 'public_pmc_versions', 'public_pmc_files', 'public_pmc_asset',
                     'public_sabiork_search', 'public_sabiork_read', 'public_brenda_search', 'public_brenda_read',
                     'public_bioassay_search', 'public_bioassay_read', 'public_chembl_search', 'public_chembl_read',
                     'public_mavedb_search', 'public_mavedb_read', 'public_brenda_graph_search')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')


ASSESS = 'assess_search_results'
FETCH = 'fetch_search_hit'


def named_page_sources(parent):
    """The sources a page of this commission can examine when the task names specific sources: the page refuses a
    source other than the one it is assigned, and a task that names several distinct sources assigns none of them."""
    named = parent['named_source_refs']
    return named if len(named) == 1 else []


def consumed_results(outcomes, named):
    """The search results handed out, in the order handed out (nano-graphrag ``web_search_binding``: a result taken up
    is consumed and no longer offered): the hits this episode fetched, whether the fetch completed or failed; under a
    task that names its sources, the sources handed to a page."""
    if named:
        return list(dict.fromkeys(outcome['arguments']['page']['source_ref'] for outcome in outcomes
                                  if outcome['kind'] == 'child'))
    return list(dict.fromkeys(outcome['arguments']['arguments']['hit'] for outcome in outcomes
                              if outcome['kind'] == 'tool' and outcome['tool'] == FETCH))


def search_hits(search_result_refs, records):
    """The distinct hits of the result lists the assignment names, each with its provider rank (``ranked_hits``). A
    result list that is not a retained search response is a wrong commission and fails."""
    contents = []
    for ref in search_result_refs:
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
    """The page commission code makes straight after a fetch that completed (the commission the model chose when it
    picked the hit: its objective, on the article that was fetched); None at every other point."""
    if last is None or last['kind'] != 'tool' or last['tool'] != FETCH or last['outcome']['status'] != 'completed':
        return None
    chosen = last['arguments']['arguments']
    return {'hit': chosen['hit'], 'objective': chosen['objective'],
            'page': page_of(records, last['outcome']['result']['source_ref'])}


def label_of(records, ref):
    return records.get(ref).get('label') or ref


def search_goal(view, task, task_key, proposed, records):
    """The immutable Search Goal Jev measures every result against (nano-graphrag: ``EpisodeGoal.for_grain(search_grain,
    parent=strategy goal, objective=...)`` and ``goal.as_record()``). The runner already built this episode's goal as
    the child of its commissioner's goal with the commission's objective (``view.goal``); its record is carried as it is
    (goal id, parent goal id, objective, result contract, root task context), with this episode's grain (binding path,
    unit, result) and what the commission requests: the commissioned task's results (for experiments their labels and
    assay classes) and the subject of the proposed annotation (its predicate and the labels of its records)."""
    hypothesis = records.get(proposed)
    value = hypothesis['value']
    requested = {'task_key': task_key, 'task_kind': task['kind'], 'answer_kind': task.get('answer_kind'),
                 'commissioned_experiments': [{'label': records.get(item['experiment_ref']).get('label'),
                                               'assay_type': item['assay_type']} for item in task.get('experiments', ())],
                 'metrics': task.get('metrics'), 'components': task.get('components')}
    return {**view.goal.as_record(), 'grain': {'binding_path': BINDING_PATH, 'unit': UNIT, 'result': RESULT},
            'requested_results': {key: item for key, item in requested.items() if item not in (None, [])},
            'subject': {'predicate': hypothesis['predicate'],
                        'subjects': [label_of(records, ref) for ref in hypothesis['subject_refs']],
                        'partner': (label_of(records, value['ref']) if value.get('type') in ('term_ref', 'reference')
                                    else value)}}


def prior_page_outcomes(children, ranks):
    """The compact measured outcome of each page child, in the order commissioned (nano-graphrag
    ``record_page_outcome``): the result it was handed and its provider rank, how it ended, its units, its credit and
    the counts of its finding."""
    return [{'result_id': outcome['arguments'].get('hit', outcome['arguments']['page']['source_ref']),
             'provider_rank': ranks.get(outcome['arguments'].get('hit')),
             'objective': outcome['arguments']['objective'], 'ended_by': outcome['completion']['ended_by'],
             'units_consumed': outcome['completion']['units_consumed'], 'credit': outcome['report']['credit'],
             'distinct_findings': len(outcome['report']['features']), 'scores': len(outcome['report']['scores']),
             'lead_sources': len(outcome['report']['lead_source_refs'])}
            for outcome in children]


def internal_summary(view):
    parent = view.parent_input
    search, task = parent['search'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The input list (nano-graphrag's input-list paradigm): the hits of the result lists of the assignment, in the order
    # the search returned them, that this episode has not fetched and whose article no page has examined (a page of an
    # earlier run, named by ``examined_article_refs`` of the assignment, or a page of this episode). An item leaves the
    # list when its work is done, not when it is held: an article a model fetched by hand stays a hit until a page has
    # examined it. A fetched hit is consumed; the list shrinks by one per hit fetched, and once it is empty no hit is
    # offered (``task.offered_actions``).
    # The yield estimator does not pass it as items (``items=None``), so an empty list ends no episode: the
    # accumulation controller of a verified_source_leads commission (``ADAPTIVE_CONTROL``, no cost) stops after 4
    # flat units in a row (expected next credit's upper bound at or below the adaptive gamma, once W = 8 attempted,
    # m = 4 observed). Under a task that names its sources the list is the one named source not yet handed to a page.
    named = bool(parent['named_source_refs'])
    consumed = consumed_results(view.outcomes, named)
    hits = [] if named else search_hits(search['search_result_refs'], records)
    examined = set(parent['examined_article_refs']) | {outcome['arguments']['page']['source_ref']
                                                      for outcome in children}
    held = {} if named else article_sources(records)
    candidates = [hit_candidate(hit) for hit in hits if not examined.intersection(held.get(hit['pmcid'], ()))]
    input_list = ([ref for ref in named_page_sources(parent) if ref not in consumed] if named
                  else [item['result_id'] for item in candidates if item['result_id'] not in consumed])
    # Jev's measurement of the search results (nano-graphrag ``SearchPageProposer``): held once by the code-decided
    # ``assess_search_results`` unit; the planner sees it for the unconsumed results only.
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    page_outcomes = prior_page_outcomes(children, {hit['pmcid']: hit['provider_rank'] for hit in hits})
    last = view.outcomes[-1] if view.outcomes else None
    spans = no_applicable_spans(view.outcomes, records)
    assignment = {**search, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **parent['requested']}
    return {
        'literature_assignment': assignment, 'search': search,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'requested': parent['requested'],
        'literature_source_custody': [],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(*ACQUISITION_TOOLS, *READ_TOOLS),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_goal_plan': {'objective': view.goal.as_record()['objective'],
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task,
                                 'progress_definition': credit_binding(parent['task_key'], task),
                                 'planning_question': PLANNING_QUESTION},
        'credit_binding': credit_binding(parent['task_key'], task),
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'input_list': input_list, 'consumed_inputs': consumed, 'named_source_refs': parent['named_source_refs'],
        'hit_fetches': hit_fetches(view.outcomes), 'pending_page': pending_page(last, records),
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
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], 'scores': outcome['report']['scores'],
                           'features': outcome['report']['features']}
                          for outcome in children],
        # The page child returns the whole subscoring sheet as it stands after it, starting from the states this episode
        # passed to it: the latest page's states, scores and features are the current sheet. Before any page returned,
        # the sheet is the one this episode was given (the states its commissioner passed, no scores, no features).
        'sheet_state_refs': children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs'],
        'base_state_refs': parent['sheet_state_refs'],
        'scores': children[-1]['report']['scores'] if children else [],
        'features': children[-1]['report']['features'] if children else [],
        'assay_sheets': current_sheet_features(records),
        'aggregation_sheets': current_aggregation_features(records),
        'no_applicable_spans': spans,
        'screening_covered': screening_covered(task, view.outcomes, spans),
        'lead_source_refs': (relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records)
                             if task['kind'] == 'verified_source_leads' else []),
        # The lead sources this episode's own reason units validated (the page children's leads are not among them: a
        # page child's lead is credited through its credit, which ``credit.py`` adds).
        'own_lead_source_refs': (relevant_lead_sources([outcome for outcome in view.outcomes
                                                        if outcome['kind'] == 'tool'],
                                                       parent['proposed_annotation_ref'], records)
                                 if task['kind'] == 'verified_source_leads' else []),
    }
