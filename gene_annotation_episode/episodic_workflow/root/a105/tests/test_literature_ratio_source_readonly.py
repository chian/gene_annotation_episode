"""Fresh source-free read-only projection of explicitly constructed fixture receipts."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_ratio_source_storage import native_case, multi_source_view_case, owned, repository

@pytest.mark.parametrize('multiple_dependencies', [False, True])
def test_first_projection_in_fresh_readonly_process_never_reads_source_or_mutates(tmp_path, multiple_dependencies):
    directory = tmp_path / 'store'
    store, context, selection, _ = multi_source_view_case(directory) if multiple_dependencies else native_case(directory, known=True)
    repo = repository(store, context)
    outcome = repo.populate(context, selection, 'selected')
    reference = outcome['result']['sheet_ref']
    saved = repo.read(reference)
    owner = owned(context, outcome)
    cells = repo.fact_cells(owner, [reference], components=['reported_ratio'])
    parent = replace(owner, episode_id='fixture-parent', role='literature', path=(('literature', 'synthetic-parent'),), assignment={})
    repo.receive_cells(parent, cells, 'manual-engineering-fixture-receipt')
    observations = [list(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    fixture = {'run_id': context.run_id, 'episode_id': parent.episode_id, 'scope': dict(context.scope), 'received': list(parent.received_record_refs), 'sheet_ref': reference, 'cells': cells, 'banned_artifacts': list({store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']} | {value for item in saved['extraction']['views'] for key, value in item['metadata'].items() if key in ('original_artifact_ref', 'image_artifact_ref')}), 'observations': observations, 'selection': selection}
    path = tmp_path / 'engineering-fixture.json'
    path.write_text(json.dumps(fixture))
    store.close()
    script = 'import json, sqlite3, sys\nfrom pathlib import Path\nfrom types import SimpleNamespace\nfrom PIL import Image\nfrom gene_annotation_episode.episodic_workflow.root.a105.state import Store\nfrom gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage import LiteratureRatioSourceRepository\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_ratio_source_inputs as inputs\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_ratio_source_calculations as calculations\nfixture = json.loads(Path(sys.argv[2]).read_text())\n\ndef forbidden(*args, **kwargs):\n    raise AssertionError(\'forbidden reacquisition, decoder, calculation or mutation\')\nstore = Store.__new__(Store)\nstore.path = Path(sys.argv[1])\nstore._savepoint = 0\nstore.db = sqlite3.connect(f"file:{store.path / \'state.sqlite3\'}?mode=ro", uri=True)\nstore.db.row_factory = sqlite3.Row\nstore.db.execute(\'PRAGMA query_only=ON\')\nstore.db.create_function(\'library_scope_record\', 2, store._scope_filter_record)\noriginal_get = store.get_artifact\nreads = []\n\ndef saved_only(reference):\n    if reference in fixture[\'banned_artifacts\']:\n        raise AssertionError(\'original scientific bytes read\')\n    reads.append(reference)\n    return original_get(reference)\nstore.get_artifact = saved_only\nfor name in (\'artifact\', \'put\', \'transaction\', \'register_material\', \'parse_material\'):\n    setattr(store, name, forbidden)\ninputs.read_relative_signal_source_inputs = forbidden\ncalculations.populate_relative_signal_v2 = forbidden\nImage.open = forbidden\nrepo = LiteratureRatioSourceRepository(store, fixture[\'run_id\'])\nrepo.receive_cells = forbidden\ncontext = SimpleNamespace(run_id=fixture[\'run_id\'], episode_id=fixture[\'episode_id\'], role=\'literature\', assignment={}, scope=fixture[\'scope\'], received_record_refs=fixture[\'received\'])\nassert store.db.total_changes == 0\nactual = repo.fact_cells(context, [fixture[\'sheet_ref\']], components=[\'reported_ratio\'])\nassert actual == fixture[\'cells\']\nassert repo.fact_cells(context, [fixture[\'sheet_ref\']], components=[\'difference_from_reference\']) == []\nrepo.validate_fact_values(context, actual)\nassert repo.received_cells(context) == actual\nassert store.db.total_changes == 0\nobserved = [list(row) for row in store.db.execute(\'SELECT * FROM runtime_observations ORDER BY episode_id,unit_index\')]\nassert observed == fixture[\'observations\']\nassert reads\nprint(json.dumps({\'evidence_class\': \'constructed engineering receipt; not connected C4\', \'mode\': \'ro\', \'query_only\': store.db.execute(\'PRAGMA query_only\').fetchone()[0], \'total_changes\': store.db.total_changes, \'first_projection\': actual, \'source_bytes_read\': False, \'decoder_or_population_called\': False, \'observation_rows\': observed, \'saved_artifact_reads\': len(reads), \'storage_import\': __import__(\'gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage\', fromlist=[\'\']).__file__}))\nstore.close()\n'
    result = subprocess.run([sys.executable, '-c', script, str(directory), str(path)], text=True, capture_output=True, env={**os.environ, 'PYTHONPATH': os.pathsep.join(filter(None, (str(Path(__file__).resolve().parents[5]), os.environ.get('PYTHONPATH', ''))))})
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(result.stdout)
    assert proof['total_changes'] == 0 and proof['query_only'] == 1
    assert proof['first_projection'] == cells and proof['observation_rows'] == []

def test_readonly_constructor_missing_required_state_fails_without_ddl(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    import pytest
    from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ratio_source_storage import LiteratureRatioSourceRepository
    path = tmp_path / 'empty.sqlite3'
    sqlite3.connect(path).close()
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    try:
        with pytest.raises(ContractError, match='saved_state_unavailable'):
            LiteratureRatioSourceRepository(SimpleNamespace(db=db), 'fixture-run')
        assert db.total_changes == 0
        assert list(db.execute('SELECT name FROM sqlite_master')) == []
    finally:
        db.close()
