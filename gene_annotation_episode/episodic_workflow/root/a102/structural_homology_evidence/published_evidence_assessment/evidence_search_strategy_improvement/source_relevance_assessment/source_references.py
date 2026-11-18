"""Private A102 literature_search source references."""
from __future__ import annotations
from .source_contracts import ContractError, reference_in_context

class SourceSourceReferences:

    def _require(self, reference, scope, namespace=None):
        if not self.services.reference_in_scope(reference, scope, namespace):
            raise ContractError('literature_reference_unavailable', detail={'reference': reference, 'namespace': namespace})
        return self.services.read_record(reference)

    @staticmethod
    def _artifact(source, representation):
        if representation == 'original':
            return source['artifact_ref']
        if representation == 'text':
            return source.get('text_ref') or source['artifact_ref']
        return source.get(representation + '_ref')

    def _within_source(self, reference, root, scope):
        pending, seen = ([reference], set())
        while pending:
            current = pending.pop()
            if current == root:
                return True
            if current in seen:
                continue
            seen.add(current)
            source = self._require(current, scope, 'source')
            pending.extend(source.get('parent_source_refs', ()))
        return False

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)
