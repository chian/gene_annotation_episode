"""Concrete fixed results binding and its genuine shared resource custody."""
from copy import deepcopy
from .execution_state import ResultAcquisitionExecutionState
from .operations import ResultAcquisitionOperations
from .report_fields import ResultAcquisitionReportFields
from .report_delivery import ResultAcquisitionReportDelivery
from .initial_references import ResultAcquisitionInitialReferences
from .reference_access import ResultAcquisitionReferenceAccess
from .to_parent import ResultAcquisitionParentReport
from gene_annotation_episode.episodic_workflow.root.execution_scientific_inputs import ExecutionScientificInputs
from gene_annotation_episode.episodic_workflow.root.execution_blast_custody import ExecutionBlastCustody
from gene_annotation_episode.episodic_workflow.root.execution_result_selection import ExecutionResultSelection
from gene_annotation_episode.episodic_workflow.root.execution_scientific_returns import ExecutionScientificReturns
from gene_annotation_episode.episodic_workflow.root.execution_result_custody import ExecutionResultCustody
from gene_annotation_episode.episodic_workflow.root.execution_received_custody import ExecutionReceivedCustody
from gene_annotation_episode.episodic_workflow.root.execution_closed_credit import ExecutionClosedCredit
from gene_annotation_episode.episodic_workflow.root.execution_resource_information import ExecutionResourceInformation
from gene_annotation_episode.episodic_workflow.root.execution_request_custody import ExecutionRequestCustody

from .task import ResultAcquisitionTask

from .credit import ResultAcquisitionCredit
from .child_commissioning import ResultAcquisitionChildCommissioning
from .from_parent import ResultAcquisitionParentAssignment
from .action_policy import ResultAcquisitionActionPolicy
from .goal import ResultAcquisitionGoal
from .internal_summary import ResultAcquisitionInternalSummary
from importlib import import_module
ResultAcquisitionYield = import_module('.yield', __package__).ResultAcquisitionYield
from .completion import ResultAcquisitionCompletion

class ResultAcquisitionBinding(ResultAcquisitionCredit, ResultAcquisitionChildCommissioning, ResultAcquisitionParentReport, ResultAcquisitionParentAssignment, ResultAcquisitionExecutionState, ResultAcquisitionActionPolicy, ResultAcquisitionGoal, ResultAcquisitionInternalSummary, ResultAcquisitionOperations, ResultAcquisitionReportFields, ResultAcquisitionReportDelivery, ResultAcquisitionInitialReferences, ResultAcquisitionReferenceAccess, ResultAcquisitionYield, ResultAcquisitionCompletion, ExecutionScientificInputs, ExecutionBlastCustody, ExecutionResultSelection, ExecutionScientificReturns, ExecutionResultCustody, ExecutionReceivedCustody, ExecutionClosedCredit, ExecutionResourceInformation, ExecutionRequestCustody):
    roles=('results',)
    entry_roles=()
    replaces_default_instructions=True
    decision_source_type=ResultAcquisitionTask
    binding_path='published_evidence_assessment/execution_result_acquisition'
    commissioning_parent='published_evidence_assessment'

    def __init__(self,owner):
        from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
        if type(owner) is not ExecutionEpisodes:
            raise TypeError('genuine_execution_resource_owner_required')
        self.owner=owner
        self._practical=owner._practical
        self.acquired_record_unit=owner.acquired_record_unit
        self.api_execution=owner.api_execution
        self.atac_results=owner.atac_results
        self.atac_returns=owner.atac_returns
        self.directory=owner.directory
        self.flux_balance_inputs=owner.flux_balance_inputs
        self.flux_balance_requests=owner.flux_balance_requests
        self.handoff_unit=owner.handoff_unit
        self.initial_information=owner.initial_information
        self.job_progress_provider=owner.job_progress_provider
        self.local_file_sources=owner.local_file_sources
        self.log_roles=owner.log_roles
        self.log_window_bytes=owner.log_window_bytes
        self.lumpy_requests=owner.lumpy_requests
        self.macs2_peak_requests=owner.macs2_peak_requests
        self.molecular_sequence_results=owner.molecular_sequence_results
        self.native_blast_database_results=owner.native_blast_database_results
        self.native_blast_database_returns=owner.native_blast_database_returns
        self.native_blast_masking_results=owner.native_blast_masking_results
        self.native_blast_masking_returns=owner.native_blast_masking_returns
        self.native_blast_results=owner.native_blast_results
        self.native_blast_returns=owner.native_blast_returns
        self.native_blast_standard_database_results=owner.native_blast_standard_database_results
        self.native_blast_standard_database_returns=owner.native_blast_standard_database_returns
        self.native_blast_utility_results=owner.native_blast_utility_results
        self.native_blast_utility_returns=owner.native_blast_utility_returns
        self.native_chromatin_interaction_results=owner.native_chromatin_interaction_results
        self.native_chromatin_interaction_returns=owner.native_chromatin_interaction_returns
        self.native_expression_nmf_results=owner.native_expression_nmf_results
        self.native_expression_nmf_returns=owner.native_expression_nmf_returns
        self.native_fluorescence_results=owner.native_fluorescence_results
        self.native_fluorescence_returns=owner.native_fluorescence_returns
        self.native_flux_balance_results=owner.native_flux_balance_results
        self.native_flux_balance_returns=owner.native_flux_balance_returns
        self.native_genomic_overlap_results=owner.native_genomic_overlap_results
        self.native_genomic_overlap_returns=owner.native_genomic_overlap_returns
        self.native_hmmer_preparation_results=owner.native_hmmer_preparation_results
        self.native_hmmer_preparation_returns=owner.native_hmmer_preparation_returns
        self.native_hmmer_results=owner.native_hmmer_results
        self.native_infernal_preparation_results=owner.native_infernal_preparation_results
        self.native_infernal_preparation_returns=owner.native_infernal_preparation_returns
        self.native_infernal_results=owner.native_infernal_results
        self.native_infernal_returns=owner.native_infernal_returns
        self.native_protein_structure_results=owner.native_protein_structure_results
        self.native_protein_structure_returns=owner.native_protein_structure_returns
        self.native_rna_structure_results=owner.native_rna_structure_results
        self.native_rna_structure_returns=owner.native_rna_structure_returns
        self.private_yield_binding=owner.private_yield_binding
        self.resources=owner.resources
        self.results_yield_profiles=owner.results_yield_profiles
        self.rna_structure_comparison_results=owner.rna_structure_comparison_results
        self.rna_structure_comparison_returns=owner.rna_structure_comparison_returns
        self.run_id=owner.run_id
        self.services=owner.services
        self.store=owner.store
        self.task_yield_profiles=owner.task_yield_profiles
        self.tool_registry=owner.tool_registry

    def as_record(self):
        return {'binding_id': 'root_published_evidence_assessment_execution_result_acquisition', 'version': 'root_published_evidence_assessment_execution_result_acquisition_v1', 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}

    def _credit_binding_record(self,context):
        if context.role!='results' or context.run_id!=self.run_id:
            raise ValueError('fixed_execution_credit_context_required')
        return self.as_record()
