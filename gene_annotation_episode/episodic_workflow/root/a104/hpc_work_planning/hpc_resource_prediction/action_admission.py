"""Private prediction task."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import ActionFailure, ContractInformationError, Draft202012Validator, EventTargetError, ReportBoundaryError, SourceEnd, ValidationError, WorkflowError, _decode_recorded_action_response, _json, _wait_target_feedback, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form
from .task_state import PredictionTaskState
from .task_decision import PredictionTaskDecision
from .waiting import PredictionSuspension
from .report_delivery import PredictionReportDelivery
from .decision_state import PredictionDecisionState

from .task_instructions import instructions as _instruction_composer

class ResourcePredictionTaskAdmission:

    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = self.workflow.journal.row('runtime_model_calls', self.episode_id, index) if original is None and self.workflow.decision_exchanges is not None else None
            saved = {} if call is None else json.loads(call['request'])
            response = _decode_recorded_action_response(response, schema, recorded_selection=None if original is None else json.loads(original['action']), exchanges=() if original is not None or self.workflow.decision_exchanges is None else self.workflow.decision_exchanges.rows(self.episode_id, index), exchange_schema=saved.get('contract_information', {}).get('exchange_schema'))
            selection = response['selection']
            Draft202012Validator(schema['properties']['selection']).validate(selection)
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
                unit = self.workflow.selected(self, selection, index)
        except EventTargetError as error:
            self.feedback = _wait_target_feedback(error, status='invalid')
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
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain='hpc_prediction', schema=self.interpret_schema, source=self)
            self.report_values = admitted
            self.report_basis = [ref for ref in actual_context['visible_record_refs'] if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {'status': 'invalid', 'category': 'report_format', 'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}
        self.record_effect(index, 'selected')
        return unit



def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'ResourcePredictionTaskAdmission.apply_response': ResourcePredictionTaskAdmission.__dict__['apply_response']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_resource_prediction.action_admission')
    setattr(ResourcePredictionTaskAdmission, 'apply_response', bound['ResourcePredictionTaskAdmission.apply_response'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
