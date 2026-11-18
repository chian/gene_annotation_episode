"""Private A101 results execution operations."""
from __future__ import annotations
from .execution_contracts import CAPABILITY_SCHEMA, HANDOFF_SCHEMA, RESOURCE_ROLES, RESULTS_VERSION, _availability_failure, _failure, _outcome, _string, _validate, inspect, obj, sqlite3

class OperationalOperations:

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

    def catalog(self, context):
        self.credit_kind(context.role)
        tools = [{'name': 'resource.capabilities', 'description': 'Read actual capability availability and configured resource information; this does not select or submit work.', 'input_schema': obj({})}]
        tools.extend(self._adapter(context.assignment).catalog(context))
        return tools

    async def execute(self, context, tool_name, arguments, operation_key):
        catalog = {item['name']: item for item in self.catalog(context)}
        if tool_name not in catalog:
            raise ValueError('tool_not_owned_by_resource_role')
        arguments = _validate(arguments, catalog[tool_name]['input_schema'])
        if tool_name == 'resource.capabilities':
            return _outcome({'capabilities': list(self.capabilities())})
        if tool_name == 'resource.inspect':
            reference = arguments['resource_id']
            capability = next((value for value in self.capabilities() if value['resource_id'] == reference), None)
            if capability is None:
                return _outcome(failure=_failure('resource_not_bound', [reference]))
            code = _availability_failure(capability)
            if code is None and reference not in self.adapters:
                code = 'resource_not_bound'
            return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
        if tool_name == 'resource.check_handoff':
            handoff = arguments['handoff']
            try:
                adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                callback = getattr(adapter, 'check_handoff', None)
                if callback is None:
                    return _outcome(failure=_failure('receiving_interface_unavailable'))
                value = callback(context, handoff, operation_key)
                return await value if inspect.isawaitable(value) else value
            except (ValueError, KeyError, OSError, sqlite3.Error) as error:
                if str(error) == 'resource_information_identity_conflict':
                    raise
                return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
        adapter = self._adapter(context.assignment)
        return await adapter.execute(context, tool_name, arguments, operation_key)
