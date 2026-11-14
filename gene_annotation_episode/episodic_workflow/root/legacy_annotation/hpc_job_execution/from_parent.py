"""Interpret and validate this terminal child assignment."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import plain
from ...practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment

class HPCFromParent:
    def _assignment(self,context):
        assignment=validate_assignment(plain(context.assignment))
        kind='hpc' if context.role=='launch_hpc' else None
        if assignment['resource_kind']!=kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def prepare_assignment(self,parent,role,selection,scope,operation_key):
        assignment=validate_assignment(plain(selection))
        if role!='launch_hpc' or assignment['resource_kind']!='hpc':
            raise ValueError('execution_resource_assignment_mismatch')
        return self._operations(assignment['resource_kind']).validate_assignment(assignment)

    def assignment_schema(self,role):return deepcopy(ASSIGNMENT_SCHEMA)

