from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)

class ScientificYield:

    def continuation_task(self, context):
        """Name the original scientific task whose own units price continuation."""
        projector = self.credit_projector(context)
        if projector is None:
            raise ContractError('scientific_task_credit_not_declared')
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]['option_id']
        if axis in {'A105', 'A106', 'A108'}:
            return axis + ':whole_axis_findings'
        assigned = plain(context.assignment).get('context', {}).get(axis.lower() + '_task')
        if assigned is not None:
            if not isinstance(assigned, dict) or not isinstance(assigned.get('name'), str) or not assigned['name']:
                raise ContractError('scientific_continuation_original_task_required')
            return axis + ':' + assigned['name']
        return axis + ':' + projector.as_record()['kind']

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned scientific task to its own credit forecast.

        A saved task declaration fixes the estimator, its parameters, the
        continuation cutoff and the exact credit units. An old workflow with
        no private declarations keeps its recorded controller contract.
        """
        if self._yield_bindings is None:
            return None
        if context.role != ROLE:
            raise ContractError('scientific_yield_role_not_bound')
        task = self.continuation_task(context)
        declaration = self._yield_bindings.get(task)
        if declaration is None:
            raise ContractError('scientific_yield_binding_missing_for_task:' + task)
        projector = self.credit_projector(context)
        if scientific_digest(plain(projector.as_record())) != scientific_digest(
                declaration['credit_definition']):
            raise ContractError('scientific_yield_credit_definition_mismatch:' + task)
        if getattr(projector, 'yield_method', None) != declaration['kind']:
            raise ContractError('scientific_yield_method_credit_mismatch:' + task)
        if declaration['kind'] == 'accumulation':
            from gene_annotation_episode.episodic_workflow.root.numerical import YieldController, YieldParameters
            return YieldController(epoch, initial_credit, declaration['cutoff'],
                YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'bounded_quality':
            from gene_annotation_episode.episodic_workflow.root.numerical import BoundedYieldController, YieldParameters
            return BoundedYieldController(epoch, initial_credit, declaration['cutoff'],
                projector.native_score_maximum, YieldParameters(**declaration['parameters']))
        if declaration['kind'] == 'completion':
            from gene_annotation_episode.episodic_workflow.root.numerical import CompletionYieldController, YieldParameters
            return CompletionYieldController(epoch, initial_credit, declaration['cutoff'],
                YieldParameters(**declaration['parameters']))
        raise ContractError('scientific_yield_method_unavailable:' + task)

