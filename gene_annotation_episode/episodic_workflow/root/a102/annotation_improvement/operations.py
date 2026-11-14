"""Original private A102 annotation operations responsibility."""
from __future__ import annotations
from .. import runtime as _runtime

class ImprovementOperations:
    def record_execution_failure(self, error, *, unit=None):
        from ..episode_source_failure import record_source_failure
        import traceback
        diagnostic = self.workflow.archive.store(_runtime.Record({'exception_type': type(error).__name__,
            'traceback': traceback.format_exc()}))
        index = getattr(unit, 'decision_index', None)
        failure = record_source_failure(self.workflow.store, self.workflow.run_id,
            self.episode_id, index if index is not None else max(0, self.calls - 1), error,
            category='episode_execution', cause_code='selected_operation_failed')
        self.feedback = {**failure, 'diagnostic_ref': str(diagnostic.path)}
        action = (None if index is None else
            self.workflow.journal.row('runtime_actions', self.episode_id, index))
        if (action is not None and action['result'] is None
                and _runtime.json.loads(action['action']).get('kind') in {'tool', 'reason'}):
            selection = _runtime.json.loads(action['action'])
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
                'feedback': self.feedback}
            with self.workflow.store.transaction():
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id,
                    'decision_index': index, 'action': action['action'], 'result': _runtime._json(outcome), 'credit': None})
                credit = self.workflow.source_credit_view(self)['credit']
                value = self.workflow.controller_value(self, index, credit)
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id,
                    'decision_index': index, 'action': action['action'], 'result': _runtime._json(outcome), 'credit': credit})
                if self.workflow.execution_binding is not None:
                    self.workflow.completions.stage(self.episode_id, index,
                        label=f"{selection['kind']}:{index}", kind='own_action',
                        controller_input=value, child_return=None)
            self.last_outcome, self.last_outcome_index = outcome, index
            self.checkpoint()
            return _runtime.ActionLeaf(selection, extract=lambda _: value, result=lambda _, result: result,
                label=f"{selection['kind']}:{index}", decision_index=index)
        self.checkpoint()

    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = (self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
                if original is None and self.workflow.decision_exchanges is not None else None)
            saved = {} if call is None else _runtime.json.loads(call['request'])
            response = _runtime._decode_recorded_action_response(response, schema,
                recorded_selection=None if original is None else _runtime.json.loads(original['action']),
                exchanges=() if original is not None or self.workflow.decision_exchanges is None else
                    self.workflow.decision_exchanges.rows(self.episode_id, index),
                exchange_schema=saved.get('contract_information', {}).get('exchange_schema'),
                unproven_replay=getattr(self, '_unproven_direct_response_index', None) == index)
            # Validate selection independently: report formatting must not
            # reject a valid scientific contribution or alter its credit.
            selection = response["selection"]
            if self._delivery_resolution_ref is not None:
                _runtime.Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            if (self.workflow.permits_common_action(self, 'reason') and isinstance(selection, _runtime.Mapping)
                    and selection.get("kind") == "reason"):
                # Store owns row-level admission and preserves independent
                # valid rows. Checking its full scientific payload here
                # would prevent its partial-result path from ever running.
                envelope = self.workflow.reasoning_action_schema(self, {"type": "object"},
                    _accept_legacy_quotes=True)
                _runtime.Draft202012Validator(envelope).validate(selection)
                payload = selection["commit"]
                commit_schema = self.workflow.store.reasoning_schema()
                if (set(commit_schema.get("required", commit_schema["properties"]))
                        <= set(payload) <= set(commit_schema["properties"])
                        and all(value == [] for value in payload.values())
                        and selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                    owner = self.workflow.specialist(self)
                    has_task_content = getattr(owner, 'reasoning_has_task_content', None)
                    if has_task_content is None or not has_task_content(
                            self.workflow.binding_context(self), selection):
                        raise ValueError("empty_reasoning_commit")
            else:
                _runtime.Draft202012Validator(schema["properties"]["selection"]).validate(selection)
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else _runtime.nullcontext()):
                unit = self.workflow.selected(self, selection, index)
        except _runtime.EventTargetError as error:
            self.feedback = _runtime._wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (OSError, _runtime.sqlite3.Error, _runtime.subprocess.SubprocessError, _runtime.AcquisitionError) as error:
            if not isinstance(selection, _runtime.Mapping) or selection.get('kind') != 'job_child':
                raise
            # Receiving-interface failure is operational feedback about
            # this commission, not a malformed contract, completed child
            # action, numerical observation or reason to stop the parent.
            handoff = selection.get('handoff') or {}
            self.feedback = {'status': 'failed', 'category': 'job_assignment',
                'code': (error.code if isinstance(error, _runtime.AcquisitionError)
                    else 'job_storage_failed' if isinstance(error, _runtime.sqlite3.Error)
                    else 'job_control_failed' if isinstance(error, _runtime.subprocess.SubprocessError)
                    else 'job_operation_failed'),
                'exception_type': type(error).__name__, 'role': selection['role'],
                'job_ref': selection.get('existing_job_ref', handoff.get('job_ref'))}
            self.record_effect(index, 'rejected')
            return None
        except (ValueError, KeyError, TypeError, _runtime.ValidationError) as error:
            self.feedback = {"status": "invalid", "category": "action_contract",
                "detail": (_runtime.schema_failure_diagnostic(error)
                           if isinstance(error, _runtime.ValidationError) else str(error))}
            if isinstance(error, _runtime.ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = (
                        'schema_json must encode a JSON Schema object with the explicit top-level '
                        'field "type": "object" and a properties object. Keep the intended properties, '
                        'declare every field in required, and set additionalProperties to false. '
                        'A properties object alone does not declare the required outer type.')
                if isinstance(error.__cause__, _runtime.ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            if (isinstance(error, _runtime.ContractError)
                    and str(error) == 'component_native_return_channels_required'):
                self.feedback['contract_error'] = {'code': str(error),
                    'field': error.detail['field']}
                self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
                self.feedback['repair'] = error.detail['repair']
            if (isinstance(error, _runtime.ValidationError) and isinstance(selection, _runtime.Mapping)
                    and selection.get("kind") == "tool" and selection.get("tool") == "reads.map"):
                from ..read_mapping import parameter_schema_failure
                branches = schema["properties"]["selection"]["anyOf"]
                for branch_error in error.context:
                    branch_path = list(branch_error.schema_path)
                    if not branch_path or not isinstance(branch_path[0], int):
                        continue
                    branch = branches[branch_path[0]]
                    if branch.get("properties", {}).get("tool", {}).get("const") != "reads.map":
                        continue
                    feedback = parameter_schema_failure(branch_error, path_prefix=("arguments",))
                    if feedback is not None:
                        self.feedback.update(feedback)
                        break
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = _runtime.validate_form(response["report_update"], self.interpret_schema,
                resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope,
                assignment=self.request.message.as_record().get("job_assignment"), grain=self.path[-1][0],
                schema=self.interpret_schema, source=self)
            self.report_values = admitted
            # Source metadata can expose private request/capture identifiers.
            # The host-filled report basis has the same account_binding rules as
            # model-selected report references; visibility alone is no grant.
            self.report_basis = [ref for ref in actual_context["visible_record_refs"]
                if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {"status": "invalid", "category": "report_format",
                             "detail": getattr(error, "diagnostic", {"code": "invalid_report_update"})}
        if isinstance(unit, _runtime.ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, _runtime.ReportRedelivery) else 'selected')
        return unit

    async def execute(self, selection, index):
        journal = self.workflow.journal
        old = journal.row("runtime_actions", self.episode_id, index)
        if old and _runtime.json.loads(old["action"]) != selection:
            raise _runtime.WorkflowError("reconstructed selected work changed")
        if old and old["result"] is not None:
            result, credit = _runtime.json.loads(old["result"]), old["credit"]
        else:
            if self.path[-1][0] == 'scientific_process':
                self.workflow.scientific_process_binding.validate_execution_context(
                    self.workflow.binding_context(self))
            journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                "action": _runtime._json(selection), "result": None, "credit": None})
            key = f"{self.workflow.run_id}:{self.episode_id}:{index}"
            with journal.measure("runtime_actions", self.episode_id, index):
                if selection["kind"] == "reason":
                    payload = selection['commit']
                    account_binding = ({'account_invocation': (self.workflow.run_id, self.episode_id)}
                                 if payload.get('interpretation_accounts') else {})
                    specialist = self.workflow.specialist(self)
                    execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                    result = (execute_reasoning(self.workflow.binding_context(self), selection, key)
                              if execute_reasoning is not None else None)
                    if result is None:
                        result = self.workflow.store.commit_reasoning(payload, self.scope, key, **account_binding)
                elif selection['kind'] == 'wait':
                    try:
                        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                    except _runtime.EventTargetError as error:
                        # An original unfinished selection (including restore)
                        # must return to the ordinary failed-action repair path.
                        # Its immutable wait request/timing remain unchanged.
                        result = {'status': 'failed', 'record_refs': [],
                            'changed_record_refs': [], 'result': None,
                            'feedback': _runtime._wait_target_feedback(error, status='failed')}
                else:
                    result = self.workflow.execute(self, selection["tool"], selection["arguments"],
                        decision_index=index, operation_key=key)
                if _runtime.inspect.isawaitable(result):
                    result = await result
            if (self.workflow.execution_binding is not None
                    or self.workflow.wait_inputs_version == 'wait_inputs_binding_v2'
                    or self.workflow.completed_action_inputs_version is not None):
                result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else _runtime.nullcontext()):
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _runtime._json(selection), "result": _runtime._json(result), "credit": None})
                self.last_outcome, self.last_outcome_index = result, index
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'],
                        'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        # Project from the recorded outcome. A crash between result publication
        # and projection resumes here without repeating the native operation.
        observed_outcome = _runtime.observes_action_outcome(selection['kind'], result['status'])
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else _runtime.nullcontext()):
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        if credit is None and observed_outcome and selection['kind'] != 'wait':
            # Native publication and its received inputs are committed before
            # an owner requests a one-shot scientific judgment. The judgment is
            # part of this same selected action, with no new episode or yield.
            result = await self.workflow.automatic_score_updates(self, index, result)
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else _runtime.nullcontext()):
            if credit is None and observed_outcome:
                if selection['kind'] == 'wait':
                    credit = self.workflow.last_observed_credit(self)
                else:
                    credit_view = self.workflow.source_credit_view(self)
                    credit = credit_view['credit']
                    if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                        self.workflow.retain_shared_grading_results(self, result, credit_view)
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _runtime._json(selection), "result": _runtime._json(result), "credit": credit})
            if self.workflow.execution_binding is not None and observed_outcome:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}",
                    kind='own_action', controller_input=self.workflow.controller_value(self, index, credit),
                    child_return=None)
                self.last_outcome, self.last_outcome_index = result, index
                self.checkpoint()
        # Tools own query bounds; never reclip a selected evidence page here.
        self.last_outcome = result
        self.last_outcome_index = index
        if not observed_outcome:
            raise _runtime.ActionFailure(result.get("feedback") or {"status": result["status"],
                "category": result.get("error_code", "work_failed")})
        return self.workflow.controller_value(self, index, credit)

