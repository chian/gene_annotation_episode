"""Source and artifact identity, scope, and ancestry used by this episode."""
from __future__ import annotations
from gene_annotation_episode.domain import ContractError

class SourceReferences:

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
