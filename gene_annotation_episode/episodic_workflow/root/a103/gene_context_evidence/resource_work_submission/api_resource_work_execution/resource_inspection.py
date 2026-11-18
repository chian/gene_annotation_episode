"""Inspect the actual declared Resource capability and binding status."""
from __future__ import annotations
from .resource_contracts import RESULTS_VERSION, _availability_failure, _failure, _outcome, _validate, inspect, obj, sqlite3

class ResourceInspection:

    def inspect_resource(self, arguments):
        reference = arguments['resource_id']
        capability = next((value for value in self.capabilities() if value['resource_id'] == reference), None)
        if capability is None:
            return _outcome(failure=_failure('resource_not_bound', [reference]))
        code = _availability_failure(capability)
        if code is None and reference not in self.adapters:
            code = 'resource_not_bound'
        return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
