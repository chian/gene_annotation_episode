"""Private to parent for A110 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.a110.communication import validate_form




class HPCReport:
    def fact_sources(self, role):
        self.credit_kind(role)
        return {'hpc_credit': {'type': 'number', 'meaning': 'Signed measured credit; repeated polling adds none.'},
                'hpc_model_ref': {'type': 'string', 'meaning': 'Immutable selected prediction model identity.',
                    'report_schema': {'type': 'string', 'format': 'reference',
                        'x-reference-namespace': 'hpc_model', 'x-source': 'hpc_model_ref'}},
                'hpc_accepted_obligations': {'type': 'array', 'meaning': 'Original obligations with accepted actual results.'},
                'hpc_result_refs': {'type': 'array', 'meaning': 'Sources containing original result bytes and attempt custody.',
                    'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                        'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
                        'x-source': 'hpc_result_refs'}}}

    def facts(self, context, completion_snapshot):
        ledger = self.state(context)
        return {'hpc_credit': self.credit_view(context, None)['credit'], 'hpc_model_ref': self._current_model(ledger),
            'hpc_accepted_obligations': [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
                                         if row['kind'] == 'actual'],
            'hpc_result_refs': [row['body']['source_ref'] for row in ledger.records('result')
                                if row['body']['source_ref'] in self._known(context)]}

    def resolve(self, context, reference, namespace):
        if namespace == 'hpc_model':
            return any(row['id'] == reference for row in self.state(context).records('model'))
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda ref, namespace: self.resolve(context, ref, namespace))
        facts = self.facts(context, {})
        for field, schema in original_schema.get('properties', {}).items():
            source = schema.get('x-source')
            if source in facts and form[field] != facts[source]:
                raise ValueError('hpc_report_disagrees_with_recorded_evidence')
