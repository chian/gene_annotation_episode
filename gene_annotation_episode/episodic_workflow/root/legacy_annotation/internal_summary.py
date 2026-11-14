from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in

class LegacyAnnotationInternalSummary:
    def conversation_key(self):
        callback = getattr(self.workflow.provider, 'conversation_key', None)
        return None if callback is None else callback(self.episode_id, 'REASONING')

    def interpretation_context(self, context, exchanges):
        subset = getattr(self.workflow.store, 'reference_subset', None)
        # Inspect only the public received lookup replies. A model's malformed
        # response does not deliver the records it happens to name.
        received = [row['lookup_result'] for row in exchanges
            if row.get('lookup_result_recorded', row.get('lookup_result') is not None)]
        publications = []
        for result in received:
            if isinstance(result, Mapping):
                for record in result.get('records', []):
                    if isinstance(record, Mapping):
                        publications.extend(record.get('published_references', {}).get('values', []))
        references = _references_in({'record_refs': publications}, self.workflow.store.get,
            reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        return {**context, 'visible_record_refs': list(dict.fromkeys([
            *context.get('visible_record_refs', []), *references]))}

