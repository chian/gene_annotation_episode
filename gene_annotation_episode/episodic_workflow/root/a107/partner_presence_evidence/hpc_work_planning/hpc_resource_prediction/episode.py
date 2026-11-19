"""A107 binding ``partner_presence_evidence/hpc_work_planning/hpc_resource_prediction`` on the generic runner.

Its decision source, credit and continuation are ``hpc_work_planning/hpc_runtime`` (role
``hpc_prediction``): model-selected fit, measurement and comparison operations over its
owner's HPC ledger.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.runtime_binding import \
    DescendantBinding

from ..hpc_runtime import PREDICTION, HPCRuntime


class HPCEpisode(HPCRuntime, DescendantBinding):
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
    goal = 'Improve the resource prediction for the planned HPC work'
    unit = 'One prediction action'
    result = 'The resource prediction with its basis'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/hpc_work_planning'
    hpc_role = PREDICTION
