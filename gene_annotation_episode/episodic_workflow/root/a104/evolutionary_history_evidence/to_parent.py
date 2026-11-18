"""Private A104 scientific to parent."""
from __future__ import annotations
from .scientific_assignment_contracts import ReportBoundaryError, alignment_site_fact_sources, build_process_result, merge_molecular_facts, merge_process_results, molecular_fact_sources, plain, project_site_action_return, report_sources, requested_molecular_fact_sources, requested_site_projections, scientific_digest, validate_form, validate_frozen_site_return, validate_process_result
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.a104_credit import A104EvolutionaryCredit, A104PanelIdentityCredit, A104AlignmentSuitabilityCredit, A104RobustnessCredit
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import TASKS
from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import RECORD_SOURCE, received_records

def received_report_facts(binding, context, completion_snapshot, schema):
    if not any((node.get('x-source') == RECORD_SOURCE for node in schema.get('properties', {}).values())):
        return {}
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a104_report_store_required')
    return {RECORD_SOURCE: received_records(workflow.store, context.received_record_refs, plain(context.scope), committed=completion_snapshot.get('committed_record_refs', ()))}

class ScientificToParent:

    def fact_sources(self, role):
        self._role(role)
        from gene_annotation_episode.episodic_workflow.root.a104.a104_investigation import fact_sources as evolutionary_fact_sources
        axis_sources = evolutionary_fact_sources()
        return {**report_sources(self.library, self.tool_library), **axis_sources, **alignment_site_fact_sources(), **molecular_fact_sources()}

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        received = self.services.scientific_received_results(context)

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'evolutionary_history_evidence_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        schema = plain(context.request)['report_contract']['measurements']['schema']
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.to_parent import received_report_facts
        facts.update(received_report_facts(self, context, completion_snapshot, schema))
        for source, requested in requested_site_projections(schema).items():
            facts[source], cursor = ([], None)
            while True:
                page = self.services.alignment_site_own_action_results(context, source=source, selection=requested['selection'], after_decision_index=cursor, limit=64)
                facts[source].extend((project_site_action_return(record, requested['fields']) for record in page['records']))
                cursor = page['next_after_decision_index']
                if cursor is None:
                    break
        for source in requested_molecular_fact_sources(schema):
            facts[source] = merge_molecular_facts(self.services.molecular_received_facts(context, fact_source=source), self.services.molecular_own_facts(context, fact_source=source), fact_source=source)
        facts.update(self._component_scoring_facts(context))
        return facts

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        self._validate_molecular_report(context, form, original_schema)
        from gene_annotation_episode.episodic_workflow.root.a104.a104_scientific_report_validation import validate_axis_report
        validate_axis_report(self, context, form, original_schema)
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'evolutionary_history_evidence_results']
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
                    raise ValueError('evolutionary_history_evidence_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error
