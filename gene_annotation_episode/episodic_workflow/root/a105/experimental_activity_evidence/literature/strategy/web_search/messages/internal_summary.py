"""Where the investigation stands, as a pure function of the loop's view: the assignment, custody of the assigned
sources, the first page of the episode's own read and acquisition outcomes, the goal plan, the controlled features of
the current grading and aggregation sheets it saved and its child returned (each sheet its own entry), the returns
of the children commissioned (their credit and the counts of their findings), and what the units answer for the
commissioned task.

Carried from the old ``internal_summary.py`` (``decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``, ``literature_goal_plan``
from ``goal.planning_context``). The old reads of ``runtime_actions`` and ``runtime_report_attempts`` are the unit
outcomes of ``view``: a tool unit's outcome, and a child unit's ``report`` (what ``read_from_child`` made of the
admitted result)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    no_applicable_spans, relevant_lead_sources, screening_covered)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    current_aggregation_features, current_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import PLANNING_QUESTION

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


def internal_summary(view):
    parent = view.parent_input
    search, task = parent['search'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The input list (nano-graphrag's input-list paradigm): the search results of the assignment, in the order the
    # search returned them, that no page child has yet been handed. A handed-out result is consumed; the list shrinks
    # by one per page commissioned and the yield estimator ends the episode when it is empty.
    consumed = consumed_results(children)
    input_list = [ref for ref in search['search_result_refs'] if ref not in consumed]
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
    }
