"""Private A102 scientific received evidence."""
from __future__ import annotations
from .scientific_contracts import PROTEIN_ACTION_FACT_SOURCES, merge_protein_structure_action_facts, plain, protein_structure_action_fact_sources, requested_protein_structure_action_fields

class ScientificReceivedEvidence:

    def received_report_sources(self, role):
        return protein_structure_action_fact_sources() if role == 'annotation' else {}

    def received_report_facts(self, context):
        if context.role != 'annotation':
            return {}
        contract = plain(context.request).get('report_contract')
        schema = {} if contract is None else contract.get('measurements', {}).get('schema', {})
        facts = {}
        for source in PROTEIN_ACTION_FACT_SOURCES:
            if requested_protein_structure_action_fields(schema, fact_source=source):
                facts[source] = merge_protein_structure_action_facts(self.services.protein_structure_action_received_facts(context, fact_source=source), fact_source=source)
        return facts

    def validate_received_report(self, context, form, schema):
        if context.role == 'annotation':
            self._validate_protein_structure_action_report(context, form, schema)
            from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.report_validation import validate_structural_report
            validate_structural_report(self, context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_action_records import protein_structure_action_form_references
        return protein_structure_action_form_references(plain(form), plain(schema))

    def resolve_received_reference(self, context, reference, namespace):
        return self.services.protein_structure_reference_access(context, reference, namespace)
