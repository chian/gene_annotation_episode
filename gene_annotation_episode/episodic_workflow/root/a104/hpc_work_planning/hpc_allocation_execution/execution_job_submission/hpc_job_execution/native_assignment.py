"""Private original A104 HPCExecution service native_assignment."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import ASSIGNMENT_SCHEMA
from .native_resource_contracts import ROLE_KINDS
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import validate_assignment

class HPCExecutionNativeAssignment:

    def _assignment(self, context):
        assignment = validate_assignment(plain(context.assignment))
        kind = ROLE_KINDS.get(context.role)
        if assignment['resource_kind'] != kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def assignment_schema(self, role):
        return deepcopy(ASSIGNMENT_SCHEMA)

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        assignment = validate_assignment(plain(selection))
        if ROLE_KINDS.get(role) != assignment['resource_kind']:
            raise ValueError('execution_resource_assignment_mismatch')
        return self._operations(assignment['resource_kind']).validate_assignment(assignment)
