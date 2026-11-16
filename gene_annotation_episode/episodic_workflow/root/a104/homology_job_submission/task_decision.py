"""Private job_launch original task task_decision.py."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.homology_binding_family import selected_homology_binding

from .decision_inputs import HomologySubmissionTaskDecisionInputs

from .decision_contracts import HomologySubmissionTaskDecisionContracts

from .decision_exchange import HomologySubmissionTaskDecisionExchange

from .decision_provider import HomologySubmissionTaskDecisionProvider

class HomologySubmissionTaskDecision(HomologySubmissionTaskDecisionProvider, HomologySubmissionTaskDecisionExchange, HomologySubmissionTaskDecisionContracts, HomologySubmissionTaskDecisionInputs):

    async def call(self, context, schema):
        index, self.calls = (self.calls, self.calls + 1)
        journal = self.workflow.journal
        row = journal.row('runtime_model_calls', self.episode_id, index)
        (row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process'
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
    definitions = {'HomologySubmissionTaskDecision.call': HomologySubmissionTaskDecision.__dict__['call'], 'HomologySubmissionTaskDecision.conversation_key': HomologySubmissionTaskDecision.__dict__['conversation_key']}
    bound = bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime',
        qualified_names={name: name for name in definitions}, defining_module='gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.task_decision')
    setattr(HomologySubmissionTaskDecision, 'call', bound['HomologySubmissionTaskDecision.call'])
    setattr(HomologySubmissionTaskDecision, 'conversation_key', bound['HomologySubmissionTaskDecision.conversation_key'])

from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__, _bind_preserved_runtime_providers)
