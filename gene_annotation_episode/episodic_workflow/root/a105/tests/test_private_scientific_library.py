"""Saved scientific adapter identities reconstruct their original A105 classes."""
from importlib import import_module
from types import SimpleNamespace
import pytest
AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'

@pytest.mark.parametrize('module,cls', [('literature_assay_grading_storage', 'LiteratureAssayGradingRepository'), ('literature_a105_aggregation_storage', 'LiteratureA105AggregationRepository')])
def test_saved_adapter_identity_resolves_current_original_class(monkeypatch, module, cls):
    updates = import_module(AXIS + '.library.literature_sheet_updates')
    seen = []
    marker = object()

    def factory(store, run_id):
        assert store is marker and run_id == 'original-run'
        return marker
    monkeypatch.setattr(updates, 'import_module', lambda name: seen.append(name) or SimpleNamespace(**{cls: factory}))
    old = AXIS + '.' + module + ':' + cls
    current = AXIS + '.library.' + module + ':' + cls
    assert updates._adapter(marker, 'original-run', old) is marker
    assert updates._adapter(marker, 'original-run', current) is marker
    assert seen == [AXIS + '.library.' + module] * 2

def test_current_scientific_receipt_files_exist():
    sources = import_module(AXIS + '.literature_implementation_sources')
    for name in ('literature_assay_grading.py', 'literature_assay_grading_storage.py', 'literature_a105_aggregation.py', 'literature_a105_aggregation_storage.py', 'literature_required_grading.py'):
        path = sources.source_file(name)
        assert path.is_file() and path.parent.name == 'library'
    assert sources.source_file('literature_assay_grading_legacy_cells_v1.json').is_file()
