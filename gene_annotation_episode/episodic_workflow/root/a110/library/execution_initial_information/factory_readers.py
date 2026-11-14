"""Construct the original factory's read dependencies without creating an episode."""
from pathlib import Path
from copy import deepcopy
from .information_readers import FactoryInformationReaders
from .information_sources import implementation_record
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
    progress = ExecutionProgressProvider(store, run_id=run_id, directory=directory,
        resources=resources, log_window_bytes=definition['log_window_bytes'], log_roles=definition['log_roles'])
    readers = FactoryInformationReaders(factory=factory, store=store, run_id=run_id,
        directory=directory, job_progress_provider=progress,
        construction_record={'version': 'factory_information_reader_construction_v1',
            'constructor': 'gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup.ExecutionServiceFactory',
            'factory_definition': definition}, implementation_record=implementation_record())
    readers.validate_original_setup(definition)
    return readers
