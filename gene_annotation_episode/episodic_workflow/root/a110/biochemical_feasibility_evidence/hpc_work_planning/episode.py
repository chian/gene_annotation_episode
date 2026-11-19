"""The A110 hpc_work_planning binding on the generic runner.

Its decision source, credit and continuation are ``hpc_runtime`` (role ``hpc``): model-selected HPC
planning operations over the commission's own ledger and commissions of its
``hpc_resource_prediction`` sister. It does not commission its submission, progress, results or allocation
slots.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    CHILD_ASSIGNMENT_FORM, RETURN_FORM, EpisodeRuntimeContract)

from .hpc_runtime import PLANNING, HPCRuntime


class HpcWorkPlanningEpisode(HPCRuntime, EpisodeRuntimeContract):
    """Plan the HPC work that the commissioned computation needs and coordinate its allocation."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning'
    grain_name = binding_path.replace('/', '__')
    goal = 'Plan the HPC work that the commissioned computation needs and coordinate its allocation'
    unit = 'One planning, prediction or commission action'
    result = 'The HPC plan and its execution findings'
    child_slots = MappingProxyType({'execution_job_submission': 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission', 'execution_progress_assessment': 'biochemical_feasibility_evidence/hpc_work_planning/execution_progress_assessment', 'execution_result_acquisition': 'biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition', 'hpc_allocation_execution': 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution', 'hpc_resource_prediction': 'biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction'})
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence'
    hpc_role = PLANNING
