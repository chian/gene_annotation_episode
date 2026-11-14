"""Connect the private A106 literature_table responsibilities."""
from __future__ import annotations
from .task import LiteratureTask
from .source_contracts import ROLES, _CHILDREN
from .configuration import LiteratureConfiguration
from .binding_record import LiteratureBindingRecord
from .goal import LiteratureGoal
from .from_parent import LiteratureAssignment
from .source_operations import LiteratureOperations
from .internal_summary import LiteratureSummary
from .scientific_records import LiteratureScientificRecords
from .source_references import LiteratureReferences
from .to_parent import LiteratureReport
from .received_evidence import LiteratureReceivedEvidence
from .credit import LiteratureCredit
from .waiting import LiteratureWaiting
from importlib import import_module
LiteratureYield = import_module('.yield', __package__).LiteratureYield
from .from_parent_page import OriginalPageAssignment
from .grading.intervention_assessment import InterventionAssessment
from .scoring.intervention_main_sheet import InterventionMainSheet

from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(OriginalPageAssignment, LiteratureConfiguration, LiteratureBindingRecord, LiteratureGoal, LiteratureAssignment, LiteratureOperations, LiteratureSummary, LiteratureScientificRecords, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, InterventionAssessment, InterventionMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_table',)
    entry_roles = ()
    _SOURCE_REPOSITORIES = {'amount': 'LiteratureAmountRepository', 'assay': 'LiteratureAssayRepository', 'binding_interaction': 'LiteratureBindingInteractionRepository', 'binding_model': 'LiteratureBindingModelRepository', 'binding': 'LiteratureBindingRepository', 'calibration_recovery': 'LiteratureCalibrationRecoveryRepository', 'controlled_response': 'LiteratureControlledResponseRepository', 'figure': 'LiteratureFigureRepository', 'gel': 'LiteratureGelRepository', 'kinetic': 'LiteratureKineticRepository', 'optical': 'LiteratureOpticalRepository', 'perturbation': 'LiteraturePerturbationRepository', 'quantity': 'LiteratureQuantityRepository', 'rate_observation': 'LiteratureRateObservationRepository', 'rate_replicate': 'LiteratureRateReplicateRepository', 'rate': 'LiteratureRateRepository', 'ratio': 'LiteratureRatioRepository', 'ratio_source': 'LiteratureRatioSourceRepository', 'transport': 'LiteratureTransportRepository'}

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature_table':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN[role]

    def context_hook_applies(self, context):
        """This private owner handles its hooks; the A106 parent receives external sheets."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'literature_table' if role in ROLES else 'literature_table' == 'literature'
