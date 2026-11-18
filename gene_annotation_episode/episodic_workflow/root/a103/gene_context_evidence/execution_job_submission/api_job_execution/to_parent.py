"""Private A103 API job to parent."""
from __future__ import annotations
from .contracts import BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, is_native_blast_database_target, is_standard_blast_database_target, obj, plain, validate_form

from .report_reference_access import ReportReferenceAccess

from .from_parent import APIJobAssignment

class APIJobReport(ReportReferenceAccess):

    def fact_sources(self, role):
        from gene_annotation_episode.episodic_workflow.root.a103.hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a103.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
                values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
        from gene_annotation_episode.episodic_workflow.root.a103.sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a103.blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        if self._has_uniprot() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a103.uniprot_return_contracts import uniprot_fact_sources
            values.update(uniprot_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values())):
            from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database attempts for partial-output acquisition; failed attempts do not establish a successful endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER producer bundles retain original attempt outputs matched by digest and requested numerical facts.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. Yielding alone is false.'}
        from gene_annotation_episode.episodic_workflow.root.a103.native_hmmer_acquisition import ORIGIN as hmmer_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin]
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. No qualified retained data yields null.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        from gene_annotation_episode.episodic_workflow.root.a103.blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        if role == 'results' and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            values[BLAST_GRADED_RETURN_SOURCE] = {'type': 'array', 'meaning': 'Retained output of the original BLAST database grader. Each artifact contains the full grader sheet and probabilities; query and any parent database constraint are checked against the original submission and native report.', 'report_schema': deepcopy(BLAST_GRADED_RETURN_SCHEMA)}
        return values

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a103.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        from gene_annotation_episode.episodic_workflow.root.a103.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a103.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a103.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        facts = self.api_execution.facts(context, completion_snapshot)
        return {**native_empty, **facts, 'execution_result_origin': None}

    def validate_report(self, context, form, original_schema):
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a103.uniprot_return_contracts import requested_uniprot_selection
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

    # Preserve the original mixin access; incoming custody is defined by its owner.
    initial_references = APIJobAssignment.initial_references
