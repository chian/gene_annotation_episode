"""Private A103 scientific from children."""
from __future__ import annotations
from .from_child_execution_progress_assessment import receive_progress as receive_monitor_progress

class ScientificChildReturns:

    def receive_child_progress_for_role(self, context, role, form, schema, operation_key, provider):
        if role != 'monitor':
            return False
        receive_monitor_progress(context, form, schema, operation_key, provider)
        return True
