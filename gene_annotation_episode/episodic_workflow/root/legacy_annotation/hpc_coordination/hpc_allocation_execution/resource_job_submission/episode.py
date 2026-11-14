from .operations import ResourceSubmissionOperations
from .report_fields import ResourceSubmissionReportFields
from .report_delivery import ResourceSubmissionReportDelivery
from .reference_access import ResourceSubmissionReferenceAccess
from .to_parent import ResourceSubmissionParentReport
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.resource_binding_records import binding_record
from .task import ResourceSubmissionTask

from .child_commissioning import ResourceSubmissionChildCommissioning
from .from_parent import ResourceSubmissionParentAssignment
from .action_policy import ResourceSubmissionActionPolicy
from .resource_selection import ResourceSubmissionResourceSelection
from .internal_summary import ResourceSubmissionInternalSummary
from .goal import ResourceSubmissionGoal
from .credit import ResourceSubmissionCredit

class ResourceSubmissionBinding(ResourceSubmissionChildCommissioning, ResourceSubmissionParentAssignment, ResourceSubmissionActionPolicy, ResourceSubmissionResourceSelection, ResourceSubmissionInternalSummary, ResourceSubmissionGoal, ResourceSubmissionOperations, ResourceSubmissionReportFields, ResourceSubmissionReportDelivery, ResourceSubmissionReferenceAccess, ResourceSubmissionParentReport, ResourceSubmissionCredit, ResourceCustody):
    roles=('launch',)
    entry_roles = ()
    binding_path='legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission'
    commissioning_parent='legacy_annotation/hpc_coordination/hpc_allocation_execution'
    decision_source_type=ResourceSubmissionTask
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
        return binding_record(self, 'root_legacy_annotation_hpc_coordination_hpc_allocation_execution_resource_job_submission', 'legacy_annotation/hpc_coordination/hpc_allocation_execution/resource_job_submission')

    @staticmethod
    def child_message_exchange(role, *, child_binding=None):
        if role == 'launch_api':
            from .api_resource_execution.episode import APIResourceBinding
            if type(child_binding) is APIResourceBinding:
                from .to_child_api_resource_execution import prepare_request
                from .from_child_api_resource_execution import admit_return
                return prepare_request, admit_return
        if role == 'launch_local':
            from .local_resource_execution.episode import LocalResourceBinding
            if type(child_binding) is LocalResourceBinding:
                from .to_child_local_resource_execution import prepare_request
                from .from_child_local_resource_execution import admit_return
                return prepare_request, admit_return
        if role == 'launch_hpc':
            from .hpc_resource_execution.episode import HPCResourceBinding
            if type(child_binding) is HPCResourceBinding:
                from .to_child_hpc_resource_execution import prepare_request
                from .from_child_hpc_resource_execution import admit_return
                return prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(ResourceSubmissionBinding)["child_message_exchange"]
