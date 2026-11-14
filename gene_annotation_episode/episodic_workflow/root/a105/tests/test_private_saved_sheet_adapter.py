"""Cold reconstruct actual A105 sheets from persisted pre-library adapters.

Source operands are explicitly synthetic and authenticated by the original A105
fixture. This verifies stored scientific adapter reconstruction and read-only
sheet custody, not autonomous interpretation or complete workflow restoration.
"""
import json
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_sheet_updates as updates
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
from .test_private_assay_publication import fixture_context

def test_cold_saved_pre_library_adapters_read_original_science_without_rewriting_history(tmp_path, monkeypatch):
    axis = 'gene_annotation_episode.episodic_workflow.root.a105.'
    with Store(tmp_path / 'state') as store:
        context, arguments = fixture_context(store)
        outcome = LiteratureAssayGradingRepository(store, context.run_id).populate(context, arguments, 'saved-assay-assessment')
        assert outcome['status'] in ('completed', 'partial'), outcome
        rows = store.db.execute(f'SELECT sheet_ref,adapter,receipt FROM {updates.TABLE}').fetchall()
        assert {row['adapter'].split(':')[1] for row in rows} == {'LiteratureAssayGradingRepository', 'LiteratureA105AggregationRepository'}
        saved = []
        for row in rows:
            original = updates._adapter(store, context.run_id, row['adapter']).read(row['sheet_ref'])
            adapter = row['adapter'].replace(axis + 'library.', axis)
            receipt = json.loads(row['receipt'])
            receipt['scientific_calculator'] = receipt['scientific_calculator'].replace(axis + 'library.', axis)
            receipt = json.dumps(receipt, sort_keys=True, separators=(',', ':'))
            store.db.execute(f'UPDATE {updates.TABLE} SET adapter=?,receipt=? WHERE sheet_ref=?', (adapter, receipt, row['sheet_ref']))
            saved.append((row['sheet_ref'], adapter, receipt, original))

    def forbidden(*args, **kwargs):
        raise AssertionError('cold adapter reconstruction must not recalculate science or reread source')
    from gene_annotation_episode.episodic_workflow.root.a105.library import literature_assay_grading_storage as grading
    from gene_annotation_episode.episodic_workflow.root.a105.library import literature_a105_aggregation_storage as scoring
    monkeypatch.setattr(grading, 'grade_assay', forbidden)
    monkeypatch.setattr(grading, 'read_assay_grading_inputs', forbidden)
    monkeypatch.setattr(scoring, 'aggregate_a105', forbidden)
    resolved = []
    import_module = updates.import_module

    def traced(name):
        resolved.append(name)
        return import_module(name)
    monkeypatch.setattr(updates, 'import_module', traced)
    with Store(tmp_path / 'state') as cold:
        cold.db.execute('PRAGMA query_only=ON')
        changes = cold.db.total_changes
        for ref, adapter, receipt, original in saved:
            rebuilt = updates._adapter(cold, context.run_id, adapter)
            assert type(rebuilt) in (LiteratureAssayGradingRepository, LiteratureA105AggregationRepository)
            assert rebuilt.read(ref) == original
            row = cold.db.execute(f'SELECT adapter,receipt FROM {updates.TABLE} WHERE sheet_ref=?', (ref,)).fetchone()
            assert tuple(row) == (adapter, receipt)
        assert cold.db.total_changes == changes
        assert cold.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
    assert LiteratureAssayGradingRepository.__module__ in resolved
    assert LiteratureA105AggregationRepository.__module__ in resolved
