"""Private A102 scientific child commissioning."""
from __future__ import annotations
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
        return assignment

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True
