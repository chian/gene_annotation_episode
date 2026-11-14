"""Own the original returned api handoff proof callback."""

def receive_handoff(adapter, context, handoff, operation_key, references):
    callback = _get_getattr()(adapter, 'received_form_references', None)
    if callback is None:
        raise _get_ValueError()('resource_information_handoff_proof_missing')
    references.extend(callback(context, handoff, {'x-source': 'execution_handoff'}, operation_key))

from .received_messages import (_parent_name_getattr as _get_getattr,
                                _parent_name_ValueError as _get_ValueError)
