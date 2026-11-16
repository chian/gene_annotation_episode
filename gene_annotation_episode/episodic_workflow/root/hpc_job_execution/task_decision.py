"""Original hpc terminal task source_decision with explicitly accounted fixed-role branches."""
from __future__ import annotations
import json
import sqlite3
from collections.abc import Mapping
from jsonschema import ValidationError
from .. import literature_numerical_contracts
from ..episode_journal import WorkflowError
from ..task_action_contracts import _recorded_assignment_transport, _ASSIGNMENT_TRANSPORT, _action_generation_schema
from ..task_values import _json, _plain, _digest
from ..decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL, INSTRUCTIONS as DECISION_EXCHANGE_INSTRUCTIONS, VERSION as DECISION_CONTEXT_VERSION
from ..decision_context import model_snapshot, instructional_model_context, state_frame
from ..decision_history import yield_table, lookup_attempts
from ..yield_parameters import _category_yield_parameters
from ..composition_information import child_options as child_option_information, requested_contract_information
from ..infernal_result_presentation import infernal_receiver_context
from ..boundary_validation import schema_failure_diagnostic


class HPCTaskDecision:
    async def call(self, context, schema):
        index, self.calls = self.calls, self.calls + 1
        journal = self.workflow.journal
        row = journal.row("runtime_model_calls", self.episode_id, index)
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = json.loads(row["request"])
            if row["purpose"] != "decision":
                raise WorkflowError("saved decision contract differs from reconstruction")
            # Historical and interrupted decisions retain the actual contract
            # supplied at dispatch. Additions to today's tool catalog belong to
            # new decisions, not retrospective reconstruction of earlier ones.
            schema = saved["schema"]
            context = saved["context"]
            try:
                _recorded_assignment_transport(saved)
            except ValueError as error:
                raise WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if literature_numerical_contracts.SAVED_MEMBER in saved:
                if profile is not None:
                    raise WorkflowError('original_literature_numerical_profile_mismatch')
                literature_numerical_contracts.validate_frozen_contracts(saved)
            if (self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL
                    and saved.get('decision_protocol') != DECISION_EXCHANGE_PROTOCOL):
                raise WorkflowError('pending_decision_requires_original_protocol')
            if row["response"] is not None:
                if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context,
                        self.workflow.decision_exchanges.rows(self.episode_id, index))
                return json.loads(row["response"]), index, context, schema
        else:
            # Selected manuals are exact immutable assignment operands. Supply
            # their bodies only to new calls; saved calls above keep the context
            # originally dispatched, including an interrupted request.
            resource_context = self.workflow.resource_context(self)
            if resource_context is not None:
                context = {**context, 'resource_context': resource_context}
            context = {**context,
                'launch_instruction_library': self.workflow.launch_instructions.context()}
            selected_instructions = self.workflow.launch_instructions.materialize(
                self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
            if selected_instructions is not None:
                context['selected_launch_instructions'] = selected_instructions
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(
                self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            # Receiver-specific native views are supplied above. Build the
            # factual work/credit report only after those authorized results
            # are available; saved calls retain their original context.
            work_results = context.pop('_completed_work_axis_results', {})
            if 'literature_completed_work' not in context:
                from ..episode_work_report import completed_action_reports
                context['completed_action_reports'] = completed_action_reports(
                    self.workflow, self, context, before=index,
                    received_axis_results=work_results)
            from ..execution_operand_presentation import is_hpc_context
            if is_hpc_context(context):
                from ..episode_work_report import requested_action_history
                context['requested_action_history'] = requested_action_history(
                    self.workflow, self, before=index)
            if 'pending_work' not in context:
                # Direct caller dispatches need the same authoritative
                # outstanding-work input as next(). Saved decisions above
                # retain the exact original context instead.
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies(self.path[-1][0]):
                planning_scopes = ()
                if (self.path[-1][0] in binding.planning_roles
                        and self.workflow.job_episodes is not None):
                    jobs = self.workflow.job_episodes
                    if 'search_modes' in jobs.jobs.config:
                        options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                        planning_scopes = list({value['execution_class'].ref: value['execution_class']
                                                for value in options}.values())
                        context = {**context, 'job_execution_options': [
                            {key: value[key] for key in ('query_ref', 'cpu', 'search_mode')}
                            | {'execution_class_ref': value['execution_class'].ref}
                            for value in options]}
                    else:
                        planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
                context = {**context, "execution_expectations": binding.capture(self.path[-1][0],
                    assignment=self.request.message.as_record().get("job_assignment"),
                    planning_scopes=planning_scopes)}
            if self.workflow.resource_estimator is not None:
                if "execution_expectations" in context:
                    estimates = self.workflow.resource_estimator.estimate_context(
                        context["execution_expectations"])
                else:
                    estimates = None
                if estimates is not None:
                    context = {**context, "resource_tool_estimates": estimates}
            native_expectations = self.workflow.native_estimation_context(self, context)
            if native_expectations is not None:
                context = {**context, 'native_execution_expectations': native_expectations}
                if self.workflow.resource_estimator is not None:
                    native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                    context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
            if self.workflow.native_event_information is not None:
                context['native_event_targets'] = self.workflow.native_event_information.read(
                    self.workflow.binding_context(self))
            if profile is not None:
                context = {**context, 'contract_information_profile': profile}
            saved = {"context": context, "schema": schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved[literature_numerical_contracts.SAVED_MEMBER] = frozen
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if (self.workflow.receipts is not None ):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                        kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, "has_session", lambda *_: False)
        if (not has_session(self.episode_id, "REASONING")
                and "restored_episode_history" not in context):
            # Restore the authoritative scientific/runtime state through the
            # existing replay path, not by rehydrating all archived contexts.
            # The fresh native conversation receives only a bounded metadata
            # index; exact older selections/outcomes are an ordinary own read.
            context = {**context, "restored_episode_history":
                self.workflow.history_preview(self, before=index)}
        context = instructional_model_context(context)
        # Save the exact supplied context, including its bounded operational
        # index, before dispatch. Completed historical calls are returned above
        # unchanged. Metadata contains no old contexts, so it cannot nest them.
        transport = (saved.get('assignment_transport') if row is not None else
            {'version': _ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _digest(schema)})
        saved = {"context": context, "schema": schema,
            **({literature_numerical_contracts.SAVED_MEMBER: saved[literature_numerical_contracts.SAVED_MEMBER]}
                if literature_numerical_contracts.SAVED_MEMBER in saved else {})}
        if transport is not None:
            saved['assignment_transport'] = transport
        if (self.workflow.receipts is not None ):
            # Scientific information is admitted through explicit inputs,
            # own outcomes and requested returns, independently of the scalar
            # credit callable. Other role inputs retain their existing delivery.
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                kind='decision_input', source_index=index)
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": None})
        with journal.measure("runtime_model_calls", self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, "REASONING", instructions,
                                                              context, _action_generation_schema(schema))
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": _json(response)})
        return response, index, saved["context"], schema

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
                with journal.measure('runtime_model_calls', self.episode_id, index):
                    with exchanges.measure(self.episode_id, index, exchange_index):
                        response = await self.workflow.provider.complete(self.episode_id, 'REASONING',
                            request['instructions'], request['context'], request['output_schema'])
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

