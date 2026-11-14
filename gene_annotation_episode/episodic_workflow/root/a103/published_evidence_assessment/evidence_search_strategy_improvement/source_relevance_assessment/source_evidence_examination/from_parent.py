"""Private A103 literature_page from parent."""
from __future__ import annotations
from .source_contracts import ContractError, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class SourceAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        schema = _PAGE
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
        validate_schema(value, self.assignment_schema(role, context=context))
        page = value
        self._validate_page(page, scope)
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        value = self._validate_assignment(role, selection, scope, context=parent)
        parent.role
        return value
