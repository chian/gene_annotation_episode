from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

from .goal import ScientificGoal

class ScientificInstructions(ScientificGoal):
    def permitted_common_actions(self, context):
        self.validate_context(context)
        selection = context.assignment['selection']
        if selection[selection_fields(selection)[0]]['option_id'] == 'A104':
            # Native work waits inside the shared operational HPC service.
            # An idle scientific calendar wait cannot make its suspended
            # annotation parent supply a requested sibling investigation.
            return ('tool', 'reason', 'child', 'redeliver_report')
        return ("tool", "reason", "child", "wait", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self.validate_context(parent)
        selection=parent.assignment['selection']
        if selection[selection_fields(selection)[0]]['option_id']=='A103':
            return tuple(role for role in self._child_roles if role in {'scientific_process','literature'})
        if selection[selection_fields(selection)[0]]['option_id']=='A104':
            return tuple(role for role in self._child_roles if role in {'scientific_process', 'hpc'})
        return self._child_roles

