"""One finite stdlib readonly capture. No application imports or artifact reads."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,sqlite3,stat,sys,time
OUT=Path('/tmp/configured-resource-prefix-R-20261022-zWmbii')
RUN='run_b1f5d2ae45664656a967e01700632ead'
ROOT='episode_6b74cd5bd09b8360ee8350db160ed10c7c3d3ca817ba43b0772c74e6ae8b25a6'
DIRECTORY=Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
MAIN=DIRECTORY/'workspace/state.sqlite3';DURABLE=DIRECTORY/'episode-execution/executions.sqlite'
REGISTRY='execution_registry_1411c4378f584a40b65ed74178e1cb05'
RESOURCE_ROLES={'launch','launch_api','launch_local','launch_hpc','results','job_launch','job_monitor'}
SQL=[]
def now():return datetime.now(timezone.utc).isoformat()
def sha(value):return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest() if value is not None else None
def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def metadata(path):
    result={}
    for suffix in ('','-wal','-shm'):
        p=Path(str(path)+suffix)
        try:s=p.lstat()
        except FileNotFoundError:result[str(p)]={'present':False};continue
        result[str(p)]={'present':True,'type':'regular' if stat.S_ISREG(s.st_mode) else 'other','size':s.st_size,'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
    return result

def query(db,text,args=()):
    SQL.append({'sql':text,'parameters':list(args)})
    return [dict(row) for row in db.execute(text,args)]
def decode(rows,fields):
    for row in rows:
        for key in fields:
            if row.get(key) is not None:row[key]=json.loads(row[key])
    return rows

def connection(path,reader):
    before=metadata(path);start=now();db=None
    try:
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0)
        db.row_factory=sqlite3.Row
        db.create_function('sha256_text',1,sha,deterministic=True)
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        assert db.execute('PRAGMA query_only').fetchone()[0]==1
        data=reader(db)
        assert db.total_changes==0
        end=now()
        return {'database':str(path),'read_started_at':start,'read_finished_at':end,'uri_mode':'ro','query_only':True,'explicit_begin':True,'immutable':False,'total_changes':0,'data':data}
    finally:
        if db is not None:
            if db.in_transaction:db.rollback()
            db.close()
        after=metadata(path)
        write(('MAIN' if path==MAIN else 'DURABLE')+'_SOURCE_METADATA001.json',{'before':before,'after':after,'meaning':'Active source metadata only; not a preservation/equality claim. Connection was closed in finally.','closed_at':now()})

def main_reader(db):
    tables={r['name'] for r in query(db,"SELECT name FROM sqlite_master WHERE type='table'")}
    data={'table_presence':{},'run_id':RUN,'root_episode_id':ROOT}
    for table in ['runtime_runs','runtime_episodes','runtime_actions','runtime_model_calls','runtime_observations','runtime_commission_intents','runtime_report_attempts','public_search_orders','public_search_operations','public_search_results','public_search_claims','provider_jobs','records']:
        data['table_presence'][table]=table in tables
    identity=query(db,'SELECT run_id,state,started_at,updated_at FROM runtime_runs WHERE run_id=?',(RUN,))
    if len(identity)!=1:raise RuntimeError('expected_exact_run_identity')
    data['run']=identity[0]
    episodes=decode(query(db,"SELECT episode_id,path,state,json_extract(completion,'$.reason') AS completion_reason FROM runtime_episodes WHERE run_id=? ORDER BY episode_id",(RUN,)),['path'])
    if not any(row['episode_id']==ROOT for row in episodes):raise RuntimeError('expected_root_identity')
    for row in episodes:row['role']=row['path'][-1][0]
    data['episodes']=episodes
    summaries=[]
    for episode in episodes:
        eid=episode['episode_id'];item={'episode_id':eid,'role':episode['role'],'counts':{}}
        for table,index in [('runtime_model_calls','call_index'),('runtime_actions','decision_index'),('runtime_observations','unit_index')]:
            if table not in tables:item['counts'][table]={'table_present':False};continue
            condition='run_id=? AND episode_id=?'
            columns=f'count(*) AS rows,min({index}) AS first_index,max({index}) AS last_index'
            if table=='runtime_model_calls':columns+=",sum(response IS NOT NULL) AS response_present"
            if table=='runtime_actions':columns+=",sum(credit IS NOT NULL) AS credit_present,sum(json_extract(result,'$.status')='pending') AS pending_results"
            item['counts'][table]=query(db,f'SELECT {columns} FROM {table} WHERE {condition}',(RUN,eid))[0]
            if table!='runtime_observations':
                intervals=query(db,f"SELECT t.{index} AS original_index,j.key AS interval_index,json_extract(j.value,'$.state') AS state,json_extract(j.value,'$.started_at') AS started_at,json_extract(j.value,'$.ended_at') AS ended_at,json_extract(j.value,'$.elapsed_seconds') AS elapsed_seconds,json_extract(j.value,'$.exception_type') AS exception_type FROM {table} t,json_each(t.timing,'$.intervals') j WHERE t.run_id=? AND t.episode_id=? ORDER BY t.{index},j.key",(RUN,eid))
                item[table+'_recorded_intervals']=intervals
        summaries.append(item)
    data['per_episode_role_counts_and_recorded_intervals']=summaries
    data['root_actions']=query(db,"SELECT decision_index,json_extract(action,'$.kind') AS kind,json_extract(action,'$.tool') AS tool,json_extract(action,'$.role') AS role,json_extract(action,'$.key') AS selected_key,sha256_text(action) AS action_text_sha256,sha256_text(json_extract(action,'$.arguments')) AS arguments_json_sha256,result IS NOT NULL AS result_present,json_extract(result,'$.status') AS outcome_status,credit IS NULL AS credit_is_null,json_extract(result,'$.feedback.code') AS feedback_code,json_extract(result,'$.pending_handle') AS pending_handle FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",(RUN,ROOT))
    c1=[]
    if 'runtime_commission_intents' in tables:
        c1=decode(query(db,"SELECT parent_episode_id,original_decision_index,handle,operation_key,commission_sha256,selected_at,sha256_text(spec) AS spec_text_sha256,sha256_text(selection) AS selection_text_sha256,json_extract(spec,'$.run_id') AS run_id,json_extract(spec,'$.child.episode_id') AS child_episode_id,json_extract(spec,'$.child.role') AS child_role,json_extract(spec,'$.child.path') AS child_path,json_extract(spec,'$.child.scope') AS child_scope,json_extract(spec,'$.child.request.report_contract') AS parent_defined_report_contract,json_extract(spec,'$.child.request.message.episode_assignment.job_request') AS job_request,json_extract(spec,'$.child.request.message.episode_assignment.resource_selection') AS assignment_resource_selection,json_extract(spec,'$.child.request.message.episode_assignment.handoff') AS handoff,json_extract(spec,'$.child.request.message.episode_assignment.requested_data_selector') AS requested_data_selector,json_extract(spec,'$.child.request.message.episode_assignment.immutable_input_versions') AS assignment_immutable_input_versions,json_extract(spec,'$.child.request.message.job_assignment') AS legacy_job_assignment,json_extract(spec,'$.resource_selection') AS resource_selection,json_extract(spec,'$.constraints') AS constraints,json_extract(spec,'$.input_versions') AS input_versions,json_extract(spec,'$.expectation_snapshot_refs') AS expectation_snapshot_refs FROM runtime_commission_intents WHERE run_id=? ORDER BY selected_at,parent_episode_id,original_decision_index",(RUN,)),['child_path','child_scope','parent_defined_report_contract','job_request','assignment_resource_selection','handoff','requested_data_selector','assignment_immutable_input_versions','legacy_job_assignment','resource_selection','constraints','input_versions','expectation_snapshot_refs'])
        for row in c1:
            if row['run_id']!=RUN:raise RuntimeError('C1_run_identity_conflict')
    data['C1_original_commissions']=c1
    root_resource=[r for r in c1 if r['parent_episode_id']==ROOT and (r['child_role'] in RESOURCE_ROLES or r['job_request'] is not None or r['legacy_job_assignment'] is not None)]
    first=min((r['original_decision_index'] for r in root_resource),default=None)
    data['first_root_resource_commission_decision_index']=first
    # Raw/model views are extracted ONLY from actual root choosing requests at
    # selected estimate indices before the first root resource commission, plus
    # the first commission itself. Never read any child model request/response.
    indices=[r['decision_index'] for r in data['root_actions'] if r['tool']=='execution.estimate' and (first is None or r['decision_index']<first)]
    data['root_precommission_explicit_estimate_decisions']=indices
    selection_indices=sorted(set(indices+([] if first is None else [first])))
    data['selected_root_choosing_requests']=[];data['root_original_selected_estimate_results']=[]
    for index in selection_indices:
        rows=query(db,'SELECT call_index,purpose,request,sha256_text(request) AS request_text_sha256 FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?',(RUN,ROOT,index))
        item={'original_decision_index':index,'row_present':bool(rows)}
        if rows:
            if len(rows)!=1:raise RuntimeError('duplicate_root_call')
            row=rows[0];text=row.pop('request');name=f'root-choosing-request-{index:04d}.json'
            with (OUT/name).open('x',encoding='utf-8') as f:f.write(text)
            value=json.loads(text);context=value.get('context',{});model=value.get('model_presentation',{}).get('context')
            item.update(row);item.update(member=name,raw_utf8_bytes=len(text.encode()),request_version=value.get('version'),model_view_present=model is not None,
                raw_api_reported_execution_forecasts=context.get('api_reported_execution_forecasts'),raw_api_execution_proposal=context.get('api_execution_proposal'),
                model_api_reported_execution_forecasts=None if model is None else model.get('api_reported_execution_forecasts'),
                model_api_execution_proposal=None if model is None else model.get('api_execution_proposal'))
        data['selected_root_choosing_requests'].append(item)
        if index in indices:
            result=query(db,'SELECT decision_index,json_extract(action,\'$.arguments\') AS selected_arguments,result,sha256_text(result) AS result_text_sha256 FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',(RUN,ROOT,index))
            data['root_original_selected_estimate_results'].extend(decode(result,['selected_arguments','result']))
    if 'runtime_report_attempts' in tables:
        data['root_public_report_admissions']=decode(query(db,'SELECT parent_episode_id,decision_index,delivery_ref,child_episode_id,contract,form,failure,timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',(RUN,ROOT)),['contract','form','failure','timing_receipts'])
    else:data['root_public_report_admissions']={'table_present':False}
    op={}
    for table in ['public_search_orders','public_search_operations','public_search_results','public_search_claims','provider_jobs']:
        op[table]={'table_present':table in tables}
        if table in tables:op[table]['workspace_count_unattributed_to_run']=query(db,f'SELECT count(*) AS count FROM {table}')[0]['count']
    if 'public_search_orders' in tables:
        op['selected_registry_orders']=decode(query(db,"SELECT job_ref,data AS original_closed_order FROM public_search_orders WHERE json_extract(data,'$.registry_ref')=? ORDER BY job_ref",(REGISTRY,)),['original_closed_order'])
    if 'public_search_orders' in tables and 'provider_jobs' in tables:
        op['selected_registry_jobs']=decode(query(db,"SELECT p.id,p.operation_key,p.request,p.state,p.remote_id,p.error_code FROM provider_jobs p JOIN public_search_orders o ON o.job_ref=p.id WHERE json_extract(o.data,'$.registry_ref')=? ORDER BY p.id",(REGISTRY,)),['request'])
    if 'public_search_operations' in tables:
        op['selected_registry_receipts']=decode(query(db,"SELECT data AS receipt FROM public_search_operations WHERE json_extract(data,'$.registry_ref')=? ORDER BY rowid",(REGISTRY,)),['receipt'])
    op['saved_selected_API_action_technical_outcomes']=decode(query(db,"SELECT episode_id,decision_index,json_extract(action,'$.tool') AS tool,sha256_text(action) AS action_text_sha256,json_extract(result,'$.status') AS status,json_extract(result,'$.provider_operation_refs') AS provider_operation_refs,json_extract(result,'$.api_timing_disposition') AS api_timing_disposition,json_extract(result,'$.api_timing_refs') AS api_timing_refs,json_extract(result,'$.feedback.code') AS feedback_code FROM runtime_actions WHERE run_id=? AND (json_extract(action,'$.tool') LIKE 'api_search.%' OR json_extract(action,'$.tool') IN ('public.hmmer.search','public.hmmer.collect','public.hmmer.page')) ORDER BY episode_id,decision_index",(RUN,)),['provider_operation_refs','api_timing_disposition','api_timing_refs'])
    if 'records' in tables:
        op['timing_source_metadata_workspace_unattributed']=decode(query(db,"SELECT id,origin,data FROM records WHERE record_type='source' AND json_extract(data,'$.provider')='episode.hmmer_reported_timing' ORDER BY id"),['data'])
    data['operational_and_timing']=op
    return data

def durable_reader(db):
    tables={r['name'] for r in query(db,"SELECT name FROM sqlite_master WHERE type='table'")}
    out={'table_presence':{t:t in tables for t in ['commissions','returns','events']}}
    if 'commissions' not in tables:return out
    out['C1_C2_C3_C4_technical_states']=query(db,"SELECT handle,operation_key,parent_episode_id,commission_sha256,lifecycle_state,json_extract(spec,'$.child.episode_id') AS child_episode_id,json_extract(spec,'$.child.role') AS child_role,return_id,acknowledgment IS NOT NULL AS acknowledgment_present,json_extract(failure,'$.code') AS failure_code,sha256_text(spec) AS spec_text_sha256 FROM commissions WHERE json_extract(spec,'$.run_id')=? ORDER BY handle",(RUN,))
    if 'returns' in tables:
        out['C3_presence']=query(db,"SELECT r.handle,r.return_id,r.returned_at,r.cursor,c.parent_episode_id,json_extract(r.envelope,'$.outcome') AS outcome,json_type(r.envelope,'$.form') AS form_json_type,json_extract(r.envelope,'$.failure.code') AS failure_code FROM returns r JOIN commissions c USING(handle) WHERE json_extract(c.spec,'$.run_id')=? ORDER BY r.cursor",(RUN,))
        out['C3_public_to_original_root_forms']=decode(query(db,"SELECT r.handle,r.return_id,r.returned_at,r.cursor,json_extract(r.envelope,'$.outcome') AS outcome,json_extract(r.envelope,'$.form') AS returned_form,json_extract(r.envelope,'$.failure') AS returned_failure FROM returns r JOIN commissions c USING(handle) WHERE json_extract(c.spec,'$.run_id')=? AND c.parent_episode_id=? ORDER BY r.cursor",(RUN,ROOT)),['returned_form','returned_failure'])
    else:out['C3_presence']={'table_present':False}
    out['C4_public_to_original_root_acknowledgments']=decode(query(db,"SELECT handle,acknowledgment FROM commissions WHERE json_extract(spec,'$.run_id')=? AND parent_episode_id=? AND acknowledgment IS NOT NULL ORDER BY handle",(RUN,ROOT)),['acknowledgment'])
    return out

def run():
    assert not (OUT/'CAPTURE001.json').exists() and not (OUT/'ATTEMPT001.json').exists()
    write('ATTEMPT001.json',{'argv':sys.argv,'started_at':now(),'operator_sha256':sha(Path(__file__).read_bytes()),'scope_sha256':sha((OUT/'SCOPE001.json').read_bytes()),'once_only':True})
    try:
        main=connection(MAIN,main_reader)
        durable=connection(DURABLE,durable_reader)
        write('CAPTURE001.json',{'version':'configured_resource_finite_prefix_v1','main':main,'durable':durable,'limits':['Two independent active read windows; no cross-database atomicity or file equality asserted.','No child model request/response or private scientific commitment/body read/exported.','Only actually selected root pre-resource-commission estimates and first resource commission original choosing requests retained.','Operational source counts lacking run_id are explicitly workspace/unattributed.','No artifacts, app imports, current projection/forecast recapture, provider logs, model/native/HTTP/control calls.']})
        write('SQL_READSET001.json',{'version':'configured_resource_finite_prefix_sql_v1','statements':SQL,'connection_count':2,'application_imports':0,'application_sql_writes':0,'control_calls':0})
    except BaseException as error:
        write('FAILURE001.json',{'type':type(error).__name__,'category':'single_readonly_capture_failed','message':str(error),'at':now(),'no_automatic_retry':True})
        write('SQL_READSET001.json',{'version':'configured_resource_finite_prefix_sql_v1','statements':SQL,'application_imports':0,'application_sql_writes':0,'no_automatic_retry':True})
        raise
if __name__=='__main__':run()
