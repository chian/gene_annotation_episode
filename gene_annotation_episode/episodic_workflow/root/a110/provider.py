"""A110 annotation provider selection, saved replay and contract exchange."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime
from .presentation import prepare_model_request

async def call(self, context, schema):
    from .episode import is_annotation_parent
    if not is_annotation_parent(self.workflow, self):
        from .runtime import DecisionSource
        return await DecisionSource.call(self, context, schema)
    index, self.calls = (self.calls, self.calls + 1)
    journal = self.workflow.journal
    row = journal.row('runtime_model_calls', self.episode_id, index)
    if (row is None or row['response'] is None) and self.path[-1][0] == 'biochemical_feasibility_evidence':
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
        context, saved = prepare_model_request(self, context, schema, index, profile)
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
