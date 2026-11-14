"""Connect this original private A102 literature_page investigation."""
from __future__ import annotations
from .source_contracts import CONTRACT_INFORMATION_PROFILE, ROLES, plain
from .configuration import SourceConfiguration
from .binding_record import SourceBindingRecord
from .goal import SourceGoal
from .from_parent import SourceFromParent
from .source_operations import SourceSourceOperations
from .source_interpretation import SourceSourceInterpretation
from .structural_sheet_operations import SourceStructuralSheetOperations
from .source_references import SourceSourceReferences
from .internal_summary import SourceInternalSummary
from .to_parent import SourceToParent
from .received_evidence import SourceReceivedEvidence
from .credit import SourceCredit
from .waiting import SourceWaiting
from .child_commissioning import SourceChildCommissioning
from importlib import import_module as _import_module
SourceYield = _import_module('.yield', __package__).SourceYield
from .task import SourceTask
from .decision_presentation import present_source_decision
from .from_child_table_evidence_extraction import receive_report as receive_table_evidence_extraction
from .from_child_source_coverage_improvement import receive_report as receive_source_coverage_improvement
from .from_child_passage_evidence_extraction import receive_report as receive_passage_evidence_extraction
from .to_child_table_evidence_extraction import assemble_request as assemble_table_evidence_extraction
from .to_child_source_coverage_improvement import assemble_request as assemble_source_coverage_improvement
from .to_child_passage_evidence_extraction import assemble_request as assemble_passage_evidence_extraction

class LiteratureEpisode(SourceConfiguration, SourceBindingRecord, SourceGoal, SourceFromParent, SourceSourceOperations, SourceSourceInterpretation, SourceStructuralSheetOperations, SourceSourceReferences, SourceInternalSummary, SourceToParent, SourceReceivedEvidence, SourceCredit, SourceYield, SourceWaiting, SourceChildCommissioning):
    decision_source_type = SourceTask
    decision_prompt_renderer = staticmethod(present_source_decision)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_page',)
    entry_roles = ()

    def __init__(self, services, *, outcome_page_size=8, structure_population=False, reference_parent_sources=None, contract_information_profile=None, private_yield_binding=False, yield_bindings=None):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError('positive_literature_outcome_page_size_required')
        if type(structure_population) is not bool:
            raise ValueError('boolean_structure_population_binding_required')
        if type(private_yield_binding) is not bool:
            raise ValueError('boolean_private_literature_yield_binding_required')
        if yield_bindings is not None and (not private_yield_binding):
            raise ValueError('literature_yield_bindings_require_private_binding')
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import validate_yield_bindings
        self._yield_bindings = validate_yield_bindings({} if yield_bindings is None else plain(yield_bindings))
        self.services = services
        self.outcome_page_size = outcome_page_size
        self.structure_population = structure_population
        self.private_yield_binding = private_yield_binding
        if contract_information_profile is not None and (contract_information_profile != CONTRACT_INFORMATION_PROFILE or not structure_population):
            raise ValueError('unsupported_literature_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        if reference_parent_sources is not None:
            if not structure_population or not isinstance(reference_parent_sources, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in reference_parent_sources)) or (len(set(reference_parent_sources)) != len(reference_parent_sources)):
                raise ValueError('explicit_unique_reference_parent_sources_required')
            reference_parent_sources = tuple(reference_parent_sources)
        self.reference_parent_sources = reference_parent_sources

    @classmethod
    def reference_evidence(cls, services, *, source_refs, contract_information_profile=CONTRACT_INFORMATION_PROFILE, **configuration):
        """Construct a fresh caller-assigned reference-source investigation.

        This explicit entry point defaults to existing on-demand contract
        information. The caller supplies its protocol, model and controller;
        no source is read or scientific action selected here. Explicit None
        retains the existing expanded presentation. The ordinary constructor
        and saved-descriptor reconstruction keep their original defaults.
        """
        configuration.setdefault('structure_population', True)
        return cls(services, reference_parent_sources=source_refs, contract_information_profile=contract_information_profile, **configuration)

    @staticmethod
    def _role(role):
        if role != 'literature_page':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'reason', 'child', 'redeliver_report')

    def child_report_receiver(self, role):
        if role == 'literature_table':
            return receive_table_evidence_extraction
        if role == 'literature_ordered':
            return receive_source_coverage_improvement
        if role == 'literature_targeted':
            return receive_passage_evidence_extraction
        return None

    def child_request_assembler(self, role):
        if role == 'literature_table':
            return assemble_table_evidence_extraction
        if role == 'literature_ordered':
            return assemble_source_coverage_improvement
        if role == 'literature_targeted':
            return assemble_passage_evidence_extraction
        return None
