"""Original ATAC/chromatin snapshot roots; current FBA route tested separately."""
from importlib import import_module
from pathlib import Path
import pytest


@pytest.mark.parametrize('stem,worker', [
    ('atac_differential', 'atac_differential_result_worker'),
    ('chromatin_interaction', 'chromatin_interaction_result_worker'),
])
def test_received_snapshot_resolves_original_project_root(monkeypatch, tmp_path, stem, worker):
    module = import_module('gene_annotation_episode.episodic_workflow.root.a107.library.native_' + stem + '_preparation')
    observed = []

    class ReachedSourceResolution(Exception):
        pass

    def resolve(root, modules):
        observed.append((Path(root), modules))
        raise ReachedSourceResolution

    monkeypatch.setattr(module, '_source_closure', resolve)
    with pytest.raises(ReachedSourceResolution):
        module._snapshot({'directory': str(tmp_path)}, object())
    import gene_annotation_episode
    actual_package_root = Path(gene_annotation_episode.__file__).resolve().parent.parent
    assert observed == [(actual_package_root, ['gene_annotation_episode.' + worker])]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('stem', ['atac_differential', 'chromatin_interaction'])
def test_missing_original_worker_source_remains_unavailable(tmp_path, stem):
    module = import_module('gene_annotation_episode.episodic_workflow.root.a107.library.native_' + stem + '_preparation')
    with pytest.raises(ValueError, match='native_dependency_unavailable'):
        module._source_closure(tmp_path, [module.WORKER_MODULE])
    assert not list(tmp_path.iterdir())
