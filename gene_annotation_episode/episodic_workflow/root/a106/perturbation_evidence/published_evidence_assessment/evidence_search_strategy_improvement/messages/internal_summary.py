"""Where the strategy investigation stands, as a pure function of the loop's view: the assignment, the queries this
episode has written and the ones it has handed out, the first page of its own outcomes, the reports of the search
children it commissioned (their credit and the controlled features of their findings), the lead sources they returned
and the typed answer the commissioned task asks for (carried from the old ``internal_summary.py``:
``literature_assignment``, ``own_literature_outcomes``, ``literature_history_meaning``; the old reads of
``runtime_actions`` are the unit outcomes of ``view``, and the old ``completed_action_reports`` are the child reports
``read_from_child`` made).

Nano-graphrag's strategy keeps a queue of searches (``SearchTask``): the queries written and not yet handed to the
search level are the input list; a query handed out is done and never offered again (``consumed_inputs``). This episode
cannot search, fetch or read, so it keeps no hit and no paper: a query is a record of this episode (the ``source``
record ``write_search`` made, whose ``request_ref`` artifact holds the request) and is what the search child receives,
by reference. The yield estimator does not count the list (``items=None``): an empty list does not stop the episode,
the search child is not offered until another query is written, and the controller's flat-unit rule alone stops it.

The old display contexts of the population route are replaced by the controlled features of the G1 and G2 sheets
(``a106_findings``), which this episode only receives from its children: it saves no sheet itself."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
WRITE_SEARCH = 'write_search'
READ_TOOLS = ('state_query', WRITE_SEARCH)
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. A record '
                   'read does not establish scientific understanding, absence or resolved science.')
NO_FINDING = {'intervention_assessments': [], 'a106_subscores': []}


def written_searches(outcomes):
    """The queries this episode has written, in the order written: the record each completed ``write_search`` unit
    produced. It is a record of this episode (the request); nothing of it is run or read here."""
    return [outcome['outcome']['result']['search_ref'] for outcome in outcomes
            if outcome['kind'] == 'tool' and outcome['tool'] == WRITE_SEARCH
            and outcome['outcome']['status'] == 'completed']


def consumed_searches(children):
    """The queries handed to a search child, in the order handed out (nano-graphrag ``processed_chunk_ids`` /
    ``processed_row_ids``: an item handed out is done and no longer offered)."""
    return list(dict.fromkeys(outcome['arguments']['search_query_ref'] for outcome in children))


def request_of(records, reference):
    """The request one of this episode's query records holds, read through custody."""
    return json.loads(records.get_artifact(records.get(reference)['request_ref']))


def internal_summary(view):
    parent = view.parent_input
    strategy, task = parent['strategy'], parent['task']
    records = view.records
    children = [outcome for outcome in view.outcomes if outcome['kind'] == 'child']
    written = written_searches(view.outcomes)
    consumed = consumed_searches(children)
    input_list = [ref for ref in written if ref not in consumed]
    last = view.outcomes[-1] if view.outcomes else None
    # The leads in the order of the units: each relevant lead source an admitted search return names (the old
    # ``lead_dispositions`` merged them by decision order).
    leads = [{'source_ref': ref, 'disposition': 'relevant', 'proposed_annotation_ref': parent['proposed_annotation_ref']}
             for outcome in children for ref in outcome['report'].get('lead_source_refs', ())]
    returned = {outcome['arguments']['search_query_ref']: outcome['report'] for outcome in children}
    assignment = {**strategy, 'literature_task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment, 'strategy': strategy,
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(records.refs()),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'input_list': input_list, 'consumed_inputs': consumed,
        # Each query this episode wrote, with the request it holds and, once handed out, what the search returned.
        'written_searches': [{'search_ref': ref, 'request': request_of(records, ref),
                              'handed_out': ref in consumed,
                              'report': (None if ref not in returned else
                                         {'credit': returned[ref]['credit'], 'finding': returned[ref]['finding'],
                                          'lead_source_refs': returned[ref].get('lead_source_refs', [])})}
                             for ref in written],
        'child_reports': [{'slot': outcome['slot'], 'arguments': outcome['arguments'], 'report': outcome['report']}
                          for outcome in children],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': merged_findings(NO_FINDING, [outcome['report']['finding'] for outcome in children]),
        'source_leads': leads,
    }
    summary['source_lead_dispositions'] = lead_dispositions(summary, records)
    return summary
