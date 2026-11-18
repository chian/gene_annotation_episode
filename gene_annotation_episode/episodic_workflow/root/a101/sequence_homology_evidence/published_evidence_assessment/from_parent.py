"""Private A101 literature from parent."""
from __future__ import annotations
from .source_contracts import ContractError, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class LiteratureAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        version, field = {'literature': ('literature_assignment_v1', 'source_refs'), 'literature_strategy': ('strategy_assignment_v1', 'prior_search_refs'), 'literature_search': ('search_assignment_v1', 'search_result_refs')}['literature']
        schema = obj({'version': {'const': version}, 'question_context_refs': _REFERENCES, field: _REFERENCES})
        schema = deepcopy(schema)
        return schema

    def _validate_page(self, page, scope):
        source = self._require(page['source_ref'], scope, 'source')
        if self._artifact(source, page['representation']) != page['artifact_ref']:
            raise ContractError('literature_source_artifact_mismatch', detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'], 'representation': page['representation']})
        self._require(page['artifact_ref'], scope, 'artifact')
        for reference in (*page['question_context_refs'], *page['prior_delivery_refs']):
            self._require(reference, scope)

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema('literature', context=context))
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
        value = self._validate_assignment('literature', selection, scope, context=parent)
        if parent.role == 'literature_page' and 'literature' in _CHILDREN['literature_page']:
            original = self._validate_assignment(parent.role, parent.assignment, parent.scope, context=parent)
            if not self._within_source(value['page']['source_ref'], original['source_ref'], scope):
                raise ContractError('literature_reading_outside_assigned_source')
        return value
