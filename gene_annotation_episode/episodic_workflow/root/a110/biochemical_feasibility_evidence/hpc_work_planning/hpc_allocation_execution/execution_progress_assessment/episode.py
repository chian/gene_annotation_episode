"""The A110 ``biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment`` binding: the A110 progress monitor (``runtime_monitor.A110MonitorBinding``)."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    EpisodeRuntimeContract)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_monitor import (
    A110MonitorBinding)


class ExecutionProgressAssessmentEpisode(A110MonitorBinding, EpisodeRuntimeContract):
    """Know the actual progress of the commissioned execution."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment'
    goal = 'Know the actual progress of the commissioned execution'
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution'
