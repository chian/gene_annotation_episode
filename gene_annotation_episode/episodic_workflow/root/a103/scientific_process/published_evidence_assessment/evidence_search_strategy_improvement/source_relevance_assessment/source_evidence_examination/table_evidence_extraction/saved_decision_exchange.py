"""Private A103 literature_table call."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table

class SourceSavedDecisionExchange:


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
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
