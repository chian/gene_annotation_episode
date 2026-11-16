"""Private annotation task_provider."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime

class AnnotationProvider:

    async def call(self, context, schema):
        index, self.calls = (self.calls, self.calls + 1)
        journal = self.workflow.journal
        row = journal.row('runtime_model_calls', self.episode_id, index)
        if (row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process':
            pass
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = _original_runtime.json.loads(row['request'])
            if row['purpose'] != 'decision':
                raise _original_runtime.WorkflowError('saved decision contract differs from reconstruction')
            schema = saved['schema']
            context = saved['context']
            try:
                _original_runtime._recorded_assignment_transport(saved)
            except ValueError as error:
                raise _original_runtime.WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise _original_runtime.WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if 'literature_numerical_contracts' in saved:
                if profile is not None:
                    raise _original_runtime.WorkflowError('original_literature_numerical_profile_mismatch')
                self.workflow.numerical_contracts().validate_frozen_contracts(saved)
            if self.workflow.decision_protocol == _original_runtime.DECISION_EXCHANGE_PROTOCOL and saved.get('decision_protocol') != _original_runtime.DECISION_EXCHANGE_PROTOCOL:
                raise _original_runtime.WorkflowError('pending_decision_requires_original_protocol')
            if row['response'] is not None:
                if self.workflow.decision_protocol == _original_runtime.DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context, self.workflow.decision_exchanges.rows(self.episode_id, index))
                return (_original_runtime.json.loads(row['response']), index, context, schema)
        else:
            resource_context = self.workflow.resource_context(self)
            if resource_context is not None:
                context = {**context, 'resource_context': resource_context}
            shared_context = self.workflow.shared_information_context(self)
            if shared_context is not None:
                context = {**context, 'shared_information_context': shared_context}
            context = {**context, 'launch_instruction_library': self.workflow.launch_instructions.context()}
            selected_instructions = self.workflow.launch_instructions.materialize(self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
            if selected_instructions is not None:
                context['selected_launch_instructions'] = selected_instructions
            if self.workflow.available_child_roles(self):
                context['child_options'] = _original_runtime.child_option_information(self.workflow, self)['text']
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            work_results = context.pop('_completed_work_axis_results', {})
            if 'literature_completed_work' not in context and (not (isinstance(context.get('current_credit'), _original_runtime.Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit')):
                from gene_annotation_episode.episodic_workflow.root.a105.episode_work_report import completed_action_reports
                context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
            if 'pending_work' not in context:
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies(self.path[-1][0]):
                context = {**context, 'execution_expectations': binding.capture(self.path[-1][0])}
            if self.workflow.resource_estimator is not None:
                if self.workflow.is_job_source(self):
                    estimates = self.workflow.resource_estimator.estimate(context.get('execution_expectations'), job_ref=self.workflow.job_episodes.assignment(self)['job_ref'], sample=self.workflow.job_episodes.latest_sample(self, include_inherited=True))
                elif 'execution_expectations' in context:
                    estimates = self.workflow.resource_estimator.estimate_context(context['execution_expectations'])
                else:
                    estimates = None
                if estimates is not None:
                    context = {**context, 'resource_tool_estimates': estimates}
            native_expectations = self.workflow.native_estimation_context(self, context)
            if native_expectations is not None:
                context = {**context, 'native_execution_expectations': native_expectations}
                if self.workflow.resource_estimator is not None:
                    native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                    context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
            if self.workflow.permits_common_action(self, 'wait'):
                context['waiting_support'] = self.workflow.waiting_support(self, context)
            if profile is not None:
                context = {**context, 'contract_information_profile': profile}
            saved = {'context': context, 'schema': schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved['literature_numerical_contracts'] = frozen
        if self.workflow.decision_protocol == _original_runtime.DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': _original_runtime.DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _original_runtime._json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, 'has_session', lambda *_: False)
        if not has_session(self.episode_id, 'REASONING') and 'restored_episode_history' not in context:
            context = {**context, 'restored_episode_history': self.workflow.history_preview(self, before=index)}
        context = _original_runtime.instructional_model_context(context)
        transport = saved.get('assignment_transport') if row is not None else {'version': _original_runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _original_runtime._digest(schema)}
        saved = {'context': context, 'schema': schema, **({'literature_numerical_contracts': saved['literature_numerical_contracts']} if 'literature_numerical_contracts' in saved else {})}
        if transport is not None:
            saved['assignment_transport'] = transport
        if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _original_runtime._json(saved), 'response': None})
        with journal.measure('runtime_model_calls', self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, 'REASONING', instructions, context, _original_runtime._action_generation_schema(schema))
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _original_runtime._json(saved), 'response': _original_runtime._json(response)})
        return (response, index, saved['context'], schema)
