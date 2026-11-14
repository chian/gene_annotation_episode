"""Private A110 scientific to_parent."""
from __future__ import annotations
from .scientific_assignment_contracts import ContractError, ReportBoundaryError, build_process_result, merge_process_results, plain, report_sources, scientific_digest, validate_form, validate_process_result
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError

def qualification_facts(binding, context, schema):
    """Publish only requested A110 qualification references already received."""
    from gene_annotation_episode.episodic_workflow.root.a110.a110_qualification import FACT_SOURCE, received
    if not any((node.get('x-source') == FACT_SOURCE for node in schema.get('properties', {}).values())):
        return {}
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a110_qualification_report_store_required')
    return {FACT_SOURCE: [row['source_ref'] for row in received(workflow.store, context.received_record_refs, context.scope)]}

class ScientificToParent:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a110.a110_qualification import fact_sources as chemical_qualification_sources
        from gene_annotation_episode.episodic_workflow.root.a110.component_axis_native_hpc import fact_sources as native_fact_sources
        axis_sources = {**chemical_qualification_sources(), **native_fact_sources()}
        return {**report_sources(self.library, self.tool_library), **axis_sources}

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a110.scientific_process_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'scientific_process_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        from gene_annotation_episode.episodic_workflow.root.a110 import component_axis_native_hpc as native
        for source, reader_name in ((native.FACT_SOURCE, 'received_components'), (native.EXECUTION_SOURCE, 'execution_findings')):
            if any((node.get('x-source') == source for node in schema.get('properties', {}).values())):
                workflow = getattr(self.services, 'workflow', None)
                if workflow is None:
                    raise ContractError('component_native_report_store_required')
                rows = getattr(native, reader_name)(workflow.store, context.received_record_refs, context.scope)
                facts[source] = [row['source_ref'] for row in sorted(rows, key=lambda item: item['source_ref'])]
        from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.to_parent import qualification_facts
        facts.update(qualification_facts(self, context, schema))
        facts.update(self._component_scoring_facts(context))
        return facts

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self._validate_component_axis_report(context, form, original_schema)
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'scientific_process_results']
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
                    raise ValueError('scientific_process_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error
