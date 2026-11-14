from .operations import APIResourceOperations
from .report_fields import APIResourceReportFields
from .report_delivery import APIResourceReportDelivery
from .reference_access import APIResourceReferenceAccess
from .to_parent import APIResourceParentReport
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.resource_binding_records import binding_record
from .task import APIResourceTask

from .child_commissioning import APIResourceChildCommissioning
from .from_parent import APIResourceParentAssignment
from .action_policy import APIResourceActionPolicy
from .resource_selection import APIResourceResourceSelection
from .internal_summary import APIResourceInternalSummary
from .goal import APIResourceGoal
from .credit import APIResourceCredit

class APIResourceBinding(APIResourceChildCommissioning, APIResourceParentAssignment, APIResourceActionPolicy, APIResourceResourceSelection, APIResourceInternalSummary, APIResourceGoal, APIResourceOperations, APIResourceReportFields, APIResourceReportDelivery, APIResourceReferenceAccess, APIResourceParentReport, APIResourceCredit, ResourceCustody):
    roles=('launch_api',)
    entry_roles=()
    binding_path='resource_job_submission/api_resource_execution'
    commissioning_parent='resource_job_submission'
    decision_source_type=APIResourceTask
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
        return binding_record(self, 'root_resource_job_submission_api_resource_execution', 'resource_job_submission/api_resource_execution')
