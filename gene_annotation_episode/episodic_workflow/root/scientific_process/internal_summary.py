from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, LEGACY_SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, SUPPORT_ENTRY_VERSION, support_observation_kinds, validate_support_entry, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _IMPLEMENTATION_FILES, _ITC_PARAMETER_SOURCE, _ANNOTATION_REF, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOLS, _LEGACY_SELECTION, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, _LEGACY_REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)



class ScientificInternalSummary:

    def initial_decision_context(self, context):
        """Present admitted scientific outputs through the existing fresh-call hook."""
        from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_evidence import is_merged_entry
        from gene_annotation_episode.episodic_workflow.root.a102.a102_structural_report import received_reports
        if context.role not in {'annotation', ROLE}:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        result = self._component_scoring_facts(context)
        if workflow is not None and (context.role == 'annotation' or context.assignment.get(
                'selection', {}).get('evidence_axis', {}).get('option_id') in {'A107', 'A110'}):
            from .received_component_reports import received_reports as component_reports
            from gene_annotation_episode.episodic_workflow.root.library.component_received_reports import mark_native_execution
            reports = component_reports(workflow.store, context=context, services=self.services)
            if reports:
                result['received_partner_and_chemical_evidence'] = reports
            from gene_annotation_episode.episodic_workflow.root.library.component_native_received_records import received_components, execution_findings as native_execution_findings
            axis_id = context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id')
            selected_axis = axis_id if context.role == ROLE else None
            native = received_components(workflow.store, context.received_record_refs, context.scope, axis=selected_axis)
            execution = native_execution_findings(workflow.store, context.received_record_refs, context.scope, axis=selected_axis)
            if native or execution:
                execution = mark_native_execution(execution, native)
                result['received_partner_and_chemical_native_components'] = {
                    'scientific_results': native, 'execution_findings': execution}
                from .prepared_execution_summary import prepared_assignments
                prepared = prepared_assignments(workflow.store, context=context,
                    execution_findings=execution,
                    resources=getattr(workflow.tools, 'component_native_resources', None))
                if prepared is not None:
                    result['received_partner_and_chemical_native_components']['prepared_hpc_assignments'] = prepared
            from gene_annotation_episode.episodic_workflow.root.a107.a107_qualification import received_qualifications
            from gene_annotation_episode.episodic_workflow.root.a110.a110_qualification import received as chemical_qualifications
            qualifications = {}
            for selected, reader in (('A107', received_qualifications), ('A110', chemical_qualifications)):
                if context.role == 'annotation' or selected_axis == selected:
                    rows = reader(workflow.store, context.received_record_refs, context.scope)
                    if rows:
                        qualifications[selected] = rows
            if qualifications:
                result['received_partner_and_chemical_qualifications'] = qualifications
        if (workflow is not None and getattr(workflow.tools,'a103_execution_resources',None) is not None
                and (context.role=='annotation' or context.assignment.get('selection',{}).get('evidence_axis',{}).get('option_id') in {'A103','A107'})):
            from gene_annotation_episode.episodic_workflow.root.a103.a103_hpc import execution_findings
            result['received_gene_context_execution'] = execution_findings(workflow.store,context,set(context.received_record_refs))
        axis = next((row['option_ref'] for row in self.library.headers()
            if row['option_ref']['option_id'] == 'A102'), None)
        if axis is None or not is_merged_entry(self.library.resolve(axis)):
            return result
        if workflow is None:
            raise ContractError('a102_report_store_required')
        result['received_structural_evidence'] = received_reports(workflow.store,
            context=context, structure_repository=self.services.literature_structure_repository(),
            axis_reference=axis)
        return result

