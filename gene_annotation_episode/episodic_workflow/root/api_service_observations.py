"""Original saved API progress views and selected native observations."""
from __future__ import annotations

from copy import deepcopy
import fcntl

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_error_feedback import api_error_feedback, api_error_response
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.immutable_json_records import _immutable, _read
from .api_service_operations import PROVIDER, _now


class APIServiceObservations:
    def received_blast_jobs(self, context, progress_provider):
        """Current saved state of only BLAST handoffs received by this episode.

        Reading this view makes no NCBI request. A status check remains a
        separately selected monitor/results action against the same RID.
        """
        from gene_annotation_episode.api_blast import blast_wait_forecast
        jobs = []
        forecast_as_of = _now()
        received = sorted(set(context.received_record_refs))
        result_targets = set()
        for reference in received:
            if not (self.directory/'result-index'/digest(reference)).exists():
                continue
            result = self.read_result(reference, context.scope)
            if result['target']['assignment'].get('service') == 'ncbi_blast':
                result_targets.add(result['target']['handle'])
        for reference in received:
            record = self.store.get(reference)
            if record.get('provider') != PROVIDER:
                continue
            body = self._read_handoff(reference, context.scope)
            if body['assignment']['service'] != 'ncbi_blast':
                continue
            target = self.read_target(reference, context.scope)
            handle = body['event']['native_handle']
            latest = progress_provider.latest_saved_observation(reference, context.scope)
            native_latest = progress_provider.latest_saved_observation(reference, context.scope,
                require_native_state=True)
            latest_failure_code = (None if latest is None else
                latest['execution_status']['native'].get('failure_code'))
            if native_latest is None:
                state = 'accepted'
                observed_at = body['snapshot']['retrieved_at']
                result_available = False
            else:
                observation = native_latest['execution_status']['native']
                state = observation['native']['facts']['native_state']
                observed_at = observation['observed_at']
                result_available = native_latest['result_available']
            progress_ref = None if latest is None else latest['progress_ref']
            # Recalculate a planning estimate from local time without polling.
            # Keep the last actual provider observation time separate so an
            # old WAITING reply is never presented as a fresh status check.
            forecast = blast_wait_forecast(handle, forecast_as_of, state)
            jobs.append({'handoff_ref': reference, 'origin_episode_id': target['origin_episode_id'],
                'rid': handle['rid'], 'subject_ref': body['assignment']['request']['subject_ref'],
                'program': body['assignment']['request']['program'],
                'database': body['assignment']['request']['database'],
                'native_state': state, 'observed_at': observed_at,
                'forecast_as_of': forecast_as_of,
                'latest_progress_failure_code': latest_failure_code,
                'wait_forecast': forecast, 'progress_ref': progress_ref,
                'result_available': result_available,
                'result_received': reference in result_targets})
        return jobs

    def _observation(self, target, event, snapshot, provenance=()):
        facts = deepcopy(event['facts'])
        if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
            facts['error_response'] = api_error_response(snapshot)
        return {'observed_at': snapshot.retrieved_at if snapshot is not None else _now(),
            'state': event['state'], 'returncode': None, 'failure_code': event['failure_code'],
            'result_available': event['result_available'], 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [target['handle'], *provenance],
            'native': {'service': target['assignment']['service'], 'kind': event['kind'],
                'handle': event['native_handle'], 'facts': facts}}

    def observe_target(self, target, *, operation_key, native_operation=None,
                       observation_context=None):
        target = validate_target(plain(target))
        if target['assignment'].get('service') == 'bvbrc_appservice':
            from .bvbrc_appservice_monitor import AppServiceMonitor
            return AppServiceMonitor(self).observe(target, operation_key=operation_key,
                native_operation=native_operation, observation_context=observation_context)
        if native_operation is not None or observation_context is not None:
            raise ValueError('api_native_observation_not_supported')
        if target['assignment'].get('version') == 'api_execution_assignment_v1':
            return self._legacy_binding().observe_target(target, operation_key=operation_key)
        if target != self.read_target(target['handle'], target['scope']):
            raise ValueError('api_observation_target_identity_conflict')
        directory = self.directory/'observations'/digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory/'.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            _immutable(directory/'target.json', target)
            if (directory/'observation.json').exists():
                return _read(directory/'observation.json')
            body = self._read_handoff(target['handle'], target['scope'])
            service = self.services[target['resource_id']]
            command = service.prepare_observation(target['assignment']['request'],
                body['event']['native_handle'], scope=target['scope'])
            if command is None:
                # An immediate completed HTTP request remains the original
                # fact, with its original observation time and no new GET.
                value = self._observation(target, body['event'], self._load_snapshot(body['snapshot']))
            else:
                try:
                    intent_path, snapshot_path = directory/'intent.json', directory/'snapshot.json'
                    fresh = not intent_path.exists()
                    _immutable(intent_path, command)
                    if snapshot_path.exists():
                        snapshot = self._load_snapshot(_read(snapshot_path))
                    elif fresh:
                        snapshot = service.invoke(command)
                        _immutable(snapshot_path, self._snapshot(snapshot))
                    else:
                        raise AcquisitionError('api_observation_response_unknown', phase='recovery')
                    event = self._event(service.decode(command, snapshot))
                    provenance = self.store.artifact(canonical(_read(snapshot_path)), 'application/json')
                    value = self._observation(target, event, snapshot, [provenance])
                except Exception as error:
                    event = {'kind': 'job', 'state': 'unknown', 'native_handle': body['event']['native_handle'],
                        'handoff_ready': False, 'result_available': False,
                        'facts': api_error_feedback(error),
                        'failure_code': getattr(error, 'code', 'api_service_observation_failed')}
                    value = self._observation(target, event, None)
            _immutable(directory/'observation.json', value)
            return value

