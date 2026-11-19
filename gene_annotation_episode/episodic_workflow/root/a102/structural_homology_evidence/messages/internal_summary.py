"""The A102 head's internal summary (carried from ``internal_summary.py``, ``source_references.py`` and the
planning context of ``goal.py`` at ``97308b94c``; the working state the old ``task_state.py`` kept): a pure
function of the view.

What the summary holds: the parent input (the selection, the commissioned task and its credit definition, the
proposed annotation, the evidence and scope records), the credit view (``credit.credit_view`` over the held
records: the credit and its measured components, retained finding counts, inactive dependencies and sheets), the
latest interpretation the head wrote with its ``report`` tool, the records its reasoning commits wrote, the
revisions it prepared with ``process_revise``, the children it commissioned with what they returned (their credit,
finding, process results and the progress observations a monitor delivered), a compact history of every unit and
the controller's yield table. The old initial references (evidence references and the proposed annotation) are the
parent input's custody records. Fields of the old decision state that came from the old runner (call counts, the
last outcome index, the feedback, pending work, report deliveries and the journal views) are not carried.
"""
from __future__ import annotations

import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_structure_cells import (
    experimental_structure_arm)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from .. import credit as credit_file

FORECAST_UNIT = ('unit of the head credit: a distinct retained finding, a resolved feature or one measured '
                 'unit of native structural correspondence, as its credit definition states')


def plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def unique(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    report, committed, revisions, children, results, snapshots, history = None, [], [], [], [], {}, []
    experimental = []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            if unit['tool'] == 'report':
                report = outcome['report']
            elif unit['tool'] == 'reason' and outcome.get('status') in ('completed', 'partial'):
                committed.extend(unit['produced'])
            elif unit['tool'] == 'process_revise' and outcome.get('status') == 'completed':
                revisions.append({'result': outcome['result'], 'revision_origin': outcome['revision_origin']})
            history.append({'tool': unit['tool'], 'status': outcome.get('status', 'completed'),
                            'record_refs': list(unit['produced'])})
        else:
            child = unit['report']
            children.append({'slot': unit['slot'], 'child_credit': child['child_credit'],
                             'child_finding': child['child_finding']})
            results.extend(child['process_results'])
            snapshots.update(child['progress_snapshots'])
            experimental.extend(child['experimental_structure_sheets'])
            history.append({'child': unit['slot'], 'credit': child['child_credit']})
    credit_view = credit_file.credit_view(parent, view.records)     # the comparative native arm
    controller = (yield_table(view.controller_state, forecast_unit=FORECAST_UNIT)
                  if view.controller_state is not None else None)
    return {**parent,
            'credit_view': credit_view,
            'experimental_structure_arm': experimental_structure_arm(experimental),
            'report': report,
            'committed_record_refs': unique(committed),
            'revisions': revisions,
            'children': children,
            'received_process_results': results,
            'progress_snapshots': snapshots,
            'outcome_history': history,
            'last_outcome': plain(view.outcomes[-1]) if view.outcomes else None,
            'controller': controller,
            'visible_record_refs': list(view.records.refs()),
            'reasoning_schema': view.records.reasoning_schema(),
            'goal': {'objective': plain(view.goal.objective)}}
