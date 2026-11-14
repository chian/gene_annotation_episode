"""Private A101 launch_hpc result acquisition."""
from __future__ import annotations
from .execution_contracts import LOCAL_FILE_SOURCE_RECEIPT_VERSION, NATIVE_RESULT_ORIGIN, RESULT_PROVIDER, _immutable, _outcome, _read, base64, canonical, deepcopy, digest, identity, is_native_blast_database_target, is_standard_blast_database_target, json, math, plain

class OperationalResultAcquisition:

    def _result_directory(self, context, *, create=True):
        if type(create) is not bool:
            raise TypeError('execution_results_directory_create_boolean_required')
        directory = self.directory / 'execution-results' / digest([context.run_id, context.episode_id])
        manifest = {'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / 'assignment.json', manifest)
        else:
            try:
                existing = _read(directory / 'assignment.json')
            except FileNotFoundError as error:
                raise ValueError('execution_results_assignment_control_missing') from error
            if canonical(existing) != canonical(manifest):
                raise ValueError('practical_immutable_record_conflict')
        return directory

    def _windows(self, selector):
        values = {path: (0, None) for path in selector.get('paths', [])}
        if 'path' in selector:
            values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
        return values

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id + ':' + episode_id + ':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

    async def _execute_native_results(self, context, target, tool_name, arguments, operation_key):
        self._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        selector = self._selector(plain(context.assignment), target)
        requested = self._windows(selector)
        windows = []
        if tool_name == 'execution.results.read':
            if arguments['path'] not in requested:
                raise ValueError('execution_results_selector_conflict')
            start, length = requested[arguments['path']]
            if arguments['offset'] < start or (length is not None and arguments['offset'] + arguments['limit'] > start + length):
                raise ValueError('execution_results_selector_conflict')
            windows = [arguments]
        elif tool_name == 'execution.results.collect':
            windows = [{'path': path, 'offset': start, 'limit': min(self.log_window_bytes, 1024 * 1024, length) if length is not None else min(self.log_window_bytes, 1024 * 1024)} for path, (start, length) in requested.items()]
        directory = self._result_directory(context)
        key = digest(operation_key)
        intent = {'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'target': target, 'assignment': plain(context.assignment)}
        receipt_path = directory / (key + '.receipt.json')
        if receipt_path.exists():
            _immutable(directory / (key + '.intent.json'), intent)
            body = _read(receipt_path)
        else:
            previous = self.store.db.execute('SELECT decision_index FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index DESC', (self.run_id, context.episode_id))
            for row in previous:
                if self._proof_for_action(context, f'{self.run_id}:{context.episode_id}:{row[0]}') is not None:
                    raise ValueError('execution_results_assignment_already_completed')
            _immutable(directory / (key + '.intent.json'), intent)
            observation_path = directory / (key + '.observation.json')
            if not observation_path.exists():
                observed = self.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(observation_path, observed)
            observation = _read(observation_path)
            acquired, failures = ([], [])
            for index, window in enumerate(windows):
                path = directory / (key + f'.window-{index}.json')
                if not path.exists():
                    try:
                        data = self.job_progress_provider.targets.read_file(target, **window, operation_key=operation_key + f':file:{index}')
                        value = {'window': data, 'failure': None}
                    except (ValueError, OSError) as error:
                        value = {'window': None, 'failure': {'path': window['path'], 'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable', 'exception_type': type(error).__name__}}
                    _immutable(path, value)
                value = _read(path)
                if value['window'] is not None:
                    acquired.append(value['window'])
                else:
                    failures.append(value['failure'])
            body = {'version': 'execution_result_information_v2', 'run_id': context.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope), 'assignment': plain(context.assignment), 'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments, 'target': target, 'observation': observation, 'windows': acquired, 'failures': failures, 'acquisition_origin': deepcopy(NATIVE_RESULT_ORIGIN)}
            _immutable(receipt_path, body)
        reference = self._publish_result(context, body)
        return _outcome(body, references=[reference])

    def _publish_result(self, context, body):
        self._validate_result_body(body, context.scope)
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([context.run_id, context.episode_id, body['operation_key']]), 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        return self.store.put('source', payload, origin='tool')['id']

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

    def _generic_result_selector_progress(self, context, results, initial):
        """Credit saved byte positions once, regardless of read boundaries."""
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        if not requested:
            return 0.0

        def covered(windows, start, end):
            intervals = sorted(((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes'])) for window in windows if window['offset'] < end and window['offset'] + window['returned_bytes'] > start))
            total, right = (0, start)
            for left, stop in intervals:
                if stop > right:
                    total += stop - max(left, right)
                    right = stop
            return total
        fractions = []
        for path, (start, length) in requested.items():
            windows = [(reference, window) for reference, body in results.items() for window in body['windows'] if window['path'] == path]
            observed_end = max((window['size_bytes'] for _, window in windows), default=start)
            end = start + length if length is not None else max(start, observed_end)
            if end <= start:
                fractions.append(0.0)
                continue
            all_bytes = covered((window for _, window in windows), start, end)
            old_bytes = covered((window for reference, window in windows if reference in initial), start, end)
            fractions.append((all_bytes - old_bytes) / (end - start))
        return math.fsum(fractions) / len(fractions)

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_blast_masking_results.applies(context):
            return False
        if self.native_blast_utility_results.applies(context):
            return False
        if is_standard_blast_database_target(self._target(context)):
            return False
        if is_native_blast_database_target(self._target(context)):
            return False
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max((window['size_bytes'] for window in windows))
            if length is not None:
                end = min(end, start + length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset'] + window['returned_bytes'])
            if cursor < end:
                return False
        return True
