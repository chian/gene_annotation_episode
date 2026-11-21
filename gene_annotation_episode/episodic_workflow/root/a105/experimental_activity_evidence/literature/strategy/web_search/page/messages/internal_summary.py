"""Where the examination stands, as a pure function of the loop's view: the assignment, custody of the page's
source, the commission (the commissioner's objective, a value of this episode's fixed vocabulary, with this episode's
meaning of it), the first page of the episode's own read outcomes, the goal plan, the controlled features of the current
grading and aggregation sheets it saved and its children returned (each sheet its own entry), the returns of the
children commissioned (their credit and the counts of their findings), and what the units answer for the
commissioned task.

Carried from the old ``internal_summary.py`` (``SourceSummary.decision_context``: ``literature_assignment``,
``literature_source_custody``, ``own_literature_outcomes``, ``literature_history_meaning``,
``source_examination_goal`` from ``goal.planning_context``). The old reads of ``runtime_actions`` and
``runtime_report_attempts`` are the unit outcomes of ``view``: a tool unit's outcome, and a child unit's ``report``
(what ``read_from_child`` made of the admitted result). The copies of the owner's grader and reader instructions
and the unwired decision-prompt renderer that were parked here are deleted: the texts are in the library prompt
files and reach the model through ``task.py``. The population display contexts of the old ``SourceSummary`` read the
reader repositories' received-cell ledgers, which are custody now, and are not carried."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    no_applicable_spans, relevant_lead_sources, screening_covered)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    classified_credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    examined_windows)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    current_aggregation_features, current_sheet_features, merged_sheet_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import PLANNING_QUESTION
from .read_from_child import LEAF_SLOTS

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('source_read', 'source_locate', 'source_sequence_references', 'source_experimental_records',
              'source_pdf_text')
CUSTODY_KEYS = ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. Source '
                   'delivery does not establish scientific understanding, absence or resolved science.')


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    records = view.records
    source = records.get(page['source_ref'])
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    spans = no_applicable_spans(view.outcomes, records)
    assignment = {**page, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **parent['requested']}
    # The sheet: the leaf records the chunk children returned (distinct refs, in arrival order), the states the commissioner
    # passed in, and the latest sheet update (each update regroups all the leaf records from those states, so the latest
    # one is the page's whole result).
    leaf_record_refs = list(dict.fromkeys(ref for outcome in children if outcome['slot'] in LEAF_SLOTS
                                          for ref in outcome['report']['record_refs']))
    updates = [outcome['outcome']['sheet_update'] for outcome in view.outcomes
               if outcome['kind'] == 'tool' and outcome['tool'] == 'update_sheet']
    sheet_update = updates[-1] if updates else None
    return {
        'commission': {'objective': parent['objective']['value'], 'objective_meaning': parent['objective']['meaning'],
                       'task': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref']},
        'literature_assignment': assignment, 'page': page,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'requested': parent['requested'],
        'literature_source_custody': [{'source_ref': page['source_ref'],
                                       **{key: source.get(key) for key in CUSTODY_KEYS}}],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'source_examination_goal': {'objective': parent['objective']['value'],
                                    'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                    'commissioned_result': task,
                                    'progress_definition': classified_credit_binding(parent['task_key'], task),
                                    'planning_question': PLANNING_QUESTION},
        'credit_binding': classified_credit_binding(parent['task_key'], task),
        'reasoning_schema': records.reasoning_schema(),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], **outcome['report']['counts']}
                          for outcome in children],
        'assay_sheets': merged_sheet_features(current_sheet_features(records),
                                              [features for outcome in children if outcome['slot'] not in LEAF_SLOTS
                                               for features in outcome['report']['assay_sheets']]),
        'aggregation_sheets': merged_sheet_features(current_aggregation_features(records),
                                                    [features for outcome in children
                                                     if outcome['slot'] not in LEAF_SLOTS
                                                     for features in outcome['report']['aggregation_sheets']]),
        'leaf_record_refs': leaf_record_refs, 'base_state_refs': parent['sheet_state_refs'],
        'sheet_update': sheet_update,
        'sheet_state_refs': sheet_update['sheet_state_refs'] if sheet_update is not None else parent['sheet_state_refs'],
        'no_applicable_spans': spans,
        'examined_windows': examined_windows(view.outcomes),
        'screening_covered': screening_covered(task, view.outcomes, spans),
        'lead_source_refs': (relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records)
                             if task['kind'] == 'verified_source_leads' else []),
    }
