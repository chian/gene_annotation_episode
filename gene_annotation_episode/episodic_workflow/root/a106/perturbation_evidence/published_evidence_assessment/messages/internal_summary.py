"""Where the literature investigation stands, as a pure function of the loop's view: the assignment, the first page of
the episode's own outcomes, the controlled features of the current A106 sheets the chain below saved and returned
(``literature_a106_findings``), the reports of the strategy investigations it commissioned and the typed answer the
commissioned task asks for (carried from the old ``internal_summary.py``: ``literature_assignment``,
``own_literature_outcomes``, ``literature_history_meaning``; the old reads of ``runtime_actions`` are the unit outcomes
of ``view``, and the old ``completed_action_reports`` are the child reports ``read_from_child`` made).

This episode holds no source of its own and shows no input list: it reads no paper, a paper reaches the chain only
through a search, and the strategy child is offered at every decision (nano-graphrag's run level proposes the next
strategy; no list limits it). Continuation is the yield controller's alone: its accumulation controller
(``ADAPTIVE_CONTROL``, ``items=None``, no cost) stops after 4 flat units in a row, a unit being flat when, once W = 8
units are attempted and m = 4 observed, the upper bound of the expected next marginal (hypervolume) credit is at or
below the adaptive gamma (max(one-result resolution, 0.1 x the median of the recent productive credits)).

The old display contexts of the population route are replaced by the controlled features of the G1 and G2 sheets
(``a106_findings``), which this episode only receives from its child: it saves no sheet itself."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    merged_findings)
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_binding, lead_dispositions

OUTCOME_PAGE_SIZE = 8        # the old configuration outcome_page_size
READ_TOOLS = ('state_query',)
HISTORY_MEANING = ('Own outcome metadata only. Read exact prior outcomes through own_literature_outcomes. A record '
                   'read does not establish scientific understanding, absence or resolved science.')
NO_FINDING = {'intervention_assessments': [], 'a106_subscores': []}


def internal_summary(view):
    parent = view.parent_input
    task = parent['task']
    last = view.outcomes[-1] if view.outcomes else None
    # The leads in the order of the units: each relevant lead source an admitted strategy return names (the old
    # ``lead_dispositions`` merged them by decision order).
    leads, children = [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            leads.extend({'source_ref': ref, 'disposition': 'relevant',
                          'proposed_annotation_ref': parent['proposed_annotation_ref']}
                         for ref in outcome['report'].get('lead_source_refs', ()))
            children.append({'slot': outcome['slot'], 'arguments': outcome['arguments'],
                             'report': outcome['report']})
    assignment = {**parent['literature'], 'literature_task': task,
                  'proposed_annotation_ref': parent['proposed_annotation_ref']}
    summary = {
        'literature_assignment': assignment, 'literature': parent['literature'],
        'task': task, 'task_key': parent['task_key'], 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'own_literature_outcomes': outcome_page(view.outcomes, offset=0, limit=OUTCOME_PAGE_SIZE, tools=READ_TOOLS,
                                                tool_of=lambda outcome: outcome.get('tool')),
        'literature_history_meaning': HISTORY_MEANING,
        'credit_binding': credit_binding(parent['task_key'], task),
        'held_record_refs': sorted(view.records.refs()),
        'last_local_outcome': (None if last is None
                               else {'tool': last['tool'], 'outcome': last['outcome']} if last['kind'] == 'tool'
                               else {'slot': last['slot'], 'report': last['report']}),
        'child_reports': children,
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'a106_findings': merged_findings(NO_FINDING, [child['report']['finding'] for child in children]),
        'source_leads': leads,
    }
    summary['source_lead_dispositions'] = lead_dispositions(summary, view.records)
    return summary
