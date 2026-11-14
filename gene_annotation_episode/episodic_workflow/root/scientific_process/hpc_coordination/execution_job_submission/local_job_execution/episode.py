"""Concrete fixed launch_local binding and its genuine shared resource custody."""
from copy import deepcopy
from .execution_state import LocalExecutionExecutionState
from .operations import LocalExecutionOperations
from .report_fields import LocalExecutionReportFields
from .report_delivery import LocalExecutionReportDelivery
from .initial_references import LocalExecutionInitialReferences
from .reference_access import LocalExecutionReferenceAccess
from .to_parent import LocalExecutionParentReport
from gene_annotation_episode.episodic_workflow.root.execution_scientific_inputs import ExecutionScientificInputs
from gene_annotation_episode.episodic_workflow.root.execution_blast_custody import ExecutionBlastCustody
from gene_annotation_episode.episodic_workflow.root.execution_result_selection import ExecutionResultSelection
from gene_annotation_episode.episodic_workflow.root.execution_scientific_returns import ExecutionScientificReturns
from gene_annotation_episode.episodic_workflow.root.execution_result_custody import ExecutionResultCustody
from gene_annotation_episode.episodic_workflow.root.execution_received_custody import ExecutionReceivedCustody
from gene_annotation_episode.episodic_workflow.root.execution_closed_credit import ExecutionClosedCredit
from gene_annotation_episode.episodic_workflow.root.execution_resource_information import ExecutionResourceInformation
from gene_annotation_episode.episodic_workflow.root.execution_request_custody import ExecutionRequestCustody

from .task import LocalExecutionTask

from .credit import LocalExecutionCredit
from .child_commissioning import LocalExecutionChildCommissioning
from .from_parent import LocalExecutionParentAssignment
from .action_policy import LocalExecutionActionPolicy
from .goal import LocalExecutionGoal
from .internal_summary import LocalExecutionInternalSummary
from importlib import import_module
from .yield_estimator import LocalExecutionYield
from .completion import LocalExecutionCompletion

class LocalExecutionBinding(LocalExecutionCredit, LocalExecutionChildCommissioning, LocalExecutionParentReport, LocalExecutionParentAssignment, LocalExecutionExecutionState, LocalExecutionActionPolicy, LocalExecutionGoal, LocalExecutionInternalSummary, LocalExecutionOperations, LocalExecutionReportFields, LocalExecutionReportDelivery, LocalExecutionInitialReferences, LocalExecutionReferenceAccess, LocalExecutionYield, LocalExecutionCompletion, ExecutionScientificInputs, ExecutionBlastCustody, ExecutionResultSelection, ExecutionScientificReturns, ExecutionResultCustody, ExecutionReceivedCustody, ExecutionClosedCredit, ExecutionResourceInformation, ExecutionRequestCustody):
    roles=('launch_local',)
    entry_roles=roles if 'launch_local' in ('launch','results') else ()
    replaces_default_instructions=True
    decision_source_type=LocalExecutionTask
    binding_path='scientific_process/hpc_coordination/execution_job_submission/local_job_execution'
    commissioning_parent='scientific_process/hpc_coordination/execution_job_submission'

    def __init__(self,owner):
        from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
        if type(owner) is not ExecutionEpisodes:
            raise TypeError('genuine_execution_resource_owner_required')
        self.owner=owner
        self._practical=owner._practical
        # The real eager custody already validated and initialized these ports.
        # Keep its mutable callbacks and physical state cache by identity while
        # selecting this home's substantive state/credit/operation methods.
        from .resource import LocalResourceExecution
        self._native_resource_owners = {}
        for resource_id, resource in owner._practical.items():
            if 'local' in resource.resources:
                private = object.__new__(LocalResourceExecution)
                private.__dict__ = resource.__dict__
                self._native_resource_owners[resource_id] = private
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
        return {'binding_id': 'root_scientific_process_hpc_coordination_execution_job_submission_local_job_execution', 'version': 'root_scientific_process_hpc_coordination_execution_job_submission_local_job_execution_v1', 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}

    def _credit_binding_record(self,context):
        if context.role!='launch_local' or context.run_id!=self.run_id:
            raise ValueError('fixed_execution_credit_context_required')
        return self.as_record()
