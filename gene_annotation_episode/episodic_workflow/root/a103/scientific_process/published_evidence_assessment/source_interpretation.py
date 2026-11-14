"""Private A103 literature source interpretation."""
from __future__ import annotations
from .source_contracts import ContractError

class SourceInterpretation:

    def reasoning_action_schema(self, context, commit_schema, *, _accept_legacy_quotes=False):
        return None

    def accept_reasoning_action_schema(self, context, commit_schema):
        return None

    def reasoning_has_task_content(self, context, selection):
        return False

    def execute_reasoning(self, context, selection, operation_key):
        raise ContractError('a103_literature_reasoning_not_commissioned')
