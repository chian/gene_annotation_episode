"""Private A105 scientific commissioning episode and its responsibility connections."""
from __future__ import annotations
from .scientific_contracts import ROLE, ROLES
from gene_annotation_episode.domain import ContractError
from .configuration import ScientificConfiguration
from .binding_record import ScientificBindingRecord
from .from_parent import ScientificAssignment
from .invocation_state import ScientificInvocationState
from .goal import ScientificGoal
from .scientific_operations import ScientificOperations
from .library_operations import ScientificLibraryOperations
from .library_services import ScientificLibraryServices
from .internal_summary import ScientificSummary
from .to_parent import ScientificReport
from .source_references import ScientificReferences
from .credit import ExperimentalActivityEvidenceCredit
from importlib import import_module
from .yield_estimator import ExperimentalActivityEvidenceYield
from .task import ScientificTask
from .to_child_experimental_activity_evidence import prepare_request as prepare_experimental_activity_evidence
from .from_child_experimental_activity_evidence import receive_report as receive_experimental_activity_evidence
from .to_child_published_evidence_assessment import prepare_request as prepare_published_evidence_assessment
from .from_child_published_evidence_assessment import receive_report as receive_published_evidence_assessment

class ExperimentalActivityEvidenceEpisode(ScientificLibraryServices, ScientificLibraryOperations, ScientificConfiguration, ScientificBindingRecord, ScientificAssignment, ScientificInvocationState, ScientificGoal, ScientificOperations, ScientificSummary, ScientificReport, ScientificReferences, ExperimentalActivityEvidenceCredit, ExperimentalActivityEvidenceYield):
    decision_source_type = ScientificTask
    'One recursive C7 role with parent-selected A/P and actual tool assignment data.'
    binding_path = 'experimental_activity_evidence'
    commissioning_parent = 'legacy_annotation'
    roles = ROLES
    entry_roles = ROLES

    def contract_information_profile(self, context):
        """Expose frozen contract information to scientific commissioning parents."""
        return self._contract_information_profile if context.role in ('annotation', ROLE) else None

    @staticmethod
    def _role(role):
        if role != ROLE:
            raise ContractError('experimental_activity_evidence_role_not_bound')

    def child_roles(self, role):
        self._role(role)
        return self._child_roles

    def permitted_common_actions(self, context):
        self.validate_context(context)
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        return self._child_roles

    def child_request_preparer(self, role):
        return {'experimental_activity_evidence': prepare_experimental_activity_evidence, 'literature': prepare_published_evidence_assessment}.get(role)

    def child_report_receiver(self, role):
        return {'experimental_activity_evidence': receive_experimental_activity_evidence, 'literature': receive_published_evidence_assessment}.get(role)
