"""Private A102 resource from parent."""
from __future__ import annotations
from .resource_contracts import LAUNCH_SCHEMA, RESOURCE_ROLES, RESULTS_SCHEMA, _validate, deepcopy, plain, validate_selection

class ResourceFromParent:

    def assignment_schema(self, role):
        self.credit_kind(role)
        return deepcopy(LAUNCH_SCHEMA)

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = plain(selection)
        schema = self.assignment_schema(role)
        selected = {key: selected[key] for key in schema['properties'] if key in selected}
        selected = _validate(selected, schema)
        if parent.role == 'launch' and role not in RESOURCE_ROLES:
            raise ValueError('resource_child_role_not_owned_by_launch')
        parent.role == 'launch'
        return selected
