from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

from .policy import ScientificPolicy

from .from_parent import ScientificFromParent

class ScientificAssignments(ScientificFromParent, ScientificPolicy):
    def assignment_schema(self, role):
        self._role(role)
        return deepcopy(_ASSIGNMENT)

    def child_assignment_schema(self, parent, role):
        schema = self.assignment_schema(role)
        required = getattr(self.services, 'annotation_task_required', lambda: False)()
        if required:
            schema['required'].append('proposed_annotation_ref')
        schema['allOf'] = [{'if': {'properties': {'selection': {'properties': {
            'evidence_axis': {'properties': {'option_id': {'const': axis}}, 'required': ['option_id']}},
            'required': ['evidence_axis']}}, 'required': ['selection']},
            'then': {'required': ['proposed_annotation_ref'], 'properties': {'context': {
                'required': ['evidence_task'], 'properties': {'evidence_task': {
                    'properties': {'evidence_axis': {'const': axis}}}}}}}}
            for axis in ('A105', 'A106', 'A108')]
        return schema

    def _selection(self, value):
        selection = validate_selection(value)
        fields = selection_fields(selection)
        for key in fields[:2]:
            reference = selection[key]
            if reference["library_id"] != self._library_record["library_id"]:
                raise ContractError("scientific_selection_library_mismatch")
            # Resolution checks the selected body's identity, not merely its ID.
            entry = self.library.resolve(reference)
            if key == fields[0]:
                if entry.get('entry_version') == INSTRUCTION_VERSION:
                    validate_instruction_entry(entry)
                elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                    validate_evidence_axis_entry(entry)
                elif entry.get("entry_version") != SUPPORT_ENTRY_VERSION:
                    raise ContractError("scientific_support_metadata_required")
                else:
                    validate_support_entry(entry)
        self.tool_library.resolve_tool_info(selection['child_tool_info'])
        return selection

    def _assignment(self, value, scope, *, materialize=False, context=None):
        assignment = _object(value, "scientific_assignment_invalid")
        if context is not None and (materialize
                or assignment != plain(context.assignment) or plain(scope) != plain(context.scope)):
            raise ContractError('scientific_filled_identity_mismatch')
        if (materialize and isinstance(assignment.get('selection'), dict)
                and assignment['selection'].get('version') == SELECTION_VERSION):
            # Descriptions and resource-specific instructions are host facts.
            # The model chooses only the exact name/resource identity pair.
            selected = assignment['selection']
            selected['child_tool_info'] = self.tool_library.resolve_tool_info(
                selected.get('child_tool_info'), self._information_catalog(scope))
        validate_schema(assignment, _RECORDED_ASSIGNMENT)
        proposed = assignment.get('proposed_annotation_ref')
        if proposed is not None and not self.services.reference_in_scope(proposed, scope, 'hypothesis'):
            raise ContractError('proposed_annotation_outside_assigned_scope')
        assignment["selection"] = self._selection(assignment["selection"])
        if "revision_origin" in assignment:
            assignment["revision_origin"] = validate_revision_origin(assignment["revision_origin"])
        for reference in assignment["evidence_refs"]:
            if (not re.fullmatch(_REFERENCE["pattern"], reference)
                    or not self.services.reference_in_scope(reference, scope, None)):
                raise ContractError("scientific_evidence_reference_unavailable", detail={
                    "reference": reference})
        # Construction must bind actual current callables before publishing a
        # child or computing its initial credit. Recovery repeats the same
        # comparison, never substituting another operation for a stale name.
        self._tool_resolution_for(assignment['selection'], scope, context=context)
        return assignment

    def _validate_origin(self, context, assignment, *, owner):
        origin = validate_revision_origin(assignment["revision_origin"])
        preparation = _object(self.services.scientific_preparation(context,
            origin["preparation_operation_ref"], owner=owner),
            "scientific_revision_preparation_invalid")
        if set(preparation) != {"operation_ref", "owner_invocation_ref", "owner_selection",
                "arguments", "proposal", "revision_origin"}:
            raise ContractError("scientific_revision_preparation_invalid")
        initial = self._selection(preparation["owner_selection"])
        arguments = _object(preparation["arguments"], "scientific_revision_preparation_invalid")
        proposal = validate_child_selection(preparation["proposal"])
        validate_schema(arguments, _REVISION_ARGUMENTS)
        prepared_origin = validate_revision_origin(preparation["revision_origin"])
        expected_path = context.path if owner == "self" else context.path[:-1]
        expected_owner = scientific_invocation_ref(context.run_id, expected_path)
        if (preparation["operation_ref"] != origin["preparation_operation_ref"]
                or preparation["owner_invocation_ref"] != expected_owner
                or origin["parent_invocation_ref"] != expected_owner
                or prepared_origin != origin
                or proposal["parent_selection_sha256"] != scientific_digest(initial)
                or proposal["selection"] != assignment["selection"]
                or proposal["selection"] != self._proposed_selection(initial, arguments,
                    proposal['selection']['version'], context.scope)):
            raise ContractError("scientific_revision_preparation_mismatch")

