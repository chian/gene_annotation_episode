from __future__ import annotations
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.progress_observations import _ASSIGNMENT
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import validate_schema

def _role(role):
    if role != 'monitor':
        raise ValueError('unsupported_monitor_role:' + str(role))

def required_return_sources(self, parent, role):
    self._role(role)
    if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
        return ('monitoring_progress_refs',)
    return ()

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
    task = getattr(self.services, 'macs2_peak_monitor_task', None)
    if callable(task):
        task(parent, assignment=selection)
    value = self._assignment(selection, scope)
    if parent.role == 'monitor':
        original = self._assignment(parent.assignment, parent.scope)
        eligible = {row['handle'] for row in self.services.dependencies(original['target_handle'], parent.scope)}
        if value['target_handle'] not in eligible:
            raise ContractError('monitor_child_target_not_exposed_direct_dependency')
        if not set(value['permitted_committed_record_types']) <= set(original['permitted_committed_record_types']):
            raise ContractError('monitor_child_expands_permitted_record_types')
    return value
