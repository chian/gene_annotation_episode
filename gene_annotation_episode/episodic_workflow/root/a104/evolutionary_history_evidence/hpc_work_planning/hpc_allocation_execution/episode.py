"""Predefined private hpc_execution iteration for A104."""
from importlib import import_module
from .presentation import present_task_context
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
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress

class HPCEpisode(HPCConfiguration, HPCAssignment, HPCReport, HPCGoal, HPCSummary, PortfolioState, MeasuredHistory, PortfolioComparison, ForecastObservations, AllocationResults, AllocationObservations, ReceivedEvidence, ClosedModels, HPCEpisodeCredit, HPCEpisodeYield, HPCActivityAdvice, QueueObservations, HPCBindingRecord, LaunchPreparation, LaunchReceiptCustody, HPCWorkOperations, ResourceDiscovery, PortfolioCandidates, PortfolioPlanning, AllocationHandoff, AllocationOrder):
    binding_path = 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution'
    commissioning_parent = 'evolutionary_history_evidence/hpc_work_planning'
    roles = ('hpc_execution',)
    decision_source_type = HPCWorkTask
    decision_prompt_renderer = staticmethod(present_task_context)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return ('launch', 'monitor', 'results')

    def allowed_children(self, parent, caller_capabilities):
        return self.child_roles(parent.role)

    def permitted_common_actions(self, context):
        if 'monitoring' in self._commission(context.assignment, context.scope):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'child', 'wait', 'redeliver_report')

    def prepare_child_request(self, parent, role, assignment):
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        return assignment

    def child_request_assembler(self, role):
        if role == 'monitor':
            from .to_child_execution_progress_assessment import assemble_request
            return assemble_request
        if role == 'launch':
            from .to_child_execution_job_submission import assemble_request
            return assemble_request
        if role == 'results':
            from .to_child_execution_result_acquisition import assemble_request
            return assemble_request
        return None

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True

    def child_report_receiver(self, role):
        if role == 'launch':
            from .from_child_execution_job_submission import receive_report
            return receive_report
        if role == 'results':
            from .from_child_execution_result_acquisition import receive_report
            return receive_report
        return None

def create_execution_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.episode import ExecutionEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.episode import ExecutionEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.episode import ExecutionEpisode as Private2
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as Private3
    from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.episode import ExecutionEpisode as Private4
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration), Private3(*args, **configuration), Private4(*args, **configuration))
