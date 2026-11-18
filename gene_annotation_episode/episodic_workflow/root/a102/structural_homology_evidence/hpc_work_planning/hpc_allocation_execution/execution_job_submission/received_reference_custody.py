"""Original cross-role A102 received reference authentication and typed return custody."""
from __future__ import annotations
from .execution_contracts import RESULT_PROVIDER, deepcopy, plain

class LaunchReceivedReferenceCustody:

    def resolve_received_reference(self, context, reference, namespace):
        captured = self.local_file_sources.reference_access(context, reference, namespace)
        if captured is not None:
            return captured
        access = self._protein_reference_access(context, reference, namespace)
        if access is not None:
            return access
        if context.role in {'annotation', 'structural_homology_evidence'}:
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

    def validate_received_report(self, context, form, schema):
        self.local_file_sources.validate_received_report(context, form, schema)
        self.native_protein_structure_returns.validate_received_report(context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        references = list(self.local_file_sources.admit_return(context, form, schema, operation_key))
        admitted = self.native_protein_structure_returns.record_admission(context, form, schema, operation_key)
        references.extend(admitted)
        admitted = set(admitted)
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') not in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs'}:
                continue
            namespace = declared['items'].get('x-reference-namespace')
            for reference in form[name]:
                if (namespace != 'execution_result' or reference not in admitted) and (not self.resolve(context, reference, namespace)):
                    raise ValueError('execution_received_reference_unqualified')
                references.append(reference)
        return list(dict.fromkeys(references))
