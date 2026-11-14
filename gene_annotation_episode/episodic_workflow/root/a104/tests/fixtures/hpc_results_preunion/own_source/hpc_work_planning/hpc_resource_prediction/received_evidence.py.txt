"""Private received evidence for A104 prediction."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain



class ReceivedEvidence:
    def _known(self, context):
        known = set(context.received_record_refs)
        selection = getattr(self.services, 'record_selection', None)
        if callable(selection):
            known.update(selection(context)['known_record_refs'])
        return known

    def resolve_received_reference(self, context, reference, namespace):
        try:
            source = self.store.get(reference)
        except (KeyError, ValueError):
            return None
        if source.get('provider') != 'episode.hpc_result':
            return None
        if namespace not in (None, 'source') or reference not in self._known(context):
            return False
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        if body['run_id'] != self.run_id:
            return False
        try:
            self.store.validate_scope(body['scope'], parent_scope=plain(context.scope))
        except ValueError:
            return False
        return True

    def read_evidence(self, context, ledger, reference):
        history = self._history(ledger)
        if reference in history:
            return history[reference]
        if not reference.startswith('source_'):
            return ledger.read(reference)
        # Results publish ordinary Store Sources as well as ledger receipts.
        # Resolve only a received Source owned by this original HPC ledger.
        rows = [row['body'] for row in ledger.records('result')
                if row['body'].get('source_ref') == reference]
        if len(rows) != 1 or self.resolve_received_reference(context, reference, 'source') is not True:
            raise ValueError('hpc_result_source_not_received_or_not_owned')
        source = self.store.get(reference)
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
        if body != expected:
            raise ValueError('hpc_result_source_receipt_conflict')
        return rows[0]
