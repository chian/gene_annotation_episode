from .operations import LocalResourceOperations
from .report_fields import LocalResourceReportFields
from .report_delivery import LocalResourceReportDelivery
from .reference_access import LocalResourceReferenceAccess
from .to_parent import LocalResourceParentReport
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.resource_binding_records import binding_record
from .task import LocalResourceTask

from .child_commissioning import LocalResourceChildCommissioning
from .from_parent import LocalResourceParentAssignment
from .action_policy import LocalResourceActionPolicy
from .resource_selection import LocalResourceResourceSelection
from .internal_summary import LocalResourceInternalSummary
from .goal import LocalResourceGoal
from .credit import LocalResourceCredit

class LocalResourceBinding(LocalResourceChildCommissioning, LocalResourceParentAssignment, LocalResourceActionPolicy, LocalResourceResourceSelection, LocalResourceInternalSummary, LocalResourceGoal, LocalResourceOperations, LocalResourceReportFields, LocalResourceReportDelivery, LocalResourceReferenceAccess, LocalResourceParentReport, LocalResourceCredit, ResourceCustody):
    roles=('launch_local',)
    entry_roles=()
    binding_path='scientific_process/hpc_coordination/resource_job_submission/local_resource_execution'
    commissioning_parent='scientific_process/hpc_coordination/resource_job_submission'
    decision_source_type=LocalResourceTask
    replaces_default_instructions=True

    def __init__(self, owner):
        from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
        if type(owner) is not ResourceEpisodes:
            raise TypeError('genuine_resource_custody_required')
        self.owner=owner
        self.services=owner.services
        self.adapters=owner.adapters
        self._contract_information_profile=owner._contract_information_profile

    def as_record(self):
        return binding_record(self, 'root_scientific_process_hpc_coordination_resource_job_submission_local_resource_execution', 'scientific_process/hpc_coordination/resource_job_submission/local_resource_execution')
