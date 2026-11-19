"""The A106 results binding (``perturbation_evidence/published_evidence_assessment/execution_result_acquisition``).

It acquires the native results of the BV-BRC AppService jobs its sibling ``perturbation_evidence/
published_evidence_assessment/execution_job_submission`` launched, from the handoffs that submission returned:
model-selected AppService result operations bound from each returned handoff
(``perturbation_evidence/execution_result_acquisition/acquisition_source.ResultAcquisitionBinding``).
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_result_acquisition.\
    acquisition_source import ResultAcquisitionBinding


class ExecutionEpisode(ResultAcquisitionBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment/execution_result_acquisition'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment'
    roles = ('results',)
    goal = "The analysis work its parent commissioned, carried to retained native records"
    unit = "One result acquisition action"
    result = "The retained acquired result record references"
