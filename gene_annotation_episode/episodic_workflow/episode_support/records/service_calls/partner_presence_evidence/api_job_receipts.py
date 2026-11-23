"""The receipts an A107 API job execution Episode publishes on the run's shared Store.

Each executed operation of the Episode's one API job (completed, failed, invalid, or an interrupted
submission recorded ``issued_outcome_unknown``) is published as a ``source`` record of provider
``episode.api_job_receipt``, as local and HPC job execution publish ``episode.practical_receipt`` records:

- artifact: the ``api_job_receipt_information`` body: ``run_id``, ``episode_id``, ``resource_id``,
  ``service``, ``request_sha256`` (the admitted service request), ``assignment_sha256`` (the commissioned
  assignment), ``scope`` (the Store-admitted scope) and ``receipt`` (``position``, ``operation``, ``status``,
  the decoded ``event``, ``response_refs`` naming the records the operation retained: its
  ``api_job_execution.<operation>`` responses, or for an AppService job its ``bvbrc_appservice.<operation>``
  responses and typed ``episode.bvbrc_appservice_receipt``, ``feedback`` and ``finished_at``);
- request artifact: the ``api_job_receipt_assignment`` snapshot of the commissioned ``assignment``, the
  ``resource_id``, ``service`` and admitted ``request``.

``library/job_provider.JobProvider`` builds an API job target from these records.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import digest

RECEIPT_PROVIDER = 'episode.api_job_receipt'
RECEIPT_VERSION = 'api_job_receipt_information'
ASSIGNMENT_VERSION = 'api_job_receipt_assignment'


class ApiJobReceipts:
    """Publishes one API job Episode's operation receipts with its run, Episode, resource and request identity."""

    def __init__(self, store, bound, scope, resource_id, service, request):
        self._store = store
        assignment = json.loads(canonical(dict(bound.assignment)))
        self.identity = {'run_id': bound.run_id, 'episode_id': bound.episode_id, 'resource_id': resource_id,
                         'service': service, 'request_sha256': digest(request),
                         'assignment_sha256': digest(assignment), 'scope': scope}
        self._snapshot = {'version': ASSIGNMENT_VERSION, 'run_id': bound.run_id, 'episode_id': bound.episode_id,
                          'scope': scope, 'assignment': assignment, 'resource_id': resource_id,
                          'service': service, 'request': request}

    def publish(self, position, outcome):
        """The receipt of one executed operation as its ``source`` record; returns its reference."""
        receipt = {'position': position, 'operation': outcome['operation'], 'status': outcome['status'],
                   'event': outcome['event'], 'response_refs': list(outcome['record_refs']),
                   'feedback': outcome['feedback'], 'finished_at': datetime.now(timezone.utc).isoformat()}
        body = {'version': RECEIPT_VERSION, **self.identity, 'receipt': receipt}
        with self._store.transaction():
            artifact = self._store.artifact(canonical(body), 'application/json')
            request = self._store.artifact(canonical(self._snapshot), 'application/json')
            source = self._store.put('source', {
                'provider': RECEIPT_PROVIDER,
                'accession': 'api_job_receipt_' + digest([self.identity['run_id'], self.identity['episode_id'],
                                                          position]),
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
                'version': RECEIPT_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')
        return source['id']


__all__ = ['ApiJobReceipts', 'ASSIGNMENT_VERSION', 'RECEIPT_PROVIDER', 'RECEIPT_VERSION']
