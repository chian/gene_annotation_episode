"""ResultsReportFields for this private A102 Results home."""
from __future__ import annotations
from .execution_contracts import LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, plain, validate_form

class ResultsReportFields:

    def fact_sources(self, role):
        values = {}
        from gene_annotation_episode.episodic_workflow.root.a102.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_result_views import protein_structure_fact_sources
        values['execution_file_source_refs'] = {'type': 'array', 'meaning': 'Selected local file sources retained by this results episode.', 'report_schema': deepcopy(SOURCE_REFS_SCHEMA)}
        values['execution_file_capture_outcomes'] = {'type': 'array', 'meaning': 'Selected file availability, status, and custody qualifications.', 'report_schema': deepcopy(OUTCOMES_SCHEMA)}
        values.update(protein_structure_fact_sources())
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Authenticated original execution handoffs available to this episode.'), ('execution_result_refs', 'execution_result', 'Actual requested A102 result acquisitions available to this episode.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether the assigned A102 endpoint has verified completion information.'}
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Acquisition semantics of the retained A102 result.', 'report_schema': {**deepcopy(NATIVE_RESULT_ORIGIN_SCHEMA), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        return values

