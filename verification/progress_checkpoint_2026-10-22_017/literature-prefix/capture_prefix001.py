#!/usr/bin/env python3
"""Single finite stdlib read-only prefix capture. No application imports."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import traceback

OUT = Path(__file__).resolve().parent
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN_ID = 'run_d1f1317290114adb95d8a1d58ad970c1'
ROOT = 'episode_dbb4a5b6e50c304d33264cfdbebff3133709af38b63d07e69fc29c193ec9ad2c'
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
FIRST = Path('/tmp/configured-literature-localization-first-request-proof-20261022-001/RESULT001.json')
FIRST_SHA = 'c052692a7e1d072e0a9c94e1234c71a4ac49b6abbf3a5a8f6634c0b925d92895'
MAIN = RUN / 'workspace/state.sqlite3'
BACK = RUN / 'episode-execution/executions.sqlite'
READSET = []
QUERIES = []

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(value):
    if isinstance(value, str): value = value.encode('utf-8')
    return hashlib.sha256(value).hexdigest()

def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def write(name, value):
    data = value if isinstance(value, bytes) else (canon(value) + '\n').encode()
    with (OUT / name).open('xb') as f:
        f.write(data)
    return {'path': name, 'bytes': len(data), 'sha256': digest(data)}

def read(path, expected=None):
    data = path.read_bytes()
    info = {'path': str(path), 'bytes': len(data), 'sha256': digest(data)}
    READSET.append(info)
    if expected is not None and info['sha256'] != expected:
        raise ValueError('input_hash_mismatch:' + str(path))
    return data

def saved(text):
    return None if text is None else json.loads(text)

def text_meta(text):
    return None if text is None else {'utf8_bytes': len(text.encode()), 'sha256': digest(text)}

def scalar_meta(value):
    if not isinstance(value, dict): return {'json_type': type(value).__name__}
    # Enum/identity/numeric metadata only; no reasoning/report prose.
    allowed = {'kind','status','role','tool','name','source','label','action_kind',
        'unit_index','decision_index','original_decision_index','sequence','credit',
        'credit_before','credit_after','gain','delta','score','reward','count',
        'elapsed_seconds','duration_seconds','completed','observation_id',
        'observation_identity','record_ref','delivery_ref','return_id','handle',
        'pending_handle','selected_at','started_at','finished_at','captured_at',
        'version','ended_by','end_reason','units_consumed'}
    result = {}
    for key in allowed & value.keys():
        item = value[key]
        if item is None or isinstance(item, (bool,int,float)):
            result[key] = item
        elif isinstance(item, str) and (key not in {'label','source','name'} or len(item) < 180):
            result[key] = item
    return result

def file_stat(path):
    st = path.stat()
    return {'path': str(path), 'device':st.st_dev,'inode':st.st_ino,'bytes':st.st_size,
        'mtime_ns':st.st_mtime_ns,'mode':oct(st.st_mode & 0o777)}

def source_guard():
    members=[]
    for base in ('gene_annotation_episode','method_loop'):
        for path in sorted((CODE/base).rglob('*.py')):
            data=path.read_bytes();members.append({'path':str(path.relative_to(CODE)),
                'sha256':digest(data),'bytes':len(data)})
    # Runtime identity is the repository's path/hash pair canonical digest.
    identity=hashlib.sha256()
    for item in members:
        identity.update(item['path'].encode()+b'\0')
        identity.update(bytes.fromhex(item['sha256']))
    return members, identity.hexdigest()

def main():
    if (OUT/'CAPTURE001.json').exists() or (OUT/'FAILURE001.json').exists():
        raise ValueError('capture_already_attempted')
    started=now()
    first=json.loads(read(FIRST,FIRST_SHA))
    assert first['run_id']==RUN_ID and first['root_path']==[['annotation','root']]
    receipt_path=RUN/'workspace/scientific-checkpoint-fork.json'
    receipt=json.loads(read(receipt_path,'b7b59190ba1f5e28b3c688a2ff0189efba735862b14826cca0ee1377c80ac9f6'))
    manifest_desc=receipt['checkpoint']['committed_reference_manifest']
    committed=json.loads(read(RUN/'workspace'/manifest_desc['path'],manifest_desc['sha256']))
    write('INHERITED_COMMITTED_MANIFEST001.json',committed)
    before_members,before_pin=source_guard()
    assert before_pin==PIN and len(before_members)==137
    write('SOURCE_BEFORE001.json',{'members':before_members,'implementation_sha256':before_pin,
        'expected_runtime_pin':PIN})
    db=None
    result={'version':'configured_literature_commission_prefix_v1','status':'capture_in_progress',
        'run_id':RUN_ID,'root_episode_id':ROOT,'started_at_utc':started,
        'database_files_at_open':[file_stat(MAIN),file_stat(BACK)],
        'read_protocol':{'mode':'ro','immutable':False,'query_only':True,'explicit_begin':True,
            'finite_single_invocation':True,'cross_database_atomicity_claimed':False,
            'execution_token_selected':False,'application_imports':0,'control_calls':0},
        'source_pin_authority':PIN,'first_request_proof_sha256':FIRST_SHA}
    try:
        db=sqlite3.connect(MAIN.as_uri()+'?mode=ro',uri=True,timeout=5)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('ATTACH DATABASE ? AS durable',(BACK.as_uri()+'?mode=ro',))
        db.execute('BEGIN')
        assert db.execute('PRAGMA query_only').fetchone()[0]==1
        def rows(sql,args=()):
            QUERIES.append({'sql':sql,'parameters':list(args)})
            return [dict(row) for row in db.execute(sql,args).fetchall()]
        result['main_read_started_at_utc']=now()
        tables=rows("SELECT name,sql FROM main.sqlite_master WHERE type='table' ORDER BY name")
        names={r['name'] for r in tables}
        write('MAIN_SCHEMA001.json',tables)
        def run_rows(table,parent=False,order=''):
            if table not in names:return []
            sql='SELECT * FROM '+table+' WHERE run_id=?'
            return rows(sql+(' ORDER BY '+order if order else ''),(RUN_ID,))
        runs=run_rows('runtime_runs')
        assert len(runs)==1
        run=runs[0]
        settings=saved(run.pop('settings'))
        result['run']={**run,'summary':saved(run.get('summary')),
            'settings_sha256':digest(canon(settings)),'directory':settings['directory']}
        assert Path(settings['directory'])==RUN
        result['bindings']={key:settings.get(key) for key in ('models','restoration','controller',
            'credit_policy','binding_versions','completed_action_inputs','wait_inputs')}
        episodes=run_rows('runtime_episodes',order='episode_id')
        result['episodes']=[]
        for row in episodes:
            result['episodes'].append({'run_id':row['run_id'],'episode_id':row['episode_id'],
                'path':saved(row['path']),'request':saved(row['request']),
                'request_text':text_meta(row['request']),'initial_credit':row['initial_credit'],
                'state':row['state'],'completion':saved(row['completion']),
                'archive_descriptor':saved(row['archive'])})
        intents=run_rows('runtime_commission_intents',order='parent_episode_id,original_decision_index')
        result['commission_intents']=[]
        for row in intents:
            spec=saved(row['spec']);selection=saved(row['selection'])
            assert digest(canon(spec))==row['commission_sha256']
            result['commission_intents'].append({**row,'spec':spec,'selection':selection,
                'spec_text':text_meta(row['spec']),'selection_text':text_meta(row['selection'])})
        actions=run_rows('runtime_actions',order='episode_id,decision_index')
        result['actions']=[]
        for row in actions:
            action=saved(row['action']);outcome=saved(row['result'])
            item={'episode_id':row['episode_id'],'decision_index':row['decision_index'],
                'credit':row['credit'],'timing':saved(row['timing']),
                'selection_text':text_meta(row['action']),'result_text':text_meta(row['result']),
                'selection_metadata':scalar_meta(action),'result_metadata':scalar_meta(outcome)}
            if isinstance(action,dict):
                item['selection_keys']=list(action)
                # Tool name is frequently under selection.action/tool_request.
                item['selected_operation_fields']={key:scalar_meta(action[key]) for key in
                    ('action','tool_request','selection','request') if isinstance(action.get(key),dict)}
            if row['episode_id']==ROOT:
                item['original_selection']=action
                item['result']=outcome
            result['actions'].append(item)
        observations=run_rows('runtime_observations',order='episode_id,unit_index')
        result['observations']=[]
        for row in observations:
            item={'episode_id':row['episode_id'],'unit_index':row['unit_index'],
                'observation_text':text_meta(row['observation']),
                'metadata':scalar_meta(saved(row['observation']))}
            if row['episode_id']==ROOT:item['observation']=saved(row['observation'])
            result['observations'].append(item)
        calls=rows('SELECT episode_id,call_index,purpose,timing,length(request) AS request_characters,'
            'response IS NOT NULL AS response_present FROM runtime_model_calls WHERE run_id=? '
            'ORDER BY episode_id,call_index',(RUN_ID,))
        for row in calls:row['timing']=saved(row['timing'])
        result['model_call_metadata']=calls
        result['root_saved_requests']=[]
        for row in rows('SELECT call_index,purpose,request,timing FROM runtime_model_calls '
                'WHERE run_id=? AND episode_id=? ORDER BY call_index',(RUN_ID,ROOT)):
            descriptor=write('ROOT_REQUEST_%04d.json'%row['call_index'],row['request'].encode())
            request=saved(row['request'])
            frame=request.get('local_commission_frame') if isinstance(request,dict) else None
            context=request.get('context',{}) if isinstance(request,dict) else {}
            result['root_saved_requests'].append({'call_index':row['call_index'],'purpose':row['purpose'],
                'timing':saved(row['timing']),'descriptor':descriptor,'version':request.get('version'),
                'local_commission_frame':frame,'pending_work':context.get('pending_work'),
                'child_reports':context.get('child_reports'),
                'history_metadata':scalar_meta(context.get('history')),
                'context_keys':list(context),
                'frame_outside_context':frame is not None and 'local_commission_frame' not in context})
        result['root_estimation_contexts']=[]
        for row in rows('SELECT decision_index,data FROM runtime_estimation_contexts WHERE run_id=? '
                'AND episode_id=? ORDER BY decision_index',(RUN_ID,ROOT)):
            result['root_estimation_contexts'].append({'decision_index':row['decision_index'],
                'data':saved(row['data']),'text':text_meta(row['data'])})
        result['admissions']=[]
        for row in run_rows('runtime_return_admissions',order='parent_episode_id,original_decision_index'):
            result['admissions'].append({**row,'admission':saved(row['admission']),
                'expectation_snapshot_refs':saved(row['expectation_snapshot_refs'])})
        result['report_attempts']=[]
        for row in run_rows('runtime_report_attempts',order='parent_episode_id,decision_index'):
            item={key:row[key] for key in ('parent_episode_id','decision_index','delivery_ref','child_episode_id')}
            for key in ('contract','failure','timing_receipts'):item[key]=saved(row[key])
            item['form_text']=text_meta(row['form'])
            if row['parent_episode_id']==ROOT:item['root_received_form']=saved(row['form'])
            result['report_attempts'].append(item)
        result['completion_slots']=[]
        for row in run_rows('runtime_completion_slots',order='episode_id,sequence'):
            item={key:row[key] for key in ('episode_id','sequence','original_decision_index')}
            item['slot_text']=text_meta(row['slot'])
            if row['episode_id']==ROOT:item['slot']=saved(row['slot'])
            result['completion_slots'].append(item)
        result['root_forms']=[]
        for row in rows('SELECT form,facts FROM runtime_forms WHERE run_id=? AND episode_id=?',(RUN_ID,ROOT)):
            result['root_forms'].append({'form':saved(row['form']),'facts_text':text_meta(row['facts'])})
        result['receipt_counts']=rows('SELECT episode_id,receipt_kind,COUNT(*) AS count FROM '
            'runtime_record_receipts WHERE run_id=? GROUP BY episode_id,receipt_kind',(RUN_ID,))
        result['root_receipts']=rows('SELECT receipt_index,record_ref,receipt_kind,source_index FROM '
            'runtime_record_receipts WHERE run_id=? AND episode_id=? ORDER BY receipt_index',(RUN_ID,ROOT))
        if 'episode_waits' in names:
            columns={row['name'] for row in rows('PRAGMA main.table_info(episode_waits)')}
            if 'run_id' in columns and 'parent_episode_id' in columns:
                result['root_waits']=rows('SELECT * FROM episode_waits WHERE run_id=? AND parent_episode_id=?',(RUN_ID,ROOT))
            else:result['root_waits_schema_only']=sorted(columns)
        result['typed_committed_metadata']=[]
        for row in rows('SELECT id,record_type,origin,data FROM records ORDER BY id'):
            result['typed_committed_metadata'].append({'id':row['id'],'record_type':row['record_type'],
                'origin':row['origin'],'data_text':text_meta(row['data'])})
        result['main_read_finished_at_utc']=now()
        result['durable_read_started_at_utc']=now()
        write('DURABLE_SCHEMA001.json',rows("SELECT name,sql FROM durable.sqlite_master WHERE type='table' ORDER BY name"))
        result['durable_commissions']=[]
        handles={row['handle'] for row in intents}
        parents={row['episode_id'] for row in episodes}
        for row in rows('SELECT handle,operation_key,parent_episode_id,commission_sha256,spec,'
                'lifecycle_state,execution_identity,return_id,acknowledgment,failure FROM durable.commissions ORDER BY handle'):
            spec=saved(row['spec'])
            if spec.get('run_id')!=RUN_ID:continue
            for key in ('spec','execution_identity','acknowledgment','failure'):row[key]=saved(row[key])
            result['durable_commissions'].append(row)
            handles.add(row['handle'])
        result['durable_returns']=[]
        for row in rows('SELECT handle,return_id,returned_at,envelope,cursor FROM durable.returns ORDER BY cursor'):
            if row['handle'] not in handles:continue
            envelope=saved(row['envelope'])
            item={key:row[key] for key in ('handle','return_id','returned_at','cursor')}
            item['envelope_text']=text_meta(row['envelope'])
            item['envelope_metadata']={key:envelope.get(key) for key in ('version','handle','return_id',
                'commission_sha256','returned_at','outcome','completion','pending_handles','failure',
                'episode_archive','result_archive','facts_archive')}
            item['form_present']=envelope.get('form') is not None
            if envelope.get('form') is not None:item['form_digest']=digest(canon(envelope['form']))
            admitted=any(a['handle']==row['handle'] and a['parent_episode_id']==ROOT for a in result['admissions'])
            if admitted:item['root_admitted_form']=envelope.get('form')
            result['durable_returns'].append(item)
        result['durable_events']=[row for row in rows('SELECT cursor,handle,event,record_ref,operation_key,'
            'observed_at FROM durable.events ORDER BY cursor') if row['handle'] in handles]
        result['durable_read_finished_at_utc']=now()
        result['status']='persisted_prefix_captured'
    finally:
        if db is not None:
            try:db.rollback()
            finally:db.close()
    result['connection_explicitly_closed']=True
    result['finished_at_utc']=now()
    after_members,after_pin=source_guard()
    assert before_members==after_members
    result['source_members_unchanged']=True
    result['runtime_file_count']=len(before_members)
    write('SOURCE_AFTER001.json',{'members':after_members,'implementation_sha256':after_pin,
        'expected_runtime_pin':PIN})
    write('QUERIES001.json',QUERIES)
    write('READSET001.json',READSET)
    descriptor=write('CAPTURE001.json',result)
    print(canon({'status':result['status'],'capture':descriptor,'episodes':len(result['episodes']),
        'commissions':len(result['commission_intents']),'C3':len(result['durable_returns']),
        'C4':len(result['admissions']),'actions':len(result['actions']),'observations':len(result['observations'])}))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        write('FAILURE001.json',{'type':type(error).__name__,'message':str(error),
            'traceback':traceback.format_exc(),'queries_completed':QUERIES,'readset':READSET,
            'failed_at_utc':now(),'no_retry_authorized':True})
        raise
