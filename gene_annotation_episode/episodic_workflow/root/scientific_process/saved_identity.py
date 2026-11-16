from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificSavedIdentity:
    def restore_closed_process(self, context) -> dict | None:
        """Return the recorded scientific process of an exact closed request."""
        self._role(context.role)
        read_closed = getattr(self.services, 'scientific_closed_request', None)
        if not callable(read_closed):
            return None
        original = read_closed(context)
        if original is None:
            return None
        original = _object(original, 'scientific_closed_request_invalid')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_closed_request_invalid') from error
        current = self.as_record()
        if saved['mechanics_binding'] != current or filled['mechanics_binding'] != current:
            raise ContractError('scientific_filled_identity_mismatch')
        if (candidate != original
                or plain(context.scope) != original['message'].get('scope')
                or plain(context.assignment) != original['message'].get('episode_assignment')):
            raise ContractError('scientific_filled_identity_mismatch')
        return saved

    def restore_saved_process(self, context, *, original_request, active_only=True) -> dict | None:
        """Project an approved repair onto the exact saved journal request.

        Workflow supplies its existing active row before its unchanged full
        request comparison. Inspection can also finish an authenticated yielded
        request's first form. New commissions keep the current implementation.
        """
        from gene_annotation_episode.episodic_workflow.root.episode_composition import scientific_binding_compatible
        self._role(context.role)
        original = _object(original_request, 'scientific_saved_request_invalid')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        recorded = read_saved(context, active_only=active_only) if callable(read_saved) else None
        if recorded is None:
            return None
        if scientific_digest(recorded) != scientific_digest(original):
            raise ContractError('scientific_saved_request_mismatch')
        candidate = _object(context.request, 'scientific_filled_request_required')
        try:
            saved = validate_filled_process(original['message']['scientific_process'])
            filled = validate_filled_process(candidate['message']['scientific_process'])
            current = self.as_record()
            if not scientific_binding_compatible(current, saved['mechanics_binding']):
                return None
            if scientific_digest(filled['mechanics_binding']) not in {
                    scientific_digest(current), scientific_digest(saved['mechanics_binding'])}:
                raise ContractError('scientific_saved_identity_mismatch')
            candidate['message']['scientific_process']['mechanics_binding'] = deepcopy(saved['mechanics_binding'])
            if (scientific_digest(candidate) != scientific_digest(original)
                    or scientific_digest(plain(context.scope)) != scientific_digest(original['message']['scope'])
                    or scientific_digest(plain(context.assignment)) != scientific_digest(
                        original['message']['episode_assignment'])):
                raise ContractError('scientific_saved_identity_mismatch')
        except (KeyError, TypeError) as error:
            raise ContractError('scientific_saved_request_invalid') from error
        return saved

    def validate_context(self, context):
        self._role(context.role)
        request = _object(context.request, "scientific_filled_request_required")
        try:
            message = request["message"]
            filled = validate_filled_process(message["scientific_process"])
            contract = request["report_contract"]
            original = self._invocation({"objective": request["goal"]["objective"],
                "purpose": contract["decision"],
                "report_schema": contract["measurements"]["schema"],
                "initial_report": message["initial_report"]}, message["scope"])
            assignment = self._assignment(context.assignment, context.scope, context=context)
        except (KeyError, TypeError) as error:
            raise ContractError("scientific_filled_request_required") from error
        if (assignment != message.get("episode_assignment")
                or plain(context.scope) != message["scope"]
                or message.get("scientific_invocation_ref") != scientific_invocation_ref(
                    context.run_id, context.path)
                or filled["selection"] != assignment["selection"]
                or filled["assignment_sha256"] != scientific_digest(assignment)
                or filled["invocation_sha256"] != scientific_digest(original)):
            raise ContractError("scientific_filled_identity_mismatch")
        if scientific_digest(self.as_record()) != scientific_digest(filled['mechanics_binding']):
            read_saved = getattr(self.services, 'scientific_saved_request', None)
            recorded = read_saved(context, active_only=False) if callable(read_saved) else None
            restored = (self.restore_saved_process(context, original_request=recorded, active_only=False)
                        if recorded is not None else None)
            if restored != filled and self.restore_closed_process(context) != filled:
                raise ContractError("scientific_filled_identity_mismatch")
        if "revision_origin" in assignment:
            self._validate_origin(context, assignment, owner="parent")

    def validate_execution_context(self, context) -> None:
        """Historical closure permits inspection/replay, never new dispatch."""
        from gene_annotation_episode.episodic_workflow.root.episode_composition import scientific_binding_compatible
        self.validate_context(context)
        current = self.as_record()
        filled = plain(context.request['message']['scientific_process']['mechanics_binding'])
        if (self.restore_closed_process(context) is not None
                or not scientific_binding_compatible(current, filled)):
            raise ContractError('scientific_execution_identity_mismatch')
        read_saved = getattr(self.services, 'scientific_saved_request', None)
        active = read_saved(context) if callable(read_saved) else None
        if active is None and callable(read_saved) and read_saved(context, active_only=False) is not None:
            raise ContractError('scientific_execution_identity_mismatch')
        if scientific_digest(current) != scientific_digest(filled):
            if active is None:
                raise ContractError('scientific_execution_identity_mismatch')

    def _original_selection(self, context):
        self.validate_context(context)
        return validate_selection(context.assignment["selection"])

