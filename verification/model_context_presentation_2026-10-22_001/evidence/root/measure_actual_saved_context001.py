"""Read-only input measurement; no old-run reconstruction or provider call."""
from pathlib import Path
from hashlib import sha256
import json,sqlite3
from gene_annotation_episode.model_context_presentation import prepare_model_context_presentation,validate_model_context_presentation
from method_loop.durable import canonical
ROOT=Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002'); DB=ROOT/'workspace/state.sqlite3'; OUT=Path('/tmp/model-context-root-005-evidence/ACTUAL_SAVED_CONTEXT_MEASUREMENT001.json'); RUN='run_a9cae64280ed405594a79255d659f917'; EP='episode_b14eea3b01b27015465bafe0cc229f7552fcd9baa33f601b82cc5a23d6c17ea8'
def h(p):return sha256(p.read_bytes()).hexdigest() if p.exists() else None
def guard():return {str(p):{'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else None,'sha256':h(p)} for p in [DB,Path(str(DB)+'-wal'),Path(str(DB)+'-shm')]}
before=guard(); wal=Path(str(DB)+'-wal'); assert not wal.exists() or wal.stat().st_size==0
with sqlite3.connect(DB.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
 db.execute('PRAGMA query_only=ON')
 request,response=db.execute('SELECT request,response FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=179',(RUN,EP)).fetchone()
 assert response is None
assert sha256(request.encode()).hexdigest()=='21e2407799ae840e2192619396d1c74ee823fc445dab2a13aab5e940816ad16c'
raw=json.loads(request)['context']; original=canonical(raw); args={'run_id':RUN,'episode_id':EP,'before_decision_index':179,'preview_size':24}; p=prepare_model_context_presentation(raw,**args); validated=validate_model_context_presentation(p,original_context=raw,**args); assert canonical(p)==canonical(validated) and canonical(raw)==original
page=p['context']['waiting_support']['own_completed_action_history_page']; assert(page['total_rows'],page['included_rows'],page['omitted_rows'])==(175,24,151); assert len(json.dumps(raw,allow_nan=False))==1059082; assert p['model_input_char_count']==392252
assert guard()==before
result={'version':'actual_saved_context_pure_measurement_v1','source_run_id':RUN,'pending_decision_index':179,'pending_request_sha256':sha256(request.encode()).hexdigest(),'original_context_chars':1059082,'model_presentation_chars':p['model_input_char_count'],'model_input_text_sha256':p['model_input_text_sha256'],'original_context_sha256':p['original_context_sha256'],'presented_context_sha256':p['presented_context_sha256'],'raw_history_rows':175,'included_history_rows':24,'omitted_from_model_only':151,'helper_validation_passed':True,'raw_context_unchanged':True,'source_database_and_sidecars_unchanged':before,'source_open':'mode=ro&immutable=1, query_only; absent/empty WAL precondition verified','source_run_reconstructed':False,'model_provider_calls':0,'scoring_or_controller_evaluations':0,'claim_limit':'Pure implemented-helper measurement on the original saved input. No repaired scientific model dispatch, source migration, request mutation or resumed execution.'}
with OUT.open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['original_context_chars','model_presentation_chars','raw_history_rows','included_history_rows','helper_validation_passed','source_run_reconstructed','model_provider_calls']}))
