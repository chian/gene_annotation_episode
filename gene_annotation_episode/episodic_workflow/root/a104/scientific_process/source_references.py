"""Private A104 scientific source references."""
from __future__ import annotations
from .scientific_assignment_contracts import ROLE, _SCIENTIFIC_NAMESPACES, reference_in_context

class ScientificSourceReferences:

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
        if namespace is None or namespace in _SCIENTIFIC_NAMESPACES:
            if self.services.scientific_reference(context, reference, namespace):
                return True
            if namespace in _SCIENTIFIC_NAMESPACES:
                return False
        return reference_in_context(self.services, context, reference, namespace)

    def initial_references(self, context):
        if context.role != ROLE:
            return []
        self.validate_context(context)
        return list(dict.fromkeys([*context.assignment['evidence_refs'], *([context.assignment['proposed_annotation_ref']] if context.assignment.get('proposed_annotation_ref') else [])]))
