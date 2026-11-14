"""Actual supplied FBA backend survives empty original factory environments."""
from copy import deepcopy

import pytest

from .test_receiving_configuration import actual_case
from .general_received_registry_probe import originals
from .original_full_fact_catalog import original_catalog
from ..tools import ToolRegistry
from ..flux_balance_tools import OrdinaryFluxBalanceTools
from ..library.received_execution_information.received_configuration import ReceivedExecutionConfiguration


def configured(case):
    tools = ToolRegistry(case.store)
    backend = OrdinaryFluxBalanceTools(tools)
    tools.ordinary_flux_balance_backend = backend
    assert tools._flux_balance_configuration is None
    # This real original method must preserve an explicitly supplied reader
    # when its declared environment table is empty. No native setup is added.
    case.factory.configure_tool_registry(tools)
    assert tools.ordinary_flux_balance_backend is backend and tools._flux_balance_configuration is None
    original = type(case.original)(case.services, store=case.store, run_id=case.original.run_id,
        directory=case.directory, tool_registry=tools, **case.constructor)
    configuration = ReceivedExecutionConfiguration.original_global_factory(case.factory)
    catalog = configuration.construct(store=case.store, run_id=case.original.run_id,
        directory=case.directory, tool_registry=tools, services=case.services)
    return tools, backend, original, configuration, catalog




@pytest.mark.parametrize('changed', ['tool_backend', 'return_backend', 'backend_registry', 'backend_store', 'configuration'])
def test_actual_backend_or_configuration_cannot_be_silently_replaced(actual_case, changed):
    tools, backend, _, _, catalog = configured(actual_case)
    selected = catalog.setup_for('@annotation')
    reader = selected.check()
    before = deepcopy(selected.as_record())
    if changed == 'tool_backend': tools.ordinary_flux_balance_backend = OrdinaryFluxBalanceTools(tools)
    elif changed == 'return_backend': reader.native_flux_balance_returns.ordinary_backend = OrdinaryFluxBalanceTools(tools)
    elif changed == 'backend_registry': backend.registry = object()
    elif changed == 'backend_store': backend.store = object()
    else: tools._flux_balance_configuration = {'synthetic_invalid_replacement': True}
    with pytest.raises(ValueError, match='received_execution_original_fba_(backend|configuration)_changed'):
        selected.as_record()
    assert before['ordinary_fba_reader']['backend_present'] is True
