"""Recalculate real local sheets from exact historical adapter descriptors.

Scientific source records are the explicit synthetic publication fixture. Stored
module names are the pre-library names, representing the saved descriptor format;
this checks their executable reconstruction, not complete workflow restoration.
"""
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a108.library import literature_sheet_updates as updates
from gene_annotation_episode.episodic_workflow.root.a108.state import Store
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import LiteratureA108GradingRepository
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
from gene_annotation_episode.episodic_workflow.root.a108.tests.test_private_context_publication import context_fixture

def test_saved_pre_library_adapters_recalculate_without_rewriting_history(tmp_path, monkeypatch):
    axis = 'gene_annotation_episode.episodic_workflow.root.a108.'
    with Store(tmp_path / 'state') as store:
        context, arguments = context_fixture(store, requested=False)
        grading = LiteratureA108GradingRepository(store, context.run_id)
        first = grading.populate(context, arguments, 'historical-assessment')
        original_sheet = first['result']['sheet_ref']
        old_main, = LiteratureA108AggregationRepository(store, context.run_id).current_annotation_cells(context)
        rows = store.db.execute(f'SELECT sheet_ref,adapter,receipt FROM {updates.TABLE}').fetchall()
        saved = []
        for row in rows:
            adapter = row['adapter'].replace(axis + 'library.', axis)
            receipt = json.loads(row['receipt'])
            receipt['scientific_calculator'] = receipt['scientific_calculator'].replace(axis + 'library.', axis)
            receipt = json.dumps(receipt, sort_keys=True, separators=(',', ':'))
            store.db.execute(f'UPDATE {updates.TABLE} SET adapter=?,receipt=? WHERE sheet_ref=?', (adapter, receipt, row['sheet_ref']))
            saved.append((row['sheet_ref'], adapter, receipt))
        resolved = []
        import_module = updates.import_module

        def traced(name):
            result = import_module(name)
            resolved.append(name)
            return result
        monkeypatch.setattr(updates, 'import_module', traced)
        historical = next((adapter for ref, adapter, _ in saved if ref == original_sheet))
        rebuilt = updates._adapter(store, context.run_id, historical)
        assert type(rebuilt) is LiteratureA108GradingRepository
        corrected = deepcopy(arguments)
        corrected['observations'][0]['relation'] = 'conflict'
        outcome = rebuilt.populate(context, corrected, 'reconstructed-assessment')
        current, = LiteratureA108AggregationRepository(store, context.run_id).current_annotation_cells(context)
        assert current['support_count'] == 0 and current['conflict_count'] == 1
        assert current['sheet_ref'] in outcome['record_refs']
        assert current['observation_sets']['conflict'] == old_main['observation_sets']['support']
        assert LiteratureA108GradingRepository.__module__ in resolved
        assert LiteratureA108AggregationRepository.__module__ in resolved
        for ref, adapter, receipt in saved:
            retained = store.db.execute(f'SELECT adapter,receipt FROM {updates.TABLE} WHERE sheet_ref=?', (ref,)).fetchone()
            assert tuple(retained) == (adapter, receipt)
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
