"""Concrete fixed launch binding and its genuine shared resource custody."""
from copy import deepcopy
from .execution_state import ExecutionSubmissionExecutionState
from .operations import ExecutionSubmissionOperations
from .report_fields import ExecutionSubmissionReportFields
from .report_delivery import ExecutionSubmissionReportDelivery
from .initial_references import ExecutionSubmissionInitialReferences
from .reference_access import ExecutionSubmissionReferenceAccess
from .to_parent import ExecutionSubmissionParentReport
from gene_annotation_episode.episodic_workflow.root.execution_scientific_inputs import ExecutionScientificInputs
from gene_annotation_episode.episodic_workflow.root.execution_blast_custody import ExecutionBlastCustody
from gene_annotation_episode.episodic_workflow.root.execution_result_selection import ExecutionResultSelection
from gene_annotation_episode.episodic_workflow.root.execution_scientific_returns import ExecutionScientificReturns
from gene_annotation_episode.episodic_workflow.root.execution_result_custody import ExecutionResultCustody
from gene_annotation_episode.episodic_workflow.root.execution_received_custody import ExecutionReceivedCustody
from gene_annotation_episode.episodic_workflow.root.execution_closed_credit import ExecutionClosedCredit
from gene_annotation_episode.episodic_workflow.root.execution_resource_information import ExecutionResourceInformation
from gene_annotation_episode.episodic_workflow.root.execution_request_custody import ExecutionRequestCustody

from .task import ExecutionSubmissionTask

from .credit import ExecutionSubmissionCredit
from .child_commissioning import ExecutionSubmissionChildCommissioning
from .from_parent import ExecutionSubmissionParentAssignment
from .action_policy import ExecutionSubmissionActionPolicy
from .goal import ExecutionSubmissionGoal
from .internal_summary import ExecutionSubmissionInternalSummary
from importlib import import_module
ExecutionSubmissionYield = import_module('.yield', __package__).ExecutionSubmissionYield
from .completion import ExecutionSubmissionCompletion

class ExecutionSubmissionBinding(ExecutionSubmissionCredit, ExecutionSubmissionChildCommissioning, ExecutionSubmissionParentReport, ExecutionSubmissionParentAssignment, ExecutionSubmissionExecutionState, ExecutionSubmissionActionPolicy, ExecutionSubmissionGoal, ExecutionSubmissionInternalSummary, ExecutionSubmissionOperations, ExecutionSubmissionReportFields, ExecutionSubmissionReportDelivery, ExecutionSubmissionInitialReferences, ExecutionSubmissionReferenceAccess, ExecutionSubmissionYield, ExecutionSubmissionCompletion, ExecutionScientificInputs, ExecutionBlastCustody, ExecutionResultSelection, ExecutionScientificReturns, ExecutionResultCustody, ExecutionReceivedCustody, ExecutionClosedCredit, ExecutionResourceInformation, ExecutionRequestCustody):
    roles=('launch',)
    entry_roles=()
    replaces_default_instructions=True
    decision_source_type=ExecutionSubmissionTask
    binding_path='legacy_annotation/published_evidence_assessment/execution_job_submission'
    commissioning_parent='legacy_annotation/published_evidence_assessment'

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
        return {'binding_id': 'root_legacy_annotation_published_evidence_assessment_execution_job_submission', 'version': 'root_legacy_annotation_published_evidence_assessment_execution_job_submission_v1', 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}

    def _credit_binding_record(self,context):
        if context.role!='launch' or context.run_id!=self.run_id:
            raise ValueError('fixed_execution_credit_context_required')
        return self.as_record()

    @staticmethod
    def child_message_exchange(role, *, child_binding=None):
        if role == 'launch_api':
            from .api_job_execution.episode import APIExecutionBinding
            if type(child_binding) is APIExecutionBinding:
                from .to_child_api_job_execution import prepare_request
                from .from_child_api_job_execution import admit_return
                return prepare_request, admit_return
        if role == 'launch_local':
            from .local_job_execution.episode import LocalExecutionBinding
            if type(child_binding) is LocalExecutionBinding:
                from .to_child_local_job_execution import prepare_request
                from .from_child_local_job_execution import admit_return
                return prepare_request, admit_return
        if role == 'launch_hpc':
            from .hpc_job_execution.episode import HPCExecutionBinding
            if type(child_binding) is HPCExecutionBinding:
                from .to_child_hpc_job_execution import prepare_request
                from .from_child_hpc_job_execution import admit_return
                return prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(ExecutionSubmissionBinding)["child_message_exchange"]
