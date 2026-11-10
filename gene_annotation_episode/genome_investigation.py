"""Caller setup for an autonomous genome investigation using existing axes.

This supplies services and source provenance. It owns no investigation loop,
function choice, annotation decision or scientific stopping rule.
"""
from dataclasses import dataclass
from pathlib import Path

from .communication import plain


@dataclass(frozen=True)
class GenomeEvidenceServices:
    source_directory: str
    execution_configuration: dict
    tool_retrieval: dict
    literature_configuration: dict
    scientific_yield_bindings: dict | None = None

    def as_record(self):
        return {'version': 'genome_existing_evidence_services_v1',
            'source_directory': self.source_directory,
            'execution_configuration': plain(self.execution_configuration),
            'tool_retrieval': plain(self.tool_retrieval),
            'literature_configuration': plain(self.literature_configuration),
            'scientific_yield_bindings': plain(self.scientific_yield_bindings)}

    def __call__(self, store, *, run_id, directory, tool_catalog, tool_registry,
                 job_episodes=None, resource_estimator=None):
        from .a102_structural_catalog import prepare_catalog
        from .literature_episodes import LiteratureEpisodes
        from .composition_information import CONTRACT_INFORMATION_PROFILE
        from .episode_application_services import EpisodeApplicationServices
        from .execution_service_setup import ExecutionServiceFactory
        from .scientific_process_setup import prepare_scientific_binding

        execution_settings = plain(self.execution_configuration)
        if execution_settings.get('monitor_yield_settings') is None:
            raise ValueError('combined_monitor_yield_binding_required')
        if execution_settings.get('require_private_execution_yield', True) is not True:
            raise ValueError('combined_execution_private_yield_binding_required')
        execution_settings['require_private_execution_yield'] = True
        if execution_settings.get('hpc_commissions') is not None:
            if execution_settings.get('require_hpc_commission_yield', True) is not True:
                raise ValueError('combined_hpc_private_yield_binding_required')
            execution_settings['require_hpc_commission_yield'] = True
        factory = ExecutionServiceFactory(**execution_settings)
        tool_registry.configure_blast_execution(factory.resources)
        tool_registry.configure_a102_hpc(factory.resources)
        tool_registry.configure_a103_hpc(factory.resources)
        tool_registry.configure_component_native_hpc(factory.resources)
        execution = factory(store, run_id=run_id, directory=directory,
            tool_catalog=tool_registry.catalog(), tool_registry=tool_registry,
            job_episodes=job_episodes, resource_estimator=resource_estimator)
        source = Path(self.source_directory)
        if not (Path(directory) / 'scientific-process-library/index.json').is_file():
            source = prepare_catalog(source, Path(directory) / 'genome-evidence-catalog')
        roles = ['scientific_process', 'literature']
        for descriptor in execution.episode_binding_descriptors:
            # Actual factory descriptors own their published roles.
            roles.extend(descriptor.get('roles', ()))
        # Execution descriptors encode their roles in versioned configuration;
        # use their existing public declarations rather than infer work.
        from .execution_episodes import ExecutionEpisodes
        from .episode_monitoring import MonitorEpisodes
        from .hpc_episodes import HPCEpisodes
        roles.extend((*ExecutionEpisodes.entry_roles, *MonitorEpisodes.entry_roles,
                      *HPCEpisodes.entry_roles))
        science = prepare_scientific_binding(run_directory=directory,
            source_directory=source, tool_catalog=tool_registry.catalog(),
            child_roles=tuple(dict.fromkeys(roles)), tool_retrieval=plain(self.tool_retrieval),
            resource_catalogs=execution.resource_tool_catalogs,
            yield_bindings=plain(self.scientific_yield_bindings),
            contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        literature_settings = plain(self.literature_configuration)
        literature_settings['private_yield_binding'] = True
        literature = LiteratureEpisodes(None, axis_scoped_profiles=True,
            contract_information_profile=CONTRACT_INFORMATION_PROFILE,
            **literature_settings).as_record()
        return EpisodeApplicationServices((science, literature, *execution.episode_binding_descriptors),
            execution.role_credit_bindings, execution.job_progress_provider,
            resource_tool_catalogs=execution.resource_tool_catalogs)
