"""Original local terminal task source_actions with explicitly accounted fixed-role branches."""
from __future__ import annotations
import json
import inspect
from contextlib import nullcontext
from jsonschema import Draft202012Validator, ValidationError
from ...method_loop import ReportRedelivery
from ...episode_journal import WorkflowError
from ...task_action_contracts import _decode_recorded_action_response
from ...task_action_units import ActionFailure
from ...task_values import _json
from ...communication import ReportBoundaryError, validate_form
from ...episode_contract_information import ContractInformationError
from ...boundary_validation import schema_failure_diagnostic
from ...episode_completion import observes_action_outcome


class LocalTaskActionOutcomes:
    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = (self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
                if original is None and self.workflow.decision_exchanges is not None else None)
            saved = {} if call is None else json.loads(call['request'])
            response = _decode_recorded_action_response(response, schema,
                recorded_selection=None if original is None else json.loads(original['action']),
                exchanges=() if original is not None or self.workflow.decision_exchanges is None else
                    self.workflow.decision_exchanges.rows(self.episode_id, index),
                exchange_schema=saved.get('contract_information', {}).get('exchange_schema'))
            # Validate selection independently: report formatting must not
            # reject a valid scientific contribution or alter its credit.
            selection = response["selection"]
            if self._delivery_resolution_ref is not None:
                Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            Draft202012Validator(schema["properties"]["selection"]).validate(selection)
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
                unit = self.workflow.selected(self, selection, index)
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            self.feedback = {"status": "invalid", "category": "action_contract",
                "detail": (schema_failure_diagnostic(error)
                           if isinstance(error, ValidationError) else str(error))}
            if isinstance(error, ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = (
                        'schema_json must encode a JSON Schema object with the explicit top-level '
                        'field "type": "object" and a properties object. Keep the intended properties, '
                        'declare every field in required, and set additionalProperties to false. '
                        'A properties object alone does not declare the required outer type.')
                if isinstance(error.__cause__, ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = validate_form(response["report_update"], self.interpret_schema,
                resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope,
                assignment=self.request.message.as_record().get("job_assignment"), grain=self.path[-1][0],
                schema=self.interpret_schema, source=self)
            self.report_values = admitted
            # Source metadata can expose private request/capture identifiers.
            # The host-filled report basis has the same ownership rules as
            # model-selected report references; visibility alone is no grant.
            self.report_basis = [ref for ref in actual_context["visible_record_refs"]
                if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {"status": "invalid", "category": "report_format",
                             "detail": getattr(error, "diagnostic", {"code": "invalid_report_update"})}
        if isinstance(unit, ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, ReportRedelivery) else 'selected')
        return unit

    async def execute(self, selection, index):
        if selection.get('kind') != 'tool':
            raise ValueError('fixed_terminal_tool_selection_required')
        journal = self.workflow.journal
        old = journal.row("runtime_actions", self.episode_id, index)
        if old and json.loads(old["action"]) != selection:
            raise WorkflowError("reconstructed selected work changed")
        if old and old["result"] is not None:
            result, credit = json.loads(old["result"]), old["credit"]
        else:
            journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                "action": _json(selection), "result": None, "credit": None})
            key = f"{self.workflow.run_id}:{self.episode_id}:{index}"
            with journal.measure("runtime_actions", self.episode_id, index):
                result = self.workflow.execute(self, selection["tool"], selection["arguments"],
                    decision_index=index, operation_key=key)
                if inspect.isawaitable(result):
                    result = await result
            result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _json(selection), "result": _json(result), "credit": None})
                self.last_outcome, self.last_outcome_index = result, index
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'],
                        'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        # Project from the recorded outcome. A crash between result publication
        # and projection resumes here without repeating the native operation.
        observed_outcome = observes_action_outcome(selection['kind'], result['status'])
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
            if credit is None and observed_outcome:
                credit_view = self.workflow.source_credit_view(self)
                credit = credit_view['credit']
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _json(selection), "result": _json(result), "credit": credit})
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
            raise ActionFailure(result.get("feedback") or {"status": result["status"],
                "category": result.get("error_code", "work_failed")})
        return self.workflow.controller_value(self, index, credit)

