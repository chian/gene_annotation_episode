"""A104 original provider defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

async def call(self, context, schema):
    index, self.calls = (self.calls, self.calls + 1)
    journal = self.workflow.journal
    row = journal.row('runtime_model_calls', self.episode_id, index)
    if (row is None or row['response'] is None) and self.path[-1][0] == 'evolutionary_history_evidence':
        self.workflow.evolutionary_history_evidence_binding.validate_execution_context(self.workflow.binding_context(self))
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
        from .presentation import prepare_model_request
        context, saved = prepare_model_request(self, context, schema, index, profile)
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
        response = await self.workflow.provider.complete(self.episode_id, 'REASONING', instructions, context, _action_generation_schema(schema))
    journal.save('runtime_model_calls', {'episode_id': self.episode_id, 'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': _json(response)})
    return (response, index, saved['context'], schema)


def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['call']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'call': 'call'}))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
