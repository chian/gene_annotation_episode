"""Private A103 resource resource selection."""
from __future__ import annotations
from .resource_contracts import CAPABILITY_SCHEMA, RESOURCE_ROLES, RESULTS_VERSION, _validate

class ResourceResourceSelection:

    def capabilities(self, context=None):
        """Include unbound declarations accurately, but never offer their tools."""
        values = {}
        for capability in self.services.capabilities():
            value = _validate(capability, CAPABILITY_SCHEMA)
            if value['resource_id'] not in self.adapters:
                value['tool_names'] = []
            values[value['resource_id']] = value
        for adapter in self.adapters.values():
            value = _validate(adapter.capability(), CAPABILITY_SCHEMA)
            if value['resource_id'] != adapter.resource_id:
                raise ValueError('resource_capability_identity_mismatch')
            if context is not None and context.role in RESOURCE_ROLES and (context.assignment.get('resource_selection', {}).get('resource_id') == adapter.resource_id):
                bound = {tool['name'] for tool in adapter.catalog(context)}
                if not set(value['tool_names']) <= bound:
                    raise ValueError('resource_capability_tool_not_bound')
            values[value['resource_id']] = value
        return tuple(values.values())

    def _adapter(self, assignment):
        selection = assignment['handoff']['resource_selection'] if assignment.get('version') == RESULTS_VERSION else assignment.get('resource_selection')
        if selection is None or selection['resource_id'] not in self.adapters:
            raise ValueError('resource_not_bound')
        return self.adapters[selection['resource_id']]

    @staticmethod
    def _permitted(assignment, capability):
        constraints = assignment.get('constraints', {})
        selection = assignment.get('resource_selection')
        return (selection is None or (capability['resource_id'] == selection['resource_id'] and capability['kind'] == selection['kind'])) and ('allowed_resource_ids' not in constraints or capability['resource_id'] in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds']) and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id']) and ('kind' not in constraints or capability['kind'] == constraints['kind'])
