from .operations import ResourceAcquisitionOperations
from .report_fields import ResourceAcquisitionReportFields
from .report_delivery import ResourceAcquisitionReportDelivery
from .reference_access import ResourceAcquisitionReferenceAccess
from .to_parent import ResourceAcquisitionParentReport
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.resource_binding_records import binding_record
from .task import ResourceAcquisitionTask

from .child_commissioning import ResourceAcquisitionChildCommissioning
from .from_parent import ResourceAcquisitionParentAssignment
from .action_policy import ResourceAcquisitionActionPolicy
from .resource_selection import ResourceAcquisitionResourceSelection
from .internal_summary import ResourceAcquisitionInternalSummary
from .goal import ResourceAcquisitionGoal
from .credit import ResourceAcquisitionCredit

class ResourceAcquisitionBinding(ResourceAcquisitionChildCommissioning, ResourceAcquisitionParentAssignment, ResourceAcquisitionActionPolicy, ResourceAcquisitionResourceSelection, ResourceAcquisitionInternalSummary, ResourceAcquisitionGoal, ResourceAcquisitionOperations, ResourceAcquisitionReportFields, ResourceAcquisitionReportDelivery, ResourceAcquisitionReferenceAccess, ResourceAcquisitionParentReport, ResourceAcquisitionCredit, ResourceCustody):
    roles=('results',)
    entry_roles=('results',)
    binding_path='resource_result_acquisition'
    commissioning_parent='annotation'
    decision_source_type=ResourceAcquisitionTask
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
        return binding_record(self, 'root_resource_result_acquisition', 'resource_result_acquisition')
