"""Private grading contextual interpretation invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_contracts import ContractError, Mapping, _A108_ACCESS_TOOLS, _a108_population_catalog, _required_grading_logic, deepcopy, identity, inspect, obj, plain, source_location_inputs, validate_schema

class ContextualInterpretation:

    def reasoning_action_schema(self, context, commit_schema):
        repository = self._required_grading_repository(context)
        leads = context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads'
        if repository is None and (not leads):
            return None
        schema = obj({'kind': {'const': 'reason'}, 'commit': deepcopy(commit_schema)}) if repository is None else _required_grading_logic(repository).action_schema(commit_schema, source_location_inputs(repository.population_schema()))
        if leads:
            from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.credit import lead_schema
            schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema)

    def reasoning_has_task_content(self, context, selection):
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import commissioned_task
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.credit import lead_schema
        if 'source_lead' not in selection:
            return False
        task, _ = commissioned_task(context)
        if task['kind'] != 'verified_source_leads':
            return False
        validate_schema(plain(selection['source_lead']), source_location_inputs(lead_schema()))
        return True

    def execute_reasoning(self, context, selection, operation_key):
        repository = self._required_grading_repository(context)
        if 'source_lead' in selection:
            from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.credit import validate_lead
            from gene_annotation_episode.episodic_workflow.root.a108.literature_contract_error import ExperimentalContractError
            store = self.services.workflow.store
            try:
                witness = selection['source_lead']['witness']
                self._tool_arguments(context, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'], 'offset': witness['start'], 'limit': witness['end'] - witness['start']})
                with store.transaction():
                    native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                    account_context = {'account_invocation': (context.run_id, context.episode_id)} if native['commit'].get('interpretation_accounts') else {}
                    result = store.commit_reasoning(native['commit'], plain(context.scope), operation_key, **account_context) if repository is None else _required_grading_logic(repository).execute(context, native, operation_key, repository, authorize_source_access=lambda ref, representation: self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation}))
                    if result['status'] not in ('completed', 'partial'):
                        return result
                    return {**result, 'literature_source_lead': validate_lead(store, context, selection['source_lead'], result)}
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}
        if repository is None:
            return None
        return _required_grading_logic(repository).execute(context, selection, operation_key, repository, authorize_source_access=lambda ref, representation: self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation}))
