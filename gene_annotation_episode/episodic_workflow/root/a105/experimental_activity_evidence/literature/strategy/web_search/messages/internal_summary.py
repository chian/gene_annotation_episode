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
``SearchPageProposer``): every search result of the assignment is a possible page child with its provider rank (its
position in ``search_result_refs``, the order the search returned it), a title and a description read from its source
record. ``jev_search_goal`` is the immutable Search Goal Jev measures them against (the runner's goal record of this
episode, as nano-graphrag's ``goal.as_record()``, with the results and subject the commission requests);
``search_assessment_ref`` is the assessment the code-decided ``assess_search_results`` unit holds, and
``search_planner_context`` is that assessment over the unconsumed results only with the measured outcomes of the
prior page children (``prior_page_outcomes``)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.search_result_assessment import (
    search_planner_context)
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


def consumed_results(children):
    """The search results (source refs) handed to a page child, in the order handed out (nano-graphrag
    ``web_search_binding``: a candidate source taken up is consumed and no longer offered)."""
    return list(dict.fromkeys(outcome['arguments']['page']['source_ref'] for outcome in children))


ASSESS = 'assess_search_results'
DESCRIPTION_KEYS = ('provider', 'accession', 'uri', 'version', 'retrieved_at')


def search_result_candidates(search_result_refs, records):
    """Each search result as a possible page child (nano-graphrag's provider result): its id (the source ref the planner
    selects), its provider rank (1-based position in the order the search returned it), a title (the source's accession,
    else its uri, else its provider) and a description (the source record's provider metadata, as ``key=value``)."""
    candidates = []
    for rank, ref in enumerate(search_result_refs, start=1):
        source = records.get(ref)
        title = source.get('accession') or source.get('uri') or source.get('provider') or ''
        description = '; '.join(f'{key}={source[key]}' for key in DESCRIPTION_KEYS if source.get(key))
        candidates.append({'result_id': ref, 'provider_rank': rank, 'title': str(title), 'description': description})
    return candidates


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
    return [{'result_id': outcome['arguments']['page']['source_ref'],
             'provider_rank': ranks[outcome['arguments']['page']['source_ref']],
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
    # The input list (nano-graphrag's input-list paradigm): the search results of the assignment, in the order the
    # search returned them, that no page child has yet been handed. A handed-out result is consumed; the list shrinks
    # by one per page commissioned, and once it is empty no page child is offered (``task.valid_slots``). The yield
    # estimator does not pass it as items (``items=None``), so an empty list ends no episode: the accumulation
    # controller of a verified_source_leads commission (``ADAPTIVE_CONTROL``, no cost) stops after 4 flat units in a
    # row (expected next credit's upper bound at or below the adaptive gamma, once W = 8 attempted, m = 4 observed).
    consumed = consumed_results(children)
    input_list = [ref for ref in search['search_result_refs'] if ref not in consumed]
    # Jev's measurement of the search results (nano-graphrag ``SearchPageProposer``): held once by the code-decided
    # ``assess_search_results`` unit; the planner sees it for the unconsumed results only.
    candidates = search_result_candidates(search['search_result_refs'], records)
    assessed = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == ASSESS]
    assessment_ref = assessed[-1]['outcome']['assessment_ref'] if assessed else None
    assessment = None if assessment_ref is None else json.loads(records.get_artifact(assessment_ref))
    page_outcomes = prior_page_outcomes(children, {item['result_id']: item['provider_rank'] for item in candidates})
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
        'input_list': input_list, 'consumed_inputs': consumed,
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
