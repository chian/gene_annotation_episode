"""Private A110 from parent."""
from __future__ import annotations
from .contracts import ContractError, _CHILDREN, _PAGE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class LiteratureAssignment:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        selection = _WINDOW
        schema = obj({'version': {'const': 'reading_assignment_v1'}, 'page': _PAGE, 'selection': selection})
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_component_binding import assignment_schema_fields
        schema['properties'].update(assignment_schema_fields())
        return schema

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema('literature_ordered', context=context))
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
        value = self._validate_assignment(role, selection, scope, context=parent)
        if parent.role == 'literature_page' and role in _CHILDREN['literature_page']:
            original = self._validate_parent_page_assignment(parent.role, parent.assignment, parent.scope, context=parent)
            if not self._within_source(value['page']['source_ref'], original['source_ref'], scope):
                raise ContractError('literature_reading_outside_assigned_source')
        return value

    def _parent_page_schema(self, role, *, context=None):
        schema = _PAGE
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_component_binding import assignment_schema_fields
        schema['properties'].update(assignment_schema_fields())
        return schema

    def _validate_parent_page_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self._parent_page_schema('literature_page', context=context))
        page = value
        self._validate_page(page, scope)
        return value
