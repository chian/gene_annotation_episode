"""Private A102 literature_table source interpretation."""
from __future__ import annotations
from .source_contracts import ContractError, deepcopy, obj, plain, source_location_inputs, validate_schema

class SourceSourceInterpretation:

    def reasoning_action_schema(self, context, commit_schema, *, _accept_legacy_quotes=False):
        leads = context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads'
        if not leads:
            return None
        schema = obj({'kind': {'const': 'reason'}, 'commit': deepcopy(commit_schema)})
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import lead_schema
        schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema, allow_legacy_quote=_accept_legacy_quotes)

    def accept_reasoning_action_schema(self, context, commit_schema):
        """Admit original quoted actions without requesting quotes from a model."""
        return self.reasoning_action_schema(context, commit_schema, _accept_legacy_quotes=True)

    def reasoning_has_task_content(self, context, selection):
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import commissioned_task, lead_schema
        if 'source_lead' not in selection:
            return False
        task, _ = commissioned_task(context)
        if task['kind'] != 'verified_source_leads':
            return False
        validate_schema(plain(selection['source_lead']), source_location_inputs(lead_schema(), allow_legacy_quote=True))
        return True

    def execute_reasoning(self, context, selection, operation_key):
        if 'source_lead' in selection:
            from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import validate_lead
            from gene_annotation_episode.episodic_workflow.root.a102.literature_contract_error import ExperimentalContractError
            store = self.services.workflow.store
            try:
                witness = selection['source_lead']['witness']
                self._tool_arguments(context, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'], 'offset': witness['start'], 'limit': witness['end'] - witness['start']})
                with store.transaction():
                    native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                    account_binding = {'account_invocation': (context.run_id, context.episode_id)} if native['commit'].get('interpretation_accounts') else {}
                    result = store.commit_reasoning(native['commit'], plain(context.scope), operation_key, **account_binding)
                    if result['status'] not in ('completed', 'partial'):
                        return result
                    return {**result, 'literature_source_lead': validate_lead(store, context, selection['source_lead'], result)}
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}
        return None
