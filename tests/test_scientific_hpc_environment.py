"""Resource wrappers retain custody without imposing a thread ceiling.

The worker probes use an explicitly simulated calculation callback and scheduler
identity. They inspect environment delivery, not Aurora execution or science.
"""
import base64
from importlib.metadata import version
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from gene_annotation_episode import component_axis_native_worker as worker
from gene_annotation_episode.hpc_scientific_commission import commission


THREAD_SETTINGS = {'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'}


def scientific_commission():
    return commission(resource_id='fixture', resource={'kind': 'fixture',
        'python_executable': '/fixture/environment/bin/python'},
        tool='chemistry.request_accounting_hpc', request_sha256='1' * 64,
        worker_sha256='2' * 64, implementation_sha256='3' * 64,
        parameters={}, files={}, worker_name='worker.py', request_name='request.json',
        program='fixture_environment_probe', version='fixture_v1',
        features={'input_bytes': 2}, preparation='Inspect the supplied environment.',
        objective='Retain the declared scientific calculation.')


def test_shared_scientific_commission_does_not_install_thread_ceilings():
    unit = scientific_commission()['candidates'][0]['units'][0]
    assert not THREAD_SETTINGS.intersection(unit['environment'])
    assert unit['environment']['PYTHONDONTWRITEBYTECODE'] == '1'


def test_unspecified_native_threads_are_not_presented_as_known_single_thread():
    declared = scientific_commission()
    assert 'worker_threads' not in declared['candidates'][0]['features']
    assert 'worker_threads' not in {row['name'] for row in declared['model']['features']}


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_worker_passes_environment_without_installing_thread_ceilings(tmp_path, monkeypatch, axis):
    input_bytes = b'{}'
    manifest = {'component-worker.py': worker.sha(Path(worker.__file__).read_bytes())}
    (tmp_path / 'component-sources.json').write_text('{}')
    request = {'version': worker.VERSION, 'axis': axis,
        'operation': 'partner.request_expression_hpc' if axis == 'A107' else 'chemistry.request_accounting_hpc',
        'selection': {}, 'scientific_profile': 'fixture_environment_probe_v1',
        'jsonschema_version': version('jsonschema'), 'code_manifest': manifest,
        'code_manifest_sha256': worker.sha(worker.canonical(manifest).encode()),
        'source_snapshot_sha256': worker.sha(b'{}'),
        'input': {'bytes_base64': base64.b64encode(input_bytes).decode(),
            'file': {'sha256': worker.sha(input_bytes), 'size_bytes': len(input_bytes)}}}
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(request))
    unit = tmp_path / 'unit'
    # A dictionary probe changes no native process's thread environment.
    environment = {'HPC_UNIT_DIRECTORY': str(unit), 'PBS_JOBID': 'simulated_policy_probe'}
    monkeypatch.setattr(worker.os, 'environ', environment)
    monkeypatch.setattr(worker.socket, 'gethostname', lambda: 'simulated-compute-policy-probe')
    monkeypatch.setattr(worker.sys, 'argv', [worker.__file__, str(path)])
    monkeypatch.setattr(worker.sys, 'path', list(sys.path))
    package = ModuleType('axis_native')
    package.__path__ = []
    contracts = ModuleType('axis_native.component_axis_native_contracts')
    contracts.load_json = json.loads
    module = ModuleType('axis_native.' + ('a107_expression_components' if axis == 'A107'
        else 'a110_chemical_accounting'))
    observed = {}

    def calculate(panel, selection):
        observed.update(environment)
        return {'version': request['scientific_profile']}

    module.calculate = calculate
    for name, supplied in (('axis_native', package), (contracts.__name__, contracts), (module.__name__, module)):
        monkeypatch.setitem(sys.modules, name, supplied)
    assert worker.main() == 0
    assert not THREAD_SETTINGS.intersection(observed)
    assert observed['TMPDIR'] == str(unit / 'tmp')
    assert observed['XDG_CACHE_HOME'] == str(unit / 'cache')
    assert observed['PYTHONDONTWRITEBYTECODE'] == '1'
