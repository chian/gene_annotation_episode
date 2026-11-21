"""Where the investigation stands, as a pure function of the loop's view: the assignment, the queries this episode has
written and the ones it has handed out, the returns of the children commissioned (their credit and the controlled
features of their findings), the sheet the latest return holds and the lead sources the children returned.

Nano-graphrag's strategy keeps a queue of searches (``SearchTask``): the queries written and not yet handed to the
search level are the input list; a query handed out is done and never offered again (``consumed_inputs``). This episode
cannot search, fetch or read, so it keeps no hits and no papers."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    relevant_lead_sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    credit_binding)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..goal import PLANNING_QUESTION

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
WRITE_SEARCH = 'write_search'


def written_searches(outcomes):
    """The queries this episode has written, in the order written: the record each completed ``write_search`` unit
    produced. It is a record of this episode (the request); nothing of it is run or read here."""
    return [outcome['outcome']['result']['search_ref'] for outcome in outcomes
            if outcome['kind'] == 'tool' and outcome['tool'] == WRITE_SEARCH
            and outcome['outcome']['status'] == 'completed']


def consumed_results(children):
    """The queries handed to a search child, in the order handed out (nano-graphrag ``processed_chunk_ids`` /
    ``processed_row_ids``: an item handed out is done and no longer offered)."""
    return list(dict.fromkeys(outcome['arguments']['search_query_ref'] for outcome in children))


def examined_article_refs(parent, children):
    """The article sources the pages of the web-search children examined (what this episode returns), and with the ones
    this episode was given, every article examined so far (passed to each later web-search child, so a hit whose work
    is done is not offered again)."""
    own = list(dict.fromkeys(ref for outcome in children for ref in outcome['report']['examined_article_refs']))
    return own, list(dict.fromkeys([*parent['examined_article_refs'], *own]))


def internal_summary(view):
    parent = view.parent_input
    strategy, task = parent['strategy'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    # The input list (nano-graphrag's input-list paradigm): the queries this episode has written that no search child
    # has yet been handed. A query handed out is done and never offered again. The yield estimator passes
    # ``items=None``, so an empty list does not stop the episode: the search child is not offered
    # (``task.valid_slots``) until another query is written, and the episode stops only by its controller's flat-unit
    # rule.
    consumed = consumed_results(children)
    input_list = [ref for ref in written_searches(view.outcomes) if ref not in consumed]
    examined = examined_article_refs(parent, children)
    last = view.outcomes[-1] if view.outcomes else None
    assignment = {**strategy, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    return {
        'literature_assignment': assignment, 'strategy': strategy,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE,
                                                tools=(WRITE_SEARCH,), tool_of=lambda outcome: outcome.get('tool')),
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
        # The articles the pages of this episode's web-search children examined (returned to the commissioner), and,
        # with the ones this episode was given, every article examined so far: passed to each later web-search child.
        'examined_article_refs': examined[0], 'all_examined_article_refs': examined[1],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'child_returns': [{'slot': outcome['slot'], 'objective': outcome['message']['objective'],
                           'credit': outcome['report']['credit'], 'scores': outcome['report']['scores'],
                           'features': outcome['report']['features']}
                          for outcome in children],
        # The web-search child returns the whole subscoring sheet as it stands after it, starting from the states this
        # episode passed to it: the latest return is the current sheet. Before any child returned, the sheet is the one
        # this episode was given (the states its commissioner passed, no scores, no features).
        'sheet_state_refs': children[-1]['report']['sheet_state_refs'] if children else parent['sheet_state_refs'],
        'given_sheet_state_refs': list(parent['sheet_state_refs']),
        'scores': children[-1]['report']['scores'] if children else [],
        'features': children[-1]['report']['features'] if children else [],
        'lead_source_refs': relevant_lead_sources(view.outcomes, parent['proposed_annotation_ref'], records),
    }
