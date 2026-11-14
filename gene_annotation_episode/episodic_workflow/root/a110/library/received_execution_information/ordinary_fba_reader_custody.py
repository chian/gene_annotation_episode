"""Actual configured ordinary-FBA reader port consumed by this A110 owner.

The record describes supplied dependency custody. It grants no native resource,
interprets no saved scientific value and imports no descriptor-named class.
"""
from copy import deepcopy
import json

from ...communication import plain


def copied(value): return json.loads(json.dumps(plain(value), allow_nan=False))


class OrdinaryFBAReaderCustody:
    def __init__(self, owner):
        self.tools = owner.tool_registry
        self.returns = owner.native_flux_balance_returns
        self.backend = None if self.returns is None else self.returns.ordinary_backend
        # Exactly the constructor's actual operand, including a preconfigured
        # backend preserved by an empty factory environment table.
        if self.backend is not getattr(self.tools, 'ordinary_flux_balance_backend', None):
            raise ValueError('received_execution_original_fba_backend_changed')
        self.registry_present = hasattr(self.backend, 'registry')
        self.registry = getattr(self.backend, 'registry', None)
        self.store_present = hasattr(self.backend, 'store')
        self.store = getattr(self.backend, 'store', None)
        self.original = self._record(owner)

    def _record(self, owner):
        present = hasattr(self.tools, '_flux_balance_configuration')
        return {'version': 'a110_original_ordinary_fba_reader_port_v1',
            'backend_present': self.backend is not None,
            # Descriptive identity only; reconstruction never imports this name.
            'backend_type': None if self.backend is None else {
                'module': type(self.backend).__module__, 'name': type(self.backend).__qualname__},
            'actual_tool_configuration': {'attribute_present': present,
                **({'value': copied(self.tools._flux_balance_configuration)} if present else {})},
            'backend_registry_attribute_present': self.registry_present,
            'backend_registry_is_supplied_tools': self.registry_present and self.registry is self.tools,
            'backend_store_attribute_present': self.store_present,
            'backend_store_is_supplied_store': self.store_present and self.store is owner.store}

    def as_record(self, owner):
        returns = owner.native_flux_balance_returns
        backend = None if returns is None else returns.ordinary_backend
        if (owner.tool_registry is not self.tools or returns is not self.returns
                or backend is not self.backend
                or getattr(self.tools, 'ordinary_flux_balance_backend', None) is not self.backend
                or hasattr(backend, 'registry') != self.registry_present
                or getattr(backend, 'registry', None) is not self.registry
                or hasattr(backend, 'store') != self.store_present
                or getattr(backend, 'store', None) is not self.store):
            raise ValueError('received_execution_original_fba_backend_changed')
        actual = self._record(owner)
        if actual != self.original:
            raise ValueError('received_execution_original_fba_configuration_changed')
        return deepcopy(actual)
