"""Private A107 scientific internal_summary."""
from __future__ import annotations
from .scientific_assignment_contracts import AXIS, EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, ROLE, SELECTION_VERSION, deepcopy, evidence_axis_instruction_view, instruction_view, plain, scientific_digest, selection_fields, selector_selection, support_observation_kinds
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError

def received_qualification_context(context, workflow, selected_axis):
    """A107 received qualifications for root presentation, if in scope."""
    if context.role != 'annotation' and selected_axis != 'A107':
        return {}
    from gene_annotation_episode.episodic_workflow.root.a107.a107_qualification import received_qualifications
    rows = received_qualifications(workflow.store, context.received_record_refs, context.scope)
    return {'A107': rows} if rows else {}

class ScientificInternalSummary:

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in selection_fields(selection)[:2])
        resolved = self._tool_resolution(context, selection)

        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        fields = selection_fields(selection)
        current = selection['version'] == SELECTION_VERSION
        assignment = plain(context.assignment)
        if current:
            assignment = {**assignment, 'selection': selector_selection(selection)}
        published = annotation.get('entry_version') == INSTRUCTION_VERSION
        if published:
            axis_view = instruction_view(annotation)
        elif annotation.get('entry_version') == EVIDENCE_AXIS_VERSION:
            axis_view = evidence_axis_instruction_view(annotation)
        else:
            raise ValueError('scientific_support_entry_invalid')
        result = {'scientific_process': {'selection': selector_selection(selection), 'initial_selection_sha256': scientific_digest(plain(context.assignment['selection'])), 'evidence_axis' if current else 'annotation': axis_view, **({} if published else {'annotation_support_routes': self.services.scientific_support_routes(context, observation_kinds=support_observation_kinds(annotation))}), 'thought_pattern' if current else 'thought': selected_fields(thought, ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance', 'outcome_contingencies', 'boundary')), **({'child_tool_info': deepcopy(selection[fields[2]])} if current else {'tools': deepcopy(resolved)}), 'assignment': assignment, 'permitted_children': list(self.allowed_children(context, None))}}
        from gene_annotation_episode.episodic_workflow.root.a107.component_axis_source_access import decision_context as source_access_context
        access = source_access_context(self.services.workflow, context)
        if access is not None:
            result['component_axis_source_access'] = access
        return result

    def _component_scoring_facts(self, context):
        from gene_annotation_episode.episodic_workflow.root.a107.component_axis_reports import current_scoring_sheets, SCORING_FACT
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            return {}
        sheets = current_scoring_sheets(workflow.store, context=context, services=self.services)
        return {SCORING_FACT: sheets} if sheets else {}

    def current_report_facts(self, context):
        return self._component_scoring_facts(context)

    def initial_decision_context(self, context):
        if context.role not in {'annotation', ROLE}:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        result = self._component_scoring_facts(context)
        if workflow is not None:
            from gene_annotation_episode.episodic_workflow.root.a107 import component_axis_reports as reports_binding
            from gene_annotation_episode.episodic_workflow.root.a107 import component_axis_native_hpc as native
            reports = reports_binding.received_reports(workflow.store, context=context, services=self.services)
            if reports:
                result['received_partner_and_chemical_evidence'] = reports
            components = native.received_components(workflow.store, context.received_record_refs, context.scope)
            execution = native.execution_findings(workflow.store, context.received_record_refs, context.scope)
            if components or execution:
                execution = reports_binding.mark_native_execution(execution, components)
                components.sort(key=lambda row: row['source_ref'])
                execution.sort(key=lambda row: row['source_ref'])
                result['received_partner_and_chemical_native_components'] = {'scientific_results': components, 'execution_findings': execution}
                from gene_annotation_episode.episodic_workflow.root.a107.component_axis_execution_context import prepared_assignments
                prepared = prepared_assignments(workflow.store, context=context, execution_findings=execution, resources=getattr(workflow.tools, 'component_native_resources', None))
                if prepared is not None:
                    result['received_partner_and_chemical_native_components']['prepared_hpc_assignments'] = prepared
            from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.internal_summary import received_qualification_context
            qualifications = received_qualification_context(context, workflow, AXIS)
            if qualifications:
                result['received_partner_and_chemical_qualifications'] = qualifications
        return result


from gene_annotation_episode.episodic_workflow.root.a107.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json

class ScientificDecisionSummary:


    def _decision_snapshot(self, view, delivery_ref=None):
        with self.workflow.store.read_snapshot():
            state = self.workflow.working_state(self)
            row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
            visual_evidence = _live_original_runtime.json.loads(row[0]) if row and row[0] is not None else []
            subset = getattr(self.workflow.store, 'reference_subset', None)
            presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
            presented_feedback = self.feedback
            if isinstance(self.last_outcome, _live_original_runtime.Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, _live_original_runtime.Mapping):
                presented_feedback = presented_outcome.get('feedback')
            credit_view = self.workflow.source_credit_view(self)
            annotation_axes = isinstance(credit_view['credit'], _live_original_runtime.Mapping) and credit_view['credit'].get('mode') == 'annotation_axis_credit'
            forms = [(self.report_values, self.interpret_schema)]
            if not annotation_axes:
                forms.extend(((report.as_record(), _live_original_runtime._plain(report.contract.measurements['schema'])) for report in view.child_reports))
            controller_state = _live_original_runtime._plain(view.controller_state)
            if annotation_axes:
                state = {}
                controller_state = {key: controller_state[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
                if presented_outcome is not None and self.last_outcome_index is not None:
                    prior = self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)
                    if prior is not None and _live_original_runtime.json.loads(prior['action']).get('kind') in {'child', 'episode_child', 'job_child'}:
                        presented_outcome = {'status': presented_outcome.get('status'), 'record_ref_count': len(presented_outcome.get('record_refs') or ()), 'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                        presented_feedback = None
            basis = _live_original_runtime._references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
            context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _live_original_runtime.FACT_MEANINGS[name]} for name in sorted(_live_original_runtime.FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
            if self.workflow.is_scientific_source(self):
                if annotation_axes:
                    context.update(proposed_annotations=[{key: row[key] for key in ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value', 'context_refs', 'scope', 'score', 'support', 'opposition', 'status')} for row in credit_view['proposed_annotations']], annotation_comparisons=credit_view['comparisons'])
                else:
                    context.update(self.workflow.annotation_context(self.scope, source=self))
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a107_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        schema = self.workflow.action_schema(self)
        if delivery_ref is not None:
            context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
        return (context, schema)
from gene_annotation_episode.episodic_workflow.root.a107 import runtime as _live_original_runtime
