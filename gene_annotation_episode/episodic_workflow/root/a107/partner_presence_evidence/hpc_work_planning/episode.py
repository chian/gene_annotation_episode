"""A107 binding ``partner_presence_evidence/hpc_work_planning`` on the generic runner.

Its decision source, credit and continuation are ``hpc_runtime`` (role ``hpc``): model-selected
HPC planning operations over the commission's own ledger and commissions of its
``hpc_prediction`` sister. Its launch, monitor, results and allocation slots are declared
but not commissioned by it (``hpc_runtime``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import \
    DescendantBinding

from .hpc_runtime import PLANNING, HPCRuntime


class HPCEpisode(HPCRuntime, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning'
    goal = 'Improve the plan, resource prediction and allocation that bring the assigned computation to completion on HPC'
    unit = 'One planning action or commissioned prediction, allocation, launch, monitor or results child'
    result = 'The HPC plan, allocation outcome and execution handoffs'
    child_slots = {'launch': 'partner_presence_evidence/hpc_work_planning/execution_job_submission', 'monitor': 'partner_presence_evidence/hpc_work_planning/execution_progress_assessment', 'results': 'partner_presence_evidence/hpc_work_planning/execution_result_acquisition', 'hpc_execution': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution', 'hpc_prediction': 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'}
    commissioning_parent = 'partner_presence_evidence'
    hpc_role = PLANNING
