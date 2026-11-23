"""A103's execution job provider over the records the Episode holds (the ``job_provider`` of ``progress_provider``).

A target is one job an A103 job execution binding recorded in this run. Two kinds are recorded:

- a practical job: the ``practical_assignment`` one local or HPC job execution Episode executed. Each executed command of that
  Episode is published to the Store as a ``source`` record of provider ``episode.practical_receipt``: its
  artifact is the ``practical_receipt_information`` body (run, Episode, assignment digest, scope and the
  immutable command receipt) and its request artifact the ``practical_receipt_assignment`` snapshot of the
  assignment. The target handle is ``practical_job_`` + the digest of the job's run, Episode and assignment
  digest;
- an API job: the one API job an API job execution Episode ran
  (``execution_job_submission/api_job_execution/api_job_receipts``). Each executed operation of that Episode is
  published as a ``source`` record of provider ``episode.api_job_receipt``: its artifact is the
  ``api_job_receipt_information`` body (run, Episode, resource id, service, request digest, assignment
  digest, scope and the operation receipt naming the retained ``api_job_execution.<operation>`` responses) and
  its request artifact the ``api_job_receipt_assignment`` snapshot of the commissioned assignment and the
  admitted service request. The target handle is ``api_job_`` + the digest of the job's run, Episode and
  assignment digest.

A target's scope is the scope its receipts record. Observation only reads what those receipts record; nothing
is re-acquired:

- execution status (``resource_execution_status``). A practical job: the ``resource_id`` and
  ``resource_kind`` from its assignment, its execution identity (the job execution Episode), the assignment
  digest as request digest, and the native state of the latest receipt that records the requested job
  (``facts.requested_job``: its ``status``, ``returncode`` and that receipt's captured output snapshots); with
  no such receipt the native state is ``unknown``. An API job: its ``resource_id``, resource kind ``api``, its
  execution identity (the API job execution Episode), its request digest, and the decoded service event of
  the latest receipt whose event carries the job's native handle (its ``state``, ``failure_code`` and
  ``result_available``); with no such receipt the native state is ``unknown``. For a BV-BRC AppService job
  (service ``bvbrc_appservice``) the native handle is the original task (``task_id``) and its result is
  available when that latest event reports the task ``completed``: a completed AppService task's result is in
  its AppService workspace, which the result acquisition reads; no outputs are read here. The status is as
  observed when that receipt finished;
- committed records and provenance: every receipt source of the job (and, for an API job, every record its
  receipts name: the retained responses and, for an AppService job, its typed AppService receipts);
- one source-bound log window: the whole receipt body of the job's latest receipt;
- dependencies: none. A receipt records no relation to another job.

Raises: a job whose assignment names no ``resource_id`` (observe), and a receipt whose body and assignment
snapshot disagree. An unknown handle raises ``KeyError``.
"""
from __future__ import annotations

import hashlib
import json

from method_loop.jsonvalue import content_digest

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import digest
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.progress_records import resource_status

RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information'
ASSIGNMENT_VERSION = 'practical_receipt_assignment'
HANDLE_PREFIX = 'practical_job_'
API_RECEIPT_PROVIDER = 'episode.api_job_receipt'
API_RECEIPT_VERSION = 'api_job_receipt_information'
API_ASSIGNMENT_VERSION = 'api_job_receipt_assignment'
API_HANDLE_PREFIX = 'api_job_'
APPSERVICE = 'bvbrc_appservice'
PROGRESS_VERSION = 'progress_snapshot'


class JobProvider:
    """The practical and API jobs A103's job execution bindings the Episode holds."""

    def __init__(self, store):
        self.store = store

    # -- the recorded jobs ----------------------------------------------------------------------------------
    def _json(self, reference):
        return json.loads(self.store.get_artifact(reference))

    def _receipt_sources(self, provider):
        for source in self.store.list('source'):
            if source.get('provider') == provider:
                yield source['id'], source

    def jobs(self):
        """Every practical and API job of this run, by handle, with its receipts in publication order."""
        jobs = {}
        for reference, source in self._receipt_sources(RECEIPT_PROVIDER):
            body = self._json(source['artifact_ref'])
            if body.get('version') != RECEIPT_VERSION:
                raise ContractError('a103_job_provider_receipt_version_unknown:' + reference)
            snapshot = self._json(source['request_ref'])
            if (snapshot.get('version') != ASSIGNMENT_VERSION or snapshot['run_id'] != body['run_id']
                    or snapshot['episode_id'] != body['episode_id'] or snapshot['scope'] != body['scope']
                    or digest(snapshot['assignment']) != body['assignment_sha256']
                    or body['receipt']['assignment_sha256'] != body['assignment_sha256']):
                raise ContractError('a103_job_provider_receipt_identity_conflict:' + reference)
            handle = HANDLE_PREFIX + digest({'run_id': body['run_id'], 'episode_id': body['episode_id'],
                                             'assignment_sha256': body['assignment_sha256']})
            job = jobs.setdefault(handle, {'handle': handle, 'kind': 'practical_job', 'run_id': body['run_id'],
                                           'episode_id': body['episode_id'],
                                           'assignment_sha256': body['assignment_sha256'],
                                           'assignment': snapshot['assignment'], 'scope': body['scope'],
                                           'receipts': []})
            if job['scope'] != body['scope']:
                raise ContractError('a103_job_provider_job_scope_conflict:' + handle)
            job['receipts'].append({'ref': reference, 'artifact_ref': source['artifact_ref'],
                                    'receipt': body['receipt']})
        for reference, source in self._receipt_sources(API_RECEIPT_PROVIDER):
            body = self._json(source['artifact_ref'])
            if body.get('version') != API_RECEIPT_VERSION:
                raise ContractError('a103_job_provider_api_receipt_version_unknown:' + reference)
            snapshot = self._json(source['request_ref'])
            if (snapshot.get('version') != API_ASSIGNMENT_VERSION or snapshot['run_id'] != body['run_id']
                    or snapshot['episode_id'] != body['episode_id'] or snapshot['scope'] != body['scope']
                    or snapshot['resource_id'] != body['resource_id'] or snapshot['service'] != body['service']
                    or digest(snapshot['assignment']) != body['assignment_sha256']
                    or digest(snapshot['request']) != body['request_sha256']):
                raise ContractError('a103_job_provider_api_receipt_identity_conflict:' + reference)
            handle = API_HANDLE_PREFIX + digest({'run_id': body['run_id'], 'episode_id': body['episode_id'],
                                                 'assignment_sha256': body['assignment_sha256']})
            identity = {'handle': handle, 'kind': 'api_job', 'run_id': body['run_id'],
                        'episode_id': body['episode_id'], 'assignment_sha256': body['assignment_sha256'],
                        'assignment': snapshot['assignment'], 'scope': body['scope'],
                        'resource_id': body['resource_id'], 'service': body['service'],
                        'request': snapshot['request'], 'request_sha256': body['request_sha256']}
            job = jobs.setdefault(handle, {**identity, 'receipts': []})
            if {key: job[key] for key in identity} != identity:
                raise ContractError('a103_job_provider_api_job_identity_conflict:' + handle)
            job['receipts'].append({'ref': reference, 'artifact_ref': source['artifact_ref'],
                                    'receipt': body['receipt']})
        for job in jobs.values():
            job['receipts'].sort(key=lambda row: (row['receipt']['finished_at'], row['ref']))
        return jobs

    def _job(self, handle):
        if isinstance(handle, str) and handle.startswith((HANDLE_PREFIX, API_HANDLE_PREFIX)):
            job = self.jobs().get(handle)
            if job is not None:
                return job
        raise KeyError(handle)

    # -- the job_provider interface ---------------------------------------------------------------------------
    def scope(self, handle):
        """The Store scope the job's receipts record; an unknown handle raises ``KeyError``."""
        return plain(self._job(handle)['scope'])

    def describe_target(self, handle, scope):
        job = self._job(handle)
        receipt_refs = [row['ref'] for row in job['receipts']]
        if job['kind'] == 'api_job':
            handles = [row['receipt']['event']['native_handle'] for row in job['receipts']
                       if row['receipt']['event'] is not None and row['receipt']['event']['native_handle'] is not None]
            return {'handle': handle, 'kind': 'api_job', 'run_id': job['run_id'],
                    'execution_episode_id': job['episode_id'], 'assignment_sha256': job['assignment_sha256'],
                    'resource_kind': 'api', 'resource_id': job['resource_id'], 'service': job['service'],
                    'request': job['request'], 'request_sha256': job['request_sha256'],
                    'native_handle': handles[-1] if handles else None, 'receipt_refs': receipt_refs,
                    'response_refs': self._response_refs(job)}
        assignment = job['assignment']
        return {'handle': handle, 'kind': 'practical_job', 'run_id': job['run_id'],
                'execution_episode_id': job['episode_id'], 'assignment_id': assignment['assignment_id'],
                'assignment_sha256': job['assignment_sha256'], 'resource_kind': assignment['resource_kind'],
                'resource_id': assignment.get('resource_id'), 'endpoint': assignment['endpoint'],
                'requested_job': assignment['requested_job'], 'completion_keys': assignment['completion_keys'],
                'receipt_refs': receipt_refs}

    def direct_dependencies(self, handle, scope):
        """A receipt records no relation to another job."""
        self._job(handle)
        return []

    @staticmethod
    def _response_refs(job):
        return list(dict.fromkeys(ref for row in job['receipts'] for ref in row['receipt']['response_refs']))

    def observe(self, handle, requested_fields, scope):
        """The job's state as its receipts record it; ``requested_fields`` are selected by the progress provider."""
        job = self._job(handle)
        receipts = job['receipts']
        latest = receipts[-1]
        receipt_refs = [row['ref'] for row in receipts]
        if job['kind'] == 'api_job':
            target, observation, committed = self._api_observation(job, receipt_refs)
        else:
            target, observation, committed = self._practical_observation(handle, job, receipt_refs)
        status = resource_status({'handle': handle, **target}, observation)
        data = self.store.get_artifact(latest['artifact_ref'])
        value = {'version': PROGRESS_VERSION, 'target_handle': handle,
                 'observed_at': latest['receipt']['finished_at'], 'provenance_refs': committed,
                 'execution_status': status, 'measurements': [],
                 'log_windows': [{'source_ref': latest['ref'], 'artifact_ref': latest['artifact_ref'],
                                  'start_byte': 0, 'end_byte': len(data),
                                  'observed_at': latest['receipt']['finished_at'],
                                  'content_sha256': hashlib.sha256(data).hexdigest()}],
                 'committed_record_refs': committed, 'dependencies': [],
                 'result_available': status['result_available']}
        return {**value, 'progress_ref': 'job_observation_' + content_digest(value)}

    def _practical_observation(self, handle, job, receipt_refs):
        assignment = job['assignment']
        if not assignment.get('resource_id'):
            raise ContractError('a103_job_provider_job_assignment_names_no_resource_id:' + handle)
        receipts = job['receipts']
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
            status_at, native = receipts[-1]['receipt']['finished_at'], {'requested_job': None, 'receipt_ref': None}
        observation = {'observed_at': status_at, 'state': state, 'returncode': returncode, 'failure_code': None,
                       'result_available': state == 'completed' and any(item['available'] for item in outputs),
                       'measurements': [], 'outputs': outputs, 'logs': [], 'provenance_refs': receipt_refs,
                       'native': native}
        target = {'resource_id': assignment['resource_id'], 'resource_kind': assignment['resource_kind'],
                  'execution_id': job['episode_id'], 'request_sha256': job['assignment_sha256']}
        return target, observation, receipt_refs

    def _api_observation(self, job, receipt_refs):
        receipts = job['receipts']
        handled = [row for row in receipts
                   if row['receipt']['event'] is not None and row['receipt']['event']['native_handle'] is not None]
        if handled:
            row = handled[-1]
            event = row['receipt']['event']
            state, failure_code = event['state'], event['failure_code']
            available = state == 'completed' if job['service'] == APPSERVICE else event['result_available']
            status_at, native = row['receipt']['finished_at'], {'event': event, 'receipt_ref': row['ref']}
        else:
            state, failure_code, available = 'unknown', None, False
            status_at, native = receipts[-1]['receipt']['finished_at'], {'event': None, 'receipt_ref': None}
        committed = [*receipt_refs, *self._response_refs(job)]
        observation = {'observed_at': status_at, 'state': state, 'returncode': None, 'failure_code': failure_code,
                       'result_available': available, 'measurements': [], 'outputs': [], 'logs': [],
                       'provenance_refs': committed, 'native': native}
        target = {'resource_id': job['resource_id'], 'resource_kind': 'api', 'execution_id': job['episode_id'],
                  'request_sha256': job['request_sha256']}
        return target, observation, committed


__all__ = ['API_HANDLE_PREFIX', 'API_RECEIPT_PROVIDER', 'HANDLE_PREFIX', 'JobProvider', 'RECEIPT_PROVIDER']
