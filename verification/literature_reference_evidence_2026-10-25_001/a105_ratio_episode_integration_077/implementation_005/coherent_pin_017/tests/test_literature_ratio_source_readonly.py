"""Fresh source-free read-only projection of explicitly constructed fixture receipts."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_literature_ratio_source_storage import native_case, multi_source_view_case, owned, repository


@pytest.mark.parametrize('multiple_dependencies', [False, True])
def test_first_projection_in_fresh_readonly_process_never_reads_source_or_mutates(tmp_path, multiple_dependencies):
    directory = tmp_path / 'store'
    store, context, selection, _ = (multi_source_view_case(directory) if multiple_dependencies
        else native_case(directory, known=True))
    repo = repository(store, context); outcome = repo.populate(context, selection, 'selected')
    reference = outcome['result']['sheet_ref']; saved = repo.read(reference)
    owner = owned(context, outcome)
    cells = repo.fact_cells(owner, [reference], components=['reported_ratio'])
    parent = replace(owner, episode_id='fixture-parent', role='literature', path=(('literature', 'synthetic-parent'),), assignment={})
    repo.receive_cells(parent, cells, 'manual-engineering-fixture-receipt')
    observations = [list(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    # No whole database copy: original fixture store is opened via actual mode=ro.
    fixture = {'run_id': context.run_id, 'episode_id': parent.episode_id, 'scope': dict(context.scope),
        'received': list(parent.received_record_refs), 'sheet_ref': reference, 'cells': cells,
        'banned_artifacts': list({store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']}
            | {value for item in saved['extraction']['views'] for key, value in item['metadata'].items()
               if key in ('original_artifact_ref', 'image_artifact_ref')}),
        'observations': observations, 'selection': selection}
    path = tmp_path / 'engineering-fixture.json'; path.write_text(json.dumps(fixture))
    store.close()
    script = r'''
import json, sqlite3, sys
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
from gene_annotation_episode import literature_ratio_source_inputs as inputs
from gene_annotation_episode import literature_ratio_source_calculations as calculations
fixture=json.loads(Path(sys.argv[2]).read_text())
def forbidden(*args,**kwargs):raise AssertionError('forbidden reacquisition, decoder, calculation or mutation')
store=Store.__new__(Store);store.path=Path(sys.argv[1]);store._savepoint=0
store.db=sqlite3.connect(f'file:{store.path / "state.sqlite3"}?mode=ro',uri=True)
store.db.row_factory=sqlite3.Row
store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record',2,store._scope_filter_record)
original_get=store.get_artifact
reads=[]
def saved_only(reference):
 if reference in fixture['banned_artifacts']:raise AssertionError('original scientific bytes read')
 reads.append(reference);return original_get(reference)
store.get_artifact=saved_only
for name in ('artifact','put','transaction','register_material','parse_material'):setattr(store,name,forbidden)
inputs.read_relative_signal_source_inputs=forbidden
calculations.populate_relative_signal_v2=forbidden
Image.open=forbidden
repo=LiteratureRatioSourceRepository(store,fixture['run_id'])
repo.receive_cells=forbidden
context=SimpleNamespace(run_id=fixture['run_id'],episode_id=fixture['episode_id'],role='literature',
 assignment={},scope=fixture['scope'],received_record_refs=fixture['received'])
assert store.db.total_changes==0
# First saved projection; no prior read warms or repairs a receipt.
actual=repo.fact_cells(context,[fixture['sheet_ref']],components=['reported_ratio'])
assert actual==fixture['cells']
assert repo.fact_cells(context,[fixture['sheet_ref']],components=['difference_from_reference'])==[]
repo.validate_fact_values(context,actual)
assert repo.received_cells(context)==actual
assert store.db.total_changes==0
observed=[list(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
assert observed==fixture['observations']
assert reads
print(json.dumps({'evidence_class':'constructed engineering receipt; not connected C4','mode':'ro',
 'query_only':store.db.execute('PRAGMA query_only').fetchone()[0], 'total_changes':store.db.total_changes,
 'first_projection':actual,'source_bytes_read':False,'decoder_or_population_called':False,
 'observation_rows':observed,'saved_artifact_reads':len(reads),'storage_import':__import__('gene_annotation_episode.literature_ratio_source_storage',fromlist=['']).__file__}))
store.close()
'''
    result = subprocess.run([sys.executable, '-c', script, str(directory), str(path)],
        text=True, capture_output=True, env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])})
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(result.stdout)
    assert proof['total_changes'] == 0 and proof['query_only'] == 1
    assert proof['first_projection'] == cells and proof['observation_rows'] == []


def test_readonly_constructor_missing_required_state_fails_without_ddl(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    import pytest
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.literature_ratio_source_storage import LiteratureRatioSourceRepository
    path = tmp_path / 'empty.sqlite3'
    sqlite3.connect(path).close()
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True); db.execute('PRAGMA query_only=ON')
    try:
        with pytest.raises(ContractError, match='saved_state_unavailable'):
            LiteratureRatioSourceRepository(SimpleNamespace(db=db), 'fixture-run')
        assert db.total_changes == 0
        assert list(db.execute('SELECT name FROM sqlite_master')) == []
    finally:
        db.close()
