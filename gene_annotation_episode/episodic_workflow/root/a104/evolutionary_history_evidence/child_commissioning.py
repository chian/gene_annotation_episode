"""Private A104 scientific child commissioning."""
from __future__ import annotations
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.a104_credit import A104EvolutionaryCredit, A104PanelIdentityCredit, A104AlignmentSuitabilityCredit, A104RobustnessCredit
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import TASKS
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import RECORD_SOURCE, received_records

def allowed_child_roles(child_roles):
    return tuple((role for role in child_roles if role in {'evolutionary_history_evidence', 'hpc'}))

def permitted_common_actions():
    return ('tool', 'reason', 'child', 'redeliver_report')

class ScientificChildCommissioning:

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def permitted_common_actions(self, context):
        self.validate_context(context)
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.child_commissioning import permitted_common_actions
        return permitted_common_actions()

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.child_commissioning import allowed_child_roles
        return allowed_child_roles(self._child_roles)

    def prepare_child_request(self, parent, role, assignment):
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        return assignment

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True

    def child_request_assembler(self, role):
        if role == 'monitor':
            from .to_child_execution_progress_assessment import assemble_request
            return assemble_request
        if role == 'evolutionary_history_evidence':
            from .to_child_evolutionary_history_evidence import assemble_request
            return assemble_request
        if role == 'hpc':
            from .to_child_hpc_work_planning import assemble_request
            return assemble_request
        if role == 'launch':
            from .to_child_execution_job_submission import assemble_request
            return assemble_request
        if role == 'results':
            from .to_child_execution_result_acquisition import assemble_request
            return assemble_request
        if role == 'literature':
            from .to_child_published_evidence_assessment import assemble_request
            return assemble_request
        return None

    def child_report_receiver(self, role):
        if role == 'evolutionary_history_evidence':
            from .from_child_evolutionary_history_evidence import receive_report
            return receive_report
        if role == 'hpc':
            from .from_child_hpc_work_planning import receive_report
            return receive_report
        if role == 'launch':
            from .from_child_execution_job_submission import receive_report
            return receive_report
        if role == 'results':
            from .from_child_execution_result_acquisition import receive_report
            return receive_report
        if role == 'literature':
            from .from_child_published_evidence_assessment import receive_report
            return receive_report
        return None
