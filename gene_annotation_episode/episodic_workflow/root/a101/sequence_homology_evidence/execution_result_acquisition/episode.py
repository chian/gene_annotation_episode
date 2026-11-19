"""The A101 ``sequence_homology_evidence/execution_result_acquisition`` binding.

Its decision source and continuation are ``acquisition_source``: the model acquires the native results of the
usable handoffs ``execution_job_submission`` returned, from the responses and native result receipts their route
children retained on the run's shared Store; credit counts the requests with acquired results and the completion
controller's target is the number of assigned handoffs.
"""
from __future__ import annotations

from types import MappingProxyType

from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.contract_binding import (
    A101ContractBinding)

from .acquisition_source import ResultAcquisitionBinding


class ExecutionResultAcquisitionEpisode(ResultAcquisitionBinding, A101ContractBinding):
    """Acquire and qualify the native results of the assigned execution."""
    binding_path = 'sequence_homology_evidence/execution_result_acquisition'
    goal = 'Acquire and qualify the native results of the assigned execution'
    unit = 'One result acquisition action'
    result = 'Acquired, graded execution result references'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence'
