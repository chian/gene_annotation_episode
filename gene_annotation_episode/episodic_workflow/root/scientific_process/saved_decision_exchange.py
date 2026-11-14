from __future__ import annotations
from .decision_contracts import (Mapping, nullcontext, inspect, json, sqlite3, subprocess, Draft202012Validator, ValidationError, AcquisitionError, ContractError, Episode, ReportRedelivery, SourceEnd, EventTargetError, interpretation_schema, validate_form, form_with_facts, ReportBoundaryError, WorkflowError, EFFECT_VERSION, observes_action_outcome, ContractInformationError, ActionLeaf, ActionFailure, Record, _plain, _json, _digest, _object, _action_generation_schema, _recorded_action_generation_schema, _recorded_assignment_transport, _decode_recorded_action_response, _ASSIGNMENT_TRANSPORT, _wait_target_feedback, schema_failure_diagnostic, _references_in, _category_yield_parameters, FACT_SOURCES, FACT_MEANINGS, INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT, KNOWLEDGE_INSTRUCTIONS, LAUNCH_INSTRUCTIONS, literature_numerical_contracts, DECISION_EXCHANGE_PROTOCOL, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_INSTRUCTIONS, model_snapshot, state_frame, instructional_model_context, apply_state_frame, lookup_attempts, yield_table, infernal_receiver_context, composition_lookup_schema, child_option_information, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)


from .internal_decision_presentation import ScientificInternalDecisionPresentation

class ScientificSavedDecisionExchange:

    async def exchange_decision(self, context, schema, index, saved):
        """Retrieve own received information while this one decision is pending.

        This loop services the explicit model exchange protocol. It never
        selects/executes work, changes interpretations or invokes a controller.
        Every actual model dispatch has its own immutable request and timing.
        """
        exchanges, journal = self.workflow.decision_exchanges, self.workflow.journal
        rows = exchanges.rows(self.episode_id, index)
        contract_record = (self.workflow.validate_contract_information(saved)
            if 'contract_information' in saved else None)
        lookup_contract = (contract_record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
            if contract_record is not None else None)
        if contract_record is not None:
            self.validate_contract_exchange_history(saved, index)
        if rows:
            # Presentation and statistical exposure were frozen before the
            # original dispatch. Reconstruction does not refresh either.
            snapshot = rows[0]['request']['restoration']['snapshot']
            instructions = rows[0]['request']['instructions']
            output_schema = rows[0]['request']['output_schema']
        else:
            parameters = _category_yield_parameters(self.workflow.controller_binding)
            if isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit':
                table = {'version': 'annotation_axis_yield_table_v1',
                    'rows': context['controller']['arms'],
                    'forecast_unit': 'another_whole_axis_invocation',
                    'source': 'actual_root_controller'}
            else:
                table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
            snapshot = model_snapshot(context, table)
            instructions = (contract_record['instructions'] if contract_record is not None else
                self.instructions(context) + '\n' + DECISION_EXCHANGE_INSTRUCTIONS)
            output_schema = _action_generation_schema(contract_record['exchange_schema']
                if contract_record is not None else self.exchange_schema(schema))

        # A resumed unfinished decision may retain an older full axis sheet or
        # automatic native observation expansion. Project its new delivery
        # before frame revisions are computed; never change the saved prior
        # request or hash one view and send another. The original calculation
        # context and explicitly requested child/lookup values stay intact.
        snapshot = infernal_receiver_context(instructional_model_context(snapshot))
        public = []
        cursor = 0
        while True:
            if (cursor + 1 < len(rows) and not rows[cursor]['response_recorded']
                    and rows[cursor + 1]['request'].get('retry_of_exchange_index') == cursor):
                cursor += 1
                continue
            if cursor < len(rows) and rows[cursor]['response_recorded']:
                current = rows[cursor]
            else:
                retry = rows[cursor] if cursor < len(rows) else None
                exchange_index = len(rows)
                key = self.conversation_key()
                continuing = (key is not None and key == self._presented_conversation_key
                    and self._model_snapshot is not None and retry is None)
                if continuing and public:
                    frame = {'version': DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result',
                        'decision_index': index, 'exchange_index': public[-1]['exchange_index'],
                        'result': public[-1]['lookup_result']}
                    if contract_record is not None:
                        frame['pending_contract_information'] = requested_contract_information(public)
                else:
                    frame = state_frame(snapshot, self._model_snapshot if continuing else None)
                    if not continuing and (public or retry is not None):
                        frame['restored_public_exchanges'] = _plain(public)
                        frame['restored_pending_decision_index'] = index
                request = {'context': instructional_model_context(frame), 'output_schema': output_schema,
                    'instructions': instructions, 'restoration': {'snapshot': snapshot,
                        'pending_public_exchanges': public},
                    'conversation_key': _plain(key)}
                if retry is not None:
                    request['retry_of_exchange_index'] = retry['exchange_index']
                if contract_record is not None:
                    self.validate_contract_exchange_request(request, saved, index, snapshot, public)
                current = exchanges.prepare(self.episode_id, index, exchange_index, request)
                rows.append(current)
                cursor = exchange_index
                # Propagate transport failures. A later reconstruction appends
                # an explicit retry row, preserving this exact failed input.
                response = await self.dispatch_exchange_decision(
                    request, index, exchange_index, journal, exchanges)
                current = exchanges.respond(self.episode_id, index, exchange_index, response)
                rows[cursor] = current
                self._model_snapshot = snapshot
                after_key = self.conversation_key()
                # An initial dispatch creates a native thread. Compaction of
                # an existing thread invalidates the next incremental base.
                self._presented_conversation_key = (after_key if key is None
                    and (after_key is None or after_key[1] == 0) else key)
            try:
                body = self.exchange_response(current['response'], lookup_contract=lookup_contract)
            except (ValueError, TypeError, ValidationError) as error:
                body = None
                result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange',
                    'code': 'invalid_decision_response', 'detail':
                        schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
            if body is not None and body['response_type'] == 'select_action':
                response = {key: body[key] for key in ('selection', 'report_update')}
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved),
                    'response': _json(response)})
                # A requested own-attempt page can expose an older published
                # reference absent from the bounded initial working-state view.
                # Keep that actual interpretation basis separate from the full
                # original estimation context saved in runtime_model_calls.
                return response, index, self.interpretation_context(context, public), schema
            if current['lookup_result_recorded']:
                result = current['lookup_result']
            else:
                if body is not None:
                    try:
                        query = body['lookup']
                        if query['view'] == 'child_options':
                            result = child_option_information(self.workflow, self, query['role'])
                        elif query['view'] == 'composition_information':
                            result = await self.workflow.execute(self, query['operation'], query['arguments'],
                                decision_index=index,
                                operation_key=f'{self.workflow.run_id}:{self.episode_id}:decision:{index}:'
                                    f'exchange:{current["exchange_index"]}:composition',
                                _composition_lookup=True)
                        else:
                            result = lookup_attempts(journal, self.episode_id, before=index, query=query)
                    except (ValueError, TypeError, ValidationError) as error:
                        result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange',
                            'code': 'invalid_own_attempt_lookup', 'detail':
                                schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
                    except (OSError, sqlite3.Error) as error:
                        result = {'status': 'failed', 'feedback': {'category': 'decision_exchange',
                            'code': 'own_attempt_lookup_failed', 'exception_type': type(error).__name__}}
                current = exchanges.resolve_lookup(self.episode_id, index,
                    current['exchange_index'], result)
                rows[cursor] = current
            public.append({'exchange_index': current['exchange_index'],
                'response': current['response'], 'lookup_result': result})
            cursor += 1

