from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, LEGACY_SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _IMPLEMENTATION_FILES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOLS, _LEGACY_SELECTION, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, _LEGACY_REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

from .report_fields import ScientificReportFields

from .to_parent import ScientificToParent

from .internal_summary import ScientificInternalSummary

class ScientificFacts(ScientificInternalSummary, ScientificToParent, ScientificReportFields):
    def received_report_sources(self, role):
        # Scientific roles declare their own source above; the registry rejects
        # duplicate own/received names. Annotation has no such specialist map.
        return {**molecular_fact_sources(), **protein_structure_action_fact_sources()} if role == 'annotation' else {}

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        contract = plain(context.request).get('report_contract')
        schema = {} if contract is None else contract.get('measurements', {}).get('schema', {})
        facts = {source: merge_molecular_facts(
            self.services.molecular_received_facts(context, fact_source=source), fact_source=source)
            for source in requested_molecular_fact_sources(schema)}
        for source in PROTEIN_ACTION_FACT_SOURCES:
            if requested_protein_structure_action_fields(schema, fact_source=source):
                facts[source] = merge_protein_structure_action_facts(
                    self.services.protein_structure_action_received_facts(context, fact_source=source),
                    fact_source=source)
        facts.update(self._component_scoring_facts(context))
        return facts

