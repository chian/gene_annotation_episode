"""Perform the original explicit Resource handoff receiving check."""
from __future__ import annotations
from .resource_contracts import RESULTS_VERSION, _availability_failure, _failure, _outcome, _validate, inspect, obj, sqlite3

class ResourceHandoffCheck:

    async def check_selected_handoff(self, context, arguments, operation_key):
        handoff = arguments['handoff']
        try:
            adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
            callback = getattr(adapter, 'check_handoff', None)
            if callback is None:
                return _outcome(failure=_failure('receiving_interface_unavailable'))
            value = callback(context, handoff, operation_key)
            return await value if inspect.isawaitable(value) else value
        except (ValueError, KeyError, OSError, sqlite3.Error) as error:
            if str(error) == 'resource_information_identity_conflict':
                raise
            return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
