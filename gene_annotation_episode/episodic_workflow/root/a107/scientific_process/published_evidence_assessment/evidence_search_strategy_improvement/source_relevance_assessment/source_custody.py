"""Private A107 source custody."""
from __future__ import annotations
from .contracts import ContractError

class LiteratureSourceCustody:

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

    def _validate_page(self, page, scope):
        source = self._require(page['source_ref'], scope, 'source')
        if self._artifact(source, page['representation']) != page['artifact_ref']:
            raise ContractError('literature_source_artifact_mismatch', detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'], 'representation': page['representation']})
        self._require(page['artifact_ref'], scope, 'artifact')
        for reference in (*page['question_context_refs'], *page['prior_delivery_refs']):
            self._require(reference, scope)
