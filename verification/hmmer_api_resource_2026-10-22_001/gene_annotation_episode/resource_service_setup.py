"""Bind received resource credit to the caller's actual run and registry."""
from __future__ import annotations

from .episode_application_services import EpisodeApplicationServices
from .episode_journal import Journal
from .resource_episodes import HomologyResourceAdapter, ResourceEpisodes
from .resource_operational_credit import ResourceOperationalCredit


def bind_public_search_ports(store, tool_registry, *, registry):
    """Bind the explicit registry to actual clients/importers without HTTP."""
    from method_loop.durable import DurableExecutionError
    from .public_search_operations import (ProviderJobOperations, PublicSearchPorts,
        hmmer_client_binding_sha256)
    from .public_search_publication import PublicSearchResultPublisher
    from .communication import plain
    try:
        descriptor = plain(registry)
        remote = tool_registry.remote_searches
        if getattr(tool_registry, 'store', None) is not store or remote.store is not store:
            raise DurableExecutionError('identity_conflict', affected_refs=['public_search.store'])
        if hmmer_client_binding_sha256(remote.clients) != descriptor['client_binding_sha256']:
            raise DurableExecutionError('identity_conflict', affected_refs=['public_search.client'])
        operations = ProviderJobOperations(store, remote, registry=descriptor)
        publisher = PublicSearchResultPublisher(store, tool_registry, operations=operations)
        return PublicSearchPorts(registry=descriptor, operations=operations,
            result_publisher=publisher)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise DurableExecutionError('unavailable_binding', affected_refs=['public_search']) from error


def bind_resource_services(store, *, run_id, directory, job_episodes,
                           resource_estimator, handoff_unit, acquired_record_unit,
                           public_search_ports=None,
                           ) -> EpisodeApplicationServices:
    """Prepare resource descriptors and projections without observing work.

    Units are explicit caller operands. The caller merges this value with its
    other services and enables ``episode_record_receipts`` with an explicit
    initial reference list. This helper neither installs that runtime mode nor
    supplies a progress provider.

    ``directory`` accepts the standard episode-service factory signature; the
    supplied ``job_episodes`` already owns the exact registry and its directory.
    Construction uses configuration and the shared Store journal only. Actual
    capability observations remain the Workflow composer's responsibility.
    """
    journal = Journal(store, run_id)
    adapter = HomologyResourceAdapter(job_episodes, store, journal, resource_estimator)
    projector = ResourceOperationalCredit(adapter.information,
        handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit)
    adapters = (adapter,)
    if public_search_ports is not None:
        from .hmmer_resource_adapter import HmmerServiceResourceAdapter
        from .api_resource_credit import ApiSearchOperationalCredit, ResourceCreditDispatch
        api_adapter = HmmerServiceResourceAdapter(None, store, journal, ports=public_search_ports)
        api_projector = ApiSearchOperationalCredit(api_adapter.information,
            handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit)
        projector = ResourceCreditDispatch(native_projector=projector,
            api_projector=api_projector, native_resource_id=adapter.resource_id,
            api_resource_id=api_adapter.resource_id)
        adapters = (*adapters, api_adapter)
    binding = ResourceEpisodes(None, resource_adapters=adapters)
    return EpisodeApplicationServices((binding.as_record(),), {
        role: {'definition': projector.as_record(), 'project': projector}
        for role in binding.roles
    })


__all__ = ['bind_resource_services', 'bind_public_search_ports']
