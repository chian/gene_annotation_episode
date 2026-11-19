"""Actual A106 Store custody after restoration of missing parser dependencies."""
import json

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.records.documents.perturbation_evidence import materials_packing as packing


def test_private_store_installs_original_material_custody_tables(tmp_path):
    with Store(tmp_path / 'state') as store:
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'material_pack_chunks', 'material_component_spans', 'material_name_counts'} <= tables


def test_received_read_members_keep_exact_bytes_and_occurrences(tmp_path, monkeypatch):
    monkeypatch.setattr(packing, 'CHUNK_BYTES', 7, raising=False)
    raw = b'@same first\nACGTACGT\n+\n!!@@##$$\n@same second\nTTTT\n+\nIIII\n'
    with Store(tmp_path / 'state') as store:
        problem = store.create_problem(raw_sequence='MKWV', molecule='protein')
        material = store.register_material(data=raw, role='read', quality_encoding='unspecified')
        attempt = store.parse_material(material['id'])
        assert attempt['status'] == 'completed'
        members = [json.loads(row[0]) for row in store.db.execute(
            'SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal', (attempt['collection_ref'],))]
        assert [m['occurrence'] for m in members] == [0, 1]
        assert packing.component_window(store, members[0], 'sequence', 0, 8) == b'ACGTACGT'
        assert packing.component_window(store, members[0], 'quality', 0, 8) == b'!!@@##$$'
        assert packing.component_window(store, members[1], 'header', 0, 50) == b'same second'
        assert store.problem() == problem
        assert not list(store.db.execute('SELECT * FROM material_name_counts'))
