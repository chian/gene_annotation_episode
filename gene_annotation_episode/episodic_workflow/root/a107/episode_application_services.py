"""Caller-owned specialist setup operands, without work or decision ownership."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from gene_annotation_episode.episodic_workflow.root.a107.method_loop.durable import canonical


VERSION = 'episode_application_services_v1'


@dataclass(frozen=True)
class EpisodeApplicationServices:
    episode_binding_descriptors: list | tuple
    role_credit_bindings: Mapping
    job_progress_provider: object | None = None
    resource_tool_catalogs: Mapping | None = None
    initial_information_configuration: object | None = None
    received_execution_configuration: object | None = None
    received_api_configuration: object | None = None

    def __post_init__(self):
            if not isinstance(self.episode_binding_descriptors, (list, tuple)):
                raise TypeError('episode_service_descriptors_required')
            if not isinstance(self.role_credit_bindings, Mapping):
                raise TypeError('episode_service_role_bindings_required')
            if self.resource_tool_catalogs is not None:
                if not isinstance(self.resource_tool_catalogs, Mapping):
                    raise TypeError('episode_service_resource_tool_catalogs_required')
                # Selection information from actual configured bindings; this is
                # not another executor and does not alter the direct tool map.
                json.loads(canonical(dict(self.resource_tool_catalogs)))
            if self.initial_information_configuration is not None:
                from .library.execution_initial_information.information_configuration import InitialInformationConfiguration
                if type(self.initial_information_configuration) is not InitialInformationConfiguration:
                    raise TypeError('actual_axis_initial_information_configuration_required')
                json.loads(canonical(self.initial_information_configuration.as_record()))
            if self.received_api_configuration is not None:
                from .library.received_api_information.received_api_authority import ReceivedAPIConfiguration
                if type(self.received_api_configuration) is not ReceivedAPIConfiguration:
                    raise TypeError('actual_a107_received_api_configuration_required')
                json.loads(canonical(self.received_api_configuration.as_record()))
            if self.received_execution_configuration is not None:
                from .library.received_execution_information.received_configuration import ReceivedExecutionConfiguration
                if type(self.received_execution_configuration) is not ReceivedExecutionConfiguration:
                    raise TypeError('actual_a107_received_execution_configuration_required')
                json.loads(canonical(self.received_execution_configuration.as_record()))


def service_binding(factory, definition, *, inputs=None):
    """Describe explicit setup, without importing or executing its callable."""
    if inputs is not None and (not isinstance(inputs, str) or inputs not in {
            'actual_tool_catalog_v1', 'actual_tool_registry_v1'}):
        raise ValueError('unsupported_episode_service_inputs')
    if factory is None and definition is None:
        if inputs is not None:
            raise ValueError('episode_service_inputs_requires_factory')
        return None
    if not callable(factory) or not isinstance(definition, Mapping) or not definition:
        raise ValueError('episode_service_factory_and_definition_required')
    descriptor = factory if hasattr(factory, '__qualname__') else type(factory)
    name = f'{descriptor.__module__}.{descriptor.__qualname__}'
    result = {'version': VERSION, 'factory': name,
              'definition': json.loads(canonical(dict(definition)))}
    if inputs is not None:
        result.update(version='episode_application_services_v2', inputs=inputs)
    return result


def job_progress_binding(provider):
    """Describe caller-bound readers without observing a target."""
    if provider is None:
        return None
    if any(not callable(getattr(provider, name, None)) for name in
           ('as_record', 'scope', 'observe', 'direct_dependencies')):
        raise ValueError('reconstructible_job_progress_provider_required')
    value = provider.as_record()
    if not isinstance(value, Mapping) or not value:
        raise ValueError('job_progress_provider_definition_required')
    return json.loads(canonical(dict(value)))


__all__ = ['EpisodeApplicationServices', 'service_binding', 'job_progress_binding', 'VERSION']
