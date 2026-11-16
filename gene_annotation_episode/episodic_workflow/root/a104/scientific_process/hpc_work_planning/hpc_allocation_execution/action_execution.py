"""Private HPC planning/allocation task."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form
from .task_state import HPCWorkTaskState
from .task_decision import HPCWorkTaskDecision
from .task_waiting import HPCWorkSuspension
from .report_delivery import HPCWorkReportDelivery
from .decision_state import HPCWorkDecisionState

from .task_instructions import instructions as _instruction_composer


class HPCWorkTaskExecution:

    async def execute(self, selection, index):
        journal = self.workflow.journal
        old = journal.row('runtime_actions', self.episode_id, index)
        if old and json.loads(old['action']) != selection:
            raise WorkflowError('reconstructed selected work changed')
        if old and old['result'] is not None:
            result, credit = (json.loads(old['result']), old['credit'])
        else:
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
            key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
            with journal.measure('runtime_actions', self.episode_id, index):
                if selection['kind'] == 'wait':
                    try:
                        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                    except EventTargetError as error:
                        result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
                else:
                    result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
                if inspect.isawaitable(result):
                    result = await result
            result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': None})
                self.last_outcome, self.last_outcome_index = (result, index)
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        observed_outcome = observes_action_outcome(selection['kind'], result['status'])
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
            if credit is None and observed_outcome:
                if selection['kind'] == 'wait':
                    credit = self.workflow.last_observed_credit(self)
                else:
                    credit_view = self.workflow.source_credit_view(self)
                    credit = credit_view['credit']
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': credit})
            if self.workflow.execution_binding is not None and observed_outcome:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
                self.last_outcome, self.last_outcome_index = (result, index)
                self.checkpoint()
        self.last_outcome = result
        self.last_outcome_index = index
        if not observed_outcome:
            raise ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
        return self.workflow.controller_value(self, index, credit)


def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'HPCWorkTaskExecution.execute': HPCWorkTaskExecution.__dict__['execute']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.action_execution')
    setattr(HPCWorkTaskExecution, 'execute', bound['HPCWorkTaskExecution.execute'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
