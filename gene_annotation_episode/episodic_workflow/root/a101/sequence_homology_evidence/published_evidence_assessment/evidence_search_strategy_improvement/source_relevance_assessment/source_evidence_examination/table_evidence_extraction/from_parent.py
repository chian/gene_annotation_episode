"""Private A101 literature_table from parent."""
from __future__ import annotations
from .source_contracts import ContractError, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class LiteratureAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        selection = {'anyOf': [_TABLE, _WINDOW]}
        schema = obj({'version': {'const': 'reading_assignment_v1'}, 'page': _PAGE, 'selection': selection})
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
        validate_schema(value, self.assignment_schema('literature_table', context=context))
        page = value['page']
        self._validate_page(page, scope)
        selected = value['selection']
        windows = [selected]
        for window in windows:
            if window['source_ref'] != page['source_ref']:
                raise ContractError('literature_reading_source_mismatch')
            if 'representation' in window and window['representation'] != page['representation']:
                raise ContractError('literature_reading_representation_mismatch')
            if 'representation' in window:
                artifact = self.services.read_record(page['artifact_ref'])
                if window['offset'] > artifact['size']:
                    raise ContractError('source_offset_out_of_bounds')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        value = self._validate_assignment('literature_table', selection, scope, context=parent)
        if parent.role == 'literature_page' and 'literature_table' in _CHILDREN['literature_page']:
            original = self._validate_parent_page(parent)
            if not self._within_source(value['page']['source_ref'], original['source_ref'], scope):
                raise ContractError('literature_reading_outside_assigned_source')
        return value
