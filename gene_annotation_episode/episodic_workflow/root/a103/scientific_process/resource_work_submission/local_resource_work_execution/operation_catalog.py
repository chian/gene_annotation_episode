"""Own the actual private Resource catalogue and adapter catalogue extension."""
from __future__ import annotations
from .resource_contracts import RESULTS_VERSION, _availability_failure, _failure, _outcome, _validate, inspect, obj, sqlite3

class ResourceOperationCatalog:

    def catalog(self, context):
        tools = [{'name': 'resource.capabilities', 'description': 'Read actual capability availability and configured resource information; this does not select or submit work.', 'input_schema': obj({})}]
        tools.extend(self._adapter(context.assignment).catalog(context))
        return tools

