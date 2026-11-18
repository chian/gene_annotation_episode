"""Private A107 scientific child_commissioning."""
from __future__ import annotations
from .from_child_execution_job_submission import receive_report as receive_launch_report
from .from_child_execution_result_acquisition import receive_report as receive_results_report
from .to_child_execution_progress_assessment import prepare_request as prepare_monitor_request
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress

class ScientificChildCommissioning:

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def permitted_common_actions(self, context):
        self.validate_context(context)
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        return self._child_roles

    def prepare_child_request(self, parent, role, assignment):
        if role == 'monitor':
            return prepare_monitor_request(assignment)
        if role == 'launch':
            return assignment
        if role == 'results':
            return assignment
        return assignment

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True

    def execution_child_report_receiver(self, role):
        if role == 'launch':
            return receive_launch_report
        if role == 'results':
            return receive_results_report
        if role == 'partner_presence_evidence':
            from .from_child_partner_presence_evidence import receive_report
            return receive_report
        if role == 'hpc':
            from .from_child_hpc_work_planning import receive_report
            return receive_report
        if role == 'literature':
            from .from_child_published_evidence_assessment import receive_report
            return receive_report
        return None

    def child_request_assembler(self, role):
        if role == 'hpc':
            from .to_child_hpc_work_planning import assemble_request
            return assemble_request
        if role == 'literature':
            from .to_child_published_evidence_assessment import assemble_request
            return assemble_request
        if role == 'launch':
            from .to_child_execution_job_submission import assemble_request
            return assemble_request
        if role == 'results':
            from .to_child_execution_result_acquisition import assemble_request
            return assemble_request
        if role == 'partner_presence_evidence':
            from .to_child_partner_presence_evidence import assemble_request
            return assemble_request
        return None
