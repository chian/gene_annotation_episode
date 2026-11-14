"""Private native terminal assignment."""
from __future__ import annotations
from .terminal_contracts import ASSIGNMENT_SCHEMA, ROLE_KINDS, deepcopy, plain, validate_assignment

class TerminalAssignment:

    def _assignment(self, context):
        assignment = validate_assignment(plain(context.assignment))
        kind = ROLE_KINDS.get(context.role)
        if assignment['resource_kind'] != kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        assignment = validate_assignment(plain(selection))
        if ROLE_KINDS.get(role) != assignment['resource_kind']:
            raise ValueError('execution_resource_assignment_mismatch')
        return self._operations(assignment['resource_kind']).validate_assignment(assignment)

    def assignment_schema(self, role):
        return deepcopy(ASSIGNMENT_SCHEMA)
