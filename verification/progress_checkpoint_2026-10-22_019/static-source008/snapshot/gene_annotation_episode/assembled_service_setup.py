"""Caller-owned setup of the existing scientific and specialist bindings.

Only immutable library snapshots and reader custody tables are prepared here.
The existing episodes retain their decisions, forms and caller-bound credit.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path

from . import episode_monitoring
from .episode_application_services import EpisodeApplicationServices
from .episode_monitoring import MonitorEpisodes
from .episode_progress_credit import ProgressInformationCredit
from .homology_episodes import HomologyEpisodes
from .homology_progress import HomologyProgressProvider
from .literature_episodes import LiteratureEpisodes
from .resource_estimation import ResourceToolEstimator
from .resource_service_setup import bind_resource_services, bind_public_search_ports
from .scientific_process_setup import prepare_scientific_binding
from .state import Store


@dataclass(frozen=True)
class _SavedProgressReader:
    store: Store
    run_id: str

    def read_progress(self, reference, scope):
        return episode_monitoring.read_progress(self.store, self.run_id, reference, scope)


class _JobProgressRouter:
    """Dispatch explicit native/API owners; retain each original registry."""
    def __init__(self, native, api, *, ports, native_resource_id):
        self.native, self.api = native, api
        self.ports, self.native_resource_id = ports, native_resource_id
        self.store, self.run_id = native.store, native.run_id
        if api.store is not self.store or api.run_id != self.run_id:
            raise ValueError('job_progress_router_identity_conflict')

    def as_record(self):
        return {'version': 'explicit_job_progress_router_v1',
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'providers': [self.native.as_record(), self.api.as_record()]}

    def _owner(self, handle):
        from .domain import ContractError
        if self.native.jobs.resolve(handle, 'homology_job'):
            return self.native
        try:
            self.ports.operations.inspect(handle)
        except ContractError as error:
            if str(error) == 'unknown_job':
                raise ContractError('progress_target_unavailable') from error
            raise
        return self.api

    def scope(self, handle):
        return self._owner(handle).scope(handle)

    def direct_dependencies(self, handle, scope):
        return self._owner(handle).direct_dependencies(handle, scope)

    async def observe(self, handle, requested_fields, scope, *, operation_key=None):
        result = self._owner(handle).observe(handle, requested_fields, scope,
            operation_key=operation_key)
        return await result if inspect.isawaitable(result) else result

    def dependency(self, spec, *, operation_key):
        message = spec['child']['request']['message']
        assignment = message.get('episode_assignment', {})
        selection = (assignment.get('handoff', {}).get('resource_selection')
            if assignment.get('version') == 'resource_results_assignment_v1'
            else assignment.get('resource_selection'))
        if selection is not None:
            resource_id = selection['resource_id']
            if resource_id == self.ports.registry['resource_id']:
                return self.api.dependency(spec, operation_key=operation_key)
            if resource_id == self.native_resource_id:
                return self.native.dependency(spec, operation_key=operation_key)
            return None
        if message.get('job_assignment') is not None:
            return self.native.dependency(spec, operation_key=operation_key)
        return None


def _bind_assembled_services(
    store: Store, *, run_id: str, directory: Path,
    job_episodes: HomologyEpisodes, resource_estimator: ResourceToolEstimator,
    source_directory: Path, tool_catalog: Mapping[str, dict] | list[dict],
    tool_retrieval: dict, scientific_child_roles: tuple[str, ...],
    handoff_unit: float, acquired_record_unit: float,
    monitoring_information_unit: float, literature_outcome_page_size: int,
    monitor_outcome_page_size: int, log_window_bytes: int,
    log_roles: tuple[str, ...],
    public_search_ports=None,
    api_timing=None,
    api_execution_planning=None,
    api_direct_timing=None,
) -> EpisodeApplicationServices:
    """Bind exact caller operands without observing or selecting work.

    The actual Workflow supplies ``tool_catalog`` through its explicit factory
    protocol. Component constructors validate their original units and settings;
    setup supplies no defaults or replacement resource/model configurations.
    """
    if not isinstance(tool_retrieval, dict):
        raise TypeError('explicit_scientific_tool_retrieval_configuration_required')
    scientific = prepare_scientific_binding(run_directory=directory,
        source_directory=source_directory, tool_catalog=tool_catalog,
        child_roles=scientific_child_roles, tool_retrieval=tool_retrieval)
    literature = LiteratureEpisodes(None, outcome_page_size=literature_outcome_page_size)
    monitor = MonitorEpisodes(None, outcome_page_size=monitor_outcome_page_size)
    resource = bind_resource_services(store, run_id=run_id, directory=directory,
        job_episodes=job_episodes, resource_estimator=resource_estimator,
        handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit,
        public_search_ports=public_search_ports, api_timing=api_timing,
        api_execution_planning=api_execution_planning, api_direct_timing=api_direct_timing)
    information = ProgressInformationCredit(_SavedProgressReader(store, run_id),
        information_unit=monitoring_information_unit)
    native_progress = HomologyProgressProvider(store, job_episodes.jobs,
        run_id=run_id, log_window_bytes=log_window_bytes, log_roles=log_roles)
    progress = native_progress
    if public_search_ports is not None:
        from .hmmer_progress import HmmerProgressProvider
        api_progress = HmmerProgressProvider(store, run_id=run_id, ports=public_search_ports)
        native_id = resource.episode_binding_descriptors[0]['configuration']['resource_adapters'][0]['resource_id']
        progress = _JobProgressRouter(native_progress, api_progress,
            ports=public_search_ports, native_resource_id=native_id)
    return EpisodeApplicationServices(
        (scientific, literature.as_record(), *resource.episode_binding_descriptors,
         monitor.as_record()),
        {**resource.role_credit_bindings,
         'monitor': {'definition': information.as_record(), 'project': information}},
        progress)


def bind_assembled_services(
    store: Store, *, run_id: str, directory: Path,
    job_episodes: HomologyEpisodes, resource_estimator: ResourceToolEstimator,
    source_directory: Path, tool_catalog: Mapping[str, dict] | list[dict],
    tool_retrieval: dict, scientific_child_roles: tuple[str, ...],
    handoff_unit: float, acquired_record_unit: float,
    monitoring_information_unit: float, literature_outcome_page_size: int,
    monitor_outcome_page_size: int, log_window_bytes: int,
    log_roles: tuple[str, ...],
) -> EpisodeApplicationServices:
    """Retain the original explicit no-API setup signature and behavior."""
    return _bind_assembled_services(store, run_id=run_id, directory=directory,
        job_episodes=job_episodes, resource_estimator=resource_estimator,
        source_directory=source_directory, tool_catalog=tool_catalog,
        tool_retrieval=tool_retrieval, scientific_child_roles=scientific_child_roles,
        handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit,
        monitoring_information_unit=monitoring_information_unit,
        literature_outcome_page_size=literature_outcome_page_size,
        monitor_outcome_page_size=monitor_outcome_page_size,
        log_window_bytes=log_window_bytes, log_roles=log_roles)


def bind_assembled_services_with_public_search(store: Store, *, tool_registry,
                                              public_search_registry, **operands):
    """Opt in using the actual caller registry and its immutable API binding."""
    ports = bind_public_search_ports(store, tool_registry, registry=public_search_registry)
    return _bind_assembled_services(store, public_search_ports=ports, **operands)


def bind_assembled_services_with_public_search_timing(store: Store, *, tool_registry,
        public_search_registry, api_timing, native_timing_information=None, **operands):
    """Explicit new-order timing binding; all numeric operands remain caller-owned."""
    from .api_timing_records import ApiTimingBinding, ApiTimingLedger
    from .api_reported_statistics import ApiReportedStatistics
    from .native_timing_information import NativeTimingInformation
    timing = api_timing if type(api_timing) is ApiTimingBinding else ApiTimingBinding.from_record(api_timing)
    if operands['monitoring_information_unit'] != timing.monitoring_information_unit:
        raise ValueError('api_timing_information_unit_mismatch')
    if native_timing_information is not None and (type(native_timing_information) is not NativeTimingInformation
            or native_timing_information.information_unit != timing.monitoring_information_unit):
        raise ValueError('api_timing_information_unit_mismatch')
    estimator = operands['resource_estimator']
    if (type(estimator) is not ResourceToolEstimator
            or estimator.as_record() != ResourceToolEstimator.with_reported_results().as_record()):
        raise ValueError('reported_result_estimator_not_enabled')
    statistics = ApiReportedStatistics(timing, registry=public_search_registry)
    ledger = ApiTimingLedger(store=store, run_id=operands['run_id'], registry=public_search_registry,
        binding=timing, statistics=statistics)
    ports = bind_public_search_ports(store, tool_registry, registry=public_search_registry, timing=ledger)
    return _bind_assembled_services(store, public_search_ports=ports, api_timing=ledger, **operands)


def bind_assembled_services_with_public_search_timing_planning(store: Store, *, tool_registry,
        public_search_registry, api_timing, native_timing_information=None, **operands):
    """Explicitly attach the actual API estimate callable before map freezing."""
    from method_loop.durable import DurableExecutionError
    from .api_execution_planning import ApiExecutionPlanner
    from .api_timing_records import ApiTimingBinding, ApiTimingLedger
    from .api_reported_statistics import ApiReportedStatistics
    from .communication import plain
    from .native_timing_information import NativeTimingInformation
    from .scientific_tool_library import _catalog
    # Compare the entire actual preattachment map, including an already attached
    # equal planner on replay. A stale fragment cannot authorize a wider map.
    if _catalog(plain(operands['tool_catalog'])) != _catalog(tool_registry.catalog()):
        raise DurableExecutionError('identity_conflict', affected_refs=['api_execution_planning.tool_catalog'])
    timing = api_timing if type(api_timing) is ApiTimingBinding else ApiTimingBinding.from_record(api_timing)
    if operands['monitoring_information_unit'] != timing.monitoring_information_unit:
        raise ValueError('api_timing_information_unit_mismatch')
    if native_timing_information is not None and (type(native_timing_information) is not NativeTimingInformation
            or native_timing_information.information_unit != timing.monitoring_information_unit):
        raise ValueError('api_timing_information_unit_mismatch')
    estimator = operands['resource_estimator']
    if (type(estimator) is not ResourceToolEstimator
            or estimator.as_record() != ResourceToolEstimator.with_reported_results().as_record()):
        raise ValueError('reported_result_estimator_not_enabled')
    statistics = ApiReportedStatistics(timing, registry=public_search_registry)
    ledger = ApiTimingLedger(store=store, run_id=operands['run_id'], registry=public_search_registry,
        binding=timing, statistics=statistics)
    ports = bind_public_search_ports(store, tool_registry, registry=public_search_registry, timing=ledger)
    planner = ApiExecutionPlanner(store, run_id=operands['run_id'], ports=ports, timing=ledger,
        resource_estimator=estimator)
    tool_registry.bind_api_execution_planner(planner)
    operands = {**operands, 'tool_catalog': tool_registry.catalog()}
    return _bind_assembled_services(store, public_search_ports=ports, api_timing=ledger,
        api_execution_planning=planner, **operands)


def bind_assembled_services_with_public_search_timing_planning_direct(store: Store, *, tool_registry,
        public_search_registry, api_timing, ordinary_hmmer_timing,
        native_timing_information=None, **operands):
    """Bind ordinary acquisition to the same explicit timing owners before freeze."""
    from method_loop.durable import DurableExecutionError
    from .api_execution_planning import ApiExecutionPlanner
    from .api_timing_information import ApiReportedTimingFactReader
    from .api_timing_records import ApiTimingBinding, ApiTimingLedger
    from .api_reported_statistics import ApiReportedStatistics
    from .communication import plain
    from .direct_hmmer_timing import DIRECT_MODE, DirectHmmerTiming
    from .native_timing_information import NativeTimingInformation
    from .scientific_tool_library import _catalog
    if plain(ordinary_hmmer_timing) != DIRECT_MODE:
        raise ValueError('unsupported_ordinary_hmmer_timing_binding')
    if _catalog(plain(operands['tool_catalog'])) != _catalog(tool_registry.catalog()):
        raise DurableExecutionError('identity_conflict', affected_refs=['ordinary_hmmer_timing.tool_catalog'])
    timing = api_timing if type(api_timing) is ApiTimingBinding else ApiTimingBinding.from_record(api_timing)
    if operands['monitoring_information_unit'] != timing.monitoring_information_unit:
        raise ValueError('api_timing_information_unit_mismatch')
    if native_timing_information is not None and (type(native_timing_information) is not NativeTimingInformation
            or native_timing_information.information_unit != timing.monitoring_information_unit):
        raise ValueError('api_timing_information_unit_mismatch')
    estimator = operands['resource_estimator']
    if (type(estimator) is not ResourceToolEstimator
            or estimator.as_record() != ResourceToolEstimator.with_reported_results().as_record()):
        raise ValueError('reported_result_estimator_not_enabled')
    statistics = ApiReportedStatistics(timing, registry=public_search_registry)
    ledger = ApiTimingLedger(store=store, run_id=operands['run_id'], registry=public_search_registry,
        binding=timing, statistics=statistics)
    ports = bind_public_search_ports(store, tool_registry, registry=public_search_registry, timing=ledger)
    planner = ApiExecutionPlanner(store, run_id=operands['run_id'], ports=ports, timing=ledger,
        resource_estimator=estimator)
    tool_registry.bind_api_execution_planner(planner)
    reader = ApiReportedTimingFactReader(ledger, ports=ports)
    direct = DirectHmmerTiming(planner, reader=reader)
    tool_registry.bind_api_direct_hmmer_timing(direct)
    operands = {**operands, 'tool_catalog': tool_registry.catalog()}
    return _bind_assembled_services(store, public_search_ports=ports, api_timing=ledger,
        api_execution_planning=planner, api_direct_timing=direct, **operands)


__all__ = ['bind_assembled_services', 'bind_assembled_services_with_public_search',
           'bind_assembled_services_with_public_search_timing',
           'bind_assembled_services_with_public_search_timing_planning',
           'bind_assembled_services_with_public_search_timing_planning_direct']
