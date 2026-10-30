"""Actual descriptor reconstruction functions over invented metadata only."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_001'
OUT = HERE / 'verification_001'


def main():
    spec = importlib.util.spec_from_file_location('owned_preflight', HERE / 'verify_preparation_001.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.verify_pin(PIN)
    helper.install_pin(PIN)
    calls, disabled = helper.forbid_model()
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.independent_execution import _saved_episode_factories
    from method_loop.durable import DurableExecutionError
    snapshot = json.loads((OUT / 'CONTRACT_SNAPSHOT_NEW_001.json').read_bytes())
    descriptor = snapshot['descriptor']
    service = SimpleNamespace(tool_catalog=lambda _scope: [])
    sentinel = object()
    journal = SimpleNamespace(store=sentinel, run_id='invented-metadata-fixture')
    def reconstruct(row):
        return compose_episode_bindings(service, store=sentinel, journal=journal,
            execution_backend=None, descriptors=[row], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
    restored = reconstruct(descriptor)
    assert len(restored.bindings) == 1 and restored.bindings[0].as_record() == descriptor
    assert restored.progress_provider is None and restored.resource_capabilities == ()
    factories = _saved_episode_factories({'episode_bindings': [descriptor]}, directory=None)
    assert len(factories) == 1 and factories[0](service).as_record() == descriptor
    altered = {**descriptor, 'implementation_sha256': '0' * 64}
    try:
        reconstruct(altered)
    except DurableExecutionError as error:
        assert error.failure['code'] == 'identity_conflict'
    else:
        raise AssertionError('substituted_implementation_descriptor_accepted')
    imported = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and name.split('.')[0] in {'gene_annotation_episode', 'method_loop'}:
            path = Path(filename).resolve()
            assert path.is_relative_to(PIN)
            imported.append({'module': name, **helper.fingerprint(path)})
    assert not calls
    helper.verify_pin(PIN)
    helper.save(OUT / 'DESCRIPTOR_RECONSTRUCTION_002.json', {
        'scope': 'actual composition/saved-factory helpers over synthetic descriptor context; no Store, run, C1/C4 receipt or scientific source',
        'complete_composition_descriptor_equal': True, 'saved_factory_descriptor_equal': True,
        'substituted_implementation_rejected': True, 'actual_project_imports': imported,
        'disabled_model_entrypoints': disabled, 'model_entries': 0,
        'source_registration': False, 'runtime_actions': 0, 'runtime_observations': 0,
        'pin_unchanged': True})
    print(json.dumps({'status': 'passed', 'descriptor_reconstruction_paths': 2,
        'substituted_implementation_rejected': True, 'model_entries': 0,
        'source_registration': False, 'runtime_observations': 0}))


if __name__ == '__main__':
    main()
