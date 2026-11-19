"""The A110 hpc_resource_prediction binding on the generic runner.

Its decision source, credit and continuation are ``hpc_work_planning/hpc_runtime`` (role
``hpc_prediction``): model-selected fit, measurement and comparison operations over its owner's HPC
ledger.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    CHILD_ASSIGNMENT_FORM, RETURN_FORM, EpisodeRuntimeContract)

from ..hpc_runtime import PREDICTION, HPCRuntime


class HpcResourcePredictionEpisode(HPCRuntime, EpisodeRuntimeContract):
    """Predict the resources the planned computation needs."""
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction'
    grain_name = binding_path.replace('/', '__')
    goal = 'Predict the resources the planned computation needs'
    unit = 'One resource-prediction action'
    result = 'The resource prediction'
    child_slots = MappingProxyType({})
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning'
    hpc_role = PREDICTION
