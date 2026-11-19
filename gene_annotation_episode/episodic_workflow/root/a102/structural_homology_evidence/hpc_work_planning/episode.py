"""The A102 ``structural_homology_evidence/hpc_work_planning`` binding on the generic runner.

Its decision source, credit and continuation are ``hpc_runtime`` (role ``hpc``): model-selected HPC
planning operations over the commission's own ledger and commissions of its
``hpc_resource_prediction`` sister; its source offers no commission of its launch, monitor, results or
allocation slots. Its assignment carries the commissioning
parent's typed HPC assignment (``role_assignment``: the HPC commission).
"""
from __future__ import annotations

from episode_runtime import Field, RecordForm

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    A102ContractBinding

from .hpc_runtime import PLANNING, HPCRuntime

HPC_ASSIGNMENT = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning A102 parent'),
    'role_assignment': Field('record', "The commissioning parent's typed HPC assignment for this episode"),
})


class HPCEpisode(HPCRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/hpc_work_planning'
    commissioning_parent = 'structural_homology_evidence'
    assignment_form = HPC_ASSIGNMENT
    hpc_role = PLANNING
