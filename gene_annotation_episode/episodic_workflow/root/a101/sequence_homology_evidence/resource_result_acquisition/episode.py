"""The A101 ``sequence_homology_evidence/resource_result_acquisition`` binding.

It acquires and qualifies the results of resource work its parent already handed off. The commissioning
parent fixes what acquisition means as a frozen ``practical_assignment_v1`` (``resource_kind`` ``local``):
the acquisition work, the result files it must bring into the workspace and their expected identities
(``path_exists``/``file_sha256``/``requested_job_outputs`` requirements). Each unit is one model-written
``exec_command`` (on the local resource, or on the coordinator for transfers) run by its own
``TerminalExecution``; credit is the satisfied acquisition requirement credit and continuation the
completion controller toward the assignment's total requirement credit (``episode_support/jobs/local_execution/sequence_homology_evidence/local_job_runtime.py``).
``a101_home_factory`` constructs it from ``services['a101']['resource_result_acquisition']``.
"""
from __future__ import annotations

from types import MappingProxyType

from ..contract_binding import A101ContractBinding
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.sequence_homology_evidence.local_job_runtime import A101LocalJobRuntime


class ResourceResultAcquisitionEpisode(A101LocalJobRuntime, A101ContractBinding):
    """Acquire and qualify the results of the assigned resource work."""
    binding_path = 'sequence_homology_evidence/resource_result_acquisition'
    goal = 'Acquire and qualify the results of the assigned resource work'
    unit = 'One resource result acquisition action'
    result = 'Acquired resource result references'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence'
