"""Private from parent for A110 prediction."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import validate_schema

TEXT = {'type': 'string', 'minLength': 1}

class PredictionAssignment:
    def assignment_schema(self, role):
        self.credit_kind(role)
        fields = {'commission_source_ref': {'type': 'string', 'format': 'reference'}}
        if self.commissions:
            fields['commission_id'] = {'type': 'string', 'enum': list(self.commissions)}
        required = []
        fields['owner_episode_id'] = TEXT
        required.append('owner_episode_id')
        schema = obj(fields, required=required)
        if self.commissions:
            schema['oneOf'] = [{'required': ['commission_id']}, {'required': ['commission_source_ref']}]
        else:
            schema['required'].append('commission_source_ref')
        return schema

    @staticmethod
    def commission_identity(assignment):
        return {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}

    def _commission(self, assignment, scope):
        if 'commission_source_ref' in assignment:
            from gene_annotation_episode.episodic_workflow.root.a110.hpc_commission_sources import read
            return read(self.store, assignment['commission_source_ref'], scope=plain(scope), resources=self.resources)
        return self.commissions[assignment['commission_id']]

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selection = plain(selection)
        validate_schema(selection, self.assignment_schema(role))
        if (parent.role != 'hpc'
                or selection['owner_episode_id'] != parent.episode_id
                or self.commission_identity(selection) != self.commission_identity(parent.assignment)):
            raise ValueError('prediction_or_execution_must_belong_to_its_original_hpc_parent')
        if self.private_yield_binding and 'yield_bindings' not in self._commission(selection, scope):
            raise ValueError('hpc_commission_yield_binding_required:' + role)
        return selection
