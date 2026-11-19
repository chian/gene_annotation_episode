"""A107 binding ``partner_presence_evidence/execution_progress_assessment``: the A107 progress monitor (``runtime_monitor.A107MonitorBinding``)."""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import (
    DescendantBinding)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_monitor import (
    A107MonitorBinding)


class MonitorEpisode(A107MonitorBinding, DescendantBinding):
    binding_path = 'partner_presence_evidence/execution_progress_assessment'
    goal = "Improve the parent's knowledge of the progress of its pending execution work"
    unit = 'One progress observation or nested monitor child'
    result = 'Observed progress records'
    child_slots = MappingProxyType({'monitor': 'partner_presence_evidence/execution_progress_assessment'})
    commissioning_parent = 'partner_presence_evidence'
