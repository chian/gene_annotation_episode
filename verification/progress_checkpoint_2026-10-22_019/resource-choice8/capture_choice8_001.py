"""Additive once-only original root request8 witness; stdlib readonly only."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sqlite3,stat,sys
OUT=Path('/tmp/configured-resource-root-choice8-R-20261022-aIDjVo')
DB=Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001/workspace/state.sqlite3')
RUN='run_b1f5d2ae45664656a967e01700632ead'
EP='episode_6b74cd5bd09b8360ee8350db160ed10c7c3d3ca817ba43b0772c74e6ae8b25a6'
SQL=[]
def now():return datetime.now(timezone.utc).isoformat()
def sha(s):return None if s is None else hashlib.sha256(s.encode() if isinstance(s,str) else s).hexdigest()
def write(name,value):
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def meta():
 out={}
 for suffix in ('','-wal','-shm'):
  p=Path(str(DB)+suffix)
  try:s=p.lstat()
  except FileNotFoundError:out[str(p)]={'present':False};continue
  out[str(p)]={'present':True,'size':s.st_size,'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
 return out
def query(db,sql,args):
 SQL.append({'sql':sql,'parameters':list(args)})
 return [dict(r) for r in db.execute(sql,args)]
def decode(rows,keys):
 for row in rows:
  for k in keys:
   if row.get(k) is not None:row[k]=json.loads(row[k])
 return rows

def run():
 assert not (OUT/'ATTEMPT001.json').exists()
 write('ATTEMPT001.json',{'argv':sys.argv,'started_at':now(),'operator_sha256':sha(Path(__file__).read_bytes()),'scope_sha256':sha((OUT/'SCOPE001.json').read_bytes()),'once_only':True})
 before=meta();db=None;start=now()
 try:
  db=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True,timeout=0);db.row_factory=sqlite3.Row
  db.create_function('sha256_text',1,sha,deterministic=True)
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  assert db.execute('PRAGMA query_only').fetchone()[0]==1
  requests=query(db,'SELECT call_index,purpose,request,sha256_text(request) AS request_text_sha256 FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?',(RUN,EP,8))
  assert len(requests)<=1
  if requests:
   text=requests[0].pop('request')
   with (OUT/'original-root-request0008.json').open('x',encoding='utf-8') as f:f.write(text)
   requests[0]['member']='original-root-request0008.json';requests[0]['utf8_bytes']=len(text.encode())
  action=decode(query(db,"SELECT decision_index,json_extract(action,'$.kind') AS kind,json_extract(action,'$.tool') AS tool,json_extract(action,'$.arguments') AS selected_arguments,sha256_text(action) AS action_text_sha256,json_extract(result,'$.status') AS status,json_extract(result,'$.operation_ref') AS operation_ref,json_extract(result,'$.result.job_ref') AS nested_job_ref,json_extract(result,'$.job_ref') AS top_job_ref FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",(RUN,EP,8)),['selected_arguments'])
  jobs=[]
  if action:
   refs={v for k,v in action[0].items() if k in {'nested_job_ref','top_job_ref'} and v is not None}
   for job in sorted(refs):
    jobs.extend(decode(query(db,'SELECT id,operation_key,request,sha256_text(request) AS request_text_sha256,state,remote_id,error_code FROM provider_jobs WHERE id=?',(job,)),['request']))
  proposal=decode(query(db,"SELECT decision_index,json_extract(action,'$.tool') AS tool,json_extract(action,'$.arguments') AS selected_arguments,sha256_text(action) AS action_text_sha256,result,sha256_text(result) AS result_text_sha256 FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",(RUN,EP,3)),['selected_arguments','result'])
  assert db.total_changes==0
  capture={'version':'configured_resource_original_choice8_witness_v1','database':str(DB),'run_id':RUN,'root_episode_id':EP,'started_at':start,'finished_at':now(),'uri_mode':'ro','query_only':True,'explicit_begin':True,'immutable':False,'total_changes':0,'original_request8':requests,'selected_action8':action,'matching_provider_jobs':jobs,'original_proposal3_journal':proposal}
  write('CAPTURE001.json',capture)
 except BaseException as error:
  write('FAILURE001.json',{'type':type(error).__name__,'message':str(error),'at':now(),'no_retry':True});raise
 finally:
  if db is not None:
   if db.in_transaction:db.rollback()
   db.close()
  write('SOURCE_METADATA001.json',{'before':before,'after':meta(),'closed_at':now(),'meaning':'Active source metadata only; not a file-equality claim.'})
  write('SQL_READSET001.json',{'statements':SQL,'database_connections':1,'application_imports':0,'application_sql_writes':0,'no_polling_or_retry':True})
if __name__=='__main__':run()
