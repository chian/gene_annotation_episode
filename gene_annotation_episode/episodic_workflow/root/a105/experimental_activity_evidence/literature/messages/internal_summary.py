"""Where the investigation stands, as a pure function of the loop's view: the assignment, the first page of the
episode's own record readings, the goal plan, the returns of the children commissioned (their credit and the controlled
features of their findings) and the sheet the latest return holds.

The strategy child is offered whenever the episode runs: it is handed this episode's objective only and writes its own
searches (nano-graphrag's run hands a strategy its objective), so this episode keeps no list of searches and no
papers."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    relevant_lead_sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import GOAL as PLANNING_QUESTION

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('state_query',)


def internal_summary(view):
    parent = view.parent_input
    literature, task = parent['literature'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {**literature, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    return {
        'literature_assignment': assignment, 'literature': literature,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=READ_TOOLS, tool_of=lambda outcome: outcome.get('tool')),
        'literature_goal_plan': {'objective': view.goal.as_record()['objective'],
                                 'proposed_annotation_ref': parent['proposed_annotation_ref'],
                                 'commissioned_result': task,
                                 'progress_definition': credit_binding(parent['task_key'], task),
                                 'planning_question': PLANNING_QUESTION},
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None else {'tool': last['tool'], 'outcome': last['outcome']}
                               if last['kind'] == 'tool' else {'slot': last['slot'], 'report': last['report']}),
        # The articles the pages of this episode's strategy children examined, passed to each later strategy child.
        'examined_article_refs': list(dict.fromkeys(ref for outcome in children
                                                    for ref in outcome['report']['examined_article_refs'])),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], 'scores': outcome['report']['scores'],
                           'features': outcome['report']['features']}
                          for outcome in children],
        # The strategy child returns the whole subscoring sheet as it stands after it, starting from the states this
        # episode passed to it: the latest return is the current sheet. Before any child returned, the sheet is the one
        # this episode was given (the states its commissioner passed, no scores, no features).
        'sheet_state_refs': children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs'],
        'given_sheet_state_refs': list(parent['sheet_state_refs']),
        'scores': children[-1]['report']['scores'] if children else [],
        'features': children[-1]['report']['features'] if children else [],
        'lead_source_refs': relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records),
    }
