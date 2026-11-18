"""Private A102 Launch retained result publication."""
from __future__ import annotations
from .execution_contracts import LOCAL_FILE_SOURCE_RECEIPT_VERSION, NATIVE_RESULT_ORIGIN, RESULT_PROVIDER, _read, base64, canonical, digest, identity, json, plain

class LaunchRetainedResultPublication:

    def _validate_result_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
        if not isinstance(body, dict) or set(body) != fields or body['version'] != 'execution_result_information_v2' or (body['run_id'] != self.run_id) or (body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
            raise ValueError('invalid_execution_result_information')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], scope)
        if canonical(target) != canonical(body['target']):
            raise ValueError('execution_result_original_target_conflict')
        selector = self._selector(body['assignment'], target)
        requested = self._windows(selector)
        row = self._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if episode is not None:
            message = json.loads(episode['request'])['message']
            if message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope'] or json.loads(episode['path'])[-1][0] != 'results':
                raise ValueError('execution_result_original_assignment_conflict')
        for window in body['windows']:
            if window['path'] not in requested:
                raise ValueError('execution_result_selector_conflict')
            raw = base64.b64decode(window['bytes_base64'], validate=True)
            start, length = requested[window['path']]
            if window['offset'] < start or window['returned_bytes'] != len(raw) or (length is not None and window['offset'] + len(raw) > start + length) or (window['size_bytes'] < 0):
                raise ValueError('execution_result_window_conflict')
        directory = self.directory / 'execution-results' / digest([self.run_id, body['episode_id']])
        path = directory / (digest(body['operation_key']) + '.receipt.json')
        if not path.exists() or canonical(_read(path)) != canonical(body):
            raise ValueError('execution_result_original_receipt_conflict')
        return row

    def _read_result(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != RESULT_PROVIDER:
            return None
        if source.get('version') == LOCAL_FILE_SOURCE_RECEIPT_VERSION:
            return self.local_file_sources.read_wrapper(reference, scope)
        raw = self.store.get_artifact(source['artifact_ref'])
        body = json.loads(raw)
        row = self._validate_result_body(body, scope)
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([body['run_id'], body['episode_id'], body['operation_key']]), 'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': None, 'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        expected = identity('source', {'origin': 'tool', 'record': payload})
        if reference != expected or raw != canonical(body).encode() or {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != payload:
            raise ValueError('execution_result_source_identity_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if outcome.get('status') != 'completed' or outcome.get('result') != body or reference not in outcome.get('record_refs', []):
                raise ValueError('execution_result_saved_outcome_conflict')
        return body
