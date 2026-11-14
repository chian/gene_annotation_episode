"""Private A107 from parent."""
from __future__ import annotations
from .contracts import ContractError, _REFERENCES, deepcopy, json, obj, plain, validate_schema

class LiteratureAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        version, field = ('search_assignment_v1', 'search_result_refs')
        schema = obj({'version': {'const': version}, 'question_context_refs': _REFERENCES, field: _REFERENCES})
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_contracts import assignment_schema_fields
        schema['properties'].update(assignment_schema_fields())
        return schema

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema('literature_search', context=context))
        for field, references in value.items():
            if field.endswith('_refs'):
                for reference in references:
                    self._require(reference, scope, None if field == 'question_context_refs' else 'source')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        value = self._validate_assignment(role, selection, scope, context=parent)
        return value
