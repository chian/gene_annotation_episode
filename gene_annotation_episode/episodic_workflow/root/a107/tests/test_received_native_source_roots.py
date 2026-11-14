"""Original ATAC/chromatin snapshot roots; current FBA route tested separately."""
from importlib import import_module
from pathlib import Path
import pytest




@pytest.mark.parametrize('stem', ['atac_differential', 'chromatin_interaction'])
def test_missing_original_worker_source_remains_unavailable(tmp_path, stem):
    module = import_module('gene_annotation_episode.episodic_workflow.root.a107.library.native_' + stem + '_preparation')
    with pytest.raises(ValueError, match='native_dependency_unavailable'):
        module._source_closure(tmp_path, [module.WORKER_MODULE])
    assert not list(tmp_path.iterdir())
