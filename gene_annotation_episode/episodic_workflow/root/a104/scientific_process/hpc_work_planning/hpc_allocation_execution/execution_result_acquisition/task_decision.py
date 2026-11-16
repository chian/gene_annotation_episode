"""Private A104 Results task decision."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table

from .decision_contracts import ResultsTaskDecisionContracts

from .decision_exchange import ResultsTaskDecisionExchange

from .decision_provider import ResultsTaskDecisionProvider

class ResultsTaskDecision(ResultsTaskDecisionProvider, ResultsTaskDecisionExchange, ResultsTaskDecisionContracts):

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
                context['child_options'] = child_option_information(self.workflow, self)['text']
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            work_results = context.pop('_completed_work_axis_results', {})
            if 'literature_completed_work' not in context and (not (isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit')):
                from gene_annotation_episode.episodic_workflow.root.a104.episode_work_report import completed_action_reports
                context['completed_action_reports'] = completed_action_reports(self.workflow, self, context, before=index, received_axis_results=work_results)
            from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_prompt import is_hpc_context
            if is_hpc_context(context):
                from gene_annotation_episode.episodic_workflow.root.a104.episode_work_report import requested_action_history
                context['requested_action_history'] = requested_action_history(self.workflow, self, before=index)
            if 'pending_work' not in context:
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies('results'):
                planning_scopes = ()
                if 'results' in binding.planning_roles and self.workflow.job_episodes is not None:
                    jobs = self.workflow.job_episodes
                    if 'search_modes' in jobs.jobs.config:
                        options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                        planning_scopes = list({value['execution_class'].ref: value['execution_class'] for value in options}.values())
                        context = {**context, 'job_execution_options': [{key: value[key] for key in ('query_ref', 'cpu', 'search_mode')} | {'execution_class_ref': value['execution_class'].ref} for value in options]}
                    else:
                        planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
                context = {**context, 'execution_expectations': binding.capture('results', assignment=self.request.message.as_record().get('job_assignment'), planning_scopes=planning_scopes)}
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
            if self.workflow.native_event_information is not None:
                context['native_event_targets'] = self.workflow.native_event_information.read(self.workflow.binding_context(self))
            if self.workflow.permits_common_action(self, 'wait'):
                context['waiting_support'] = self.workflow.waiting_support(self, context)
            if profile is not None:
                context = {**context, 'contract_information_profile': profile}
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
                if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
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
        if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
        with journal.measure('runtime_model_calls', self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.decision_completion()(self.episode_id, 'REASONING', instructions, context, _action_generation_schema(schema))
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': _json(response)})
        return (response, index, saved['context'], schema)

    def instructions(self, context):
        return self.workflow.services.instructions(self, context)

    def conversation_key(self):
        callback = getattr(self.workflow.provider, 'conversation_key', None)
        return None if callback is None else callback(self.episode_id, 'REASONING')



def _bind_preserved_runtime_providers(namespace):
    from gene_annotation_episode.episodic_workflow.root.a104.library.live_runtime_functions import bind_functions
    definitions = {'ResultsTaskDecision.call': ResultsTaskDecision.__dict__['call'], 'ResultsTaskDecision.conversation_key': ResultsTaskDecision.__dict__['conversation_key']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.task_decision')
    setattr(ResultsTaskDecision, 'call', bound['ResultsTaskDecision.call'])
    setattr(ResultsTaskDecision, 'conversation_key', bound['ResultsTaskDecision.conversation_key'])

from gene_annotation_episode.episodic_workflow.root.a104 import runtime as _preserved_runtime_namespace
_bind_preserved_runtime_providers(vars(_preserved_runtime_namespace))
