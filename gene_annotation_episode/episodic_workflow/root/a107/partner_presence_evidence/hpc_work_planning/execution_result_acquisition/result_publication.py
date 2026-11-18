"""Private A107 Results result_publication"""
from __future__ import annotations
from .result_records import RESULT_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest

class ResultsResultPublication:

    def _publish_result(self, context, body):
        self._validate_result_body(body, context.scope)
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([context.run_id, context.episode_id, body['operation_key']]), 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        return self.store.put('source', payload, origin='tool')['id']
