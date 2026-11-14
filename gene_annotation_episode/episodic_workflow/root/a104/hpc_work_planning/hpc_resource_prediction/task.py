"""Private prediction task."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form
from .task_state import PredictionTaskState
from .task_decision import PredictionTaskDecision
from .waiting import PredictionSuspension
from .report_delivery import PredictionReportDelivery
from .decision_state import PredictionDecisionState
from .decision_inputs import PredictionDecisionInputs

from .task_instructions import instructions as _instruction_composer

from .action_admission import ResourcePredictionTaskAdmission

from .action_execution import ResourcePredictionTaskExecution

class ResourcePredictionTask(ResourcePredictionTaskExecution, ResourcePredictionTaskAdmission, PredictionTaskState, PredictionTaskDecision, PredictionSuspension, PredictionReportDelivery, PredictionDecisionState, PredictionDecisionInputs):

    instruction_composer = staticmethod(_instruction_composer)

    async def next(self, view, *, delivery_ref=None):
        self._selection_view = view
        closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
        if closed is not None and closed['state'] == 'yielded' and (closed['completion'] is not None):
            completion = json.loads(closed['completion'])
            if completion['ended_by'] == 'source_failed' and view.units_consumed == completion['actions']:
                return SourceEnd('source_failed')
        if self.workflow.inprocess_replay is not None:
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
        if self.workflow.execution_binding is not None:
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
        while True:
            original_call = self.workflow.journal.row('runtime_model_calls', self.episode_id, self.calls)
            original_request = json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None or 'contract_information' in original_request or 'literature_numerical_contracts' in original_request):
                context, schema = (original_request['context'], original_request['schema'])
            else:
                context = self.decision_state(view)
                schema = self.workflow.action_schema(self)
            from gene_annotation_episode.episodic_workflow.root.a104.providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.a104.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source', 'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                return SourceEnd('source_failed')
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None else nullcontext():
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit



def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'ResourcePredictionTask.next': ResourcePredictionTask.__dict__['next']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_resource_prediction.task')
    setattr(ResourcePredictionTask, 'next', bound['ResourcePredictionTask.next'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
