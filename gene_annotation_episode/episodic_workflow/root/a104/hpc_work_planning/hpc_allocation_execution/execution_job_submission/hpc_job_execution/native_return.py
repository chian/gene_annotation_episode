"""Private original A104 HPCExecution service native_return."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.native_terminal_transport import digest
from gene_annotation_episode.episodic_workflow.root.a104.communication import validate_form

class HPCExecutionNativeReturn:

    def fact_sources(self, role):
        return {'practical_completed': {'type': 'boolean', 'meaning': 'Whether original requested endpoint predicates have a saved validated completion.'}, 'practical_receipt_digests': {'type': 'array', 'meaning': 'Host-recorded digests of the original selected command receipts.'}, 'practical_receipt_refs': {'type': 'array', 'meaning': 'Original selected command, actual result and earned operational credit sources.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'practical_receipt'}, 'x-source': 'practical_receipt_refs'}}}

    def facts(self, context, completion_snapshot):
        state = self.state(context)
        references = []
        if self.store is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
            information = PracticalReceiptInformation(self.store, context.run_id)
            references = [information.publish(context, receipt) for receipt in state.receipts()]
        return {'practical_completed': state.completion_proof() is not None, 'practical_receipt_digests': [digest(receipt) for receipt in state.receipts()], 'practical_receipt_refs': references}

    def resolve(self, context, reference, namespace):
        if self.store is not None and isinstance(reference, str) and reference.startswith('source_'):
            from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store, context.run_id).resolve(context, reference, namespace)
        return namespace == 'practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in original_schema.get('properties', {}).items():
            source = node.get('x-source')
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
