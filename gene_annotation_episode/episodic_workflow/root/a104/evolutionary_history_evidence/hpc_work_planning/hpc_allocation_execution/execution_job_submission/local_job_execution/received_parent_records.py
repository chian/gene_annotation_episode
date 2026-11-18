"""Private A104 LocalExecution received parent records."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SOURCE
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

from .received_reference_access import LocalExecutionReceivedParentRecordsReferenceAccess

from .received_report_admission import LocalExecutionReceivedParentRecordsAdmission

class LocalExecutionReceivedParentRecords(LocalExecutionReceivedParentRecordsAdmission, LocalExecutionReceivedParentRecordsReferenceAccess):

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import homology_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import phylogeny_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import proteome_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **proteome_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

    def _forwards_bvbrc_reports(self, role):
        return role in {'annotation', 'evolutionary_history_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def received_report_sources(self, role):
        result = {}
        if role in {'annotation', 'evolutionary_history_evidence'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = self.fact_sources('results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'evolutionary_history_evidence'}:
            from gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._forwards_bvbrc_reports(role):
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._has_appservice() and role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'evolutionary_history_evidence'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'evolutionary_history_evidence'}:
            if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            result.update(self.api_execution.homology_returns.received_facts(context, schema))
            result.update(self.api_execution.phylogeny_returns.received_facts(context, schema))
            proteome = self.api_execution.proteome_returns.received_facts(context, schema)
            if set(result).intersection(proteome):
                raise ValueError('received_report_fact_conflict')
            result.update(proteome)
        return result

    def received_report_closure_facts(self, context):
        """Private return bindings, called only by the registry at episode closure."""
        if context.role not in {'annotation', 'evolutionary_history_evidence'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        return result

