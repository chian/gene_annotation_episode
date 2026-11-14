"""Private A101 results to parent."""
from __future__ import annotations
from .execution_contracts import HANDOFF_SCHEMA, Mapping, RESOURCE_ROLES, ReportBoundaryError, _array, _nullable, plain, reference_in_context

class OperationalReport:

    def fact_sources(self, role):
        self.credit_kind(role)
        values = {'execution_handoff': {'type': ['object', 'null'], 'meaning': 'The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure.', 'report_schema': {**_nullable(HANDOFF_SCHEMA), 'x-source': 'execution_handoff'}}, 'execution_handoffs': {'type': 'array', 'meaning': 'For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it.', 'report_schema': {**_array(HANDOFF_SCHEMA), 'x-source': 'execution_handoffs'}}}
        for adapter in self.adapters.values():
            for name, definition in adapter.fact_sources('results').items():
                if name in values and values[name] != definition:
                    raise ValueError('resource_fact_definition_conflict:' + name)
                values[name] = definition
        return values

    def facts(self, context, completion_snapshot):
        self.credit_kind(context.role)
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

    def resolve(self, context, reference, namespace):
        if reference_in_context(self.services, context, reference, namespace):
            return True
        if context.role in RESOURCE_ROLES or context.role == 'results':
            return self._adapter(context.assignment).resolve(context, reference, namespace)
        return any((adapter.resolve(context, reference, namespace) for adapter in self.adapters.values()))

    def validate_report(self, context, form, original_schema):
        adapters = self.adapters.values() if context.role == 'launch' else (self._adapter(context.assignment),)
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
