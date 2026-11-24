"""Where the published evidence assessment stands, as a pure function of the loop's view: the literature assignment,
the records it holds, the first page of its own reads of held records, what the child returned, the investigation
findings of the child's assessments, the contextual sheets saved below, and the typed answer the commissioned task asks
for.

Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``), ``decision_inputs.py`` and
``decision_presentation.py`` of ``literature``: ``literature_assignment``, ``own_literature_outcomes``,
``literature_history_meaning``, ``literature_goal_plan`` (the old ``planning_context``) and the yield table. This
episode searches for nothing, fetches nothing, reads no paper and commits no reasoning, so the source custody, the
input list of sources, the received-fact display, the population contexts and the visual evidence of the old context
are gone. ``proposed_annotation_subject_refs`` lists the subjects of the proposed annotation, which ``msg_to_child``
names when it commissions the child (decision T5).

The child's return (``read_from_child``) is controlled data only (credit, the features of its sheets with their
references, the lead count and lead sources, the requested cell rows by reference); the records it returned reach this
episode's code, never its model."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis, merged_findings, own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_return
from ..goal import GOAL
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
LITERATURE_ASSIGNMENT = 'literature_assignment'
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes.')
GRADING_NAMESPACE = 'literature_a108_grading_cells'
AGGREGATION_NAMESPACE = 'literature_a108_aggregation_cells'


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    records = view.records
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    child_reports = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'], **outcome['report']}
                     for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {'version': LITERATURE_ASSIGNMENT, 'question_context_refs': parent['question_context_refs'],
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'proposed_annotation_subject_refs': records.get(parent['proposed_annotation_ref'])['subject_refs'],
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=('state_query',),
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'literature_goal_plan': {'objective': view.goal.as_record(),
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task, 'progress_definition': binding,
                                 'planning_question': GOAL},
        'credit_binding': binding,
        'held_record_refs': sorted(records.refs()),
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
