"""Connect the private A106 literature responsibilities."""
from __future__ import annotations
from .task import LiteratureTask
from .source_contracts import ROLES, _CHILDREN, deepcopy
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
from .yield_estimator import LiteratureYield
from .to_child_evidence_search_strategy_improvement import prepare_request as prepare_evidence_search_strategy_improvement
from .from_child_evidence_search_strategy_improvement import receive_report as receive_evidence_search_strategy_improvement
from .grading.intervention_assessment import InterventionAssessment
from .scoring.intervention_main_sheet import InterventionMainSheet

from .to_child_execution_job_submission import prepare_commission as prepare_execution_job_submission
from .from_child_execution_job_submission import receive_report as receive_execution_job_submission
from .to_child_execution_result_acquisition import prepare_commission as prepare_execution_result_acquisition
from .from_child_execution_result_acquisition import receive_report as receive_execution_result_acquisition

from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureGoal, LiteratureAssignment, LiteratureOperations, LiteratureSummary, LiteratureScientificRecords, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, InterventionAssessment, InterventionMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'scientific_process/published_evidence_assessment'
    commissioning_parent = 'scientific_process'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature',)
    entry_roles = ('literature',)
    _SOURCE_REPOSITORIES = {'amount': 'LiteratureAmountRepository', 'assay': 'LiteratureAssayRepository', 'binding_interaction': 'LiteratureBindingInteractionRepository', 'binding_model': 'LiteratureBindingModelRepository', 'binding': 'LiteratureBindingRepository', 'calibration_recovery': 'LiteratureCalibrationRecoveryRepository', 'controlled_response': 'LiteratureControlledResponseRepository', 'figure': 'LiteratureFigureRepository', 'gel': 'LiteratureGelRepository', 'kinetic': 'LiteratureKineticRepository', 'optical': 'LiteratureOpticalRepository', 'perturbation': 'LiteraturePerturbationRepository', 'quantity': 'LiteratureQuantityRepository', 'rate_observation': 'LiteratureRateObservationRepository', 'rate_replicate': 'LiteratureRateReplicateRepository', 'rate': 'LiteratureRateRepository', 'ratio': 'LiteratureRatioRepository', 'ratio_source': 'LiteratureRatioSourceRepository', 'transport': 'LiteratureTransportRepository'}

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        if role == 'literature':
            from .to_child_execution_job_submission import analysis_children
            return (*_CHILDREN[role], *analysis_children(self.services, owner=self, context=context))
        return _CHILDREN[role]

    def context_hook_applies(self, context):
        """This private owner handles its hooks; the A106 parent receives external sheets."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'literature' if role in ROLES else 'literature' == 'literature'

    def child_request_preparer(self, role):
        return {'literature_strategy': prepare_evidence_search_strategy_improvement}.get(role)

    def child_report_receiver(self, role):
        return {'literature_strategy': receive_evidence_search_strategy_improvement}.get(role)

    def child_request_preparer_for_binding(self, role, binding_path):
        return {('launch', 'scientific_process/published_evidence_assessment/execution_job_submission'): prepare_execution_job_submission, ('results', 'scientific_process/published_evidence_assessment/execution_result_acquisition'): prepare_execution_result_acquisition}.get((role, binding_path))

    def child_report_receiver_for_binding(self, role, binding_path):
        return {('launch', 'scientific_process/published_evidence_assessment/execution_job_submission'): receive_execution_job_submission, ('results', 'scientific_process/published_evidence_assessment/execution_result_acquisition'): receive_execution_result_acquisition}.get((role, binding_path))

def create_binding_tree(services, **configuration):
    """Assemble the original caller configuration as seven private bindings."""
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Child1
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Child2
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Child3
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Child4
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Child5
    from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Child6
    return tuple((binding(services, **deepcopy(configuration)) for binding in (LiteratureEpisode, Child1, Child2, Child3, Child4, Child5, Child6)))


def create_execution_bindings(*args, **configuration):
    """Construct this Literature parent's original configured analysis children."""
    from .execution_job_submission.episode import ExecutionEpisode as Private0
    from .execution_job_submission.api_job_execution.episode import ExecutionEpisode as Private1
    from .execution_result_acquisition.episode import ExecutionEpisode as Private2
    return (Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))
