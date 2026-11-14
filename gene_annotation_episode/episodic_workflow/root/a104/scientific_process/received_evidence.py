"""Private A104 scientific received evidence."""
from __future__ import annotations
from .scientific_assignment_contracts import merge_molecular_facts, molecular_fact_sources, plain, requested_molecular_fact_fields, requested_molecular_fact_sources

class ScientificReceivedEvidence:

    def received_report_sources(self, role):
        return molecular_fact_sources() if role == 'annotation' else {}

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        contract = plain(context.request).get('report_contract')
        schema = {} if contract is None else contract.get('measurements', {}).get('schema', {})
        facts = {source: merge_molecular_facts(self.services.molecular_received_facts(context, fact_source=source), fact_source=source) for source in requested_molecular_fact_sources(schema)}
        facts.update(self._component_scoring_facts(context))
        return facts

    def validate_received_report(self, context, form, schema):
        if context.role == 'annotation':
            self._validate_molecular_report(context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a104.protein_conservation_result_contracts import validate_conservation_return
        from gene_annotation_episode.episodic_workflow.root.a104.protein_phylogeny_result_contracts import validate_phylogeny_return
        form, schema = (plain(form), plain(schema))
        references = []
        for field in requested_molecular_fact_fields(schema, fact_source='protein_conservation_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_conservation_return_array_required')
            references.extend((validate_conservation_return(value)['source_ref'] for value in form[field]))
        for field in requested_molecular_fact_fields(schema, fact_source='protein_phylogeny_outcomes'):
            if type(form) is not dict or type(form.get(field)) is not list:
                raise ValueError('protein_phylogeny_return_array_required')
            references.extend((validate_phylogeny_return(value)['source_ref'] for value in form[field]))
        return list(dict.fromkeys(references))
