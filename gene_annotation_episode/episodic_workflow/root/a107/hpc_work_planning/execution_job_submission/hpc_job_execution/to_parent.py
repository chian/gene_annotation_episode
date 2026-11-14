from __future__ import annotations
from .execution_contracts import BLAST_GRADED_RETURN_SOURCE
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import ROLE_KINDS
from .execution_contracts import deepcopy
from .execution_contracts import plain
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _infernal_reference_source
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import fact_sources
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import resolve
from .execution_contracts import validate_form

class NativeParentReturns:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            pass
        return ()
    fact_sources = fact_sources
    resolve = resolve
    _infernal_reference_source = staticmethod(_infernal_reference_source)

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.rna_structure_comparison_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
            native_empty.update({source: [] for source in rna_comparison_fact_sources()})
        if self.native_expression_nmf_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import FACT_SOURCES
            native_empty.update({source: [] for source in FACT_SOURCES})
        if self.native_rna_structure_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
        if self.native_infernal_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
        if self.native_infernal_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
        extra = self._delegate(context).facts(self._practical_context(context), completion_snapshot)
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            for reference in extra['practical_receipt_refs']:
                try:
                    target, _, returnable = read(reference, context.scope)
                    target = self._context_target(context, target)
                    if returnable:
                        handoffs[reference] = target
                except ValueError:
                    pass
            completed = extra.get('practical_completed', False)
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
