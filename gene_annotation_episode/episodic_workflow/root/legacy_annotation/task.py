from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.action_contracts import action_schema as _private_action_schema
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
import json
from contextlib import nullcontext
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in
from gene_annotation_episode.episodic_workflow.root.task_values import _plain
from gene_annotation_episode.episodic_workflow.root import literature_numerical_contracts
from gene_annotation_episode.episodic_workflow.root.method_loop.episode import SourceEnd
from gene_annotation_episode.episodic_workflow.root.report_facts import FACT_SOURCES, FACT_MEANINGS
from .decision_protocol import LegacyAnnotationDecisionProtocol
from .from_parent import LegacyAnnotationFromParent
from .instructions import LegacyAnnotationInstructions
from .internal_summary import LegacyAnnotationInternalSummary
from .task_actions import LegacyAnnotationTaskActions
from .task_decision import LegacyAnnotationTaskDecision
from .task_state import LegacyAnnotationTaskState
from .to_parent import LegacyAnnotationToParent
from .waiting import LegacyAnnotationWaiting

from .decision_context import LegacyAnnotationDecisionContext

class LegacyAnnotationTask(LegacyAnnotationDecisionContext, LegacyAnnotationDecisionProtocol, LegacyAnnotationFromParent, LegacyAnnotationInstructions, LegacyAnnotationInternalSummary, LegacyAnnotationTaskActions, LegacyAnnotationTaskDecision, LegacyAnnotationTaskState, LegacyAnnotationToParent, LegacyAnnotationWaiting):
    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and closed['completion'] is not None:
                completion = json.loads(closed['completion'])
                if (completion['ended_by'] == 'source_failed'
                        and view.units_consumed == completion['actions']):
                    # Replaying a finalized partial result must not retry the
                    # already-failed source or select new scientific work.
                    return SourceEnd('source_failed')
        if self.workflow.inprocess_replay is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.inprocess_replay.unit(self, view.units_consumed)
            if ready is not None:
                return ready
            self.restore_checkpoint()
            self._inprocess_replay_ready = True
            with self.workflow.store.transaction():
                self.workflow.inprocess_replay.capture(self)
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
        if self.workflow.execution_binding is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            self.restore_checkpoint()
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
            ready = self.workflow.next_return(self)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            await self.workflow.resolve_pending_deliveries(self, view)
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
        while True:
            original_call = self.workflow.journal.row('runtime_model_calls', self.episode_id, self.calls)
            if (delivery_ref is None and original_call is None
                    and self._execution_context is not None):
                # A rejected selection stays inside this source loop. Collect
                # an original child that finished meanwhile before asking for
                # another decision. Saved calls and delivery repairs retain
                # their original ordering and journal context.
                ready = self._execution_context._ready_owned_child(self.path)
                if ready is not None:
                    return ready
            original_request = json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None
                    or 'contract_information' in original_request
                    or literature_numerical_contracts.SAVED_MEMBER in original_request):
                # Answered decisions already have their supplied context and
                # contracts. Rebuilding them can reopen old native payloads.
                # Opted-in pending decisions also retain their original input.
                context, schema = original_request['context'], original_request['schema']
            else:
                context = self.assemble_decision_context(view)
                schema = _invoke_private_policy(self.workflow.action_schema, _private_action_schema, self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(
                        self, delivery_ref, context)
            if (delivery_ref is not None and
                    context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref):
                raise WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.provider_errors import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id,
                    self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source',
                    'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return SourceEnd('source_failed')
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None
                    or self.workflow.inprocess_replay is not None else nullcontext()):
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit

