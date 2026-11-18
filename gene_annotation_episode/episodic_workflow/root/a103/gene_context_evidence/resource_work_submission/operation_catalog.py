"""Own the actual private Resource catalogue and adapter catalogue extension."""
from __future__ import annotations
from .resource_contracts import HANDOFF_SCHEMA, RESULTS_VERSION, _availability_failure, _failure, _outcome, _string, _validate, inspect, obj, sqlite3

class ResourceOperationCatalog:

    def catalog(self, context):
        tools = [{'name': 'resource.capabilities', 'description': 'Read actual capability availability and configured resource information; this does not select or submit work.', 'input_schema': obj({})}]
        tools.append({'name': 'resource.inspect', 'description': 'Inspect one declared resource and its actual binding. Unavailable, unknown, unauthenticated and unbound resources return distinct structured failures; this does not submit work.', 'input_schema': obj({'resource_id': _string()})})
        tools.append({'name': 'resource.check_handoff', 'description': 'Exercise the configured receiving interfaces of an explicitly supplied returned handoff. No submission or resource substitution.', 'input_schema': obj({'handoff': HANDOFF_SCHEMA})})
        return tools

