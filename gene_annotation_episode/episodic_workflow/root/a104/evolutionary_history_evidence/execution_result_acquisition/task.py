"""Private Results task selected by its actual binding."""
from __future__ import annotations
from .task_state import ResultsTaskState
from .task_decision import ResultsTaskDecision
from .waiting import ResultsWaiting
from .report_delivery import ResultsReportDelivery
from .task_action import ResultsTaskAction
from gene_annotation_episode.episodic_workflow.root.a104.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, SourceEnd, WorkflowError, _plain, _references_in, json, nullcontext
from .instructions import instructions as _instruction_composer

from .decision_context import ResultsTaskContext

class ResultsTask(ResultsTaskContext, ResultsTaskState, ResultsTaskDecision, ResultsWaiting, ResultsReportDelivery, ResultsTaskAction):
    instruction_composer = staticmethod(_instruction_composer)

    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and (closed['completion'] is not None):
                completion = json.loads(closed['completion'])
                if completion['ended_by'] == 'source_failed' and view.units_consumed == completion['actions']:
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
            if delivery_ref is None and original_call is None and (self._execution_context is not None):
                ready = self._execution_context._ready_owned_child(self.path)
                if ready is not None:
                    return ready
            original_request = json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None or 'contract_information' in original_request or 'literature_numerical_contracts' in original_request):
                context, schema = (original_request['context'], original_request['schema'])
            else:
                context = self.assemble_decision_context(view)
                schema = self.workflow.action_schema(self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
            if delivery_ref is not None and context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref:
                raise WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.a104.providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.a104.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source', 'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return SourceEnd('source_failed')
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None else nullcontext():
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'ResultsTask.next': ResultsTask.__dict__['next']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.task')
    setattr(ResultsTask, 'next', bound['ResultsTask.next'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
