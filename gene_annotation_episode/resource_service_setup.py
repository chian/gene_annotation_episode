"""Bind received resource credit to the caller's actual run and registry."""
from __future__ import annotations

from .episode_application_services import EpisodeApplicationServices
from .episode_journal import Journal
from .resource_episodes import HomologyResourceAdapter, ResourceEpisodes
from .resource_operational_credit import ResourceOperationalCredit


def bind_resource_services(store, *, run_id, directory, job_episodes,
                           resource_estimator, handoff_unit, acquired_record_unit,
                           contract_information_profile=None,
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
    binding = ResourceEpisodes(None, resource_adapters=(adapter,),
        contract_information_profile=contract_information_profile)
    return EpisodeApplicationServices((binding.as_record(),), {
        role: {'definition': projector.as_record(), 'project': projector}
        for role in binding.roles
    })


__all__ = ['bind_resource_services']
