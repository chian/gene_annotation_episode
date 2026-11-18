"""Private scientific to parent."""
from __future__ import annotations
from .scientific_contracts import ReportBoundaryError, _SCIENTIFIC_NAMESPACES, alignment_site_fact_sources, build_process_result, merge_process_results, plain, project_site_action_return, reference_in_context, report_sources, requested_site_projections, scientific_digest, validate_form, validate_frozen_site_return, validate_process_result

class ScientificReport:

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and getattr(self.services, 'annotation_task_required', lambda: False)():
            if len(parent.path) == 1:
                return ('sequence_homology_evidence_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()

    def fact_sources(self, role):
        self._role(role)
        return {**report_sources(self.library, self.tool_library), **alignment_site_fact_sources()}

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'sequence_homology_evidence_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        for source, requested in requested_site_projections(schema).items():
            facts[source], cursor = ([], None)
            while True:
                page = self.services.alignment_site_own_action_results(context, source=source, selection=requested['selection'], after_decision_index=cursor, limit=64)
                facts[source].extend((project_site_action_return(record, requested['fields']) for record in page['records']))
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
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
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'sequence_homology_evidence_results']
        projections = requested_site_projections(plain(original_schema))
        if projections:
            try:
                frozen_sites = self.services.alignment_site_frozen_facts(context, sources=tuple(projections))
            except ValueError as error:
                raise ReportBoundaryError('Original site results unavailable', code=str(error)) from error
            validate_frozen_site_return(plain(form), plain(original_schema), frozen_sites)
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
                    raise ValueError('sequence_homology_evidence_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error
