"""Private A103 resource received messages."""
from __future__ import annotations

def _parent_name_ValueError():
    return ValueError

def _parent_name_getattr():
    return getattr

from .resource_contracts import Mapping, RESULTS_VERSION
from .initial_references import ResourceInitialReferences

class ResourceReceivedMessages(ResourceInitialReferences):

    def received_form_references(self, context, form, schema, operation_key):
        references = []

        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else [] if value is None else [value]
                for handoff in values:
                    adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                    receiver = _handoff_receiver(handoff)
                    if receiver is not None:
                        receiver(adapter, context, handoff, operation_key, references)
                    else:
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


def _handoff_receiver(handoff):
    # Select a defining owner only from inert builtin operands. All arbitrary
    # mappings/unknown kinds retain the exact original local callback body.
    if type(handoff) is not dict or any(type(key) is not str for key in handoff):
        return None
    selection = handoff.get('resource_selection')
    if type(selection) is not dict or any(type(key) is not str for key in selection):
        return None
    kind = selection.get('kind')
    if type(kind) is not str:
        return None
    if kind == 'api':
        from .from_child_api_resource_work_execution import receive_handoff
    elif kind == 'local':
        from .from_child_local_resource_work_execution import receive_handoff
    elif kind == 'hpc':
        from .from_child_hpc_resource_work_execution import receive_handoff
    else:
        return None
    return receive_handoff
