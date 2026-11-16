from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

from importlib import import_module as _private_yield_import
ScientificYield = _private_yield_import(__package__ + '.yield_estimator').ScientificYield

class ScientificCredit(ScientificYield):
    def credit_projector(self, context):
        """Axis-owned deterministic numerical dispatch, never a model choice."""
        if context.role != ROLE:
            return None
        if (getattr(self, '_yield_bindings', None) is not None
                and not context.assignment.get('proposed_annotation_ref')):
            raise ContractError('scientific_task_proposed_annotation_required')
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]
        if axis['option_id'] in {'A105', 'A106', 'A108'} and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            if not context.assignment.get('proposed_annotation_ref'):
                raise ContractError('axis_finding_task_requires_proposed_annotation')
            return original_axis_task_projector(axis['option_id'], context.assignment)
        if axis['option_id'] == 'A101' and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            return original_axis_task_projector('A101', context.assignment)
        if axis['option_id'] == 'A102' and self.library.resolve(axis).get('entry_version') in {
                INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION}:
            from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_evidence import is_merged_entry, credit_projector
            if is_merged_entry(self.library.resolve(axis)):
                return original_axis_task_projector('A102', context.assignment, merged_a102=True)
            return original_axis_task_projector('A102', context.assignment)
        if axis['option_id'] == 'A103' and self.library.resolve(axis).get('entry_version') in {
                'evidence_axis_instruction_v1'}:
            return original_axis_task_projector('A103', context.assignment)
        if axis['option_id'] == 'A104' and self.library.resolve(axis).get('entry_version') in {'evidence_axis_instruction_v1'}:
            return original_axis_task_projector('A104', context.assignment)
        if axis['option_id'] in {'A107', 'A110'} and self.library.resolve(axis).get('entry_version') == INSTRUCTION_VERSION:
            return original_axis_task_projector(axis['option_id'], context.assignment)
        return None

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        return self.services.scientific_credit(context, receiver_selection)

