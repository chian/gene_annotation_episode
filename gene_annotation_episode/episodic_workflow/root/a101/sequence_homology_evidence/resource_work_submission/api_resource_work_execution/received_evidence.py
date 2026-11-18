"""Private A101 launch_api received evidence."""
from __future__ import annotations
from .execution_contracts import Mapping, RESULTS_VERSION

class ReceivedOperationalEvidence:

    def received_form_references(self, context, form, schema, operation_key):
        references = []

        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else [] if value is None else [value]
                for handoff in values:
                    adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                    callback = getattr(adapter, 'received_form_references', None)
                    if callback is None:
                        raise ValueError('resource_information_handoff_proof_missing')
                    references.extend(callback(context, handoff, {'x-source': 'execution_handoff'}, operation_key))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))
