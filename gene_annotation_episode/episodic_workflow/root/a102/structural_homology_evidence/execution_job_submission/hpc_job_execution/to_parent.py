"""Private A102 native execution to parent."""
from __future__ import annotations
from .contracts import LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, plain, validate_form

from .report_reference_access import NativeReportReferenceAccess

from .from_parent import NativeAssignment

class NativeReport(NativeReportReferenceAccess):

    def fact_sources(self, role):
        values = {}
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a102.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_result_views import protein_structure_fact_sources
            values['execution_file_source_refs'] = {'type': 'array', 'meaning': 'Selected local file sources retained by this results episode.', 'report_schema': deepcopy(SOURCE_REFS_SCHEMA)}
            values['execution_file_capture_outcomes'] = {'type': 'array', 'meaning': 'Selected file availability, status, and custody qualifications.', 'report_schema': deepcopy(OUTCOMES_SCHEMA)}
            values.update(protein_structure_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            values.update(TerminalExecutionBehavior.fact_sources(None, role))
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Authenticated original execution handoffs available to this episode.'), ('execution_result_refs', 'execution_result', 'Actual requested A102 result acquisitions available to this episode.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether the assigned A102 endpoint has verified completion information.'}
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Acquisition semantics of the retained A102 result.', 'report_schema': {**deepcopy(NATIVE_RESULT_ORIGIN_SCHEMA), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        return values

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_result_views import protein_structure_fact_sources
        native_empty = {source: [] for source in protein_structure_fact_sources()}
        if self.native_protein_structure_results.applies(context):
            return {**native_empty, **self.native_protein_structure_results.facts(context, verify_artifacts=False)}
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

    # Preserve the original direct report-mixin access to incoming references.
    initial_references = NativeAssignment.initial_references
