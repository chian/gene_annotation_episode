"""Own actual Resource report field contracts from configured adapters."""
from __future__ import annotations
from .resource_contracts import HANDOFF_SCHEMA, Mapping, ReportBoundaryError, _array, _nullable, plain, reference_in_context

class ResourceReportFields:

    def fact_sources(self, role):
        values = {'execution_handoff': {'type': ['object', 'null'], 'meaning': 'The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure.', 'report_schema': {**_nullable(HANDOFF_SCHEMA), 'x-source': 'execution_handoff'}}, 'execution_handoffs': {'type': 'array', 'meaning': 'For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it.', 'report_schema': {**_array(HANDOFF_SCHEMA), 'x-source': 'execution_handoffs'}}}
        for adapter in self.adapters.values():
            for name, definition in adapter.fact_sources(role).items():
                if name in values and values[name] != definition:
                    raise ValueError('resource_fact_definition_conflict:' + name)
                values[name] = definition
        return values

