"""Caller-owned setup of the existing scientific and specialist bindings.

Only immutable library snapshots and reader custody tables are prepared here.
The existing episodes retain their decisions, forms and caller-bound credit.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import episode_monitoring
from .episode_application_services import EpisodeApplicationServices
from .episode_monitoring import MonitorEpisodes
from .episode_progress_credit import ProgressInformationCredit
from .homology_episodes import HomologyEpisodes
from .homology_progress import HomologyProgressProvider
from .literature_episodes import LiteratureEpisodes
from .resource_estimation import ResourceToolEstimator
from .resource_service_setup import bind_resource_services
from .scientific_process_setup import prepare_scientific_binding
from .state import Store


@dataclass(frozen=True)
class _SavedProgressReader:
    store: Store
    run_id: str

    def read_progress(self, reference, scope):
        return episode_monitoring.read_progress(self.store, self.run_id, reference, scope)


def bind_assembled_services(
    store: Store, *, run_id: str, directory: Path,
    job_episodes: HomologyEpisodes, resource_estimator: ResourceToolEstimator,
    source_directory: Path, tool_catalog: Mapping[str, dict] | list[dict],
    tool_retrieval: dict, scientific_child_roles: tuple[str, ...],
    handoff_unit: float, acquired_record_unit: float,
    monitoring_information_unit: float, literature_outcome_page_size: int,
    monitor_outcome_page_size: int, log_window_bytes: int,
    log_roles: tuple[str, ...],
    execution_resources: dict | None = None,
    initial_execution_information: dict | None = None,
    tool_registry=None,
    protein_structure_environments=(),
    flux_balance_environments=(),
    scientific_contract_information_profile=None,
    literature_configuration=None,
    hpc_commissions=None,
    shared_execution_memory=None,
) -> EpisodeApplicationServices:
    """Bind exact caller operands without observing or selecting work.

    The actual Workflow supplies ``tool_catalog`` through its explicit factory
    protocol. Component constructors validate their original units and settings;
    setup supplies no defaults or replacement resource/model configurations.
    """
    if not isinstance(tool_retrieval, dict):
        raise TypeError('explicit_scientific_tool_retrieval_configuration_required')
    literature = LiteratureEpisodes(None, outcome_page_size=literature_outcome_page_size,
        **({} if literature_configuration is None else literature_configuration))
    if execution_resources is not None:
        if initial_execution_information is None:
            raise ValueError('explicit_initial_execution_information_required')
        from .execution_service_setup import ExecutionServiceFactory
        from .execution_memory import ExecutionMemory
        if shared_execution_memory is None:
            shared_execution_memory = ExecutionMemory.configured().as_record()
        factory = ExecutionServiceFactory(execution_resources,
            initial_execution_information, handoff_unit, acquired_record_unit,
            monitoring_information_unit, log_window_bytes, tuple(log_roles),
            monitor_outcome_page_size,
            protein_structure_environments=protein_structure_environments,
            flux_balance_environments=flux_balance_environments,
            hpc_commissions=hpc_commissions, shared_execution_memory=shared_execution_memory)
        if hpc_commissions is not None and 'hpc' not in scientific_child_roles:
            scientific_child_roles = (*scientific_child_roles, 'hpc')
        if factory.protein_structure_environments or factory.flux_balance_environments:
            factory.configure_tool_registry(tool_registry)
            tool_catalog = tool_registry.catalog()
        execution = factory(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator,
            tool_registry=tool_registry, tool_catalog=tool_catalog)
        scientific = prepare_scientific_binding(run_directory=directory,
            source_directory=source_directory, tool_catalog=tool_catalog,
            child_roles=scientific_child_roles, tool_retrieval=tool_retrieval,
            resource_catalogs=execution.resource_tool_catalogs,
            **({'contract_information_profile': scientific_contract_information_profile}
               if scientific_contract_information_profile is not None else {}))
        return EpisodeApplicationServices(
            (scientific, literature.as_record(), *execution.episode_binding_descriptors),
            execution.role_credit_bindings, execution.job_progress_provider,
            resource_tool_catalogs=execution.resource_tool_catalogs)
    if hpc_commissions is not None:
        raise ValueError('hpc_commissions_require_execution_resources')
    scientific = prepare_scientific_binding(run_directory=directory,
        source_directory=source_directory, tool_catalog=tool_catalog,
        child_roles=scientific_child_roles, tool_retrieval=tool_retrieval,
        **({'contract_information_profile': scientific_contract_information_profile}
           if scientific_contract_information_profile is not None else {}))
    monitor = MonitorEpisodes(None, outcome_page_size=monitor_outcome_page_size)
    resource = bind_resource_services(store, run_id=run_id, directory=directory,
        job_episodes=job_episodes, resource_estimator=resource_estimator,
        handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit,
        **({'contract_information_profile': scientific_contract_information_profile}
           if scientific_contract_information_profile is not None else {}))
    information = ProgressInformationCredit(_SavedProgressReader(store, run_id),
        information_unit=monitoring_information_unit)
    native_progress = HomologyProgressProvider(store, job_episodes.jobs,
        run_id=run_id, log_window_bytes=log_window_bytes, log_roles=log_roles)
    return EpisodeApplicationServices(
        (scientific, literature.as_record(), *resource.episode_binding_descriptors,
         monitor.as_record()),
        {**resource.role_credit_bindings,
         'monitor': {'definition': information.as_record(), 'project': information}},
        native_progress)


__all__ = ['bind_assembled_services']
