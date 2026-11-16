"""Private HPC planning/allocation task."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.hpc_handoff_report_contract import validate_hpc_launch_report_contract
from gene_annotation_episode.episodic_workflow.root.a110.runtime import ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form
from .task_state import HPCWorkTaskState
from .task_decision import HPCWorkTaskDecision
from .task_waiting import HPCWorkSuspension
from .report_delivery import HPCWorkReportDelivery
from .decision_state import HPCWorkDecisionState
from .decision_inputs import HPCWorkDecisionInputs

class HPCWorkTask(HPCWorkTaskState, HPCWorkTaskDecision, HPCWorkSuspension, HPCWorkReportDelivery, HPCWorkDecisionState, HPCWorkDecisionInputs):


    _validate_hpc_launch_report_contract = staticmethod(validate_hpc_launch_report_contract)
    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and (closed['completion'] is not None):
                completion = _live_original_runtime.json.loads(closed['completion'])
                if completion['ended_by'] == 'source_failed' and view.units_consumed == completion['actions']:
                    return _live_original_runtime.SourceEnd('source_failed')
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
                return self.workflow.selected(self, _live_original_runtime.json.loads(action['action']), index)
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
                return self.workflow.selected(self, _live_original_runtime.json.loads(action['action']), index)
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
            original_request = _live_original_runtime.json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None or 'contract_information' in original_request or 'literature_numerical_contracts' in original_request):
                context, schema = (original_request['context'], original_request['schema'])
            else:
                context = self.decision_state(view)
                schema = self.workflow.action_schema(self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
            if delivery_ref is not None and context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref:
                raise _live_original_runtime.WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.a110.providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.a110.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source', 'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return _live_original_runtime.SourceEnd('source_failed')
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None else _live_original_runtime.nullcontext():
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit


    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = self.workflow.journal.row('runtime_model_calls', self.episode_id, index) if original is None and self.workflow.decision_exchanges is not None else None
            saved = {} if call is None else _live_original_runtime.json.loads(call['request'])
            response = _live_original_runtime._decode_recorded_action_response(response, schema, recorded_selection=None if original is None else _live_original_runtime.json.loads(original['action']), exchanges=() if original is not None or self.workflow.decision_exchanges is None else self.workflow.decision_exchanges.rows(self.episode_id, index), exchange_schema=saved.get('contract_information', {}).get('exchange_schema'))
            selection = response['selection']
            if self._delivery_resolution_ref is not None:
                _live_original_runtime.Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            _live_original_runtime.Draft202012Validator(schema['properties']['selection']).validate(selection)
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
                unit = self.workflow.selected(self, selection, index)
        except _live_original_runtime.EventTargetError as error:
            self.feedback = _live_original_runtime._wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (ValueError, KeyError, TypeError, _live_original_runtime.ValidationError) as error:
            self.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': _live_original_runtime.schema_failure_diagnostic(error) if isinstance(error, _live_original_runtime.ValidationError) else str(error)}
            if isinstance(error, _live_original_runtime.ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = 'schema_json must encode a JSON Schema object with the explicit top-level field "type": "object" and a properties object. Keep the intended properties, declare every field in required, and set additionalProperties to false. A properties object alone does not declare the required outer type.'
                if isinstance(error.__cause__, _live_original_runtime.ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = _live_original_runtime.validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain='hpc_execution', schema=self.interpret_schema, source=self)
            self.report_values = admitted
            self.report_basis = [ref for ref in actual_context['visible_record_refs'] if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {'status': 'invalid', 'category': 'report_format', 'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}
        if isinstance(unit, _live_original_runtime.ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, _live_original_runtime.ReportRedelivery) else 'selected')
        return unit


    async def execute(self, selection, index):
        journal = self.workflow.journal
        old = journal.row('runtime_actions', self.episode_id, index)
        if old and _live_original_runtime.json.loads(old['action']) != selection:
            raise _live_original_runtime.WorkflowError('reconstructed selected work changed')
        if old and old['result'] is not None:
            result, credit = (_live_original_runtime.json.loads(old['result']), old['credit'])
        else:
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _live_original_runtime._json(selection), 'result': None, 'credit': None})
            key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
            with journal.measure('runtime_actions', self.episode_id, index):
                if selection['kind'] == 'wait':
                    try:
                        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                    except _live_original_runtime.EventTargetError as error:
                        result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _live_original_runtime._wait_target_feedback(error, status='failed')}
                else:
                    result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
                if _live_original_runtime.inspect.isawaitable(result):
                    result = await result
            if self.workflow.execution_binding is not None or self.workflow.wait_inputs_version == 'wait_inputs_binding_v2' or self.workflow.completed_action_inputs_version is not None:
                result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _live_original_runtime._json(selection), 'result': _live_original_runtime._json(result), 'credit': None})
                self.last_outcome, self.last_outcome_index = (result, index)
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        observed_outcome = _live_original_runtime.observes_action_outcome(selection['kind'], result['status'])
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
            if credit is None and observed_outcome:
                if selection['kind'] == 'wait':
                    credit = self.workflow.last_observed_credit(self)
                else:
                    credit_view = self.workflow.source_credit_view(self)
                    credit = credit_view['credit']
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _live_original_runtime._json(selection), 'result': _live_original_runtime._json(result), 'credit': credit})
            if self.workflow.execution_binding is not None and observed_outcome:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
                self.last_outcome, self.last_outcome_index = (result, index)
                self.checkpoint()
        self.last_outcome = result
        self.last_outcome_index = index
        if not observed_outcome:
            raise _live_original_runtime.ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
        return self.workflow.controller_value(self, index, credit)
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _live_original_runtime
