"""Private A106 results task decision."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table

from .decision_presentation import decision_yield_table

class OperationalTaskDecision:

    async def call(self, context, schema):
        index, self.calls = (self.calls, self.calls + 1)
        journal = self.workflow.journal
        row = journal.row('runtime_model_calls', self.episode_id, index)
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = json.loads(row['request'])
            if row['purpose'] != 'decision':
                raise WorkflowError('saved decision contract differs from reconstruction')
            schema = saved['schema']
            context = saved['context']
            try:
                _recorded_assignment_transport(saved)
            except ValueError as error:
                raise WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if 'literature_numerical_contracts' in saved:
                if profile is not None:
                    raise WorkflowError('original_literature_numerical_profile_mismatch')
                self.workflow.numerical_contracts().validate_frozen_contracts(saved)
            if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL and saved.get('decision_protocol') != DECISION_EXCHANGE_PROTOCOL:
                raise WorkflowError('pending_decision_requires_original_protocol')
            if row['response'] is not None:
                if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context, self.workflow.decision_exchanges.rows(self.episode_id, index))
                return (json.loads(row['response']), index, context, schema)
        else:
            context = self.decision_inputs(context, index, profile)
            saved = {'context': context, 'schema': schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved['literature_numerical_contracts'] = frozen
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if self.workflow.receipts is not None and (not self.workflow.uses_received_record_context(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, 'has_session', lambda *_: False)
        if not has_session(self.episode_id, 'REASONING') and 'restored_episode_history' not in context:
            context = {**context, 'restored_episode_history': self.workflow.history_preview(self, before=index)}
        context = instructional_model_context(context)
        transport = saved.get('assignment_transport') if row is not None else {'version': _ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _digest(schema)}
        saved = {'context': context, 'schema': schema, **({'literature_numerical_contracts': saved['literature_numerical_contracts']} if 'literature_numerical_contracts' in saved else {})}
        if transport is not None:
            saved['assignment_transport'] = transport
        if self.workflow.receipts is not None and (not self.workflow.uses_received_record_context(self)):
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
        with journal.measure('runtime_model_calls', self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, 'REASONING', instructions, context, _action_generation_schema(schema))
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': _json(response)})
        return (response, index, saved['context'], schema)

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
            table = decision_yield_table(self, context, journal, index)
            snapshot = _a106_original_global_model_snapshot()(context, table)
            instructions = contract_record['instructions'] if contract_record is not None else self.instructions(context) + '\n' + self.workflow.services.decision_exchange_instructions()
            output_schema = _a106_original_global__action_generation_schema()(contract_record['exchange_schema'] if contract_record is not None else self.exchange_schema(schema))
        snapshot = _a106_original_global_instructional_model_context()(snapshot)
        public = []
        cursor = 0
        while True:
            if cursor + 1 < _a106_original_global_len()(rows) and (not rows[cursor]['response_recorded']) and (rows[cursor + 1]['request'].get('retry_of_exchange_index') == cursor):
                cursor += 1
                continue
            if cursor < _a106_original_global_len()(rows) and rows[cursor]['response_recorded']:
                current = rows[cursor]
            else:
                retry = rows[cursor] if cursor < _a106_original_global_len()(rows) else None
                exchange_index = _a106_original_global_len()(rows)
                key = self.conversation_key()
                continuing = key is not None and key == self._presented_conversation_key and (self._model_snapshot is not None) and (retry is None)
                if continuing and public:
                    frame = {'version': _a106_original_global_DECISION_CONTEXT_VERSION(), 'kind': 'decision_lookup_result', 'decision_index': index, 'exchange_index': public[-1]['exchange_index'], 'result': public[-1]['lookup_result']}
                    if contract_record is not None:
                        frame['pending_contract_information'] = _a106_original_global_requested_contract_information()(public)
                else:
                    frame = _a106_original_global_state_frame()(snapshot, self._model_snapshot if continuing else None)
                    if not continuing and (public or retry is not None):
                        frame['restored_public_exchanges'] = _a106_original_global__plain()(public)
                        frame['restored_pending_decision_index'] = index
                request = {'context': _a106_original_global_instructional_model_context()(frame), 'output_schema': output_schema, 'instructions': instructions, 'restoration': {'snapshot': snapshot, 'pending_public_exchanges': public}, 'conversation_key': _a106_original_global__plain()(key)}
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
            except (_a106_original_global_ValueError(), _a106_original_global_TypeError(), _a106_original_global_ValidationError()) as error:
                body = None
                result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange', 'code': 'invalid_decision_response', 'detail': _a106_original_global_schema_failure_diagnostic()(error) if _a106_original_global_isinstance()(error, _a106_original_global_ValidationError()) else _a106_original_global_str()(error)}}
            if body is not None and body['response_type'] == 'select_action':
                response = {key: body[key] for key in ('selection', 'report_update')}
                journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _a106_original_global__json()(saved), 'response': _a106_original_global__json()(response)})
                return (response, index, self.interpretation_context(context, public), schema)
            if current['lookup_result_recorded']:
                result = current['lookup_result']
            else:
                if body is not None:
                    try:
                        query = body['lookup']
                        if query['view'] == 'child_options':
                            result = _a106_original_global_child_option_information()(self.workflow, self, query['role'])
                        elif query['view'] == 'composition_information':
                            result = await self.workflow.execute(self, query['operation'], query['arguments'], decision_index=index, operation_key=f"{self.workflow.run_id}:{self.episode_id}:decision:{index}:exchange:{current['exchange_index']}:composition", _composition_lookup=True)
                        else:
                            result = _a106_original_global_lookup_attempts()(journal, self.episode_id, before=index, query=query)
                    except (_a106_original_global_ValueError(), _a106_original_global_TypeError(), _a106_original_global_ValidationError()) as error:
                        result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange', 'code': 'invalid_own_attempt_lookup', 'detail': _a106_original_global_schema_failure_diagnostic()(error) if _a106_original_global_isinstance()(error, _a106_original_global_ValidationError()) else _a106_original_global_str()(error)}}
                    except (_a106_original_global_OSError(), _a106_original_global_sqlite3().Error) as error:
                        result = {'status': 'failed', 'feedback': {'category': 'decision_exchange', 'code': 'own_attempt_lookup_failed', 'exception_type': _a106_original_global_type()(error).__name__}}
                current = exchanges.resolve_lookup(self.episode_id, index, current['exchange_index'], result)
                rows[cursor] = current
            public.append({'exchange_index': current['exchange_index'], 'response': current['response'], 'lookup_result': result})
            cursor += 1


def _a106_original_global_DECISION_CONTEXT_VERSION():
    return DECISION_CONTEXT_VERSION


def _a106_original_global_OSError():
    return OSError


def _a106_original_global_TypeError():
    return TypeError


def _a106_original_global_ValidationError():
    return ValidationError


def _a106_original_global_ValueError():
    return ValueError


def _a106_original_global__action_generation_schema():
    return _action_generation_schema


def _a106_original_global__json():
    return _json


def _a106_original_global__plain():
    return _plain


def _a106_original_global_child_option_information():
    return child_option_information


def _a106_original_global_instructional_model_context():
    return instructional_model_context


def _a106_original_global_isinstance():
    return isinstance


def _a106_original_global_len():
    return len


def _a106_original_global_lookup_attempts():
    return lookup_attempts


def _a106_original_global_model_snapshot():
    return model_snapshot


def _a106_original_global_requested_contract_information():
    return requested_contract_information


def _a106_original_global_schema_failure_diagnostic():
    return schema_failure_diagnostic


def _a106_original_global_sqlite3():
    return sqlite3


def _a106_original_global_state_frame():
    return state_frame


def _a106_original_global_str():
    return str


def _a106_original_global_type():
    return type


def _bind_original_task_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a106.library.live_runtime_functions import bind_functions
    names = {'call': 'OperationalTaskDecision.call', 'interpretation_context': 'OperationalTaskDecision.interpretation_context', 'exchange_schema': 'OperationalTaskDecision.exchange_schema', 'exchange_response': 'OperationalTaskDecision.exchange_response', 'validate_contract_exchange_request': 'OperationalTaskDecision.validate_contract_exchange_request', 'validate_contract_exchange_history': 'OperationalTaskDecision.validate_contract_exchange_history', 'conversation_key': 'OperationalTaskDecision.conversation_key'}
    functions = bind_functions(namespace, {name: OperationalTaskDecision.__dict__[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names, defining_module='gene_annotation_episode.episodic_workflow.root.a106.published_evidence_assessment.execution_result_acquisition.task_decision')
    for name, function in functions.items():
        setattr(OperationalTaskDecision, name, function)
    getters = {'_a106_original_global_DECISION_CONTEXT_VERSION': '_a106_original_global_DECISION_CONTEXT_VERSION', '_a106_original_global_OSError': '_a106_original_global_OSError', '_a106_original_global_TypeError': '_a106_original_global_TypeError', '_a106_original_global_ValidationError': '_a106_original_global_ValidationError', '_a106_original_global_ValueError': '_a106_original_global_ValueError', '_a106_original_global__action_generation_schema': '_a106_original_global__action_generation_schema', '_a106_original_global__json': '_a106_original_global__json', '_a106_original_global__plain': '_a106_original_global__plain', '_a106_original_global_child_option_information': '_a106_original_global_child_option_information', '_a106_original_global_instructional_model_context': '_a106_original_global_instructional_model_context', '_a106_original_global_isinstance': '_a106_original_global_isinstance', '_a106_original_global_len': '_a106_original_global_len', '_a106_original_global_lookup_attempts': '_a106_original_global_lookup_attempts', '_a106_original_global_model_snapshot': '_a106_original_global_model_snapshot', '_a106_original_global_requested_contract_information': '_a106_original_global_requested_contract_information', '_a106_original_global_schema_failure_diagnostic': '_a106_original_global_schema_failure_diagnostic', '_a106_original_global_sqlite3': '_a106_original_global_sqlite3', '_a106_original_global_state_frame': '_a106_original_global_state_frame', '_a106_original_global_str': '_a106_original_global_str', '_a106_original_global_type': '_a106_original_global_type'}
    globals().update(bind_functions(namespace, {name: globals()[name] for name in getters},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=getters, defining_module='gene_annotation_episode.episodic_workflow.root.a106.published_evidence_assessment.execution_result_acquisition.task_decision'))

from gene_annotation_episode.episodic_workflow.root.a106 import runtime as _a106_original_runtime
_bind_original_task_runtime_providers(vars(_a106_original_runtime))
