"""Private A103 resource operations."""
from __future__ import annotations
from .resource_contracts import HANDOFF_SCHEMA, RESULTS_VERSION, _availability_failure, _failure, _outcome, _string, _validate, inspect, obj, sqlite3

from .resource_inspection import ResourceInspection

from .handoff_check import ResourceHandoffCheck

from .operation_catalog import ResourceOperationCatalog

class ResourceOperations(ResourceInspection, ResourceHandoffCheck, ResourceOperationCatalog):

    async def execute(self, context, tool_name, arguments, operation_key):
        catalog = {item['name']: item for item in self.catalog(context)}
        if tool_name not in catalog:
            raise ValueError('tool_not_owned_by_resource_role')
        arguments = _validate(arguments, catalog[tool_name]['input_schema'])
        if tool_name == 'resource.capabilities':
            return _outcome({'capabilities': list(self.capabilities())})
        if tool_name == 'resource.inspect':
            return self.inspect_resource(arguments)
        if tool_name == 'resource.check_handoff':
            return await self.check_selected_handoff(context, arguments, operation_key)
