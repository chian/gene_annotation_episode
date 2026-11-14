"""Private A102 resource to parent."""
from __future__ import annotations
from .resource_contracts import HANDOFF_SCHEMA, Mapping, ReportBoundaryError, _array, _nullable, plain, reference_in_context

from .report_fields import ResourceReportFields

from .report_reference_access import ResourceReportReferenceAccess

class ResourceToParent(ResourceReportFields, ResourceReportReferenceAccess):

    def facts(self, context, completion_snapshot):
        values = {'execution_handoff': None, 'execution_handoffs': []}
        adapters = [self._adapter(context.assignment)]
        for adapter in adapters:
            facts = adapter.facts(context, completion_snapshot)
            for key, value in facts.items():
                if key == 'execution_handoffs':
                    values[key].extend(value)
                    continue
                if key == 'execution_handoff':
                    continue
                if value is not None:
                    values[key] = value
                else:
                    values.setdefault(key, None)
        identities = {(item['resource_selection']['capability_binding_ref'], item['execution_handle']): item for item in values['execution_handoffs']}
        values['execution_handoffs'] = [identities[key] for key in sorted(identities)]
        values['execution_handoff'] = values['execution_handoffs'][0] if len(identities) == 1 else None
        return values

    def validate_report(self, context, form, original_schema):
        adapters = (self._adapter(context.assignment),)
        for adapter in adapters:
            adapter.validate_report(context, form, original_schema)
        facts = self.facts(context, {})

        def visit(value, schema):
            if schema.get('x-source') in {'execution_handoff', 'execution_handoffs'}:
                if plain(value) != facts[schema['x-source']]:
                    raise ReportBoundaryError('Resource handoff differs from selected recorded check', code='resource_handoff_fact_mismatch')
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in schema.get('properties', {}):
                        visit(child, schema['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in schema:
                for child in value:
                    visit(child, schema['items'])
        visit(form, original_schema)
