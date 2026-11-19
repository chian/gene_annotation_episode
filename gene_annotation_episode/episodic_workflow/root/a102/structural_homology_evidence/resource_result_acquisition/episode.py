"""The A102 ``structural_homology_evidence/resource_result_acquisition`` binding on the generic runner.

It acquires and qualifies the results of resource work its parent already handed off. The commissioning
parent fixes what acquisition means as a frozen ``practical_assignment_v1`` (``resource_kind`` ``local``):
the acquisition work, the result files it must bring into the workspace and their expected identities
(``path_exists``/``file_sha256``/``requested_job_outputs`` requirements). Each unit is one model-written
``exec_command`` run by its own ``TerminalExecution``; credit is the satisfied acquisition requirement credit
and continuation the completion controller toward the assignment's total requirement credit
(``episode_support/jobs/local_execution/structural_homology_evidence/local_job_runtime.py``). ``a102_home_factory`` constructs it from
``services['a102']['resource_result_acquisition']``.
"""
from __future__ import annotations

from ..contract_binding import A102ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.local_job_runtime import A102LocalJobRuntime


class ResourceEpisode(A102LocalJobRuntime, A102ContractBinding):
    binding_path = 'structural_homology_evidence/resource_result_acquisition'
    commissioning_parent = 'structural_homology_evidence'
