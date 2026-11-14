"""Private A107 Results to_parent"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_RETURN_SOURCE
from .result_records import NATIVE_RESULT_ORIGIN
from .binding_roles import ROLE_KINDS
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import plain

class ResultsToParent:

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        if self.rna_structure_comparison_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
            native_empty.update({source: [] for source in rna_comparison_fact_sources()})
            if self.rna_structure_comparison_results.applies(context):
                from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
                native_empty.update({source: [] for source in rna_structure_fact_sources()})
                return {**native_empty, **self.rna_structure_comparison_results.facts(context)}
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
            if self.native_expression_nmf_results.applies(context):
                return {**native_empty, **self.native_expression_nmf_results.facts(context)}
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
            if self.native_rna_structure_results.applies(context):
                return {**native_empty, **self.native_rna_structure_results.facts(context)}
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_infernal_preparation_results.applies(context):
                return {**native_empty, **self.native_infernal_preparation_results.facts(context)}
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
            if self.native_infernal_results.applies(context):
                return {**native_empty, **self.native_infernal_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        if self._target(context)['resource_kind'] == 'api':
            facts = self.api_execution.facts(context, completion_snapshot)
            required = self._blast_target_requirement(self._target(context), context.scope)
            if required is not None:
                facts[BLAST_GRADED_RETURN_SOURCE] = self._blast_grader_rows(context, facts['execution_result_refs'], required)
            return {**native_empty, **facts, 'execution_result_origin': None}
        extra = {}
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            completed = self._native_results_complete(context, list(results.values()))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)} if self._has_appservice() else {}), 'execution_blast_hsps': [], 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

    def validate_report(self, context, form, original_schema):
        for adapter in (self.rna_structure_comparison_returns, self.native_rna_structure_returns, self.native_expression_nmf_returns, self.native_infernal_preparation_returns, self.native_infernal_returns):
            if adapter is not None:
                adapter.validate_received_report(context, form, original_schema)
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        if self._has_rfam():
            self.api_execution.rfam_returns.validate_received_report(context, form, original_schema)
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def _blast_grader_rows(self, context, result_refs, required):
        """Return only original retained database-grader results that meet the request."""
        from gene_annotation_episode.episodic_workflow.root.a107.tool_grading_artifacts import source_tool_grading_entries
        rows = []
        for reference in result_refs:
            body = self.api_execution.read_result(reference, context.scope)
            if body['target']['assignment'].get('service') != 'ncbi_blast':
                continue
            if body['target']['handle'] != plain(context.assignment)['handoff_ref']:
                raise ValueError('blast_grader_result_handoff_conflict')
            source = self.store.get(body['source_ref'])
            graders = source_tool_grading_entries(self.store, source['id'])
            if len(graders) != 1:
                raise ValueError('blast_grader_result_required')
            grading = graders[0]['grading']
            sheet = grading.get('sheet')
            if grading.get('failure') is not None or not isinstance(sheet, dict) or sheet.get('schema') != required['return_type']:
                raise ValueError('blast_grader_result_type_conflict')
            normalized = sheet.get('normalized_result') or {}
            query, search = (normalized.get('query') or {}, normalized.get('search') or {})
            request = search.get('request') or {}
            if normalized.get('mode') != 'database' or normalized.get('resource') != 'api' or query.get('length') != required['query_length'] or (request.get('sequence_sha256') != required['query_sha256']) or (request.get('subject_ref') != body['service_request']['subject_ref']) or (request.get('database') != body['service_request']['database']):
                raise ValueError('blast_grader_result_query_conflict')
            database = search.get('database')
            if not isinstance(database, str) or not database:
                raise ValueError('blast_grader_native_database_missing')
            if required['database'] is not None and database != required['database']:
                raise ValueError('blast_grader_result_database_conflict')
            rows.append({'result_ref': reference, 'grading_artifact_ref': graders[0]['artifact_ref'], 'sheet_schema': sheet['schema']})
        return rows
