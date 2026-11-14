"""Original request custody only; runtime verification is a controlled dependency.

No native preparation, process, scientific worker or copied runtime runs here.
The separate retained import-control workflow owns those integration claims.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from .. import native_hmmer_preparation_result_publication as publication
from ..local_jobs import LocalJobPolicy


@pytest.fixture
def sealed_request(tmp_path, monkeypatch):
    def create(form, mutation=None):
        directory = tmp_path / 'grading' / 'native-hmmer-preparation-grading'
        directory.mkdir(parents=True)
        policy = LocalJobPolicy(memory_bytes=1024, scratch_bytes=1024 * 1024)
        driver = {'python_executable': '/controlled/python'}
        retained = {'driver_runtime': driver, 'python_home': '/controlled/python-home'}
        runtime_path = tmp_path / 'native-hmmer-preparation-worker-runtime' / 'runtime.json'
        runtime_path.parent.mkdir()
        runtime_path.write_text(json.dumps(retained))
        environment = {'CONTROLLED_ORIGINAL_VALUE': 'retained'}
        monkeypatch.setattr(publication, '_runtime_files', lambda value: value)
        monkeypatch.setattr(publication, '_worker_runtime', lambda location, selected_policy: retained)
        monkeypatch.setattr(publication, '_worker_environment', lambda location, selected_driver, home: environment)

        def forbidden(*args, **kwargs):
            pytest.fail('request custody validation entered native lifecycle')

        for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'collect'):
            monkeypatch.setattr(publication.native, name, forbidden)
        intent = {'controlled_request_custody': True}
        plan = {'task': 'grade', 'directory': str(directory)}
        selected = {'version': publication._WORKER_SELECTION, 'task': 'grade',
            'plan_sha256': publication.native_record_digest(plan),
            'intent_sha256': publication.native_record_digest(intent),
            'driver_runtime': driver, 'python_home': retained['python_home'],
            'runtime_path': str(runtime_path), 'runtime_sha256': publication.native_record_digest(retained),
            'command': [driver['python_executable'], '-B', '-c', publication._WORKER_PROGRAM,
                str(directory / 'execution-selection.json'), str(directory / 'plan.json')],
            'cwd': str(directory), 'environment': environment, 'policy': policy.to_dict(),
            'handle_path': str(directory / 'native-handle.json'),
            'stdout': str(directory / 'worker.stdout'), 'stderr': str(directory / 'worker.stderr')}
        paths = {name: str(directory / ('control.' + name)) for name in ('request', 'ready', 'release', 'result')}
        original_workflow = {'run_directory': str(tmp_path / 'original-workflow'),
            'window_id': '11111111-1111-1111-1111-111111111111'}
        metadata = {'policy': policy.to_dict()}
        if form != 'legacy_without_metadata':
            metadata['whole_workflow_budget'] = deepcopy(original_workflow)
        request_environment = dict(environment)
        if form == 'propagated':
            request_environment.update(GENE_EPISODE_WORKFLOW_BUDGET_FILE=str(Path(original_workflow['run_directory']) / 'workflow-budget.json'),
                GENE_EPISODE_WORKFLOW_SLOT=original_workflow['window_id'])
        request = {'command': selected['command'], 'cwd': str(directory),
            'file_bytes': policy.scratch_bytes, 'ready_path': paths['ready'],
            'release_path': paths['release'], 'result_path': paths['result'],
            'stdin_path': None, 'env': request_environment}
        if mutation is not None:
            mutation(request, metadata)
        raw = json.dumps(request, sort_keys=True).encode()
        Path(paths['request']).write_bytes(raw)
        body = {'version': publication.native.VERSION, 'unit': 'controlled-original.service',
            'paths': paths, 'request_sha256': hashlib.sha256(raw).hexdigest(),
            'command': selected['command'], 'cwd': str(directory), 'stdout': selected['stdout'],
            'stderr': selected['stderr'], 'metadata': metadata, 'stage': 'prepared', 'started_at': None}
        binding = {'version': publication.PREFIX + 'worker_handle_v1', 'handle_path': selected['handle_path'],
            'selection_sha256': publication.native_record_digest(selected), 'unit': body['unit'],
            'request_sha256': body['request_sha256'], 'paths': paths}
        for name, value in (('intent.json', intent), ('plan.json', plan), ('execution-selection.json', selected),
                ('native-handle.json', body), ('original-handle.json', binding)):
            publication._immutable(directory / name, value)
        return directory, policy, plan, selected, body
    return create


@pytest.mark.parametrize('form', ['legacy_without_metadata', 'legacy_with_metadata', 'propagated'])
def test_original_request_forms_do_not_use_current_workflow(sealed_request, monkeypatch, form):
    directory, policy, plan, selected, body = sealed_request(form)
    monkeypatch.setenv('GENE_EPISODE_WORKFLOW_BUDGET_FILE', '/unrelated/current/workflow-budget.json')
    monkeypatch.setenv('GENE_EPISODE_WORKFLOW_SLOT', '22222222-2222-2222-2222-222222222222')
    restored, handle = publication._worker_selection(directory, task='grade', policy=policy, plan=plan)
    assert restored == selected
    assert handle.read() == body
    assert body['stage'] == 'prepared' and body['started_at'] is None


@pytest.mark.parametrize('change', ['workflow_path', 'window_id', 'missing_path', 'missing_window',
    'extra_environment', 'original_environment', 'metadata_path', 'metadata_window', 'missing_metadata',
    'command', 'cwd', 'file_bytes', 'stdin_path', 'ready_path', 'release_path', 'result_path'])
def test_pinned_request_still_requires_every_original_operand(sealed_request, change):
    def mutate(request, metadata):
        if change == 'workflow_path':
            request['env']['GENE_EPISODE_WORKFLOW_BUDGET_FILE'] = '/another/workflow-budget.json'
        elif change == 'window_id':
            request['env']['GENE_EPISODE_WORKFLOW_SLOT'] = 'another-window'
        elif change == 'missing_path':
            del request['env']['GENE_EPISODE_WORKFLOW_BUDGET_FILE']
        elif change == 'missing_window':
            del request['env']['GENE_EPISODE_WORKFLOW_SLOT']
        elif change == 'extra_environment':
            request['env']['UNSELECTED'] = 'value'
        elif change == 'original_environment':
            request['env']['CONTROLLED_ORIGINAL_VALUE'] = 'changed'
        elif change == 'metadata_path':
            metadata['whole_workflow_budget']['run_directory'] = '/another/original'
        elif change == 'metadata_window':
            metadata['whole_workflow_budget']['window_id'] = 'another-original-window'
        elif change == 'missing_metadata':
            del metadata['whole_workflow_budget']
        elif change == 'command':
            request['command'] = ['another-command']
        elif change == 'file_bytes':
            request['file_bytes'] += 1
        else:
            request[change] = '/unselected/' + change
    directory, policy, plan, _, _ = sealed_request('propagated', mutate)
    with pytest.raises(publication.ContractError, match='result_worker_original_request_conflict'):
        publication._worker_selection(directory, task='grade', policy=policy, plan=plan)


def test_original_request_hash_remains_mandatory(sealed_request):
    directory, policy, plan, _, body = sealed_request('propagated')
    request_path = Path(body['paths']['request'])
    request_path.write_bytes(request_path.read_bytes() + b'\n')
    with pytest.raises(publication.ContractError, match='result_worker_original_request_conflict'):
        publication._worker_selection(directory, task='grade', policy=policy, plan=plan)
