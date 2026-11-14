"""Bind received resource credit to the caller's actual run and registry."""
from __future__ import annotations

from .episode_application_services import EpisodeApplicationServices
from .episode_journal import Journal
from .homology_resource_adapter import HomologyResourceAdapter
from .resource_episodes import ResourceEpisodes
from .resource_binding_catalogue import resource_bindings, PARENTS, family_entries, saved_family
from gene_annotation_episode.execution_contracts import canonical
from .library.resource_operational_credit import ResourceOperationalCredit


def bind_resource_services(store, *, run_id, directory, job_episodes,
                           resource_estimator, handoff_unit, acquired_record_unit,
                           contract_information_profile=None, episode_binding_descriptors=None,
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
    owner = ResourceEpisodes(None, resource_adapters=(adapter,),
        contract_information_profile=contract_information_profile)
    saved = None if episode_binding_descriptors is None else saved_family(episode_binding_descriptors)
    parents = PARENTS if saved is None else tuple(parent for parent in PARENTS
        if any(row['binding_id'] in {entry[2] for entry in family_entries(parent)} for row in saved))
    bindings = resource_bindings(owner, parents=parents)
    if saved is not None and canonical([binding.as_record() for binding in bindings]) != canonical(list(saved)):
        raise ValueError('root_resource_saved_factory_descriptor_conflict')
    return EpisodeApplicationServices(tuple(binding.as_record() for binding in bindings), {
        role: {'definition': projector.as_record(), 'project': projector}
        for binding in bindings for role in binding.roles
    })


__all__ = ['bind_resource_services']
