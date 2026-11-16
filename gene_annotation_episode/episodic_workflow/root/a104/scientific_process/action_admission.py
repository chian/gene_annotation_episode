"""Private A104 scientific iterative task."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import AcquisitionError, ActionFailure, ContractError, ContractInformationError, Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, ReportBoundaryError, ReportRedelivery, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, sqlite3, subprocess, validate_form
from .task_state import ScientificTaskState
from .decision_delivery import ScientificDecisionDelivery
from .task_waiting import ScientificTaskWaiting
from .report_delivery import ScientificReportDelivery
from .task_instructions import compose_instructions

from .decision_context import ScientificTaskContext

class ScientificTaskAdmission:

    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = self.workflow.journal.row('runtime_model_calls', self.episode_id, index) if original is None and self.workflow.decision_exchanges is not None else None
            saved = {} if call is None else json.loads(call['request'])
            response = _decode_recorded_action_response(response, schema, recorded_selection=None if original is None else json.loads(original['action']), exchanges=() if original is not None or self.workflow.decision_exchanges is None else self.workflow.decision_exchanges.rows(self.episode_id, index), exchange_schema=saved.get('contract_information', {}).get('exchange_schema'), unproven_replay=getattr(self, '_unproven_direct_response_index', None) == index)
            selection = response['selection']
            if self._delivery_resolution_ref is not None:
                Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            if self.workflow.permits_common_action(self, 'reason') and isinstance(selection, Mapping) and (selection.get('kind') == 'reason'):
                envelope = self.workflow.reasoning_action_schema(self, {'type': 'object'})
                Draft202012Validator(envelope).validate(selection)
                payload = selection['commit']
                commit_schema = self.workflow.store.reasoning_schema()
                if set(commit_schema.get('required', commit_schema['properties'])) <= set(payload) <= set(commit_schema['properties']) and all((value == [] for value in payload.values())) and (selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                    binding = self.workflow.specialist(self)
                    has_task_content = getattr(binding, 'reasoning_has_task_content', None)
                    if has_task_content is None or not has_task_content(self.workflow.binding_context(self), selection):
                        raise ValueError('empty_reasoning_commit')
            else:
                Draft202012Validator(schema['properties']['selection']).validate(selection)
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
                unit = self.workflow.selected(self, selection, index)
        except EventTargetError as error:
            self.feedback = _wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (OSError, sqlite3.Error, subprocess.SubprocessError, AcquisitionError) as error:
            if not isinstance(selection, Mapping) or selection.get('kind') != 'job_child':
                raise
            handoff = selection.get('handoff') or {}
            self.feedback = {'status': 'failed', 'category': 'job_assignment', 'code': error.code if isinstance(error, AcquisitionError) else 'job_storage_failed' if isinstance(error, sqlite3.Error) else 'job_control_failed' if isinstance(error, subprocess.SubprocessError) else 'job_operation_failed', 'exception_type': type(error).__name__, 'role': selection['role'], 'job_ref': selection.get('existing_job_ref', handoff.get('job_ref'))}
            self.record_effect(index, 'rejected')
            return None
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            self.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}
            if isinstance(error, ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = 'schema_json must encode a JSON Schema object with the explicit top-level field "type": "object" and a properties object. Keep the intended properties, declare every field in required, and set additionalProperties to false. A properties object alone does not declare the required outer type.'
                if isinstance(error.__cause__, ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            if isinstance(error, ContractError) and str(error) == 'component_native_return_channels_required':
                self.feedback['contract_error'] = {'code': str(error), 'field': error.detail['field']}
                self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
                self.feedback['repair'] = error.detail['repair']
            if isinstance(error, ValidationError) and isinstance(selection, Mapping) and (selection.get('kind') == 'tool') and (selection.get('tool') == 'reads.map'):
                from gene_annotation_episode.episodic_workflow.root.a104.read_mapping import parameter_schema_failure
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
            admitted = validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain=self.path[-1][0], schema=self.interpret_schema, source=self)
            self.report_values = admitted
            self.report_basis = [ref for ref in actual_context['visible_record_refs'] if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {'status': 'invalid', 'category': 'report_format', 'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}
        if isinstance(unit, ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, ReportRedelivery) else 'selected')
        return unit



def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'ScientificTaskAdmission.apply_response': ScientificTaskAdmission.__dict__['apply_response']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.scientific_process.action_admission')
    setattr(ScientificTaskAdmission, 'apply_response', bound['ScientificTaskAdmission.apply_response'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
