"""Private A104 LocalExecution to parent."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SOURCE
from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER
from .result_records import NATIVE_RESULT_ORIGIN
from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
from .result_records import RESULT_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.execution_job_submission.local_job_execution.native_execution_service import TerminalExecutionBehavior
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.communication import validate_form

from .report_fields import LocalExecutionToParentFields

from .report_reference_access import LocalExecutionToParentReferenceAccess

class LocalExecutionToParent(LocalExecutionToParentReferenceAccess, LocalExecutionToParentFields):

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a104.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        self.native_blast_masking_results.applies(context)
        self.native_blast_utility_results.applies(context)
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_standard_database_result_records import empty_facts
            native_empty.update(empty_facts())
            self.native_blast_standard_database_results.applies(context)
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_database_result_records import empty_facts
            native_empty.update(empty_facts())
            self.native_blast_database_results.applies(context)
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            self.native_hmmer_preparation_results.applies(context)
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            self.native_blast_results.applies(context)
        self.native_hmmer_results.applies(context)
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
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a104.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
