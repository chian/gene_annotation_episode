"""The A103 ``gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`` binding on the generic runner.

Its decision source and completion continuation are ``execution_result_acquisition.acquisition_source``: the
model acquires the native results of the usable handoffs its sibling ``execution_job_submission`` returned
(``role_assignment.handoffs``), from the responses and native result receipts their route children retained on
the run's shared Store.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.contract_binding import (
    A103ContractBinding)
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.execution_result_acquisition.acquisition_source import (
    ResultAcquisitionBinding)


class ExecutionEpisode(ResultAcquisitionBinding, A103ContractBinding):
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
    grain_name = 'gene_context_evidence__hpc_work_planning__hpc_allocation_execution__execution_result_acquisition'
    goal = 'Improve the acquired results of completed execution'
    unit = 'One result acquisition action'
    result = 'The acquired result records'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
