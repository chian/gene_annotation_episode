"""Controlled source-discovery boundaries; no scientific/native execution."""
from pathlib import Path
import pytest

from gene_annotation_episode.episodic_workflow.root.a107.library.native_received_worker_sources import (
    AXIS, CURRENT_WORKERS, current_worker_sources, snapshot_relative_source,
)


def _source(root, module, text, *, package=False):
    path = root / Path(*module.split('.'))
    path = path / '__init__.py' if package else path.with_suffix('.py')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_current_worker_closure_keeps_defining_modules_and_package_initializers(tmp_path):
    worker = CURRENT_WORKERS['genomic_overlap']
    _source(tmp_path, 'gene_annotation_episode', '', package=True)
    _source(tmp_path, AXIS, '', package=True)
    _source(tmp_path, AXIS + '.library', '', package=True)
    _source(tmp_path, worker, 'from . import route_operand\nfrom .route_operand import value\n')
    operand = _source(tmp_path, AXIS + '.library.route_operand', 'value = 7\n')
    result = current_worker_sources(worker, module_root=tmp_path)
    assert set(result) == {'gene_annotation_episode', AXIS, AXIS + '.library', worker, AXIS + '.library.route_operand'}
    assert result[AXIS + '.library.route_operand'] == operand
    assert snapshot_relative_source(AXIS, result[AXIS]) == Path(*AXIS.split('.')) / '__init__.py'
    assert snapshot_relative_source(worker, result[worker]) == Path(*worker.split('.')).with_suffix('.py')


def test_unavailable_original_global_name_is_not_redirected_to_current_worker(tmp_path):
    with pytest.raises(ValueError, match='received_worker_source_identity_invalid'):
        current_worker_sources('gene_annotation_episode.genomic_overlap_result_worker', module_root=tmp_path)


def test_missing_current_worker_remains_unavailable(tmp_path):
    with pytest.raises(ValueError, match='native_dependency_unavailable'):
        current_worker_sources(CURRENT_WORKERS['flux_balance'], module_root=tmp_path)


def test_current_worker_rejects_foreign_axis_donor(tmp_path):
    worker = CURRENT_WORKERS['flux_balance']
    _source(tmp_path, worker, 'from gene_annotation_episode.episodic_workflow.root.a110 import flux_balance_result_worker\n')
    _source(tmp_path, 'gene_annotation_episode.episodic_workflow.root.a110', '', package=True)
    with pytest.raises(ValueError, match='received_worker_foreign_source_owner'):
        current_worker_sources(worker, module_root=tmp_path)


def test_current_source_paths_follow_real_bytes_without_retained_digest_substitution(tmp_path):
    worker = CURRENT_WORKERS['flux_balance']
    source = _source(tmp_path, worker, 'value = 1\n')
    first = current_worker_sources(worker, module_root=tmp_path)
    source.write_text('value = 2\n')
    second = current_worker_sources(worker, module_root=tmp_path)
    assert first[worker] == second[worker] == source
    assert second[worker].read_bytes() == b'value = 2\n'


def test_default_current_source_root_is_the_actual_repository(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_received_worker_sources as module
    import gene_annotation_episode
    observed = []

    class ReachedSourceResolution(Exception):
        pass

    def source(root, name):
        observed.append((root, name))
        raise ReachedSourceResolution

    monkeypatch.setattr(module, '_project_source', source)
    with pytest.raises(ReachedSourceResolution):
        module.current_worker_sources(CURRENT_WORKERS['flux_balance'])
    assert observed == [(Path(gene_annotation_episode.__file__).resolve().parent.parent, CURRENT_WORKERS['flux_balance'])]


def test_fresh_fba_snapshot_selects_current_private_worker_before_staging(monkeypatch, tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_flux_balance_preparation as module
    observed = []

    class ReachedSourceResolution(Exception):
        pass

    def source(name):
        observed.append(name)
        raise ReachedSourceResolution

    monkeypatch.setattr(module, '_current_worker_sources', source)
    with pytest.raises(ReachedSourceResolution):
        module._snapshot({'mode': 'saved_sheet_recalculation', 'directory': str(tmp_path / 'worker'),
            'sheet': {'path': '/retained/sheet'}}, object())
    assert observed == [CURRENT_WORKERS['flux_balance']]
    assert not list(tmp_path.iterdir())


def _pin(path):
    return {'path': str(path), 'sha256': '1' * 64, 'size_bytes': 1}


def _fba_intent(module, tmp_path, *, current):
    # This is an in-memory structural intent, not authenticated native evidence.
    plan = {'mode': 'saved_sheet_recalculation', 'directory': str(tmp_path / 'worker'),
        'sheet': {'path': '/retained/sheet'}}
    common, root, _ = module._layout(plan)
    worker = module._CURRENT_WORKER_MODULE if current else module.WORKER_MODULE
    dependencies = [{'distribution': 'controlled-package', 'version': '1',
        'package_root': '/runtime/site-packages/controlled',
        'files': [_pin('/runtime/site-packages/controlled/__init__.py')]}]
    value = {'version': module._CURRENT_INTENT_VERSION if current else module._INTENT_VERSION,
        'plan': plan, 'execution_directory': str(root), 'policy': module.POLICY,
        'command': [str(root / 'runtime/python'), '-B', '-S', '-m', worker, str(root / 'plan.json')],
        'environment': module._environment(root, common, '/runtime', dependencies),
        'source_pins': [_pin(root / 'source_snapshot/gene_annotation_episode/__init__.py'),
            _pin(root / 'source_snapshot' / (worker.replace('.', '/') + '.py'))],
        'interpreter': _pin(root / 'runtime/python'), 'dependencies': dependencies,
        'python_version': 'controlled', 'python_home': '/runtime',
        'runtime_files': [_pin('/runtime/lib/controlled.py')]}
    return value, plan


@pytest.mark.parametrize('current', [False, True])
def test_fba_intent_preserves_distinct_original_and_current_source_routes(tmp_path, current):
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_flux_balance_preparation as module
    value, plan = _fba_intent(module, tmp_path, current=current)
    assert module._validate_intent(value, plan) is value
    value['version'] = module._INTENT_VERSION if current else module._CURRENT_INTENT_VERSION
    with pytest.raises(ValueError, match='intent_mismatch'):
        module._validate_intent(value, plan)


def test_fba_current_intent_rejects_original_filename_under_current_command(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_flux_balance_preparation as module
    value, plan = _fba_intent(module, tmp_path, current=True)
    _, root, _ = module._layout(plan)
    value['source_pins'][1]['path'] = str(root / 'source_snapshot/gene_annotation_episode/flux_balance_result_worker.py')
    with pytest.raises(ValueError, match='source_missing'):
        module._validate_intent(value, plan)


@pytest.mark.parametrize('current', [False, True])
def test_genomic_intent_checks_the_versioned_command_and_required_source_paths(monkeypatch, tmp_path, current):
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_genomic_overlap_preparation as module
    plan = {'directory': str(tmp_path)}
    value = {'version': module._CURRENT_INTENT if current else 'genomic_overlap_worker_intent_v1',
        'plan': plan, 'policy': module._POLICY, 'environment': {}, 'interpreter': _pin(tmp_path / 'runtime/python')}
    worker = module._CURRENT_MODULE if current else module._MODULE
    value['source_pins'] = [_pin(tmp_path / 'source_snapshot' / path) for path in sorted(module._worker_source_paths(value))]
    value['command'] = [value['interpreter']['path'], '-B', '-S', '-m', worker, str(tmp_path / 'plan.json')]
    observed = []
    # Isolate source-route validation while retaining the actual _pins and
    # command predicates. No environment/dependency or native claim follows.
    monkeypatch.setattr(module, '_checked_environment', lambda *args: observed.append(args))
    assert module._validate_intent(value, plan) is value
    assert len(observed) == 1
    value['command'][4] = module._MODULE if current else module._CURRENT_MODULE
    with pytest.raises(ValueError, match='intent_conflict'):
        module._validate_intent(value, plan)


def test_genomic_original_execution_does_not_gain_current_source_identity():
    from gene_annotation_episode.episodic_workflow.root.a107.library import native_genomic_overlap_preparation as module
    assert module._worker_source_module({'version': module._EXECUTION}) == 'gene_annotation_episode.genomic_overlap_result_worker'
    assert module._worker_source_module({'version': module._CURRENT_EXECUTION}) == CURRENT_WORKERS['genomic_overlap']
    with pytest.raises(ValueError, match='source_identity_invalid'):
        module._worker_source_module({'version': 'unknown'})
    with pytest.raises(ValueError, match='execution_binding'):
        module._execution_file_format({'format': 'unknown'})


def test_current_worker_accepts_exact_shared_resource_owner_without_foreign_axis_fallback(tmp_path):
    import gene_annotation_episode
    worker = CURRENT_WORKERS['flux_balance']
    _source(tmp_path, worker, 'from gene_annotation_episode.workflow_budget import ENV, active_budget\n')
    actual = Path(gene_annotation_episode.__file__).resolve().parent / 'workflow_budget.py'
    shared = _source(tmp_path, 'gene_annotation_episode.workflow_budget', actual.read_text())
    result = current_worker_sources(worker, module_root=tmp_path)
    assert set(result) == {worker, 'gene_annotation_episode.workflow_budget'}
    assert result['gene_annotation_episode.workflow_budget'].read_bytes() == actual.read_bytes()
    assert result['gene_annotation_episode.workflow_budget'] == shared
