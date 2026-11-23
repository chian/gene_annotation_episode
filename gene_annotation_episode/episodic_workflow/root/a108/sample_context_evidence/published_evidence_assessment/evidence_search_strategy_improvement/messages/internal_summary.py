"""Where the strategy stands, as a pure function of the loop's view: the strategy assignment, the searches this episode
wrote and handed out, what the search child returned for each, the investigation findings of the sheets saved below and
the typed answer the commissioned task asks for.

Carried from the old ``internal_summary.py`` (``LiteratureSummary.decision_context``), ``decision_inputs.py`` and
``decision_presentation.py`` of ``literature_strategy``: ``literature_assignment``, ``own_literature_outcomes``,
``literature_history_meaning``, ``literature_goal_plan`` (the old ``planning_context``) and the yield table. The
strategy cannot search, fetch or read a paper and commits no reasoning, so the source custody, the received-fact
display, the population contexts and the visual evidence of the old context are gone.

The input list (nano-graphrag ``StrategySearches``: the queued search tasks; a task popped is done): the searches this
episode wrote with ``write_search`` and has not handed to a child. A search handed out is consumed and never offered
again. The yield estimator does not pass the list as items (``items=None``): an empty list ends no episode, it only
means no child is offered until the model writes another search.

A child's return is controlled data only (credit, the features of its sheets with their references, the lead count and
lead sources, the requested cell rows by reference)."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    assessment_basis, merged_findings, own_findings)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_return
from ..goal import GOAL
from .read_from_parent import REQUESTED_AGGREGATION, REQUESTED_GRADING

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
STRATEGY_ASSIGNMENT = 'strategy_assignment'
WRITE_SEARCH = 'write_search'
HISTORY_MEANING = ('Own outcome metadata only. The searches you wrote are shown as written_searches.')
GRADING_NAMESPACE = 'literature_a108_grading_cells'
AGGREGATION_NAMESPACE = 'literature_a108_aggregation_cells'


def written_searches(outcomes):
    """The references of the searches this episode wrote, in the order written (each completed ``write_search``
    unit produced one record)."""
    return [outcome['outcome']['result']['search_ref'] for outcome in outcomes
            if outcome['tool'] == WRITE_SEARCH and outcome['outcome']['status'] == 'completed']


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    records = view.records
    outcomes = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool']
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    written = written_searches(outcomes)
    handed = list(dict.fromkeys(outcome['arguments']['search_query_ref'] for outcome in children))
    child_reports = [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                      'search_query_ref': outcome['arguments']['search_query_ref'], **outcome['report']}
                     for outcome in children]
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {'version': STRATEGY_ASSIGNMENT, 'question_context_refs': parent['question_context_refs'],
                  'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                  **{name: parent[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if parent[name]}}
    binding = credit_binding(parent['task_key'], task)
    summary = {
        'literature_assignment': assignment,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'proposed_annotation_subject_refs': records.get(parent['proposed_annotation_ref'])['subject_refs'],
        'input_list': [ref for ref in written if ref not in handed], 'consumed_inputs': handed,
        'written_searches': [{'search_ref': ref,
                              'request': json.loads(records.get_artifact(records.get(ref)['request_ref']))}
                             for ref in written],
        'own_literature_outcomes': outcome_page(outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(WRITE_SEARCH,), tool_of=lambda outcome: outcome.get('tool')),
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
