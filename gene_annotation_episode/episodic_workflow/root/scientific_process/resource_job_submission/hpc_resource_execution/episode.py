from .operations import HPCResourceOperations
from .report_fields import HPCResourceReportFields
from .report_delivery import HPCResourceReportDelivery
from .reference_access import HPCResourceReferenceAccess
from .to_parent import HPCResourceParentReport
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.resource_binding_records import binding_record
from .task import HPCResourceTask

from .child_commissioning import HPCResourceChildCommissioning
from .from_parent import HPCResourceParentAssignment
from .action_policy import HPCResourceActionPolicy
from .resource_selection import HPCResourceResourceSelection
from .internal_summary import HPCResourceInternalSummary
from .goal import HPCResourceGoal
from .credit import HPCResourceCredit

class HPCResourceBinding(HPCResourceChildCommissioning, HPCResourceParentAssignment, HPCResourceActionPolicy, HPCResourceResourceSelection, HPCResourceInternalSummary, HPCResourceGoal, HPCResourceOperations, HPCResourceReportFields, HPCResourceReportDelivery, HPCResourceReferenceAccess, HPCResourceParentReport, HPCResourceCredit, ResourceCustody):
    roles=('launch_hpc',)
    entry_roles=()
    binding_path='scientific_process/resource_job_submission/hpc_resource_execution'
    commissioning_parent='scientific_process/resource_job_submission'
    decision_source_type=HPCResourceTask
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
        return binding_record(self, 'root_scientific_process_resource_job_submission_hpc_resource_execution', 'scientific_process/resource_job_submission/hpc_resource_execution')
