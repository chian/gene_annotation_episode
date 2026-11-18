"""Private A103 literature_targeted call."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table

class SourceDecisionContracts:


    def exchange_schema(self, schema):
        return _live_original_runtime._object({'response': {'anyOf': [_live_original_runtime._object({'response_type': {'type': 'string', 'const': 'request_context'}, 'lookup': _live_original_runtime.composition_lookup_schema(self.workflow, self)}), _live_original_runtime._object({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})]}})


    def exchange_response(self, response, *, lookup_contract=None):
        """Validate the exchange envelope; ordinary action admission stays intact.

        The existing action path deliberately admits independent valid reasoning
        rows and preserves scientific work when report values need repair. Do
        not replace those rules with a whole-action schema gate here.
        """
        if not isinstance(response, dict) or set(response) != {'response'}:
            raise ValueError('decision_response_envelope_required')
        body = response['response']
        if not isinstance(body, dict):
            raise ValueError('decision_response_object_required')
        kind = body.get('response_type')
        if kind == 'request_context':
            if set(body) != {'response_type', 'lookup'}:
                raise ValueError('invalid_request_context_response')
            _live_original_runtime.Draft202012Validator(lookup_contract if lookup_contract is not None else _live_original_runtime.composition_lookup_schema(self.workflow, self)).validate(body['lookup'])
        elif kind == 'select_action':
            if set(body) != {'response_type', 'selection', 'report_update'}:
                raise ValueError('invalid_select_action_response')
        else:
            raise ValueError('unknown_decision_response_type')
        return body
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
