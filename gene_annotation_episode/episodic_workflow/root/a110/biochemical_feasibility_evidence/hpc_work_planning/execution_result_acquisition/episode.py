"""The A110 ``biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition`` binding.

Its decision source and completion continuation are ``execution_result_acquisition.acquisition_source``: the
model acquires the native results of the usable handoffs its sibling ``execution_job_submission`` returned
(``assignment.handoffs``), from the native result receipts their route children retained on the run's shared
Store.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    RETURN_FORM, EpisodeRuntimeContract)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.execution_result_acquisition.acquisition_source import (
    ResultAcquisitionBinding)


class ExecutionResultAcquisitionEpisode(ResultAcquisitionBinding, EpisodeRuntimeContract):
    """Acquire the returned results of the commissioned execution as records."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/execution_result_acquisition'
    grain_name = binding_path.replace('/', '__')
    goal = 'Acquire the returned results of the commissioned execution as records'
    unit = 'One result-acquisition action'
    result = 'The acquired result records'
    child_slots = MappingProxyType({})
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning'
