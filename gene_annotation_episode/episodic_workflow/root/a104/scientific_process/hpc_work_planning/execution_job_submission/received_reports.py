"""Private A104 Launch received reports."""
from __future__ import annotations
from .contracts import BLAST_GRADED_RETURN_SOURCE, deepcopy, is_native_blast_database_target, is_standard_blast_database_target, plain

from .received_reference_access import LaunchReceivedReportsReferenceAccess

from .received_report_admission import LaunchReceivedReportsAdmission

class LaunchReceivedReports(LaunchReceivedReportsAdmission, LaunchReceivedReportsReferenceAccess):

    def received_report_sources(self, role):
        result = {}
        if role in {'annotation', 'scientific_process'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = self.fact_sources('results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._forwards_bvbrc_reports(role):
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._has_appservice() and role in {'annotation', 'scientific_process'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'scientific_process'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
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
        if context.role not in {'annotation', 'scientific_process'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        return result

    def initial_references(self, context):
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            for request in requests:
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        selected = [assignment['handoff_ref']]
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        return list(dict.fromkeys(selected))
