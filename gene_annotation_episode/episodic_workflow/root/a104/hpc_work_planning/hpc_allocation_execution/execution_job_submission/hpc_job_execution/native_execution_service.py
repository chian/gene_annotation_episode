"""Private original A104 HPCExecution service native_execution_service."""
from __future__ import annotations
from .native_configuration import HPCExecutionNativeConfiguration
from .native_assignment import HPCExecutionNativeAssignment
from .native_receipt_state import HPCExecutionNativeReceiptState
from .native_goal import HPCExecutionNativeGoal
from .native_internal_summary import HPCExecutionNativeInternalSummary
from .native_tool_actions import HPCExecutionNativeToolActions
from .native_completion import HPCExecutionNativeCompletion
from .native_return import HPCExecutionNativeReturn
from .native_credit import HPCExecutionNativeCredit

class TerminalExecutionBehavior(HPCExecutionNativeConfiguration, HPCExecutionNativeAssignment, HPCExecutionNativeReceiptState, HPCExecutionNativeGoal, HPCExecutionNativeInternalSummary, HPCExecutionNativeToolActions, HPCExecutionNativeCompletion, HPCExecutionNativeReturn, HPCExecutionNativeCredit):

    def child_roles(self, role):
        return ()

    def permitted_common_actions(self, context):
        return ('tool',)

    def allowed_children(self, parent, caller_capabilities):
        return ()
