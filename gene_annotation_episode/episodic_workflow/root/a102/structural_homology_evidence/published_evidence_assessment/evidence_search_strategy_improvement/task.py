"""Original iterative literature_strategy decisions, actions, returned outcomes and replay."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.library.action_contracts import action_schema as _private_action_schema
from gene_annotation_episode.episodic_workflow.root.a102.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.a102.runtime import AcquisitionError, ActionFailure, ContractError, ContractInformationError, Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, sqlite3, subprocess, validate_form
from .task_state import SourceTaskState
from .decision_delivery import SourceDecisionDelivery
from .task_waiting import SourceTaskWaiting
from .report_delivery import SourceReportDelivery
from .task_instructions import compose_instructions

class SourceTask(SourceTaskState, SourceDecisionDelivery, SourceTaskWaiting, SourceReportDelivery):
    instruction_composer = staticmethod(compose_instructions)


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
                    context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a102_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
                    contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
                    if callable(contract_catalog):
                        context['available_report_facts'] = contract_catalog(context)
                schema = _invoke_private_policy(self.workflow.action_schema, _private_action_schema, self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
            if delivery_ref is not None and context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref:
                raise _live_original_runtime.WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.a102.providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.a102.episode_source_failure import record_source_failure
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
            if self.workflow.permits_common_action(self, 'reason') and isinstance(selection, _live_original_runtime.Mapping) and (selection.get('kind') == 'reason'):
                envelope = self.workflow.reasoning_action_schema(self, {'type': 'object'})
                _live_original_runtime.Draft202012Validator(envelope).validate(selection)
                payload = selection['commit']
                commit_schema = self.workflow.store.reasoning_schema()
                if set(commit_schema.get('required', commit_schema['properties'])) <= set(payload) <= set(commit_schema['properties']) and all((value == [] for value in payload.values())) and (selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                    owner = self.workflow.specialist(self)
                    has_task_content = getattr(owner, 'reasoning_has_task_content', None)
                    if has_task_content is None or not has_task_content(self.workflow.binding_context(self), selection):
                        raise ValueError('empty_reasoning_commit')
            else:
                _live_original_runtime.Draft202012Validator(schema['properties']['selection']).validate(selection)
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
                unit = self.workflow.selected(self, selection, index)
        except _live_original_runtime.EventTargetError as error:
            self.feedback = _live_original_runtime._wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (OSError, _live_original_runtime.sqlite3.Error, _live_original_runtime.subprocess.SubprocessError, _live_original_runtime.AcquisitionError) as error:
            if not isinstance(selection, _live_original_runtime.Mapping) or selection.get('kind') != 'job_child':
                raise
            handoff = selection.get('handoff') or {}
            self.feedback = {'status': 'failed', 'category': 'job_assignment', 'code': error.code if isinstance(error, _live_original_runtime.AcquisitionError) else 'job_storage_failed' if isinstance(error, _live_original_runtime.sqlite3.Error) else 'job_control_failed' if isinstance(error, _live_original_runtime.subprocess.SubprocessError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'role': selection['role'], 'job_ref': selection.get('existing_job_ref', handoff.get('job_ref'))}
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
            if isinstance(error, _live_original_runtime.ContractError) and str(error) == 'component_native_return_channels_required':
                self.feedback['contract_error'] = {'code': str(error), 'field': error.detail['field']}
                self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
                self.feedback['repair'] = error.detail['repair']
            if isinstance(error, _live_original_runtime.ValidationError) and isinstance(selection, _live_original_runtime.Mapping) and (selection.get('kind') == 'tool') and (selection.get('tool') == 'reads.map'):
                from gene_annotation_episode.episodic_workflow.root.a102.read_mapping import parameter_schema_failure
                branches = schema['properties']['selection']['anyOf']
                for branch_error in error.context:
                    branch_path = list(branch_error.schema_path)
                    if not branch_path or not isinstance(branch_path[0], int):
                        continue
                    branch = branches[branch_path[0]]
                    if branch.get('properties', {}).get('tool', {}).get('const') != 'reads.map':
                        continue
                    feedback = parameter_schema_failure(branch_error, path_prefix=('arguments',))
                    if feedback is not None:
                        self.feedback.update(feedback)
                        break
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = _live_original_runtime.validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain='literature_strategy', schema=self.interpret_schema, source=self)
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
                if selection['kind'] == 'reason':
                    payload = selection['commit']
                    account_binding = {'account_invocation': (self.workflow.run_id, self.episode_id)} if payload.get('interpretation_accounts') else {}
                    specialist = self.workflow.specialist(self)
                    execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                    result = execute_reasoning(self.workflow.binding_context(self), selection, key) if execute_reasoning is not None else None
                    if result is None:
                        result = self.workflow.store.commit_reasoning(payload, self.scope, key, **account_binding)
                elif selection['kind'] == 'wait':
                    try:
                        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                    except _live_original_runtime.EventTargetError as error:
                        result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _live_original_runtime._wait_target_feedback(error, status='failed')}
                else:
                    result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
                if _live_original_runtime.inspect.isawaitable(result):
                    result = await result
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
        if credit is None and observed_outcome and (selection['kind'] != 'wait'):
            result = await self.workflow.automatic_score_updates(self, index, result)
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _live_original_runtime.nullcontext():
            if credit is None and observed_outcome:
                if selection['kind'] == 'wait':
                    credit = self.workflow.last_observed_credit(self)
                else:
                    credit_view = self.workflow.source_credit_view(self)
                    credit = credit_view['credit']
                    if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                        self.workflow.retain_shared_grading_results(self, result, credit_view)
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
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
