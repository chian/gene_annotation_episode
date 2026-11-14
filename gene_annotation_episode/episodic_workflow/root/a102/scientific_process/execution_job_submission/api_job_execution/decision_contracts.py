"""Private API job task decision."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table
from gene_annotation_episode.episodic_workflow.root.a102.execution_prompt import is_api_launch_context
from gene_annotation_episode.episodic_workflow.root.a102.decision_context import VERSION as DECISION_CONTEXT_VERSION
from gene_annotation_episode.episodic_workflow.root.a102.library.hpc_prompt import is_hpc_context
from gene_annotation_episode.episodic_workflow.root.a102.scientific_process_prompt import is_published_scientific_context

class APITaskDecisionContracts:


    def interpretation_context(self, context, exchanges):
        subset = getattr(self.workflow.store, 'reference_subset', None)
        received = [row['lookup_result'] for row in exchanges if row.get('lookup_result_recorded', row.get('lookup_result') is not None)]
        publications = []
        for result in received:
            if isinstance(result, _live_original_runtime.Mapping):
                for record in result.get('records', []):
                    if isinstance(record, _live_original_runtime.Mapping):
                        publications.extend(record.get('published_references', {}).get('values', []))
        references = _live_original_runtime._references_in({'record_refs': publications}, self.workflow.store.get, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        return {**context, 'visible_record_refs': list(dict.fromkeys([*context.get('visible_record_refs', []), *references]))}


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


    def validate_contract_exchange_request(self, request, saved, index, snapshot, public):
        """Authenticate a new-profile frame against its original host records."""
        record = self.workflow.validate_contract_information(saved)
        if request.get('instructions') != record['instructions'] or not _live_original_runtime._recorded_action_generation_schema(request.get('output_schema'), record['exchange_schema']) or request.get('restoration') != {'snapshot': snapshot, 'pending_public_exchanges': public}:
            raise _live_original_runtime.WorkflowError('original_contract_exchange_request_mismatch')
        frame = request.get('context', {})
        try:
            if frame.get('kind') == 'decision_lookup_result':
                if not public:
                    raise ValueError('lookup_requires_received_information')
                expected = {'version': _live_original_runtime.DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result', 'decision_index': index, 'exchange_index': public[-1]['exchange_index'], 'result': public[-1]['lookup_result'], 'pending_contract_information': _live_original_runtime.requested_contract_information(public)}
                if frame != expected:
                    raise ValueError('lookup_frame_differs')
            else:
                previous = None
                if frame.get('kind') == 'decision_update':
                    older = self.workflow.decision_exchanges.rows(self.episode_id, index - 1) if index else []
                    if not older:
                        raise ValueError('original_update_base_unavailable')
                    previous = older[0]['request']['restoration']['snapshot']
                if _live_original_runtime._json(_live_original_runtime.apply_state_frame(previous, frame)) != _live_original_runtime._json(snapshot):
                    raise ValueError('frame_differs_from_original_snapshot')
                restored = frame.get('restored_public_exchanges')
                if restored is not None and (restored != public or frame.get('restored_pending_decision_index') != index):
                    raise ValueError('restored_information_differs')
                if public and restored is None:
                    raise ValueError('restored_information_missing')
        except (ValueError, TypeError, KeyError) as error:
            raise _live_original_runtime.WorkflowError('original_contract_exchange_frame_mismatch') from error


    def validate_contract_exchange_history(self, saved, index):
        """Validate saved exchanges without dispatch, state writes or factories."""
        record = self.workflow.validate_contract_information(saved)
        rows = self.workflow.decision_exchanges.rows(self.episode_id, index)
        if not rows:
            return
        snapshot = rows[0]['request']['restoration']['snapshot']
        expected = _live_original_runtime.instructional_model_context(_live_original_runtime.model_snapshot(saved['context'], snapshot['action_yields']))
        if _live_original_runtime._json(expected) != _live_original_runtime._json(snapshot):
            raise _live_original_runtime.WorkflowError('original_contract_decision_snapshot_mismatch')
        lookup = record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
        public = []
        for position, row in enumerate(rows):
            self.validate_contract_exchange_request(row['request'], saved, index, snapshot, public)
            if not row['response_recorded']:
                if position + 1 < len(rows) and rows[position + 1]['request'].get('retry_of_exchange_index') != row['exchange_index']:
                    raise _live_original_runtime.WorkflowError('original_contract_exchange_retry_mismatch')
                continue
            try:
                body = self.exchange_response(row['response'], lookup_contract=lookup)
            except (ValueError, TypeError, _live_original_runtime.ValidationError):
                body = None
            if body is not None and body['response_type'] == 'select_action':
                if position != len(rows) - 1:
                    raise _live_original_runtime.WorkflowError('original_contract_exchange_after_selection')
                original = self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
                selected = {key: body[key] for key in ('selection', 'report_update')}
                if original['response'] is not None and _live_original_runtime._json(_live_original_runtime.json.loads(original['response'])) != _live_original_runtime._json(selected):
                    raise _live_original_runtime.WorkflowError('original_contract_selected_response_mismatch')
                return
            if row['lookup_result_recorded']:
                query = body['lookup'] if body is not None and body['response_type'] == 'request_context' else None
                contract_query = query is not None and query.get('view') == 'composition_information' and (query.get('operation') in _live_original_runtime.CONTRACT_INFORMATION_OPERATIONS)
                if _live_original_runtime.is_contract_information(row['lookup_result']) and (not contract_query):
                    raise _live_original_runtime.WorkflowError('original_contract_information_query_mismatch')
                if contract_query:
                    result = self.workflow.contract_information_reply(saved, record, query['operation'], query['arguments'])
                    if _live_original_runtime._json(row['lookup_result']) != _live_original_runtime._json(result):
                        raise _live_original_runtime.WorkflowError('original_contract_information_reply_mismatch')
                public.append({'exchange_index': row['exchange_index'], 'response': row['response'], 'lookup_result': row['lookup_result']})
            elif position + 1 < len(rows):
                raise _live_original_runtime.WorkflowError('original_contract_information_reply_missing')
from gene_annotation_episode.episodic_workflow.root.a102 import runtime as _live_original_runtime
