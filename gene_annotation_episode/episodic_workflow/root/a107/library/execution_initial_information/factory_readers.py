"""Construct the original factory's read dependencies without creating an episode."""
from pathlib import Path
from copy import deepcopy
from .information_readers import FactoryInformationReaders
from ...communication import plain
from ...execution_service_setup import ExecutionServiceFactory
from ...execution_progress import ExecutionProgressProvider


def construct_factory_information_readers(factory, *, store, run_id, directory, tool_registry, services):
    if type(factory) is not ExecutionServiceFactory:
        raise TypeError('initial_information_actual_axis_factory_required')
    definition = plain(factory.as_record())
    directory = Path(directory)
    resources = deepcopy(definition['resources'])
    initial = deepcopy(definition['initial_information'])
    if not isinstance(initial, dict) or not set(initial) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    from ...api_service_execution import APIServiceExecution
    api_resources = {key: value for key, value in resources.items() if value['kind'] in {'api', 'hmmer_api'}}
    api = None if not api_resources else APIServiceExecution(store,
        run_id=run_id, directory=directory, configuration=api_resources,
        tool_registry=tool_registry, handoff_unit=definition['handoff_unit'],
        acquired_record_unit=definition['acquired_record_unit'],
        received_input_reader=getattr(services, 'read_received_molecular_input', None))
    progress = ExecutionProgressProvider(store, run_id=run_id, directory=directory,
        resources=resources, api_execution=api, log_window_bytes=definition['log_window_bytes'],
        log_roles=definition['log_roles'])
    from .saved_result_information import SavedResultInformationHost
    host = (SavedResultInformationHost(factory, store=store, run_id=run_id, directory=directory,
        job_progress_provider=progress) if any(row.get('native_rna_structure') for row in resources.values()) else None)
    readers = FactoryInformationReaders(factory=factory, store=store, run_id=run_id,
        directory=directory, job_progress_provider=progress,
        api_execution=api,
        native_rna_structure_returns=None if host is None else host.native_rna_structure_returns,
        rna_structure_comparison_returns=None if host is None else host.rna_structure_comparison_returns,
        construction_record={'version': 'factory_information_reader_construction_v1',
            'constructor': 'gene_annotation_episode.episodic_workflow.root.a107.execution_service_setup.ExecutionServiceFactory',
            'factory_definition': definition})
    readers.validate_original_setup(definition)
    return readers
