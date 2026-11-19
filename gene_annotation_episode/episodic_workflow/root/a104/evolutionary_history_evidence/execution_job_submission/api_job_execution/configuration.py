"""Construction-time configuration of the A104 API job-execution bindings.

``runtime_bindings.a104_home`` builds each API job-execution binding (role ``launch_api``)
with its own A104 ``ToolRegistry`` over the run's shared store and
``services['a104']['api_job_execution']``:

- ``resources``: ``{resource_id: service configuration}``; each configuration names its
  API ``service`` kind; A104's own ``api_services.build_service`` validates it and builds
  that service (one of the binding's own tools) over its registry.
- ``continuation``: ``{'cutoff', 'uncertainty_alpha'}`` of its completion controller.

Nothing is defaulted: a missing or malformed value raises when the binding is
constructed, and so does a service kind ``api_services`` does not build
(``api_service_unknown``). A ``bvbrc_appservice`` resource runs its jobs through
``appservice_source``; every other service kind through ``runtime_source``.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from gene_annotation_episode.domain import ContractError

_CONFIGURATION = ('resources', 'continuation')
_CONTINUATION = ('cutoff', 'uncertainty_alpha')


def build_api_service(kind, configuration, tool_registry):
    """One of this binding's own API services over its own tool registry."""
    from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.evolutionary_history_evidence.api_services import build_service
    return build_service(kind, dict(configuration), tool_registry)


class ApiJobConfiguration:
    """The binding's own API services (its tools) and its completion continuation settings."""

    def __init__(self, *, tool_registry, configuration):
        if not isinstance(configuration, Mapping) or set(configuration) != set(_CONFIGURATION):
            raise ContractError('a104_api_job_configuration_requires_exactly:' + ','.join(_CONFIGURATION))
        resources, continuation = configuration['resources'], configuration['continuation']
        if not isinstance(resources, Mapping) or not resources:
            raise ContractError('a104_api_job_resources_required')
        if not isinstance(continuation, Mapping) or set(continuation) != set(_CONTINUATION):
            raise ContractError('a104_api_job_continuation_requires_exactly:' + ','.join(_CONTINUATION))
        services = {}
        for resource_id, service in resources.items():
            if not isinstance(resource_id, str) or not resource_id or not isinstance(service, Mapping) \
                    or not isinstance(service.get('service'), str):
                raise ContractError('a104_api_job_resource_must_name_its_service:' + str(resource_id))
            services[resource_id] = build_api_service(service['service'], service, tool_registry)
        self.tool_registry = tool_registry
        self.services = MappingProxyType(services)
        self.continuation = MappingProxyType(dict(continuation))
        from .runtime_credit import completion_controller
        completion_controller('configuration', 0.0, self.continuation)  # rejects an unusable cutoff now
