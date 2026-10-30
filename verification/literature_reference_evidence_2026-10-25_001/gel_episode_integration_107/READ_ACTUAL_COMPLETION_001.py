"""Read genuine retained C4 completion metadata; never add an observation."""
from pathlib import Path
import json,sqlite3
from types import SimpleNamespace
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.runtime import Record
from gene_annotation_episode.completion_evidence import CompletionEvidence
from method_loop.identities import UnitRef
from method_loop.durable import DurableExecutionStore

base=Path(__file__).resolve().parent
folder=base/'actual_tests_001/test_actual_independent_worker0'
store=Store.__new__(Store);store.path=folder/'state';store._savepoint=0
store.db=sqlite3.connect(store.path.joinpath('state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)
store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record',2,store._scope_filter_record)
def forbidden(*a,**kw):raise AssertionError('completion metadata read invoked scientific source, model or mutation')
store.get_artifact=forbidden
for name in ('put','artifact','transaction'):setattr(store,name,forbidden)
manifest=json.loads((folder/'run/run.json').read_text());run=manifest['run_id']
journal=Journal.__new__(Journal);journal.store=store;journal.db=store.db;journal.run_id=run
row=store.db.execute("SELECT * FROM runtime_completion_slots WHERE json_extract(slot,'$.kind')='child_return'").fetchone()
slot=json.loads(row['slot']);episode=slot['episode_id'];index=slot['original_decision_index']
observed=store.db.execute("SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?",(run,episode,index)).fetchone()
observed=json.loads(observed[0]);unit=UnitRef.from_record(observed['unit_ref'])
provider=SimpleNamespace(run_id=run,read_progress=forbidden)
backend=DurableExecutionStore(folder/'run/episode-execution')
before=store.db.total_changes;count=store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
evidence=CompletionEvidence(store,journal,backend,provider).capture(episode,original_decision_index=index,
    unit_ref=unit,controller_input=Record(slot['controller_input']))
assert evidence['child_return']['admission_state']=='admitted'
assert evidence['received_record_refs'] and evidence['received_progress_refs']==[]
assert evidence['child_return']['child_handle']==slot['child_return']['handle']
assert store.db.total_changes==before==0
assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==count
proof={'evidence_class':'Actual completed scripted independent-worker C4 original return read through CompletionEvidence in mode=ro; not paper/model science',
    'source_directory':str(folder),'evidence':evidence,'total_changes':store.db.total_changes,'observation_count_before_after':count}
path=base/'ACTUAL_COMPLETION_EVIDENCE_001.json';assert not path.exists();path.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'admission_state':evidence['child_return']['admission_state'],'record_ref_count':len(evidence['received_record_refs']),
    'received_progress_refs':evidence['received_progress_refs'],'total_changes':store.db.total_changes,'observations':count}))
store.close()
