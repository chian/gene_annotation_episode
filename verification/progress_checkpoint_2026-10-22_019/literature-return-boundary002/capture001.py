"""One finite read-only later return boundary, metadata only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from urllib.parse import quote

OUT=Path(__file__).parent
RUN='run_d1f1317290114adb95d8a1d58ad970c1'
ROOT='episode_dbb4a5b6e50c304d33264cfdbebff3133709af38b63d07e69fc29c193ec9ad2c'
CHILD='episode_267cad05b876f1333f2c094cc23c5ad87fd97243aeb837e8bddff8040d08ca7a'
HANDLE='execution_c748279857cf36bcdcc67d2fc2b1df77dece496fab91d9165c31e204de84aa79'
BASE=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')


def now():return datetime.now(timezone.utc).isoformat()


def uri(path):return 'file:'+quote(str(path),safe='/')+'?mode=ro'


def main():
 assert not (OUT/'CAPTURE001.json').exists()
 db=None;queries=[];result={'version':'later_literature_return_boundary_v1','run_id':RUN,
  'root_episode_id':ROOT,'child_episode_id':CHILD,'handle':HANDLE,
  'scope':'finite metadata-only observation, no scientific return/use claim',
  'started_at':now(),'cross_database_atomicity_claimed':False}
 try:
  db=sqlite3.connect(uri(BASE/'workspace/state.sqlite3'),uri=True)
  db.row_factory=sqlite3.Row
  def query(sql,params=()):
   queries.append({'sql':sql,'parameters':list(params)})
   return [dict(x) for x in db.execute(sql,params).fetchall()]
  db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA query_only').fetchone()[0]==1
  db.execute('ATTACH DATABASE ? AS durable',(uri(BASE/'episode-execution/executions.sqlite'),))
  db.execute('BEGIN')
  result['main_window_start']=now()
  result['episodes']=query('SELECT episode_id,state FROM runtime_episodes WHERE run_id=? ORDER BY episode_id',(RUN,))
  result['original_intent']=query('SELECT parent_episode_id,original_decision_index,handle,commission_sha256,selected_at FROM runtime_commission_intents WHERE run_id=? AND handle=?',(RUN,HANDLE))
  result['counts_by_episode']=[]
  for episode in (ROOT,CHILD):
   counts={'episode_id':episode}
   for table in ('runtime_actions','runtime_observations','runtime_model_calls'):
    counts[table]=query('SELECT count(*) AS n FROM '+table+' WHERE run_id=? AND episode_id=?',(RUN,episode))[0]['n']
   result['counts_by_episode'].append(counts)
  installed=query("SELECT name FROM main.sqlite_master WHERE type='table' AND name='runtime_return_admissions'")
  result['admissions_table_present']=bool(installed)
  result['admissions']=query("SELECT parent_episode_id,original_decision_index,handle,return_id,credit_snapshot,json_extract(admission,'$.state') AS admission_state FROM runtime_return_admissions WHERE run_id=? AND handle=?",(RUN,HANDLE)) if installed else None
  result['main_window_end']=now();result['durable_window_start']=now()
  result['durable_commission']=query('SELECT handle,commission_sha256,lifecycle_state,return_id FROM durable.commissions WHERE handle=?',(HANDLE,))
  result['returns']=query("SELECT handle,return_id,returned_at,cursor,json_extract(envelope,'$.outcome') AS outcome FROM durable.returns WHERE handle=?",(HANDLE,))
  result['durable_window_end']=now();result['sqlite_total_changes']=db.total_changes
  assert db.total_changes==0
 finally:
  if db is not None:
   try:db.rollback()
   finally:db.close()
 result['connection_explicitly_closed']=True;result['finished_at']=now();result['queries']=queries
 result['input_paths']=[str(BASE/'workspace/state.sqlite3'),str(BASE/'episode-execution/executions.sqlite')]
 with (OUT/'CAPTURE001.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
 (OUT/'CAPTURE001.json').chmod(0o444)
 print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
