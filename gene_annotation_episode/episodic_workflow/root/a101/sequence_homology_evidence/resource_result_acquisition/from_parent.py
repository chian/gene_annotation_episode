"""Private A101 results from parent."""
from __future__ import annotations
from .execution_contracts import LAUNCH_SCHEMA, RESOURCE_ROLES, RESULTS_SCHEMA, _validate, deepcopy, plain, validate_selection

class OperationalAssignment:

    def assignment_schema(self, role):
        self.credit_kind(role)
        return deepcopy(RESULTS_SCHEMA)

    @staticmethod
    def _permitted(assignment, capability):
        constraints = assignment.get('constraints', {})
        selection = assignment.get('resource_selection')
        return (selection is None or (capability['resource_id'] == selection['resource_id'] and capability['kind'] == selection['kind'])) and ('allowed_resource_ids' not in constraints or capability['resource_id'] in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds']) and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id']) and ('kind' not in constraints or capability['kind'] == constraints['kind'])

    @staticmethod
    def _require_launch_child_instruction_pins(parent_selection, child_selection):
        """The resource launch parent owns the instruction pins it supplied."""
        parent_selection = validate_selection(parent_selection)
        child_selection = validate_selection(child_selection)
        if parent_selection is None:
            return
        if child_selection is None or child_selection['library_id'] != parent_selection['library_id']:
            raise ValueError('launch_instruction_inheritance_conflict')
        retained = {(row['entry_id'], row['section_id'], row['sha256']) for row in child_selection['sections']}
        if any(((row['entry_id'], row['section_id'], row['sha256']) not in retained for row in parent_selection['sections'])):
            raise ValueError('launch_instruction_inheritance_conflict')

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self.credit_kind(role)
        selected = plain(selection)
        schema = self.assignment_schema('results')
        selected = {key: selected[key] for key in schema['properties'] if key in selected}
        selected = _validate(selected, schema)
        if parent.role == 'launch' and 'results' not in RESOURCE_ROLES:
            raise ValueError('resource_child_role_not_owned_by_launch')
        return self._adapter(selected).prepare_assignment(parent, 'results', selected, scope, operation_key)

    def initial_references(self, context):
        self.credit_kind(context.role)
        callback = getattr(self._adapter(context.assignment), 'initial_references', None)
        return [] if callback is None else callback(context)
