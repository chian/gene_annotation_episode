"""Private Results task decision."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.runtime import CONTRACT_INFORMATION_OPERATIONS, DECISION_CONTEXT_VERSION, DECISION_EXCHANGE_PROTOCOL, Draft202012Validator, Mapping, ValidationError, WorkflowError, _ASSIGNMENT_TRANSPORT, _action_generation_schema, _category_yield_parameters, _digest, _json, _object, _plain, _recorded_action_generation_schema, _recorded_assignment_transport, _references_in, apply_state_frame, child_option_information, composition_lookup_schema, instructional_model_context, is_contract_information, json, lookup_attempts, model_snapshot, requested_contract_information, schema_failure_diagnostic, sqlite3, state_frame, yield_table
from gene_annotation_episode.episodic_workflow.root.a103.execution_prompt import is_api_launch_context
from gene_annotation_episode.episodic_workflow.root.a103.decision_context import VERSION as DECISION_CONTEXT_VERSION
from gene_annotation_episode.episodic_workflow.root.a103.library.hpc_prompt import is_hpc_context
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence_prompt import is_published_scientific_context, is_selected_execution_context

from .decision_contracts import ResultsDecisionContracts
from .saved_decision_exchange import ResultsSavedDecisionExchange
from .decision_exchange import ResultsDecisionExchange
from .decision_provider import ResultsDecisionProvider

class ResultsTaskDecision(ResultsDecisionContracts, ResultsSavedDecisionExchange, ResultsDecisionExchange, ResultsDecisionProvider):


    async def call(self, context, schema):
        index, self.calls = (self.calls, self.calls + 1)
        journal = self.workflow.journal
        row = journal.row('runtime_model_calls', self.episode_id, index)
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = _live_original_runtime.json.loads(row['request'])
            if row['purpose'] != 'decision':
                raise _live_original_runtime.WorkflowError('saved decision contract differs from reconstruction')
            schema = saved['schema']
            context = saved['context']
            try:
                _live_original_runtime._recorded_assignment_transport(saved)
            except ValueError as error:
                raise _live_original_runtime.WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise _live_original_runtime.WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if 'literature_numerical_contracts' in saved:
                if profile is not None:
                    raise _live_original_runtime.WorkflowError('original_literature_numerical_profile_mismatch')
                self.workflow.numerical_contracts().validate_frozen_contracts(saved)
            if self.workflow.decision_protocol == _live_original_runtime.DECISION_EXCHANGE_PROTOCOL and saved.get('decision_protocol') != _live_original_runtime.DECISION_EXCHANGE_PROTOCOL:
                raise _live_original_runtime.WorkflowError('pending_decision_requires_original_protocol')
            if row['response'] is not None:
                if self.workflow.decision_protocol == _live_original_runtime.DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context, self.workflow.decision_exchanges.rows(self.episode_id, index))
                return (_live_original_runtime.json.loads(row['response']), index, context, schema)
        else:
            context = self.decision_inputs(context, index, profile)
            saved = {'context': context, 'schema': schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved['literature_numerical_contracts'] = frozen
        if self.workflow.decision_protocol == _live_original_runtime.DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': _live_original_runtime.DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _live_original_runtime._json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, 'has_session', lambda *_: False)
        if not has_session(self.episode_id, 'REASONING') and 'restored_episode_history' not in context:
            context = {**context, 'restored_episode_history': self.workflow.history_preview(self, before=index)}
        context = _live_original_runtime.instructional_model_context(context)
        transport = saved['assignment_transport'] if row is not None else {'version': _live_original_runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _live_original_runtime._digest(schema)}
        saved = {'context': context, 'schema': schema, **({'literature_numerical_contracts': saved['literature_numerical_contracts']} if 'literature_numerical_contracts' in saved else {})}
        saved['assignment_transport'] = transport
        if self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self)):
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'], kind='decision_input', source_index=index)
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _live_original_runtime._json(saved), 'response': None})
        with journal.measure('runtime_model_calls', self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.complete_decision(instructions, context, _live_original_runtime._action_generation_schema(schema))
        journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _live_original_runtime._json(saved), 'response': _live_original_runtime._json(response)})
        return (response, index, saved['context'], schema)

    def instructions(self, context):
        return self.workflow.services.instructions(self, context)
from gene_annotation_episode.episodic_workflow.root.a103 import runtime as _live_original_runtime
