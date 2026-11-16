from __future__ import annotations
from .source_contracts import (Mapping, deepcopy, hashlib, inspect, json, Path, re, ReportBoundaryError, interpretation_schema, plain, validate_closed_schema, validate_form, ContractError, identity, obj, validate_schema, reference_in_context, scientific_digest, scientific_invocation_ref, validate_child_selection, validate_filled_process, validate_option_ref, validate_revision_origin, validate_selection, selection_fields, selector_selection, SELECTION_VERSION, build_process_result, merge_process_results, report_sources, validate_process_result, support_observation_kinds, EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry, INSTRUCTION_VERSION, instruction_view, validate_instruction_entry, evidence_axis_instruction_view, alignment_site_fact_sources, requested_site_projections, project_site_action_return, validate_frozen_site_return, restriction_mapping_fact_sources, requested_restriction_projections, project_restriction_action_return, validate_frozen_restriction_return, molecular_fact_sources, merge_molecular_facts, requested_molecular_fact_sources, requested_molecular_fact_fields, validate_frozen_molecular_return, PROTEIN_ACTION_FACT_SOURCES, protein_structure_action_fact_sources, merge_protein_structure_action_facts, requested_protein_structure_action_fields, validate_frozen_protein_structure_action_return, VERSION, ROLE, ROLES, _COMMON_TOOLS, _REFERENCE, _SHA256, _SCIENTIFIC_NAMESPACES, _ITC_PARAMETER_SOURCE, _EVIDENCE_AXIS, _THOUGHT_REF, _TOOL_SELECTOR, _TOOL_INFO, _SELECTION, _CANONICAL_SELECTION, _REVISION_ORIGIN, _EVIDENCE_TASK, _ASSIGNMENT, _RECORDED_ASSIGNMENT, _REVISION_ARGUMENTS, original_axis_task_projector, _object, _ref_schema)


class ScientificToParent:

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.scientific_process.report_generation import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)
        def project(value):
            return project_process_result(value, library=self.library,
                tool_library=self.tool_library)
        facts = {"scientific_process_results": merge_process_results(
            None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        from gene_annotation_episode.episodic_workflow.root.library.component_native_received_records import FACT_SOURCE as NATIVE_COMPONENTS, EXECUTION_SOURCE as NATIVE_EXECUTION, received_components, execution_findings as native_execution_findings
        axis = context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id')
        for source, reader in ((NATIVE_COMPONENTS, received_components), (NATIVE_EXECUTION, native_execution_findings)):
            if any(node.get('x-source') == source for node in schema.get('properties', {}).values()):
                workflow = getattr(self.services, 'workflow', None)
                if workflow is None:
                    raise ContractError('component_native_report_store_required')
                facts[source] = [row['source_ref'] for row in reader(workflow.store,
                    context.received_record_refs, context.scope, axis=axis if axis in {'A107', 'A110'} else None)]
        from gene_annotation_episode.episodic_workflow.root.a107.a107_qualification import FACT_SOURCE as PARTNER_QUALIFICATIONS, received_qualifications
        from gene_annotation_episode.episodic_workflow.root.a110.a110_qualification import FACT_SOURCE as CHEMICAL_QUALIFICATIONS, received as chemical_qualifications
        if any(node.get('x-source') == CHEMICAL_QUALIFICATIONS for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a110_qualification_report_store_required')
            facts[CHEMICAL_QUALIFICATIONS] = [row['source_ref'] for row in chemical_qualifications(
                workflow.store, context.received_record_refs, context.scope)]
        if any(node.get('x-source') == PARTNER_QUALIFICATIONS for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a107_qualification_report_store_required')
            facts[PARTNER_QUALIFICATIONS] = [row['source_ref'] for row in received_qualifications(
                workflow.store, context.received_record_refs, context.scope)]
        from gene_annotation_episode.episodic_workflow.root.a107.a107_qualification import EXECUTION_SOURCE as PARTNER_EXECUTION, execution_findings as partner_execution_findings
        if any(node.get('x-source') == PARTNER_EXECUTION for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a107_genomic_execution_report_store_required')
            facts[PARTNER_EXECUTION] = [row['source_ref'] for row in partner_execution_findings(
                workflow.store, context, set(context.received_record_refs))]
        from gene_annotation_episode.episodic_workflow.root.a103.a103_investigation import CONTEXT_RECORD_SOURCE,received_context_records
        if any(node.get('x-source')==CONTEXT_RECORD_SOURCE for node in schema.get('properties',{}).values()):
            workflow=getattr(self.services,'workflow',None)
            if workflow is None:raise ContractError('a103_report_store_required')
            facts[CONTEXT_RECORD_SOURCE]=received_context_records(workflow.store,
                context.received_record_refs,plain(context.scope),
                committed=completion_snapshot.get('committed_record_refs',()))
        from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import RECORD_SOURCE as EVOLUTIONARY_RECORD_SOURCE, received_records as received_evolutionary_records
        if any(node.get('x-source') == EVOLUTIONARY_RECORD_SOURCE for node in schema.get('properties', {}).values()):
            workflow = getattr(self.services, 'workflow', None)
            if workflow is None:
                raise ContractError('a104_report_store_required')
            facts[EVOLUTIONARY_RECORD_SOURCE] = received_evolutionary_records(workflow.store,
                context.received_record_refs, plain(context.scope),
                committed=completion_snapshot.get('committed_record_refs', ()))
        for source, requested in requested_site_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.alignment_site_own_action_results(context,
                    source=source, selection=requested['selection'],
                    after_decision_index=cursor, limit=64)
                facts[source].extend(project_site_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source, requested in requested_restriction_projections(schema).items():
            facts[source], cursor = [], None
            while True:
                page = self.services.restriction_mapping_own_action_results(context,
                    selection=requested['selection'], after_decision_index=cursor, limit=64)
                facts[source].extend(project_restriction_action_return(record, requested['fields'])
                    for record in page['records'])
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source in requested_molecular_fact_sources(schema):
            facts[source] = merge_molecular_facts(
                self.services.molecular_received_facts(context, fact_source=source),
                self.services.molecular_own_facts(context, fact_source=source), fact_source=source)
        for source in PROTEIN_ACTION_FACT_SOURCES:
            if requested_protein_structure_action_fields(schema, fact_source=source):
                facts[source] = merge_protein_structure_action_facts(
                    self.services.protein_structure_action_received_facts(context, fact_source=source),
                    self.services.protein_structure_action_own_facts(context, fact_source=source),
                    fact_source=source)
        facts.update(self._component_scoring_facts(context))
        return facts

    def _component_scoring_facts(self, context):
        from .current_scoring_sheets import current_scoring_sheets
        from gene_annotation_episode.episodic_workflow.root.library.component_received_reports import SCORING_FACT
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        sheets = current_scoring_sheets(workflow.store, context=context, services=self.services)
        return {SCORING_FACT: sheets} if sheets else {}

    def current_report_facts(self, context):
        return self._component_scoring_facts(context)

