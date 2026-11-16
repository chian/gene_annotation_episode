from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificBindingRecord:
    def as_record(self):
        from .definition_inputs import (DEFINITION_FILES, OPTIONAL_WORK_REPORT_FILES,
            INFORMATION_PROFILE_FILES)
        root = Path(__file__).parents[4]
        files = DEFINITION_FILES
        # Preserve the original optional report and information-profile branches.
        files = (*files, *(name for name in OPTIONAL_WORK_REPORT_FILES
            if (root / name).is_file()))
        if self._contract_information_profile is not None:
            files = (*files, *INFORMATION_PROFILE_FILES)
        implementation = scientific_digest({name: hashlib.sha256(
            (root / name).read_bytes()).hexdigest()
            for name in files})
        return {"version": VERSION, "binding_id": ROLE,
            "implementation_sha256": implementation, "configuration": {
                "library": deepcopy(self._library_record),
                "tool_library": deepcopy(self._tools_record),
                "child_roles": list(self._child_roles),
                **({"tool_retrieval": deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}),
                **({'contract_information_profile': self._contract_information_profile}
                   if self._contract_information_profile is not None else {}),
                **({'yield_bindings': deepcopy(self._yield_bindings)}
                   if self._yield_bindings is not None else {})}}

