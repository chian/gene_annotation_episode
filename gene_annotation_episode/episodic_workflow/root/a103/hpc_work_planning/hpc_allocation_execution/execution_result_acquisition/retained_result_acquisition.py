"""Private A103 Results retained result acquisition."""
from __future__ import annotations
from .execution_contracts import NATIVE_RESULT_ORIGIN, _immutable, _outcome, _read, deepcopy, digest, json, plain

class ResultsRetainedResultAcquisition:

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
