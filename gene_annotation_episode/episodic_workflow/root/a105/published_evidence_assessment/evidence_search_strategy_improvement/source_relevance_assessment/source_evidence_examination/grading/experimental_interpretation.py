"""Private grading experimental interpretation invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_contracts import Mapping, _ACCESS_TOOLS, _population_catalog, _required_grading_logic, deepcopy, identity, inspect, obj, plain, source_location_inputs, validate_schema
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.runtime import Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, Record, ReportRedelivery, SourceEnd, ValidationError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, form_with_facts, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, sqlite3, subprocess, validate_form
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.episode_contract_information import ContractInformationError
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.task_state import LiteratureTaskState
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.task_decision import LiteratureTaskDecision

class ExperimentalInterpretation:

    def reasoning_action_schema(self, context, commit_schema, *, _accept_legacy_quotes=False):
        repository = self._required_grading_repository(context)
        leads = context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads'
        if repository is None and (not leads):
            return None
        schema = obj({'kind': {'const': 'reason'}, 'commit': deepcopy(commit_schema)}) if repository is None else _required_grading_logic(repository).action_schema(commit_schema, source_location_inputs(repository.population_schema(), allow_legacy_quote=_accept_legacy_quotes))
        if leads:
            from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.credit import lead_schema
            schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema, allow_legacy_quote=_accept_legacy_quotes)

    def accept_reasoning_action_schema(self, context, commit_schema):
        """Admit original quoted actions without requesting quotes from a model."""
        return self.reasoning_action_schema(context, commit_schema, _accept_legacy_quotes=True)

    def reasoning_has_task_content(self, context, selection):
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import commissioned_task
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.credit import lead_schema
        if 'source_lead' not in selection:
            return False
        task, _ = commissioned_task(context)
        if task['kind'] != 'verified_source_leads':
            return False
        validate_schema(plain(selection['source_lead']), source_location_inputs(lead_schema(), allow_legacy_quote=True))
        return True

    def execute_reasoning(self, context, selection, operation_key):
        repository = self._required_grading_repository(context)
        if 'source_lead' in selection:
            from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.credit import validate_lead
            from gene_annotation_episode.episodic_workflow.root.a105.literature_contract_error import ExperimentalContractError
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
