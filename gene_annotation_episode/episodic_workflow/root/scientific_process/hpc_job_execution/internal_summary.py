"""Present this terminal episode assignment, outcomes, credit and unresolved work."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.action_contracts import action_schema as _private_action_schema
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from copy import deepcopy
import json
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.communication import plain
from ...task_values import _plain
from ...reference_selection import _references_in
from ...report_facts import FACT_SOURCES, FACT_MEANINGS

class HPCSummary:
    def initial_decision_context(self,context):
        return {'execution_resource_information':deepcopy(self.initial_information)}

    def _resource_information(self,kind):
        configuration=self.resources[kind]
        return {'resource_kind':kind,'workspace':configuration['workspace'],
            **{name:deepcopy(configuration[name]) for name in (
                'kind','policy','account','ssh_argv','python_executable','scheduler')
                if name in configuration},
            'inventory_snapshot':deepcopy(self.initial_information.get(kind))}

    def decision_context(self,context,current_view):
        state=self.state(context)
        return {'execution_assignment':plain(context.assignment),
            'execution_resource':self._resource_information(context.assignment['resource_kind']),
            'coordinator_workspace':str(self.directory.resolve()),
            'execution_progress':state.credit_view(),
            'execution_completion':state.completion_proof()}



class HPCTaskSummary:
    def prepare_decision_inputs(self, view):
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
            forms = [(self.report_values, self.interpret_schema)]
            forms.extend((report.as_record(), _plain(report.contract.measurements["schema"]))
                         for report in view.child_reports)
            controller_state = _plain(view.controller_state)
            basis = _references_in({"working_state": state, "last_local_outcome": presented_outcome,
                                    "visual_evidence": visual_evidence}, self.workflow.store.get,
                                   forms=forms, reference_subset=(lambda refs: subset(refs, self.scope))
                                   if subset is not None else None)
            context = view.model_inputs({"goal": self.request.goal.as_record(), "scope": self.scope,
                "working_state": state, "visible_record_refs": basis,
                "current_credit": credit_view["credit"],
                "current_evidence_vector": credit_view.get("axis_components"),
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
                reports=view.child_reports)
            if 'monitoring_information_credit' in credit_view:
                context.update({key: credit_view[key] for key in
                    ('monitoring_information_credit', 'monitoring_information_binding')})
            specialist = self.workflow.specialist(self)
            if specialist is not None:
                context.update(specialist.decision_context(self.workflow.binding_context(self), view))
            contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
            if callable(contract_catalog):
                context['available_report_facts'] = contract_catalog(context)
        return context, _invoke_private_policy(self.workflow.action_schema, _private_action_schema, self)
