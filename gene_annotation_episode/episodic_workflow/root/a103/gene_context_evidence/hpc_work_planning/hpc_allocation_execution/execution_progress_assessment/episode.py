"""The A103 progress monitor commissioned by HPC allocation execution.

Binds the A103 monitor runtime (``episode_support/jobs/service_calls/gene_context_evidence/monitor_runtime.py``): its
progress tools, decision, information credit and yield continuation.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.gene_context_evidence.monitor_runtime import A103MonitorRuntime

from .contracts import _ASSIGNMENT


class MonitorEpisode(A103MonitorRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment'
    grain_name = 'gene_context_evidence__hpc_work_planning__hpc_allocation_execution__execution_progress_assessment'
    goal = 'Improve knowledge of the progress of the parent running execution'
    unit = 'One progress observation'
    result = 'The observed execution progress'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
    roles = ('monitor',)
    entry_roles = ('monitor',)
    monitor_assignment_schema = _ASSIGNMENT
