"""Private scientific-process episode behavior for A106."""
from __future__ import annotations
from .task import ScientificInvestigationTask
from .scientific_contracts import ContractError, ROLE, ROLES
from .credit import PerturbationEvidenceCredit
from importlib import import_module as _import_module
from .yield_estimator import PerturbationEvidenceYield
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress

def create_execution_bindings(*args, **configuration):
    """Construct private bindings with this caller's existing operands."""
    from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.episode import ExecutionEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_job_submission.api_job_execution.episode import ExecutionEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_result_acquisition.episode import ExecutionEpisode as Private2
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))
from .configuration import ScientificConfiguration
from .binding_record import ScientificBindingRecord
from .goal import ScientificGoal
from .from_parent import ScientificAssignment
from .process_state import PerturbationEvidenceState
from .alternate_process_selection import AlternateProcessSelection
from .to_parent import ScientificReport
from .tool_selection import ScientificToolSelection
from .internal_summary import ScientificSummary
from .scientific_operations import ScientificOperations
from .to_child_published_evidence_assessment import prepare_request as prepare_published_evidence_assessment
from .from_child_published_evidence_assessment import receive_report as receive_published_evidence_assessment
from .to_child_execution_job_submission import prepare_commission as prepare_execution_job_submission
from .from_child_execution_job_submission import receive_report as receive_execution_job_submission
from .to_child_execution_progress_assessment import prepare_commission as prepare_execution_progress_assessment
from .from_child_execution_progress_assessment import receive_report as receive_execution_progress_assessment
from .to_child_execution_result_acquisition import prepare_commission as prepare_execution_result_acquisition
from .from_child_execution_result_acquisition import receive_report as receive_execution_result_acquisition

class PerturbationEvidenceEpisode(ScientificConfiguration, ScientificBindingRecord, ScientificGoal, ScientificAssignment, PerturbationEvidenceState, AlternateProcessSelection, ScientificReport, ScientificToolSelection, ScientificSummary, ScientificOperations, PerturbationEvidenceCredit, PerturbationEvidenceYield):
    """One recursive C7 role with parent-selected A/P and actual tool assignment data."""
    decision_source_type = ScientificInvestigationTask
    binding_path = 'perturbation_evidence'
    commissioning_parent = 'legacy_annotation'
    roles = ROLES
    entry_roles = ROLES

    def contract_information_profile(self, context):
        """Expose frozen contract information to scientific commissioning parents."""
        return self._contract_information_profile if context.role in ('annotation', ROLE) else None

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError('perturbation_evidence_role_not_bound')

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def permitted_common_actions(self, context):
        self.validate_context(context)
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        return self._child_roles

    def _component_scoring_facts(self, context):
        return {}

    def current_report_facts(self, context):
        return self._component_scoring_facts(context)

    def initial_decision_context(self, context):
        if context.role not in {'annotation', ROLE}:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        result = self._component_scoring_facts(context)
        return result

    def _validate_component_axis_report(self, context, form, schema):
        return

    def prepare_child_request(self, parent, role, assignment):
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        return assignment

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True

    def child_request_preparer(self, role):
        return {'literature': prepare_published_evidence_assessment}.get(role)

    def child_report_receiver(self, role):
        return {'literature': receive_published_evidence_assessment}.get(role)

    def child_request_preparer_for_binding(self, role, binding_path):
        return {('launch', 'perturbation_evidence/execution_job_submission'): prepare_execution_job_submission, ('monitor', 'perturbation_evidence/execution_progress_assessment'): prepare_execution_progress_assessment, ('results', 'perturbation_evidence/execution_result_acquisition'): prepare_execution_result_acquisition}.get((role, binding_path))

    def child_report_receiver_for_binding(self, role, binding_path):
        return {('launch', 'perturbation_evidence/execution_job_submission'): receive_execution_job_submission, ('monitor', 'perturbation_evidence/execution_progress_assessment'): receive_execution_progress_assessment, ('results', 'perturbation_evidence/execution_result_acquisition'): receive_execution_result_acquisition}.get((role, binding_path))
