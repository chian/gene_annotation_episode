from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_progress_assessment.hmmer_observer import HMMERObserver

class APIObserver:

    def __init__(self, reader):
        self.reader = reader

    def _observation(self, target, event, snapshot, provenance=()):
        facts = deepcopy(event['facts'])
        if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
            facts['error_response'] = api_error_response(snapshot)
        return {'observed_at': snapshot.retrieved_at if snapshot is not None else _now(), 'state': event['state'], 'returncode': None, 'failure_code': event['failure_code'], 'result_available': event['result_available'], 'measurements': [], 'outputs': [], 'logs': [], 'provenance_refs': [target['handle'], *provenance], 'native': {'service': target['assignment']['service'], 'kind': event['kind'], 'handle': event['native_handle'], 'facts': facts}}

    def observe_target(self, target, *, operation_key, native_operation=None, observation_context=None):
        target = validate_target(plain(target))
        if target['assignment'].get('service') == 'bvbrc_appservice':
            from gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_progress_assessment.appservice_observer import AppServiceObserver as AppServiceMonitor
            return AppServiceMonitor(self.reader).observe(target, operation_key=operation_key, native_operation=native_operation, observation_context=observation_context)
        if native_operation is not None or observation_context is not None:
            raise ValueError('api_native_observation_not_supported')
        if target['assignment'].get('version') == 'api_execution_assignment_v1':
            return HMMERObserver(self.reader._legacy_binding()).observe_target(target, operation_key=operation_key)
        if target != self.reader.read_target(target['handle'], target['scope']):
            raise ValueError('api_observation_target_identity_conflict')
        directory = self.reader.directory / 'observations' / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            _immutable(directory / 'target.json', target)
            if (directory / 'observation.json').exists():
                return _read(directory / 'observation.json')
            body = self.reader._read_handoff(target['handle'], target['scope'])
            service = self.reader.services[target['resource_id']]
            command = service.prepare_observation(target['assignment']['request'], body['event']['native_handle'], scope=target['scope'])
            if command is None:
                value = self._observation(target, body['event'], self.reader._load_snapshot(body['snapshot']))
            else:
                try:
                    intent_path, snapshot_path = (directory / 'intent.json', directory / 'snapshot.json')
                    fresh = not intent_path.exists()
                    _immutable(intent_path, command)
                    if snapshot_path.exists():
                        snapshot = self.reader._load_snapshot(_read(snapshot_path))
                    elif fresh:
                        snapshot = service.invoke(command)
                        _immutable(snapshot_path, self.reader._snapshot(snapshot))
                    else:
                        raise AcquisitionError('api_observation_response_unknown', phase='recovery')
                    event = self.reader._event(service.decode(command, snapshot))
                    provenance = self.reader.store.artifact(canonical(_read(snapshot_path)), 'application/json')
                    value = self._observation(target, event, snapshot, [provenance])
                except Exception as error:
                    event = {'kind': 'job', 'state': 'unknown', 'native_handle': body['event']['native_handle'], 'handoff_ready': False, 'result_available': False, 'facts': api_error_feedback(error), 'failure_code': getattr(error, 'code', 'api_service_observation_failed')}
                    value = self._observation(target, event, None)
            _immutable(directory / 'observation.json', value)
            return value
