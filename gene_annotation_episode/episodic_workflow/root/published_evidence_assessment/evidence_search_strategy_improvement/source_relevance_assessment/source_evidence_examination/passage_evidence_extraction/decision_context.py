from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_state import LiteratureDecisionState
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_exchange import LiteratureDecisionExchange
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_instructions import LiteratureDecisionInstructions
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_actions import LiteratureDecisionActions
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_return import LiteratureDecisionReturn

from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.decision_provider import LiteratureProviderCompletion

class LiteratureDecisionContext:

    def assemble_decision_context(self, view):
        with self.workflow.store.read_snapshot():
            state = self.workflow.working_state(self)
            # The last local tool outcome can remain visible while a child
            # runs. Select pixels from the authoritative most recent own
            # action instead: a completed child must not reattach an older
            # image or expose one of its private selections to its parent.
            row = self.workflow.journal.db.execute("""SELECT CASE
                WHEN json_extract(action,'$.kind')='tool'
                 AND json_extract(action,'$.tool')='image.view'
                 AND json_extract(result,'$.status')='completed'
                THEN json_extract(result,'$.visual_inputs') ELSE NULL END
                FROM runtime_actions WHERE run_id=? AND episode_id=?
                AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1""",
                (self.workflow.run_id, self.episode_id)).fetchone()
            visual_evidence = json.loads(row[0]) if row and row[0] is not None else []
            subset = getattr(self.workflow.store, "reference_subset", None)
            presented_outcome = self.workflow.local_outcome_preview(
                self.last_outcome, decision_index=self.last_outcome_index)
            presented_feedback = self.feedback
            if (isinstance(self.last_outcome, Mapping)
                    and self.feedback is self.last_outcome.get("feedback")
                    and isinstance(presented_outcome, Mapping)):
                presented_feedback = presented_outcome.get("feedback")
            credit_view = self.workflow.source_credit_view(self)
            annotation_axes = (isinstance(credit_view['credit'], Mapping)
                and credit_view['credit'].get('mode') == 'annotation_axis_credit')
            forms = [(self.report_values, self.interpret_schema)]
            if not annotation_axes:
                forms.extend((report.as_record(), _plain(report.contract.measurements["schema"]))
                             for report in view.child_reports)
            controller_state = _plain(view.controller_state)
            if annotation_axes:
                state = {}
                controller_state = {key: controller_state[key] for key in
                    ('arms', 'annotation_credits', 'root_score', 'decision')}
                if presented_outcome is not None and self.last_outcome_index is not None:
                    prior = self.workflow.journal.row('runtime_actions', self.episode_id,
                        self.last_outcome_index)
                    if prior is not None and json.loads(prior['action']).get('kind') in {
                            'child', 'episode_child', 'job_child'}:
                        presented_outcome = {
                            'status': presented_outcome.get('status'),
                            'record_ref_count': len(presented_outcome.get('record_refs') or ()),
                            'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                        presented_feedback = None
            basis = _references_in({"working_state": state, "last_local_outcome": presented_outcome,
                                    "visual_evidence": visual_evidence}, self.workflow.store.get,
                                   forms=forms, reference_subset=(lambda refs: subset(refs, self.scope))
                                   if subset is not None else None)
            context = view.model_inputs({"goal": self.request.goal.as_record(), "scope": self.scope,
                "working_state": state, "visible_record_refs": basis,
                "current_credit": ({'mode': 'annotation_axis_credit',
                    'root_score': controller_state['root_score']}
                    if annotation_axes else credit_view["credit"]),
                "current_evidence_vector": credit_view.get("axis_components"),
                **({'investigation_progress': {key: credit_view[key] for key in
                    ('retained_finding_count', 'inactive_dependencies', 'detail_pages')
                    if key in credit_view}} if self.workflow.receipt_projection(self) else {}),
                "credit_binding": self.workflow.source_credit_binding(self),
                "time_accounting": self.workflow.journal.elapsed_view(self.episode_id),
                "pending_work": self.workflow.pending_work(self),
                "last_local_outcome": presented_outcome, "feedback": presented_feedback,
                "visual_evidence": visual_evidence,
                "report_deliveries": self.workflow.delivery_status(self.episode_id),
                "controller": controller_state,
                "controller_binding": self.workflow.controller_binding,
                "tools": self.workflow.catalog(self.scope, source=self),
                "tool_knowledge": self.workflow.knowledge.context(),
                "job_episode_options": self.workflow.job_episode_options(self),
                "available_report_facts": {name: {"type": "number" if name == "credit" else "reference_array",
                                                   "meaning": FACT_MEANINGS[name]}
                                           for name in sorted(FACT_SOURCES)} | self.workflow.extra_report_sources(self),
                "requested_report_purpose": (self.request.report_contract.decision
                    if self.request.report_contract else None),
                "requested_form": self.request.report_contract.schema if self.request.report_contract else None,
                "current_report_update": self.report_values,
                "current_report_basis_refs": self.report_basis,
                "report_lifecycle": "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment."},
                reports=() if annotation_axes else view.child_reports)
            if self.workflow.is_scientific_source(self):
                if annotation_axes:
                    context.update(proposed_annotations=[{key: row[key] for key in
                        ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value',
                         'context_refs', 'scope', 'score', 'support', 'opposition', 'status')}
                        for row in credit_view['proposed_annotations']],
                        annotation_comparisons=credit_view['comparisons'])
                else:
                    context.update(self.workflow.annotation_context(self.scope, source=self))
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in
                    ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            context['_completed_work_axis_results'] = {
                key: credit_view[key] for key in (
                    'a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet',
                    'target_sheets', 'tool_attachments', 'source_contributions')
                if key in credit_view}
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        return context
