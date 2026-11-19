"""Construction-time configuration of the A102 API job-execution bindings.

``a102_home_factory`` builds each API job-execution binding with its own A102
``ToolRegistry`` over the run's shared store and ``services['a102']['api_job_execution']``:

- ``resources``: ``{resource_id: service configuration}``; each configuration names
  its API ``service`` kind and is validated by A102's own
  ``api_services.validate_service_configuration``. The binding's own API services
  (its tools) are built from these over its registry.
- ``continuation``: ``{'cutoff', 'uncertainty_alpha'}`` of its completion controller.

Nothing is defaulted: a missing or malformed value raises when the binding is
constructed. The only A102 API service is ``ncbi_blast`` (``api_blast.NCBIBlastService``);
any other configured service kind raises.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from gene_annotation_episode.domain import ContractError

_CONFIGURATION = ('resources', 'continuation')
_CONTINUATION = ('cutoff', 'uncertainty_alpha')


def build_api_service(kind, configuration, tool_registry):
    """One of this binding's own API services over its own tool registry; any other kind raises."""
    from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.structural_homology_evidence.api_services import validate_service_configuration
    configuration = validate_service_configuration(kind, dict(configuration))
    if kind == 'ncbi_blast':
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.structural_homology_evidence.api_blast import NCBIBlastService
        return NCBIBlastService(tool_registry, configuration)
    raise ContractError('a102_api_job_service_has_no_a102_primitive:' + kind)


class ApiJobConfiguration:
    """The binding's own API services (its tools) and its completion continuation settings."""

    def __init__(self, *, tool_registry, configuration):
        if not isinstance(configuration, Mapping) or set(configuration) != set(_CONFIGURATION):
            raise ContractError('a102_api_job_configuration_requires_exactly:' + ','.join(_CONFIGURATION))
        resources, continuation = configuration['resources'], configuration['continuation']
        if not isinstance(resources, Mapping) or not resources:
            raise ContractError('a102_api_job_resources_required')
        if not isinstance(continuation, Mapping) or set(continuation) != set(_CONTINUATION):
            raise ContractError('a102_api_job_continuation_requires_exactly:' + ','.join(_CONTINUATION))
        services = {}
        for resource_id, service in resources.items():
            if not isinstance(resource_id, str) or not resource_id or not isinstance(service, Mapping) \
                    or not isinstance(service.get('service'), str):
                raise ContractError('a102_api_job_resource_must_name_its_service:' + str(resource_id))
            services[resource_id] = build_api_service(service['service'], service, tool_registry)
        self.tool_registry = tool_registry
        self.services = MappingProxyType(services)
        self.continuation = MappingProxyType(dict(continuation))
        from .runtime_credit import completion_controller
        completion_controller('configuration', 0.0, self.continuation)  # rejects an unusable cutoff now
