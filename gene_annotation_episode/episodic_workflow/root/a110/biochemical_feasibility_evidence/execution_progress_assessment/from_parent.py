"""MonitorAssignment"""
from __future__ import annotations
from .to_child_execution_progress_assessment import prepare_dependency_request
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, validate_schema
from .contracts import _ASSIGNMENT

class MonitorAssignment:

    def assignment_schema(self, role):
        self._role(role)
        return deepcopy(_ASSIGNMENT)

    def _assignment(self, assignment, scope):
        value = plain(assignment)
        validate_schema(value, _ASSIGNMENT)
        if not self.services.reference_in_scope(value['target_handle'], scope, 'execution_handle'):
            raise ContractError('progress_target_unavailable_or_outside_scope')
        for reference in value['known_progress_refs']:
            snapshot = self.services.read_progress(reference, scope)
            if snapshot['target_handle'] != value['target_handle']:
                raise ContractError('monitor_known_progress_target_mismatch')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        value = self._assignment(selection, scope)
        if parent.role == 'monitor':
            value = prepare_dependency_request(self, parent, value)
        return value
