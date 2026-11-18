"""Predefined private hpc iteration for A103."""
from importlib import import_module
from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_prompt import render_hpc_prompt
from .task import HPCWorkTask
from .configuration import HPCConfiguration
from .from_parent import HPCAssignment
from .to_parent import HPCReport
from .goal import HPCGoal
from .internal_summary import HPCSummary
from .portfolio_state import PortfolioState
from .measured_history import MeasuredHistory
from .portfolio_comparison import PortfolioComparison
from .forecast_observations import ForecastObservations
from .allocation_results import AllocationResults
from .allocation_observations import AllocationObservations
from .received_evidence import ReceivedEvidence
from .closed_models import ClosedModels
from .credit import HPCEpisodeCredit
from .waiting import HPCActivityAdvice
from .queue_observations import QueueObservations
from .binding_record import HPCBindingRecord
from .to_child_execution_job_submission import LaunchPreparation
from .from_child_execution_job_submission import LaunchReceiptCustody
from .work_operations import HPCWorkOperations
from .resource_discovery import ResourceDiscovery
from .portfolio_candidates import PortfolioCandidates
from .portfolio_planning import PortfolioPlanning
from .allocation_handoff import AllocationHandoff
from .allocation_order import AllocationOrder
from .yield_estimator import HPCEpisodeYield
from .to_child_hpc_resource_prediction import prepare_request as prepare_prediction_request
from .from_child_hpc_resource_prediction import receive_prediction_report
from .to_child_hpc_allocation_execution import prepare_request as prepare_allocation_request
from .from_child_hpc_allocation_execution import receive_allocation_report
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress

class HPCEpisode(HPCConfiguration, HPCAssignment, HPCReport, HPCGoal, HPCSummary, PortfolioState, MeasuredHistory, PortfolioComparison, ForecastObservations, AllocationResults, AllocationObservations, ReceivedEvidence, ClosedModels, HPCEpisodeCredit, HPCEpisodeYield, HPCActivityAdvice, QueueObservations, HPCBindingRecord, LaunchPreparation, LaunchReceiptCustody, HPCWorkOperations, ResourceDiscovery, PortfolioCandidates, PortfolioPlanning, AllocationHandoff, AllocationOrder):
    binding_path = 'gene_context_evidence/hpc_work_planning'
    commissioning_parent = 'gene_context_evidence'
    roles = ('hpc',)
    decision_source_type = HPCWorkTask
    decision_prompt_renderer = staticmethod(render_hpc_prompt)
    entry_roles = ('hpc',)
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return ('hpc_prediction', 'hpc_execution', 'launch', 'monitor', 'results')
    def allowed_children(self, parent, caller_capabilities):
        return self.child_roles(parent.role)
    def permitted_common_actions(self, context):
        if 'monitoring' in self._commission(context.assignment, context.scope):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'child', 'wait', 'redeliver_report')
    def prepare_child_request(self, parent, role, assignment):
        if role == 'hpc_prediction':
            return prepare_prediction_request(parent, assignment, self.commissions)
        if role == 'hpc_execution':
            return prepare_allocation_request(parent, assignment, self.commissions)
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        return assignment
    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True
    def child_report_receiver(self, role):
        if role == 'hpc_execution':
            return receive_allocation_report
        return receive_prediction_report if role == 'hpc_prediction' else None

def create_execution_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.execution_job_submission.episode import ExecutionEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.execution_job_submission.api_job_execution.episode import ExecutionEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.execution_job_submission.local_job_execution.episode import ExecutionEpisode as Private2
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as Private3
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.execution_result_acquisition.episode import ExecutionEpisode as Private4
    return (
        Private0(*args, **configuration),
        Private1(*args, **configuration),
        Private2(*args, **configuration),
        Private3(*args, **configuration),
        Private4(*args, **configuration),
    )
