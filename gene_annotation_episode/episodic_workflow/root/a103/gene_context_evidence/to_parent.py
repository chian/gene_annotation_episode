"""Private A103 scientific to parent."""
from __future__ import annotations
from .contracts import ReportBoundaryError, _SCIENTIFIC_NAMESPACES, build_process_result, merge_process_results, plain, reference_in_context, report_sources, scientific_digest, validate_form, validate_process_result

class ScientificReport:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a103.a103_investigation import context_fact_sources
        axis_sources = context_fact_sources()
        return {**report_sources(self.library, self.tool_library), **axis_sources}

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'gene_context_evidence_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.received_context_report import received_report_facts
        facts.update(received_report_facts(self, context, completion_snapshot, schema))
        return facts

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
        if namespace is None or namespace in _SCIENTIFIC_NAMESPACES:
            if self.services.scientific_reference(context, reference, namespace):
                return True
            if namespace in _SCIENTIFIC_NAMESPACES:
                return False
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.report_validation import validate_axis_report
        validate_axis_report(self, context, form, original_schema)
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'gene_context_evidence_results']
        if not fields:
            return
        try:
            read_frozen = getattr(self.services, 'scientific_frozen_results', None)
            if not callable(read_frozen):
                raise ValueError('scientific_frozen_results_unavailable')
            frozen = read_frozen(context)
        except ValueError as error:
            raise ReportBoundaryError('Original process results unavailable', code=str(error), field=fields[0]) from error
        for name in fields:
            values = plain(form)[name]
            try:
                for value in values:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)
                if frozen is None or scientific_digest(values) != scientific_digest(frozen):
                    raise ValueError('gene_context_evidence_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error
