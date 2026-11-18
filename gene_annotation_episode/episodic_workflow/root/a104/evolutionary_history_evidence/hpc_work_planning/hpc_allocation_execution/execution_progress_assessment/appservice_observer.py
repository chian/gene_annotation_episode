from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_monitor_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_monitor_custody import AppServiceMonitorCustody

class AppServiceObserver(AppServiceMonitorCustody):

    def _selection(self, target, native_operation, context, operation_key):
        _require(type(native_operation) is str and native_operation in _CHOICES, 'native_operation_required')
        assignment, _, _ = self._monitor(context)
        _require(type(operation_key) is str, 'selected_action_identity_required')
        prefix = f'{self.api.run_id}:{context.episode_id}:'
        suffix = operation_key.removeprefix(prefix)
        _require(operation_key.startswith(prefix) and suffix.isdecimal() and (str(int(suffix)) == suffix), 'selected_action_identity_required')
        row = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.api.run_id, context.episode_id, int(suffix))).fetchone()
        _require(row is not None, 'selected_action_missing')
        action = json.loads(row['action'])
        arguments = action.get('arguments')
        schema = {'type': 'object', 'additionalProperties': False, 'properties': {'requested_fields': _FIELDS, 'native_operation': {'type': 'string', 'enum': list(_CHOICES)}}, 'required': ['requested_fields', 'native_operation']}
        validate_schema(arguments, schema)
        _require(action == {'kind': 'tool', 'tool': 'progress.observe', 'arguments': arguments} and arguments['native_operation'] == native_operation and (set(arguments['requested_fields']) <= set(assignment['requested_fields'])), 'selected_action_conflict')
        original = self.api.appservice.read_target(target['handle'], context.scope)
        _require(canonical(target) == canonical(original), 'target_identity_conflict')
        body = self.api.appservice.read_handoff(target['handle'], context.scope)
        self._possession(context, target, body['task_handoff'])
        return (arguments, body)

    def _prepare(self, target, native_operation, body):
        suffix = 'status' if native_operation == 'query_tasks' else 'task_info'
        arguments = {'handoff_ref': target['handle']}
        if suffix == 'task_info':
            arguments['file'] = native_operation
        handoff = body['task_handoff']
        bound = validate_contract('BoundInputs', {'version': 'bvbrc_appservice_bound_inputs_v1', 'original_job_owner': handoff['original_job_owner'], 'resource_id': target['resource_id'], 'request_sha256': digest(target['assignment']['request']), 'selected_argument_sha256': digest(arguments), 'definition': None, 'inputs': [], 'objects': [], 'support_receipt_refs': [target['handle']], 'original_handoff_ref': target['handle'], 'capability': None, 'custody_proof_refs': [target['handle']], 'resolved': {'operation': _PREFIX + suffix, 'original_task': handoff['original_task']}})
        service = self.api.services[target['resource_id']]
        prepared = service.prepare_observation(target['assignment']['request'], {'task_id': handoff['original_task']['task_id']}, scope=target['scope'], native_operation=native_operation, bound_inputs=bound)
        _require(prepared['purpose'] == 'observation' and (not prepared['mutates_remote']) and (not prepared['effects']), 'unexpected_effect')
        return (service, prepared)

    def _response(self, directory, intent, service, *, fresh):
        path = directory / 'response.json'
        signature = digest(intent)

        def retain(snapshot, failure):
            _require(snapshot is None or isinstance(snapshot, SourceSnapshot), 'snapshot_required')
            value = {'version': VERSION, 'intent_sha256': signature, 'snapshot': None if snapshot is None else self.api._snapshot(snapshot), 'failure': failure}
            _immutable(path, value)
            return value
        if path.exists():
            value = _read(path)
        elif not fresh:
            issued = directory / 'issued.json'
            if issued.exists():
                _require(_read(issued)['intent_sha256'] == signature, 'issue_identity_conflict')
            value = retain(None, {'code': 'api_observation_response_unknown' if issued.exists() else 'api_observation_not_issued', 'phase': 'recovery'})
        else:
            _immutable(directory / 'issued.json', {'version': VERSION, 'intent_sha256': signature, 'issued_at': _now()})
            try:
                snapshot = service.invoke(intent['prepared'])
                _require(isinstance(snapshot, SourceSnapshot), 'snapshot_required')
            except AcquisitionError as error:
                value = retain(error.snapshot, {name: deepcopy(getattr(error, name)) for name in ('code', 'phase', 'retry_after', 'submission_outcome', 'job_ref', 'diagnostic', 'operational')})
            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit) as error:
                if getattr(error, 'snapshot', None) is not None:
                    retain(error.snapshot, None)
                raise
            else:
                value = retain(snapshot, None)
        _require(set(value) == {'version', 'intent_sha256', 'snapshot', 'failure'} and value['version'] == VERSION and (value['intent_sha256'] == signature), 'response_identity_conflict')
        snapshot = None if value['snapshot'] is None else self.api._load_snapshot(value['snapshot'])
        return (snapshot, value)

    def _source(self, intent, response, snapshot):
        metadata = self.store.artifact(canonical({'intent': intent, 'response': response}), 'application/json')
        return self.store.put('source', {'provider': PROVIDER, 'accession': 'monitor_' + digest(intent), 'uri': snapshot.url, 'artifact_ref': response['snapshot']['content_ref'], 'text_ref': None, 'request_ref': metadata, 'version': VERSION, 'retrieved_at': snapshot.retrieved_at, 'parent_source_refs': [intent['target']['handle']]}, origin='external')['id']

    def _project(self, intent, response, snapshot, service):
        target, choice = (intent['target'], intent['native_operation'])
        failure = response['failure']
        facts, source, event = ({}, None, None)
        if snapshot is not None:
            source = self._source(intent, response, snapshot)
            event = self.api._event(service.decode(intent['prepared'], snapshot))
            facts = event['facts']
        qualified_query = bool(choice == 'query_tasks' and event is not None and (event['failure_code'] is None) and (facts.get('native_task_id') == target['execution_id']))
        observed_state = qualified_query and facts.get('native_status') is not None
        native = {'service': 'bvbrc_appservice', 'kind': 'job', 'handle': {'task_id': target['execution_id']}, 'operation': choice, 'state_observed': observed_state, 'source_ref': source, 'qualification_codes': list(facts.get('qualification_codes', []))}
        if not observed_state:
            native['qualification_codes'] = list(dict.fromkeys([*native['qualification_codes'], 'execution_state_not_observed']))
        if qualified_query:
            native.update(native_status=facts['native_status'], native_timing=deepcopy(facts['native_timing']), timing_representation={'timestamp_timezone': None, 'elapsed_time_unit': 'SQL_TIMEDIFF'})
        if event is not None:
            native['parse_status'] = facts.get('parse_status')
            native['diagnostics'] = [{key: row[key] for key in ('code', 'path', 'severity') if key in row} for name in ('diagnostics', 'task_diagnostics', 'rpc_diagnostics') for row in facts.get(name, [])]
        if failure is not None:
            native['acquisition_failure'] = {key: failure.get(key) for key in ('code', 'phase')}
        outputs, logs = ([], [])
        if snapshot is not None:
            native['transport'] = {key: deepcopy(snapshot.transport[key]) for key in ('status', 'body_complete', 'received_body_bytes', 'duration_measure', 'http_turnaround_seconds') if key in snapshot.transport}
            if choice in ('stdout', 'stderr'):
                try:
                    service._snapshot(intent['prepared'], snapshot)
                except (ValueError, KeyError, TypeError):
                    pass
                else:
                    if 200 <= snapshot.transport['status'] < 300 and 'log_windows' in intent['arguments']['requested_fields']:
                        raw = snapshot.content
                        outputs = [{'role': choice, 'available': True, 'bytes': len(raw), 'writer_closed': False}]
                        logs = [{'role': choice, 'path': snapshot.url, 'offset': 0, 'observed_size': len(raw), 'bytes_base64': base64.b64encode(raw).decode('ascii')}]
                        native['log_representation'] = 'signature_redacted_http_bytes'
                        native['log_offset_basis'] = 'retained_response_bytes'
        return validate_resource_observation({'observed_at': snapshot.retrieved_at if snapshot is not None else intent['started_at'], 'state': event['state'] if observed_state else 'unknown', 'returncode': None, 'failure_code': failure['code'] if failure is not None else None if event is None else event['failure_code'], 'result_available': False, 'measurements': [], 'outputs': outputs, 'logs': logs, 'provenance_refs': [target['handle'], *([] if source is None else [source])], 'native': native})

    def observe(self, target, *, operation_key, native_operation, observation_context):
        target = validate_target(plain(target))
        arguments, body = self._selection(target, native_operation, observation_context, operation_key)
        service, prepared = self._prepare(target, native_operation, body)
        directory = self.api.directory / 'observations' / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        original = {'version': VERSION, 'operation_key': operation_key, 'target': target, 'native_operation': native_operation, 'observation_context': observation_context.as_record(), 'name': 'progress.observe', 'arguments': arguments, 'prepared': prepared, 'resource_configuration': deepcopy(service.configuration)}
        with (directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = directory / 'intent.json'
            fresh = not path.exists()
            if fresh:
                intent = {**original, 'started_at': _now()}
                _immutable(path, intent)
            else:
                intent = _read(path)
                _require(canonical({k: v for k, v in intent.items() if k != 'started_at'}) == canonical(original), 'operation_key_reused_for_different_work')
            outcome = directory / 'observation.json'
            if outcome.exists():
                return validate_resource_observation(_read(outcome))
            snapshot, response = self._response(directory, intent, service, fresh=fresh)
            value = self._project(intent, response, snapshot, service)
            _immutable(outcome, value)
            return value
