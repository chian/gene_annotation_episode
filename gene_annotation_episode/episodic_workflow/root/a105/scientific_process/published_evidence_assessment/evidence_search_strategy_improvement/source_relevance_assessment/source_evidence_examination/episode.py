"""Private connector for the source-examination goal, task, assessment, progress, and message functions."""
from .configuration import SourceConfiguration
from .source_contracts import ROLES, _CHILDREN
from .from_parent import SourceAssignment
from .goal import SourceGoal
from .task import SourceTask
from .internal_summary import SourceSummary
from .scientific_records import SourceScientificRecords
from .source_references import SourceReferences
from .to_parent import SourceReport
from .received_evidence import ReceivedEvidence
from .credit import SourceCredit
from .waiting import SourceWaiting
from .binding_record import SourceBindingRecord
from importlib import import_module
SourceYield = import_module('.yield', __package__).SourceYield
from .to_child_table_evidence_extraction import to_child as to_table_evidence_extraction
from .from_child_table_evidence_extraction import FromTableEvidenceExtraction
from .to_child_passage_evidence_extraction import to_child as to_passage_evidence_extraction
from .from_child_passage_evidence_extraction import FromPassageEvidenceExtraction
from .to_child_source_coverage_improvement import to_child as to_source_coverage_improvement
from .from_child_source_coverage_improvement import FromSourceCoverageImprovement
from .task import SourceExaminationTask
from .to_child_table_evidence_extraction import prepare_request as prepare_table_evidence_extraction
from .from_child_table_evidence_extraction import receive_report as receive_table_evidence_extraction
from .to_child_source_coverage_improvement import prepare_request as prepare_source_coverage_improvement
from .from_child_source_coverage_improvement import receive_report as receive_source_coverage_improvement
from .to_child_passage_evidence_extraction import prepare_request as prepare_passage_evidence_extraction
from .from_child_passage_evidence_extraction import receive_report as receive_passage_evidence_extraction
from .grading.experimental_interpretation import ExperimentalInterpretation
from .grading.assay_subscoring import AssaySubscoring
from .scoring.experimental_main_sheet import ExperimentalMainSheet

from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.prompts.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(SourceConfiguration, SourceAssignment, SourceGoal, SourceTask, SourceSummary, SourceScientificRecords, SourceReferences, SourceReport, ReceivedEvidence, SourceCredit, SourceWaiting, SourceBindingRecord, SourceYield, FromTableEvidenceExtraction, FromPassageEvidenceExtraction, FromSourceCoverageImprovement, ExperimentalInterpretation, AssaySubscoring, ExperimentalMainSheet):
    decision_source_type = SourceExaminationTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    roles = ('literature_page',)
    entry_roles = ()

    def _enabled(self, option, context=None):
        return option == 'assay_grading_population' and self.assay_grading_population

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role not in ROLES:
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN[role]

    def prepare_child_request(self, parent, role, assignment):
        handlers = {'literature_table': to_table_evidence_extraction, 'literature_targeted': to_passage_evidence_extraction, 'literature_ordered': to_source_coverage_improvement}
        return handlers[role](parent, assignment)

    def receive_child_result(self, context, role, form, schema, operation_key):
        handlers = {'literature_table': self.receive_table_evidence_extraction, 'literature_targeted': self.receive_passage_evidence_extraction, 'literature_ordered': self.receive_source_coverage_improvement}
        return handlers[role](context, form, schema, operation_key)

    def context_hook_applies(self, context):
        """Own local hooks; the literature parent owns external-family delivery hooks."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        family_roles = ('literature', 'literature_strategy', 'literature_search', 'literature_page', 'literature_table', 'literature_ordered', 'literature_targeted')
        return role == 'literature_page' if role in family_roles else 'literature_page' == 'literature'

    def child_request_preparer(self, role):
        return {'literature_table': prepare_table_evidence_extraction, 'literature_ordered': prepare_source_coverage_improvement, 'literature_targeted': prepare_passage_evidence_extraction}.get(role)

    def child_report_receiver(self, role):
        return {'literature_table': receive_table_evidence_extraction, 'literature_ordered': receive_source_coverage_improvement, 'literature_targeted': receive_passage_evidence_extraction}.get(role)
