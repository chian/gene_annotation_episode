
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
