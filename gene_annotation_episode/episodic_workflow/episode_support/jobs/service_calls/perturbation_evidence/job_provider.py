"""A106's execution job provider over the records the Episode holds (the ``job_provider`` of ``progress_provider``).

A106's only job execution bindings are its BV-BRC AppService API job bindings
(``perturbation_evidence/.../execution_job_submission/api_job_execution``). Each retains its typed receipts in
the Store as ``source`` records of provider ``episode.bvbrc_appservice_receipt``
(``bvbrc_appservice_records.PROVIDER``; artifact ``{'version', 'contract', 'scope', 'value'}``: ``scope`` is the
admitted Store scope the operation ran under, whose digest is the receipt's ``origin.scope_sha256``). A target
is one AppService task a ``TaskHandoff`` receipt the Episode holds recorded: handle ``appservice_task_`` + the digest
of the run, the receipt's ``original_task.resource_id`` and ``task_id``; its scope is the scope that receipt
records.

Observation only reads what the receipts record; nothing is re-acquired:

- execution status (``resource_execution_status_v1``): the task's ``resource_id``, resource kind ``api``, its
  execution identity (the AppService ``task_id``), the launch assignment digest as request digest, and the
  state of the latest ``TaskObservation`` receipt of this run whose ``original_task.submission_receipt_ref``
  is the handoff and whose ``origin.scope_sha256`` is the handoff's (else the handoff's own state), as of that
  receipt's native response (``snapshot.retrieved_at``). A completed task's result is available in its
  AppService workspace; no outputs are read here;
- committed records and provenance: the handoff and those observation receipts;
- one source-bound log window: the whole retained artifact of the latest of those receipts;
- dependencies: none. An AppService receipt records no relation to another task.

Raises: a ``TaskHandoff`` receipt retained without its scope, or whose scope does not match its
``origin.scope_sha256``; a task handed off twice; a receipt whose native response has no retrieval time. An
unknown handle raises ``KeyError``.
"""
from __future__ import annotations

import hashlib
import json

from method_loop.jsonvalue import content_digest

from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_records import PROVIDER as RECEIPT_PROVIDER, VERSION as RECEIPT_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.practical_execution_records import digest
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.progress_records import resource_status

HANDLE_PREFIX = 'appservice_task_'
PROGRESS_VERSION = 'progress_snapshot_v1'


class JobProvider:
    """The AppService tasks A106's API job execution bindings the Episode holds."""

    def __init__(self, store):
        self.store = store

    # -- the recorded tasks -----------------------------------------------------------------------------------
    def _receipts(self):
        """Every retained AppService receipt of this run, in retention order."""
        rows = []
        for source in self.store.list('source'):
            if source.get('provider') != RECEIPT_PROVIDER:
                continue
            stored = json.loads(self.store.get_artifact(source['artifact_ref']))
            if stored.get('version') != RECEIPT_VERSION:
                raise ContractError('a106_job_provider_receipt_version_unknown:' + source['id'])
            # A CommonReceipt and an AcquisitionReceipt carry origin and snapshot at their top level.
            common = (stored['value'] if stored['contract'] in ('CommonReceipt', 'AcquisitionReceipt')
                      else stored['value']['receipt'])
            rows.append({'ref': source['id'], 'artifact_ref': source['artifact_ref'], 'stored': stored, 'common': common})
        return rows

    def jobs(self):
        """Every AppService task of this run that a ``TaskHandoff`` receipt recorded, by handle."""
        receipts = self._receipts()
        jobs = {}
        for row in receipts:
            if row['stored']['contract'] != 'TaskHandoff':
                continue
            reference, value, origin = row['ref'], row['stored']['value'], row['common']['origin']
            if 'scope' not in row['stored']:
                raise ContractError('a106_job_provider_task_handoff_records_no_scope:' + reference)
            scope = row['stored']['scope']
            if digest(scope) != origin['scope_sha256']:
                raise ContractError('a106_job_provider_task_handoff_scope_digest_conflict:' + reference)
            task = value['original_task']
            handle = HANDLE_PREFIX + digest({'run_id': origin['run_id'], 'resource_id': task['resource_id'],
                                             'task_id': task['task_id']})
            if handle in jobs:
                raise ContractError('a106_job_provider_task_handed_off_twice:' + handle)
            observations = [item for item in receipts if item['stored']['contract'] == 'TaskObservation'
                            and item['stored']['value']['original_task'].get('submission_receipt_ref') == reference
                            and item['common']['origin']['scope_sha256'] == origin['scope_sha256']]
            observations.sort(key=lambda item: ((item['common']['snapshot'] or {}).get('retrieved_at') or '', item['ref']))
            jobs[handle] = {'handle': handle, 'handoff': row, 'observations': observations,
                            'resource_id': task['resource_id'], 'task_id': task['task_id'], 'origin': origin,
                            'owner': value['original_job_owner'], 'scope': scope}
        return jobs

    def _job(self, handle):
        job = self.jobs().get(handle) if isinstance(handle, str) else None
        if job is None:
            raise KeyError(handle)
        return job

    # -- the job_provider interface ---------------------------------------------------------------------------
    def scope(self, handle):
        """The admitted Store scope the task's handoff receipt records; an unknown handle raises ``KeyError``."""
        return plain(self._job(handle)['scope'])

    def describe_target(self, handle, scope):
        job = self._job(handle)
        task = job['handoff']['stored']['value']['original_task']
        return {'handle': handle, 'kind': 'appservice_task', 'run_id': job['origin']['run_id'],
                'launch_episode_id': job['origin']['episode_id'], 'resource_id': job['resource_id'],
                'task_id': job['task_id'], 'required_application_id': task['required_application_id'],
                'native_application_id': task['native_application_id'],
                'assignment_sha256': job['origin']['assignment_sha256'], 'handoff_ref': job['handoff']['ref'],
                'receipt_refs': [job['handoff']['ref'], *[row['ref'] for row in job['observations']]]}

    def direct_dependencies(self, handle, scope):
        """An AppService receipt records no relation to another task."""
        self._job(handle)
        return []

    def observe(self, handle, requested_fields, scope):
        """The task's state as its receipts record it; ``requested_fields`` are selected by the progress provider."""
        job = self._job(handle)
        rows = [job['handoff'], *job['observations']]
        latest = rows[-1]
        snapshot = latest['common']['snapshot']
        if snapshot is None:
            raise ContractError('a106_job_provider_receipt_records_no_native_response:' + latest['ref'])
        state = latest['stored']['value']['state']
        receipt_refs = [row['ref'] for row in rows]
        native = {'receipt_ref': latest['ref'], 'contract': latest['stored']['contract'], 'state': state,
                  'native_status': latest['stored']['value'].get('native_status')}
        observation = {'observed_at': snapshot['retrieved_at'], 'state': state, 'returncode': None,
                       'failure_code': None, 'result_available': state == 'completed', 'measurements': [],
                       'outputs': [], 'logs': [], 'provenance_refs': receipt_refs, 'native': native}
        status = resource_status({'handle': handle, 'resource_id': job['resource_id'], 'resource_kind': 'api',
                                  'execution_id': job['task_id'],
                                  'request_sha256': job['origin']['assignment_sha256']}, observation)
        data = self.store.get_artifact(latest['artifact_ref'])
        value = {'version': PROGRESS_VERSION, 'target_handle': handle, 'observed_at': snapshot['retrieved_at'],
                 'provenance_refs': receipt_refs, 'execution_status': status, 'measurements': [],
                 'log_windows': [{'source_ref': latest['ref'], 'artifact_ref': latest['artifact_ref'],
                                  'start_byte': 0, 'end_byte': len(data), 'observed_at': snapshot['retrieved_at'],
                                  'content_sha256': hashlib.sha256(data).hexdigest()}],
                 'committed_record_refs': receipt_refs, 'dependencies': [],
                 'result_available': status['result_available']}
        return {**value, 'progress_ref': 'job_observation_' + content_digest(value)}


__all__ = ['HANDLE_PREFIX', 'JobProvider']
