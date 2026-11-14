"""Six actual monitor actions and immutable saved-progress replay.

Only the existing controlled HTTP response and task checkpoint port are used.
The monitor uses real WorkflowServices, public ProgressProvider, original
Launch-exported job provider, Journal, receipts and information-credit formula.
These raw singleton cases claim neither parent admission nor whole Workflow
resumption. A changed job-provider fingerprint remains an explicit denial.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from .api_cases import Case, HOMES, canonical, error_record, module, rows, task_case

sha = lambda data: hashlib.sha256(data).hexdigest()


def files(directory):
    root = Path(directory)
    return {str(path.relative_to(root)): sha(path.read_bytes())
        for path in sorted(root.rglob('*')) if path.is_file()}


class MonitorCase:
    def __init__(self, directory, home, *, saved=None):
        self.api = Case(directory, home, existing=saved is not None)
        try:
            api = self.api
            self.store, self.journal, self.receipts = api.store, api.journal, api.receipts
            self.run_id, self.scope = api.run_id, api.scope
            if saved is None:
                result = api.act('api.uniprot.record')
                assert result['status'] == 'completed'
                self.handoff = result['result']['handoff_ref']
            else:
                self.handoff = saved['handoff']
            self.launch_home = home.removesuffix('/api_job_execution')
            self.home = home.removesuffix('execution_job_submission/api_job_execution') + 'execution_progress_assessment'
            self.launch = module(self.launch_home + '/episode').ExecutionEpisode(api.services, **api.options)
            self.job_provider = self.launch.job_progress_provider
            assert self.job_provider.targets.api_execution is self.launch.api_execution
            durable = module('method_loop.durable').DurableExecutionStore(Path(directory) / 'durable')
            self.progress = module('episode_monitoring').ProgressProvider(self.store, durable,
                run_id=self.run_id, job_provider=self.job_provider)
            host = SimpleNamespace(store=self.store, run_id=self.run_id, progress_provider=self.progress)
            self.services = module('episode_services').WorkflowServices(host)
            self.binding = module(self.home + '/episode').MonitorEpisode(self.services)
            self.path = (('monitor', 'controlled-saved-api-monitor'),)
            self.episode_id = module('method_loop.identities').EpisodeRef(self.run_id, self.path).episode_id
            assignment = {'version': 'monitor_assignment_v1', 'target_handle': self.handoff,
                'requested_fields': ['execution_status'], 'known_progress_refs': [],
                'permitted_committed_record_types': []}
            # Exact incoming advertised contract; no commissioned parent edge
            # is invented for these explicitly saved singleton invocations.
            assignment = self.binding.prepare_assignment(api.context, 'monitor', assignment,
                self.scope, self.run_id + ':' + api.episode_id + ':1')
            inheritance = self.receipts.bind(self.episode_id)
            self.receipts.receive(self.episode_id, [*self.scope['subject_refs'], self.handoff], kind='initial')
            self.request = {'message': {'scope': deepcopy(self.scope),
                'episode_assignment': assignment, 'knowledge_inheritance': inheritance}}
            self.context = module('episode_bindings').BindingContext(self.run_id, self.episode_id,
                'monitor', self.path, self.scope, assignment, self.request)
            old = self.journal.row('runtime_episodes', self.episode_id)
            if old is None:
                self.journal.save('runtime_episodes', {'episode_id': self.episode_id,
                    'path': module('runtime')._json(self.path), 'request': module('runtime')._json(self.request),
                    'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            else:
                assert json.loads(old['request']) == self.request
            self.task = task_case(self)
            workflow = self.task.workflow
            workflow.services, workflow.progress_provider = self.services, self.progress
            workflow.progress_selection = lambda source: module('runtime').Workflow.progress_selection(workflow, source)
            workflow.role_credit_projectors = {'monitor': self.binding.information_credit(
                self.progress, information_unit=2.)}
            self.services.workflow = workflow
            self.chosen = {'kind': 'tool', 'tool': 'progress.observe',
                'arguments': {'requested_fields': ['execution_status']}}
            self.key = self.run_id + ':' + self.episode_id + ':0'
            if saved is not None:
                assert self.context.as_record() == saved['context']
                assert self.request == saved['request'] and self.chosen == saved['chosen'] and self.key == saved['operation_key']
        except BaseException as original:
            try:
                self.api.close()
            except BaseException as closing:
                raise BaseExceptionGroup('monitor constructor and close failures', [original, closing])
            raise

    def selection(self):
        return {'run_id': self.run_id, 'episode_id': self.episode_id,
            'known_record_refs': list(self.receipts.known(self.episode_id)),
            'initial_known_record_refs': list(self.receipts.known(self.episode_id, baseline=True)),
            **module('runtime').Workflow.progress_selection(self.task.workflow, self.context)}

    def close(self):
        self.api.close()


def capture(directory):
    destination = Path(directory); assert not destination.exists(); destination.mkdir(parents=True)
    captures = []
    for number, home in enumerate(HOMES):
        root = destination / str(number)
        value = MonitorCase(root, home)
        try:
            calls = deepcopy(value.api.client.calls)
            result = asyncio.run(value.task.task.execute(value.chosen, 0)).as_record()
            assert len(value.task.executions) == len(value.task.observations) == len(value.task.projections) == 1
            action = dict(value.journal.row('runtime_actions', value.episode_id, 0))
            payload = json.loads(action['result'])
            assert payload['status'] == 'completed' and payload['progress_refs']
            assert value.api.client.calls == calls and result['credit'] == action['credit']
            assert value.selection()['known_progress_refs'] == payload['progress_refs']
            raw = value.job_provider.latest_saved_observation(value.handoff, value.scope)
            assert raw is not None
            before = rows(value.store)
            assert asyncio.run(value.task.task.execute(value.chosen, 0)).as_record() == result
            assert rows(value.store) == before and len(value.task.executions) == 1
            snapshot = {'home': home, 'monitor_home': value.home, 'launch_home': value.launch_home,
                'handoff': value.handoff, 'context': value.context.as_record(), 'request': value.request,
                'chosen': value.chosen, 'operation_key': value.key, 'action_row': action,
                'returned_payload': payload, 'controller_input': result, 'credit_view': value.task.projections[0],
                'job_provider_descriptor': value.job_provider.as_record(), 'raw_observation': raw,
                'public_observation': value.progress.read_progress(payload['progress_refs'][0], value.scope),
                'all_rows': before, 'controlled_http_calls': calls,
                'full_workflow_resumption_established': False, 'whole_iterator_restoration_established': False}
        finally:
            value.close()
        (root / 'capture.json').write_text(json.dumps(canonical(snapshot), indent=2, sort_keys=True) + '\n')
        captures.append({'home': home, 'directory': str(number), 'files': files(root)})
    index = {'version': 'a104_actual_monitor_saved_progress_v1', 'captures': captures,
        'case_count': 6, 'controlled_ports': ['api_cases.Responses', 'api_cases.task_case.checkpoint']}
    (destination / 'index.json').write_text(json.dumps(index, indent=2, sort_keys=True) + '\n')
    return {'index_sha256': sha((destination / 'index.json').read_bytes()), 'files': files(destination)}


def authenticate(directory, custody):
    root = Path(directory)
    assert files(root) == custody['files']
    assert sha((root / 'index.json').read_bytes()) == custody['index_sha256']
    index = json.loads((root / 'index.json').read_text())
    assert index['version'] == 'a104_actual_monitor_saved_progress_v1' and index['case_count'] == 6
    assert [row['home'] for row in index['captures']] == list(HOMES)
    assert len({row['directory'] for row in index['captures']}) == 6
    for row in index['captures']:
        assert row['directory'] in {str(i) for i in range(6)}
        assert files(root / row['directory']) == row['files']
        assert json.loads((root / row['directory'] / 'capture.json').read_text())['home'] == row['home']
    return index


def reopen(directory, output, *, custody):
    root, output = Path(directory), Path(output)
    index = authenticate(root, custody)
    assert not output.exists(); output.mkdir(parents=True)
    results = []
    for row in index['captures']:
        original = root / row['directory']; copied = output / row['directory']
        shutil.copytree(original, copied)
        assert files(copied) == row['files']  # Authenticate copy before Store().
        saved = json.loads((copied / 'capture.json').read_text())
        value = MonitorCase(copied, row['home'], saved=saved)
        try:
            assert rows(value.store) == saved['all_rows'], 'constructor_changed_original_rows'
            assert value.api.client.calls == []
            original_job = value.job_provider
            native_calls = []
            def forbidden(*args, **kwargs):
                native_calls.append((args, kwargs))
                raise AssertionError('cached_monitor_action_reached_native_provider')
            # The real public provider must replay before consulting its job
            # adapter. No saved result, signature, descriptor or queue is edited.
            value.progress.job_provider = SimpleNamespace(observe=forbidden, scope=forbidden,
                direct_dependencies=forbidden, describe_target=forbidden)
            result = asyncio.run(value.task.task.execute(value.chosen, 0)).as_record()
            assert result == saved['controller_input']
            assert value.task.task.last_outcome == saved['returned_payload']
            assert value.task.executions == value.task.observations == value.task.projections == []
            public = value.progress.observe(value.handoff, ['execution_status'], value.scope,
                permitted_committed_record_types=[], operation_key=value.key)
            assert public == saved['public_observation']
            assert value.progress.read_progress(public['progress_ref'], value.scope) == public
            assert native_calls == [] and rows(value.store) == saved['all_rows']
            value.progress.job_provider = original_job
            raw = original_job.latest_saved_observation(value.handoff, value.scope)
            assert raw == saved['raw_observation']
            current = original_job.as_record()
            # A direct resource operation intentionally authenticates the real
            # current provider. Its old signature is not a compatibility alias.
            try:
                repeated = original_job.observe(value.handoff, ['execution_status'], value.scope,
                    operation_key=value.key)
            except Exception as error:
                boundary = {'raised': error_record(error)}
                assert current != saved['job_provider_descriptor']
                assert type(error) is module('domain').ContractError
                assert str(error) == 'execution_progress_operation_identity_conflict'
            else:
                assert current == saved['job_provider_descriptor'] and repeated == raw
                boundary = {'returned': repeated}
            assert value.api.client.calls == [] and rows(value.store) == saved['all_rows']
            results.append({'home': row['home'], 'context': value.context.as_record(),
                'controller_input': result, 'returned_payload': value.task.task.last_outcome,
                'public_observation': public, 'raw_observation': raw,
                'original_job_provider_descriptor': saved['job_provider_descriptor'],
                'current_job_provider_descriptor': current, 'direct_provider_same_key': boundary,
                'cached_action_and_public_selection_replayed': True, 'all_rows_unchanged': True,
                'new_native_calls': 0, 'full_workflow_resumption_established': False,
                'whole_iterator_restoration_established': False})
        finally:
            value.close()
        assert files(original) == row['files']
    assert authenticate(root, custody) == index
    return results
