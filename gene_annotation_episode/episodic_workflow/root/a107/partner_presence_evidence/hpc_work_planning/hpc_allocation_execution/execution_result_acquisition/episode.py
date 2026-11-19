"""A107 binding ``partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition``.

Its decision source and completion continuation are ``execution_result_acquisition.acquisition_source``: the
model acquires the native results of the usable handoffs its sibling ``execution_job_submission`` returned
(``assignment.handoffs``), from the responses and native result receipts their route children retained on the
run's shared Store.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.execution_result_acquisition.acquisition_source import (
    ResultAcquisitionBinding)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import DescendantBinding


class ExecutionEpisode(ResultAcquisitionBinding, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
    goal = 'Improve acquisition of completed job results into retained records'
    unit = 'One result-acquisition action'
    result = 'Acquired result records with their provenance'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution'
