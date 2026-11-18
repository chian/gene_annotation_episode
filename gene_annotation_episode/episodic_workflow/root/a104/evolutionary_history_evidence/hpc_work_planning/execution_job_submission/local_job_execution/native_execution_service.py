"""Private original A104 LocalExecution service native_execution_service."""
from __future__ import annotations
from .native_configuration import LocalExecutionNativeConfiguration
from .native_assignment import LocalExecutionNativeAssignment
from .native_receipt_state import LocalExecutionNativeReceiptState
from .native_goal import LocalExecutionNativeGoal
from .native_internal_summary import LocalExecutionNativeInternalSummary
from .native_tool_actions import LocalExecutionNativeToolActions
from .native_completion import LocalExecutionNativeCompletion
from .native_return import LocalExecutionNativeReturn
from .native_credit import LocalExecutionNativeCredit

class TerminalExecutionBehavior(LocalExecutionNativeConfiguration, LocalExecutionNativeAssignment, LocalExecutionNativeReceiptState, LocalExecutionNativeGoal, LocalExecutionNativeInternalSummary, LocalExecutionNativeToolActions, LocalExecutionNativeCompletion, LocalExecutionNativeReturn, LocalExecutionNativeCredit):

    def child_roles(self, role):
        return ()

    def permitted_common_actions(self, context):
        return ('tool',)

    def allowed_children(self, parent, caller_capabilities):
        return ()
