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
from .resource_estimation import ResourceToolEstimator
from .scientific_process_setup import prepare_scientific_binding
from .state import Store
from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.execution_job_submission.episode import ExecutionEpisode
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_submission.episode import HomologyEpisode as AnnotationSubmission
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_monitoring.episode import HomologyEpisode as AnnotationMonitoring
from gene_annotation_episode.episodic_workflow.root.a103.homology_result_acquisition.episode import HomologyEpisode as AnnotationAcquisition
from .legacy_improvement.homology_job_submission.episode import HomologyEpisode as ImprovementSubmission
from .legacy_improvement.homology_job_monitoring.episode import HomologyEpisode as ImprovementMonitoring
from .legacy_improvement.homology_result_acquisition.episode import HomologyEpisode as ImprovementAcquisition
from .homology_progress import HomologyProgressProvider
from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.hpc_work_planning.episode import HPCEpisode
from .scientific_process.published_evidence_assessment.episode import create_binding_tree
from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.execution_progress_assessment.episode import MonitorEpisode
from .resource_service_setup import bind_resource_services
from .scientific_process.episode import ScientificProcessEpisode


@dataclass(frozen=True)
class _SavedProgressReader:
    store: Store
    run_id: str

    def read_progress(self, reference, scope):
        return episode_monitoring.read_progress(self.store, self.run_id, reference, scope)


def bind_assembled_services(
    store: Store, *, run_id: str, directory: Path,
    job_episodes: AnnotationSubmission | AnnotationMonitoring | AnnotationAcquisition | ImprovementSubmission | ImprovementMonitoring | ImprovementAcquisition, resource_estimator: ResourceToolEstimator,
    source_directory: Path, tool_catalog: Mapping[str, dict] | list[dict],
    tool_retrieval: dict, scientific_child_roles: tuple[str, ...],
    handoff_unit: float, acquired_record_unit: float,
    monitoring_information_unit: float, literature_outcome_page_size: int,
    monitor_outcome_page_size: int, log_window_bytes: int,
    log_roles: tuple[str, ...],
    execution_resources: dict | None = None,
    initial_execution_information: dict | None = None,
    tool_registry=None,
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
    literature_settings = {} if literature_configuration is None else dict(literature_configuration)
    literature = create_binding_tree(None,
        outcome_page_size=literature_outcome_page_size, **literature_settings)
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
            hpc_commissions=hpc_commissions, shared_execution_memory=shared_execution_memory)
        if hpc_commissions is not None and 'hpc' not in scientific_child_roles:
            scientific_child_roles = (*scientific_child_roles, 'hpc')
        execution = factory(store, run_id=run_id, directory=directory,
            execution_factory=create_execution_bindings, monitor_type=MonitorEpisode,
            hpc_factory=create_hpc_bindings,
            job_episodes=job_episodes, resource_estimator=resource_estimator,
            tool_registry=tool_registry, tool_catalog=tool_catalog)
        scientific = prepare_scientific_binding(episode_type=ScientificProcessEpisode,
            run_directory=directory,
            source_directory=source_directory, tool_catalog=tool_catalog,
            child_roles=scientific_child_roles, tool_retrieval=tool_retrieval,
            resource_catalogs=execution.resource_tool_catalogs,
            **({'contract_information_profile': scientific_contract_information_profile}
               if scientific_contract_information_profile is not None else {}))
        return EpisodeApplicationServices(
            (scientific, *(binding.as_record() for binding in literature), *execution.episode_binding_descriptors),
            execution.role_credit_bindings, execution.job_progress_provider,
            resource_tool_catalogs=execution.resource_tool_catalogs)
    if hpc_commissions is not None:
        raise ValueError('hpc_commissions_require_execution_resources')
    scientific = prepare_scientific_binding(episode_type=ScientificProcessEpisode,
        run_directory=directory,
        source_directory=source_directory, tool_catalog=tool_catalog,
        child_roles=scientific_child_roles, tool_retrieval=tool_retrieval,
        **({'contract_information_profile': scientific_contract_information_profile}
           if scientific_contract_information_profile is not None else {}))
    monitor = MonitorEpisode(None, outcome_page_size=monitor_outcome_page_size)
    resource = bind_resource_services(store, run_id=run_id, directory=directory,
        job_episodes=job_episodes, resource_estimator=resource_estimator,
        handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit,
        **({'contract_information_profile': scientific_contract_information_profile}
           if scientific_contract_information_profile is not None else {}))
    information = monitor.information_credit(_SavedProgressReader(store, run_id),
        information_unit=monitoring_information_unit)
    native_progress = HomologyProgressProvider(store, job_episodes.jobs,
        run_id=run_id, log_window_bytes=log_window_bytes, log_roles=log_roles)
    return EpisodeApplicationServices(
        (scientific, *(binding.as_record() for binding in literature), *resource.episode_binding_descriptors,
         monitor.as_record()),
        {**resource.role_credit_bindings,
         'monitor': {'definition': information.as_record(), 'project': information}},
        native_progress)


__all__ = ['bind_assembled_services']

from .scientific_process.episode import create_execution_bindings, create_hpc_bindings
