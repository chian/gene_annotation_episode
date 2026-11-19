"""The A103 ``gene_context_evidence/resource_result_acquisition`` binding on the generic runner.

It acquires and qualifies the results of resource work its parent already handed off. The commissioning
parent fixes what acquisition means as a frozen ``practical_assignment_v1`` (``resource_kind`` ``local``):
the acquisition work, the result files it must bring into the workspace and their expected identities
(``path_exists``/``file_sha256``/``requested_job_outputs`` requirements). Each unit is one model-written
``exec_command`` run by its own ``TerminalExecution``; credit is the satisfied acquisition requirement credit
and continuation the completion controller toward the assignment's total requirement credit
(``episode_support/jobs/local_execution/gene_context_evidence/local_job_runtime.py``). The A103 home factory constructs it from
``a103_resource_result_acquisition``.
"""
from __future__ import annotations

from types import MappingProxyType

from ..contract_binding import A103ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.local_job_runtime import A103LocalJobRuntime


class ResourceEpisode(A103LocalJobRuntime, A103ContractBinding):
    binding_path = 'gene_context_evidence/resource_result_acquisition'
    grain_name = 'gene_context_evidence__resource_result_acquisition'
    goal = 'Improve the acquired results of resource work'
    unit = 'One resource result acquisition action'
    result = 'The acquired resource result records'
    child_slots = MappingProxyType({})
    commissioning_parent = 'gene_context_evidence'
