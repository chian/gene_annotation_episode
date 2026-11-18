"""Private A104 source task decision."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table


class SourceTaskDecisionExchange:

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
                        response = await self.decision_completion()(self.episode_id, 'REASONING', request['instructions'], request['context'], request['output_schema'])
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



def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'SourceTaskDecisionExchange.exchange_decision': SourceTaskDecisionExchange.__dict__['exchange_decision']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.decision_exchange')
    setattr(SourceTaskDecisionExchange, 'exchange_decision', bound['SourceTaskDecisionExchange.exchange_decision'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
