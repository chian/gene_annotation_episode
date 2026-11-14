"""A104 original library/decision_source_exchange defining responsibilities."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def conversation_key(self):
    callback = getattr(self.workflow.provider, 'conversation_key', None)
    return None if callback is None else callback(self.episode_id, 'REASONING')

def interpretation_context(self, context, exchanges):
    subset = getattr(self.workflow.store, 'reference_subset', None)
    received = [row['lookup_result'] for row in exchanges if row.get('lookup_result_recorded', row.get('lookup_result') is not None)]
    publications = []
    for result in received:
        if isinstance(result, Mapping):
            for record in result.get('records', []):
                if isinstance(record, Mapping):
                    publications.extend(record.get('published_references', {}).get('values', []))
    references = _references_in({'record_refs': publications}, self.workflow.store.get, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
    return {**context, 'visible_record_refs': list(dict.fromkeys([*context.get('visible_record_refs', []), *references]))}

def exchange_schema(self, schema):
    return _object({'response': {'anyOf': [_object({'response_type': {'type': 'string', 'const': 'request_context'}, 'lookup': composition_lookup_schema(self.workflow, self)}), _object({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})]}})

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
        Draft202012Validator(lookup_contract if lookup_contract is not None else composition_lookup_schema(self.workflow, self)).validate(body['lookup'])
    elif kind == 'select_action':
        if set(body) != {'response_type', 'selection', 'report_update'}:
            raise ValueError('invalid_select_action_response')
    else:
        raise ValueError('unknown_decision_response_type')
    return body

def validate_contract_exchange_request(self, request, saved, index, snapshot, public):
    """Authenticate a new-profile frame against its original host records."""
    record = self.workflow.validate_contract_information(saved)
    if request.get('instructions') != record['instructions'] or not _recorded_action_generation_schema(request.get('output_schema'), record['exchange_schema']) or request.get('restoration') != {'snapshot': snapshot, 'pending_public_exchanges': public}:
        raise WorkflowError('original_contract_exchange_request_mismatch')
    frame = request.get('context', {})
    try:
        if frame.get('kind') == 'decision_lookup_result':
            if not public:
                raise ValueError('lookup_requires_received_information')
            expected = {'version': DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result', 'decision_index': index, 'exchange_index': public[-1]['exchange_index'], 'result': public[-1]['lookup_result'], 'pending_contract_information': requested_contract_information(public)}
            if frame != expected:
                raise ValueError('lookup_frame_differs')
        else:
            previous = None
            if frame.get('kind') == 'decision_update':
                older = self.workflow.decision_exchanges.rows(self.episode_id, index - 1) if index else []
                if not older:
                    raise ValueError('original_update_base_unavailable')
                previous = older[0]['request']['restoration']['snapshot']
            if _json(apply_state_frame(previous, frame)) != _json(snapshot):
                raise ValueError('frame_differs_from_original_snapshot')
            restored = frame.get('restored_public_exchanges')
            if restored is not None and (restored != public or frame.get('restored_pending_decision_index') != index):
                raise ValueError('restored_information_differs')
            if public and restored is None:
                raise ValueError('restored_information_missing')
    except (ValueError, TypeError, KeyError) as error:
        raise WorkflowError('original_contract_exchange_frame_mismatch') from error

def validate_contract_exchange_history(self, saved, index):
    """Validate saved exchanges without dispatch, state writes or factories."""
    record = self.workflow.validate_contract_information(saved)
    rows = self.workflow.decision_exchanges.rows(self.episode_id, index)
    if not rows:
        return
    snapshot = rows[0]['request']['restoration']['snapshot']
    expected = instructional_model_context(model_snapshot(saved['context'], snapshot['action_yields']))
    if _json(expected) != _json(snapshot):
        raise WorkflowError('original_contract_decision_snapshot_mismatch')
    lookup = record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
    public = []
    for position, row in enumerate(rows):
        self.validate_contract_exchange_request(row['request'], saved, index, snapshot, public)
        if not row['response_recorded']:
            if position + 1 < len(rows) and rows[position + 1]['request'].get('retry_of_exchange_index') != row['exchange_index']:
                raise WorkflowError('original_contract_exchange_retry_mismatch')
            continue
        try:
            body = self.exchange_response(row['response'], lookup_contract=lookup)
        except (ValueError, TypeError, ValidationError):
            body = None
        if body is not None and body['response_type'] == 'select_action':
            if position != len(rows) - 1:
                raise WorkflowError('original_contract_exchange_after_selection')
            original = self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
            selected = {key: body[key] for key in ('selection', 'report_update')}
            if original['response'] is not None and _json(json.loads(original['response'])) != _json(selected):
                raise WorkflowError('original_contract_selected_response_mismatch')
            return
        if row['lookup_result_recorded']:
            query = body['lookup'] if body is not None and body['response_type'] == 'request_context' else None
            contract_query = query is not None and query.get('view') == 'composition_information' and (query.get('operation') in CONTRACT_INFORMATION_OPERATIONS)
            if is_contract_information(row['lookup_result']) and (not contract_query):
                raise WorkflowError('original_contract_information_query_mismatch')
            if contract_query:
                result = self.workflow.contract_information_reply(saved, record, query['operation'], query['arguments'])
                if _json(row['lookup_result']) != _json(result):
                    raise WorkflowError('original_contract_information_reply_mismatch')
            public.append({'exchange_index': row['exchange_index'], 'response': row['response'], 'lookup_result': row['lookup_result']})
        elif position + 1 < len(rows):
            raise WorkflowError('original_contract_information_reply_missing')

async def exchange_decision(self, context, schema, index, saved):
    """Retrieve own received information while this one decision is pending.

        This loop services the explicit model exchange protocol. It never
        selects/executes work, changes interpretations or invokes a controller.
        Every actual model dispatch has its own immutable request and timing.
        """
    exchanges, journal = (self.workflow.decision_exchanges, self.workflow.journal)
    rows = exchanges.rows(self.episode_id, index)
    contract_record = self.workflow.validate_contract_information(saved) if 'contract_information' in saved else None
    lookup_contract = contract_record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup'] if contract_record is not None else None
    if contract_record is not None:
        self.validate_contract_exchange_history(saved, index)
    if rows:
        snapshot = rows[0]['request']['restoration']['snapshot']
        instructions = rows[0]['request']['instructions']
        output_schema = rows[0]['request']['output_schema']
    else:
        parameters = _category_yield_parameters(self.workflow.controller_binding)
        if isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit':
            table = {'version': 'annotation_axis_yield_table_v1', 'rows': context['controller']['arms'], 'forecast_unit': 'another_whole_axis_invocation', 'source': 'actual_root_controller'}
        else:
            table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
        snapshot = model_snapshot(context, table)
        instructions = contract_record['instructions'] if contract_record is not None else self.instructions(context) + '\n' + self.workflow.services.decision_exchange_instructions()
        output_schema = _action_generation_schema(contract_record['exchange_schema'] if contract_record is not None else self.exchange_schema(schema))
    snapshot = instructional_model_context(snapshot)
    public = []
    cursor = 0
    while True:
        if cursor + 1 < len(rows) and (not rows[cursor]['response_recorded']) and (rows[cursor + 1]['request'].get('retry_of_exchange_index') == cursor):
            cursor += 1
            continue
        if cursor < len(rows) and rows[cursor]['response_recorded']:
            current = rows[cursor]
        else:
            retry = rows[cursor] if cursor < len(rows) else None
            exchange_index = len(rows)
            key = self.conversation_key()
            continuing = key is not None and key == self._presented_conversation_key and (self._model_snapshot is not None) and (retry is None)
            if continuing and public:
                frame = {'version': DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result', 'decision_index': index, 'exchange_index': public[-1]['exchange_index'], 'result': public[-1]['lookup_result']}
                if contract_record is not None:
                    frame['pending_contract_information'] = requested_contract_information(public)
            else:
                frame = state_frame(snapshot, self._model_snapshot if continuing else None)
                if not continuing and (public or retry is not None):
                    frame['restored_public_exchanges'] = _plain(public)
                    frame['restored_pending_decision_index'] = index
            request = {'context': instructional_model_context(frame), 'output_schema': output_schema, 'instructions': instructions, 'restoration': {'snapshot': snapshot, 'pending_public_exchanges': public}, 'conversation_key': _plain(key)}
            if retry is not None:
                request['retry_of_exchange_index'] = retry['exchange_index']
            if contract_record is not None:
                self.validate_contract_exchange_request(request, saved, index, snapshot, public)
            current = exchanges.prepare(self.episode_id, index, exchange_index, request)
            rows.append(current)
            cursor = exchange_index
            with journal.measure('runtime_model_calls', self.episode_id, index):
                with exchanges.measure(self.episode_id, index, exchange_index):
                    response = await self.workflow.provider.complete(self.episode_id, 'REASONING', request['instructions'], request['context'], request['output_schema'])
            current = exchanges.respond(self.episode_id, index, exchange_index, response)
            rows[cursor] = current
            self._model_snapshot = snapshot
            after_key = self.conversation_key()
            self._presented_conversation_key = after_key if key is None and (after_key is None or after_key[1] == 0) else key
        try:
            body = self.exchange_response(current['response'], lookup_contract=lookup_contract)
        except (ValueError, TypeError, ValidationError) as error:
            body = None
            result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange', 'code': 'invalid_decision_response', 'detail': schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
        if body is not None and body['response_type'] == 'select_action':
            response = {key: body[key] for key in ('selection', 'report_update')}
            journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': _json(response)})
            return (response, index, self.interpretation_context(context, public), schema)
        if current['lookup_result_recorded']:
            result = current['lookup_result']
        else:
            if body is not None:
                try:
                    query = body['lookup']
                    if query['view'] == 'child_options':
                        result = child_option_information(self.workflow, self, query['role'])
                    elif query['view'] == 'composition_information':
                        result = await self.workflow.execute(self, query['operation'], query['arguments'], decision_index=index, operation_key=f"{self.workflow.run_id}:{self.episode_id}:decision:{index}:exchange:{current['exchange_index']}:composition", _composition_lookup=True)
                    else:
                        result = lookup_attempts(journal, self.episode_id, before=index, query=query)
                except (ValueError, TypeError, ValidationError) as error:
                    result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange', 'code': 'invalid_own_attempt_lookup', 'detail': schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
                except (OSError, sqlite3.Error) as error:
                    result = {'status': 'failed', 'feedback': {'category': 'decision_exchange', 'code': 'own_attempt_lookup_failed', 'exception_type': type(error).__name__}}
            current = exchanges.resolve_lookup(self.episode_id, index, current['exchange_index'], result)
            rows[cursor] = current
        public.append({'exchange_index': current['exchange_index'], 'response': current['response'], 'lookup_result': result})
        cursor += 1


def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['conversation_key', 'interpretation_context', 'exchange_schema', 'exchange_response', 'validate_contract_exchange_request', 'validate_contract_exchange_history', 'exchange_decision']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'conversation_key': 'DecisionSource.conversation_key', 'interpretation_context': 'DecisionSource.interpretation_context', 'exchange_schema': 'DecisionSource.exchange_schema', 'exchange_response': 'DecisionSource.exchange_response', 'validate_contract_exchange_request': 'DecisionSource.validate_contract_exchange_request', 'validate_contract_exchange_history': 'DecisionSource.validate_contract_exchange_history', 'exchange_decision': 'DecisionSource.exchange_decision'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
