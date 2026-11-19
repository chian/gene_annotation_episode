"""A110's execution job provider over the records the Episode holds (the ``job_provider`` of ``progress_provider``).

A target is one practical job an A110 job execution binding recorded in this run: the
``practical_assignment_v1`` one local or HPC job execution Episode executed. Each executed command of that
Episode is published to the Store as a ``source`` record of provider ``episode.practical_receipt``: its
artifact is the ``practical_receipt_information_v1`` body (run, Episode, assignment digest, scope and the
immutable command receipt) and its request artifact the ``practical_receipt_assignment_v1`` snapshot of the
assignment. The target handle is ``practical_job_`` + the digest of the job's run, Episode and assignment
digest; its scope is the scope its receipts record.

Observation only reads what those receipts record; nothing is re-acquired:

- execution status (``resource_execution_status_v1``): the job's ``resource_id`` and ``resource_kind`` from its
  assignment, its execution identity (the job execution Episode), the assignment digest as request digest, and
  the native state of the latest receipt that records the requested job (``facts.requested_job``: its
  ``status``, ``returncode`` and that receipt's captured output snapshots); with no such receipt the native
  state is ``unknown``. The status is as observed when that receipt finished;
- committed records and provenance: every receipt source of the job;
- one source-bound log window: the whole receipt body of the job's latest receipt;
- dependencies: none. A practical receipt records no relation to another job.

Raises: a job whose assignment names no ``resource_id`` (observe) and a receipt whose body and assignment
snapshot disagree. (A110 has no API job execution binding.)
"""
from __future__ import annotations

import hashlib
import json

from method_loop.jsonvalue import content_digest

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import digest
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.progress_records import resource_status

RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
ASSIGNMENT_VERSION = 'practical_receipt_assignment_v1'
HANDLE_PREFIX = 'practical_job_'
PROGRESS_VERSION = 'progress_snapshot_v1'


class JobProvider:
    """The practical jobs A110's job execution bindings the Episode holds."""

    def __init__(self, store):
        self.store = store

    # -- the recorded jobs ----------------------------------------------------------------------------------
    def _json(self, reference):
        return json.loads(self.store.get_artifact(reference))

    def jobs(self):
        """Every practical job of this run, by handle, with its receipts in publication order."""
        jobs = {}
        for source in self.store.list('source'):
            if source.get('provider') != RECEIPT_PROVIDER:
                continue
            reference = source['id']
            body = self._json(source['artifact_ref'])
            if body.get('version') != RECEIPT_VERSION:
                raise ContractError('a110_job_provider_receipt_version_unknown:' + reference)
            snapshot = self._json(source['request_ref'])
            if (snapshot.get('version') != ASSIGNMENT_VERSION or snapshot['run_id'] != body['run_id']
                    or snapshot['episode_id'] != body['episode_id'] or snapshot['scope'] != body['scope']
                    or digest(snapshot['assignment']) != body['assignment_sha256']
                    or body['receipt']['assignment_sha256'] != body['assignment_sha256']):
                raise ContractError('a110_job_provider_receipt_identity_conflict:' + reference)
            handle = HANDLE_PREFIX + digest({'run_id': body['run_id'], 'episode_id': body['episode_id'],
                                             'assignment_sha256': body['assignment_sha256']})
            job = jobs.setdefault(handle, {'handle': handle, 'run_id': body['run_id'],
                                           'episode_id': body['episode_id'],
                                           'assignment_sha256': body['assignment_sha256'],
                                           'assignment': snapshot['assignment'], 'scope': body['scope'],
                                           'receipts': []})
            if job['scope'] != body['scope']:
                raise ContractError('a110_job_provider_job_scope_conflict:' + handle)
            job['receipts'].append({'ref': reference, 'artifact_ref': source['artifact_ref'],
                                    'receipt': body['receipt']})
        for job in jobs.values():
            job['receipts'].sort(key=lambda row: (row['receipt']['finished_at'], row['ref']))
        return jobs

    def _job(self, handle):
        job = self.jobs().get(handle) if isinstance(handle, str) and handle.startswith(HANDLE_PREFIX) else None
        if job is None:
            raise KeyError(handle)
        return job

    # -- the job_provider interface ---------------------------------------------------------------------------
    def scope(self, handle):
        """The Store scope the job's receipts record; an unknown handle raises ``KeyError``."""
        return plain(self._job(handle)['scope'])

    def describe_target(self, handle, scope):
        job = self._job(handle)
        assignment = job['assignment']
        return {'handle': handle, 'kind': 'practical_job', 'run_id': job['run_id'],
                'execution_episode_id': job['episode_id'], 'assignment_id': assignment['assignment_id'],
                'assignment_sha256': job['assignment_sha256'], 'resource_kind': assignment['resource_kind'],
                'resource_id': assignment.get('resource_id'), 'endpoint': assignment['endpoint'],
                'requested_job': assignment['requested_job'], 'completion_keys': assignment['completion_keys'],
                'receipt_refs': [row['ref'] for row in job['receipts']]}

    def direct_dependencies(self, handle, scope):
        """A practical receipt records no relation to another job."""
        self._job(handle)
        return []

    def observe(self, handle, requested_fields, scope):
        """The job's state as its receipts record it; ``requested_fields`` are selected by the progress provider."""
        job = self._job(handle)
        assignment = job['assignment']
        if not assignment.get('resource_id'):
            raise ContractError('a110_job_provider_job_assignment_names_no_resource_id:' + handle)
        receipts = job['receipts']
        latest = receipts[-1]
        recorded = [row for row in receipts if 'requested_job' in row['receipt']['outcome'].get('facts', {})]
        if recorded:
            row = recorded[-1]
            fact = row['receipt']['outcome']['facts']['requested_job']
            state, returncode = fact['status'], fact['returncode']
            native_outcome = row['receipt']['outcome'].get('native_outcome') or {}
            outputs = [{'role': 'requested_output:' + item['path'], 'available': item['available'],
                        'bytes': item['size_bytes'] if item['available'] else None,
                        'writer_closed': item['available'] and state in ('completed', 'failed')}
                       for item in native_outcome.get('output_snapshots', [])]
            status_at, native = row['receipt']['finished_at'], {'requested_job': fact,
                                                                  'receipt_ref': row['ref']}
        else:
            state, returncode, outputs = 'unknown', None, []
            status_at, native = latest['receipt']['finished_at'], {'requested_job': None, 'receipt_ref': None}
        receipt_refs = [row['ref'] for row in receipts]
        observation = {'observed_at': status_at, 'state': state, 'returncode': returncode, 'failure_code': None,
                       'result_available': state == 'completed' and any(item['available'] for item in outputs),
                       'measurements': [], 'outputs': outputs, 'logs': [], 'provenance_refs': receipt_refs,
                       'native': native}
        status = resource_status({'handle': handle, 'resource_id': assignment['resource_id'],
                                  'resource_kind': assignment['resource_kind'], 'execution_id': job['episode_id'],
                                  'request_sha256': job['assignment_sha256']}, observation)
        data = self.store.get_artifact(latest['artifact_ref'])
        value = {'version': PROGRESS_VERSION, 'target_handle': handle,
                 'observed_at': latest['receipt']['finished_at'], 'provenance_refs': receipt_refs,
                 'execution_status': status, 'measurements': [],
                 'log_windows': [{'source_ref': latest['ref'], 'artifact_ref': latest['artifact_ref'],
                                  'start_byte': 0, 'end_byte': len(data),
                                  'observed_at': latest['receipt']['finished_at'],
                                  'content_sha256': hashlib.sha256(data).hexdigest()}],
                 'committed_record_refs': receipt_refs, 'dependencies': [],
                 'result_available': status['result_available']}
        return {**value, 'progress_ref': 'job_observation_' + content_digest(value)}


__all__ = ['HANDLE_PREFIX', 'JobProvider', 'RECEIPT_PROVIDER']
