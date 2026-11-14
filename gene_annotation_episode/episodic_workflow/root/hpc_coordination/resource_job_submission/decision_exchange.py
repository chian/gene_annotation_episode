from __future__ import annotations

import json

import inspect

from contextlib import nullcontext

from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode.episodic_workflow.root.method_loop import ReportRedelivery

from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _decode_recorded_action_response

from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure

from gene_annotation_episode.episodic_workflow.root.task_values import _json

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, validate_form

from gene_annotation_episode.episodic_workflow.root.episode_contract_information import ContractInformationError

from gene_annotation_episode.episodic_workflow.root.boundary_validation import schema_failure_diagnostic

from gene_annotation_episode.episodic_workflow.root.episode_completion import observes_action_outcome

from collections.abc import Mapping

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _object, _recorded_action_generation_schema

from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in

from gene_annotation_episode.episodic_workflow.root.decision_context import VERSION as DECISION_CONTEXT_VERSION

from gene_annotation_episode.episodic_workflow.root.decision_context import apply_state_frame, model_snapshot, instructional_model_context

from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information

from gene_annotation_episode.episodic_workflow.root.composition_information import lookup_schema as composition_lookup_schema

from gene_annotation_episode.episodic_workflow.root.infernal_result_presentation import infernal_receiver_context

from gene_annotation_episode.episodic_workflow.root.method_loop import Episode

from gene_annotation_episode.episodic_workflow.root.task_values import Record, _plain, _json

from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionLeaf

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _object

from gene_annotation_episode.episodic_workflow.root.episode_completion import EFFECT_VERSION

from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema

from gene_annotation_episode.episodic_workflow.root.task_values import Record, _json

from gene_annotation_episode.episodic_workflow.root.communication import form_with_facts

import sqlite3

from jsonschema import ValidationError

from gene_annotation_episode.episodic_workflow.root import literature_numerical_contracts

from gene_annotation_episode.episodic_workflow.root.task_action_contracts import _recorded_assignment_transport, _ASSIGNMENT_TRANSPORT, _action_generation_schema

from gene_annotation_episode.episodic_workflow.root.task_values import _json, _plain, _digest

from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS as DECISION_EXCHANGE_INSTRUCTIONS, VERSION as DECISION_CONTEXT_VERSION

from gene_annotation_episode.episodic_workflow.root.decision_context import model_snapshot, instructional_model_context, state_frame

from gene_annotation_episode.episodic_workflow.root.decision_history import yield_table, lookup_attempts

from gene_annotation_episode.episodic_workflow.root.yield_parameters import _category_yield_parameters

from gene_annotation_episode.episodic_workflow.root.composition_information import child_options as child_option_information, requested_contract_information

from gene_annotation_episode.episodic_workflow.root.method_loop import SourceEnd

from gene_annotation_episode.episodic_workflow.root.task_values import _plain

from gene_annotation_episode.episodic_workflow.root.report_facts import FACT_SOURCES, FACT_MEANINGS

from gene_annotation_episode.episodic_workflow.root.decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL

from gene_annotation_episode.tool_knowledge import INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS

from gene_annotation_episode.launch_instructions import INSTRUCTIONS as LAUNCH_INSTRUCTIONS

import subprocess

from gene_annotation_episode.acquisition import AcquisitionError

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.root.method_loop.durable import EventTargetError

from gene_annotation_episode.episodic_workflow.root.waiting import _wait_target_feedback

from gene_annotation_episode.episodic_workflow.root.goal import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT

from gene_annotation_episode.episodic_workflow.root.method_loop import Episode, SourceEnd

from gene_annotation_episode.episodic_workflow.root.communication import interpretation_schema, form_with_facts

class ResourceSubmissionTaskDecisionExchange:
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
            instructions = contract_record['instructions'] if contract_record is not None else self.instructions(context) + '\n' + DECISION_EXCHANGE_INSTRUCTIONS
            output_schema = _action_generation_schema(contract_record['exchange_schema'] if contract_record is not None else self.exchange_schema(schema))
        snapshot = infernal_receiver_context(instructional_model_context(snapshot))
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
