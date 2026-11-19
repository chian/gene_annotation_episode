"""How the A102 monitor reads its dependency monitor's return (carried from ``from_child_execution_progress_assessment.py``).

The old receiver validated the child's typed form and read every ``episode_progress`` reference in it through the
progress provider before admitting it into this monitor's received progress. Here the child's result is admitted
against its return form by its builder; every delivered progress reference is read through the run's progress
provider in this monitor's scope (a reference it cannot read raises) and the admitted references join this
monitor's received progress through the unit's recorded outcome. The old ``provider._receive_progress`` ledger
and its form/schema/scope signature are old-runner receipts and are not carried.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError


def _unique(values):
    return list(dict.fromkeys(values))


def received_progress(provider, admitted, scope):
    """The progress references the dependency monitor delivered, each read in this monitor's scope."""
    references = admitted['finding'].get('monitoring_progress_refs')
    if not isinstance(references, list) or any(type(reference) is not str for reference in references):
        raise ContractError('dependency_monitor_report_requires_progress_refs')
    for reference in references:
        provider.read_progress(reference, scope)
    return _unique(references)


__all__ = ['received_progress']
