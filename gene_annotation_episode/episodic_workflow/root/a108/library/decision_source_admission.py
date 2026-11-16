"""Shared original source protocol decision_source_admission."""
from __future__ import annotations


def apply_response(self, response, index, actual_context, schema):
    selection = None
    try:
        original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
        call = self.workflow.journal.row('runtime_model_calls', self.episode_id, index) if original is None and self.workflow.decision_exchanges is not None else None
        saved = {} if call is None else _original_runtime.json.loads(call['request'])
        response = _original_runtime._decode_recorded_action_response(response, schema, recorded_selection=None if original is None else _original_runtime.json.loads(original['action']), exchanges=() if original is not None or self.workflow.decision_exchanges is None else self.workflow.decision_exchanges.rows(self.episode_id, index), exchange_schema=saved.get('contract_information', {}).get('exchange_schema'))
        selection = response['selection']
        if self._delivery_resolution_ref is not None:
            _original_runtime.Draft202012Validator(schema).validate(response)
            if response['report_update'] != self.report_values:
                raise ValueError('delivery_resolution_must_preserve_current_interpretation')
        if self.workflow.permits_common_action(self, 'reason') and isinstance(selection, _original_runtime.Mapping) and (selection.get('kind') == 'reason'):
            envelope = self.workflow.reasoning_action_schema(self, {'type': 'object'})
            _original_runtime.Draft202012Validator(envelope).validate(selection)
            payload = selection['commit']
            commit_schema = self.workflow.store.reasoning_schema()
            if set(commit_schema.get('required', commit_schema['properties'])) <= set(payload) <= set(commit_schema['properties']) and all((value == [] for value in payload.values())) and (selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                binding = self.workflow.specialist(self)
                has_task_content = getattr(binding, 'reasoning_has_task_content', None)
                if has_task_content is None or not has_task_content(self.workflow.binding_context(self), selection):
                    raise ValueError('empty_reasoning_commit')
        else:
            _original_runtime.Draft202012Validator(schema['properties']['selection']).validate(selection)
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
            unit = self.workflow.selected(self, selection, index)
    except _original_runtime.EventTargetError as error:
        self.feedback = _original_runtime._wait_target_feedback(error, status='invalid')
        self.record_effect(index, 'rejected')
        return None
    except (OSError, _original_runtime.sqlite3.Error, _original_runtime.subprocess.SubprocessError, _original_runtime.AcquisitionError) as error:
        if not isinstance(selection, _original_runtime.Mapping) or selection.get('kind') != 'job_child':
            raise
        handoff = selection.get('handoff') or {}
        self.feedback = {'status': 'failed', 'category': 'job_assignment', 'code': error.code if isinstance(error, _original_runtime.AcquisitionError) else 'job_storage_failed' if isinstance(error, _original_runtime.sqlite3.Error) else 'job_control_failed' if isinstance(error, _original_runtime.subprocess.SubprocessError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'role': selection['role'], 'job_ref': selection.get('existing_job_ref', handoff.get('job_ref'))}
        self.record_effect(index, 'rejected')
        return None
    except (ValueError, KeyError, TypeError, _original_runtime.ValidationError) as error:
        self.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': _original_runtime.schema_failure_diagnostic(error) if isinstance(error, _original_runtime.ValidationError) else str(error)}
        if isinstance(error, _original_runtime.ContractInformationError):
            self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
            if error.code == 'closed_top_level_form_required':
                self.feedback['repair'] = 'schema_json must encode a JSON Schema object with the explicit top-level field "type": "object" and a properties object. Keep the intended properties, declare every field in required, and set additionalProperties to false. A properties object alone does not declare the required outer type.'
            if isinstance(error.__cause__, _original_runtime.ReportBoundaryError):
                self.feedback['schema_reason'] = str(error.__cause__)
        if isinstance(error, _original_runtime.ContractError) and str(error) == 'component_native_return_channels_required':
            self.feedback['contract_error'] = {'code': str(error), 'field': error.detail['field']}
            self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
            self.feedback['repair'] = error.detail['repair']
        self.record_effect(index, 'rejected')
        return None
    try:
        resolve_report_reference = self.workflow.resolver(self.scope, source=self)
        admitted = _original_runtime.validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
        self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain=self.path[-1][0], schema=self.interpret_schema, source=self)
        self.report_values = admitted
        self.report_basis = [ref for ref in actual_context['visible_record_refs'] if resolve_report_reference(ref)]
        self.feedback = None
    except (ValueError, KeyError, TypeError) as error:
        self.feedback = {'status': 'invalid', 'category': 'report_format', 'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}
    if isinstance(unit, _original_runtime.ReportRedelivery):
        self.feedback = None if unit.failure is None else unit.failure.as_record()
    self.record_effect(index, 'redelivery' if isinstance(unit, _original_runtime.ReportRedelivery) else 'selected')
    return unit

from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime
