"""The A102 ``structural_homology_evidence/execution_result_acquisition`` binding on the generic runner.

Its decision source and completion continuation are ``execution_result_acquisition.acquisition_source``: the
model acquires the native results of the usable handoffs its sibling ``execution_job_submission`` returned, from
the responses and native result receipts their route children retained on the run's shared Store.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import (
    A102ContractBinding)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_result_acquisition.acquisition_source import (
    ResultAcquisitionBinding)


class ExecutionEpisode(ResultAcquisitionBinding, A102ContractBinding):
    binding_path = 'structural_homology_evidence/execution_result_acquisition'
    commissioning_parent = 'structural_homology_evidence'
