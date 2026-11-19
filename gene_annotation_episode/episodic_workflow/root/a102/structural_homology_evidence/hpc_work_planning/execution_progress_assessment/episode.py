"""This A102 progress monitor on the generic runner (``episode_runtime``).

Its decisions, credit and continuation are the A102 monitor runtime
(``runtime_monitor.A102MonitorBinding`` over ``episode_support/jobs/service_calls/structural_homology_evidence/monitor_runtime.py``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_monitor import \
    A102MonitorBinding


class MonitorEpisode(A102MonitorBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/hpc_work_planning/execution_progress_assessment'
    commissioning_parent = 'structural_homology_evidence/hpc_work_planning'
