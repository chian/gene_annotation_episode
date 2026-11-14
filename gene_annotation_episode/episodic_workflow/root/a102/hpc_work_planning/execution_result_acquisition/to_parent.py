"""Private A102 Results to parent."""
from __future__ import annotations
from .execution_contracts import LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, plain, validate_form

from .report_fields import ResultsReportFields

from .report_reference_access import ResultsReportReferenceAccess

class ResultsToParent(ResultsReportFields, ResultsReportReferenceAccess):

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_result_views import protein_structure_fact_sources
        native_empty = {source: [] for source in protein_structure_fact_sources()}
        if self.native_protein_structure_results.applies(context):
            return {**native_empty, **self.native_protein_structure_results.facts(context, verify_artifacts=False)}
        if self._target(context)['resource_kind'] == 'api':
            return {**native_empty, **self.api_execution.facts(context, completion_snapshot), 'execution_result_origin': None}
        extra = {}
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            completed = self._native_results_complete(context, list(results.values()))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

    def validate_report(self, context, form, original_schema):
        self.native_protein_structure_returns.validate_received_report(context, form, original_schema)
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {})
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
