"""How the A107 monitor reads its dependency monitor's return (carried from ``from_child_execution_progress_assessment.py``).

The old receiver validated the child's typed form and read every ``episode_progress`` reference in it through the
progress provider before admitting it into this monitor's received progress. Here the child's result is admitted
against its return form by the system; each delivered progress reference must come with its snapshot (the child
returns them as ``monitoring_progress_snapshots``), because ``credit`` and the summary have no provider to read it
from. The admitted references join this monitor's received progress through the unit's report. The old
``provider._receive_progress`` ledger and its form/schema/scope signature are old-runner receipts, not carried.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError


def read_from_child(slot, result, summary, records):
    references = list(dict.fromkeys(result['monitoring_progress_refs']))
    snapshots = result['monitoring_progress_snapshots']
    for reference in references:
        if reference not in snapshots:
            raise ContractError('dependency_monitor_report_requires_progress_refs')
    return {'slot': slot, 'progress_refs': references,
            'progress_snapshots': {reference: snapshots[reference] for reference in references},
            'child_credit': result['credit'], 'child_finding': result['finding']}
