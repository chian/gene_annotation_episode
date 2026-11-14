"""Private A104 API to parent."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SOURCE
from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER
from .received_result_values import NATIVE_RESULT_ORIGIN
from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
from .received_result_values import RESULT_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a104.execution_job_submission.api_job_execution.terminal_receipt_state import TerminalExecutionBehavior
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.communication import validate_form

class APIToParentFields:

    def fact_sources(self, role):
        from gene_annotation_episode.episodic_workflow.root.a104.hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
                values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
        from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        if self._has_uniprot() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a104.uniprot_return_contracts import uniprot_fact_sources
            values.update(uniprot_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            values.update(TerminalExecutionBehavior.fact_sources(None, role))
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database attempts for partial-output acquisition; failed attempts do not establish a successful endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER producer bundles retain original attempt outputs matched by digest and requested numerical facts.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. Yielding alone is false.'}
        from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_acquisition import ORIGIN as hmmer_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin]
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. No qualified retained data yields null.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        from gene_annotation_episode.episodic_workflow.root.a104.blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        if role == 'results' and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            values[BLAST_GRADED_RETURN_SOURCE] = {'type': 'array', 'meaning': 'Retained output of the original BLAST database grader. Each artifact contains the full grader sheet and probabilities; query and any parent database constraint are checked against the original submission and native report.', 'report_schema': deepcopy(BLAST_GRADED_RETURN_SCHEMA)}
        return values

