"""Bind received resource credit to the caller's actual run and registry."""
from __future__ import annotations

from .episode_application_services import EpisodeApplicationServices
from .episode_journal import Journal
from .episodic_workflow.root.a101.resource_work_submission.episode import ResourceEpisode as ResourceSubmission
from .episodic_workflow.root.a101.resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as APIResourceExecution
from .episodic_workflow.root.a101.resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as LocalResourceExecution
from .episodic_workflow.root.a101.resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as HPCResourceExecution
from .episodic_workflow.root.a101.resource_result_acquisition.episode import ResourceEpisode as ResourceAcquisition
from .episodic_workflow.root.a101.a101_homology_resource_adapter import HomologyResourceAdapter
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
    bindings = tuple(binding_type(None, resource_adapters=(adapter,),
        contract_information_profile=contract_information_profile)
        for binding_type in (ResourceSubmission, APIResourceExecution,
            LocalResourceExecution, HPCResourceExecution, ResourceAcquisition))
    return EpisodeApplicationServices(tuple(binding.as_record() for binding in bindings), {
        role: {'definition': projector.as_record(), 'project': projector}
        for binding in bindings for role in binding.roles
    })


__all__ = ['bind_resource_services']
