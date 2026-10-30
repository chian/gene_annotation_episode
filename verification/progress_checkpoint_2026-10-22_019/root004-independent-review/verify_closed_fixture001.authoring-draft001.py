"""Finite stdlib-only offline review of the explicitly selected preserved fixture.
No application imports, score projection, test execution, or original/live DB access.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, sqlite3, stat, traceback
from urllib.parse import quote
import xml.etree.ElementTree as ET

EVIDENCE = Path('/tmp/direct-hmmer-root008-evidence-20261022-001')
INV = EVIDENCE / 'invocation-004'
FIXTURE = INV / 'preserved-fixtures/test_real_detached_direct_sear0'
SOURCE = Path('/tmp/gene-annotation-configured-caller-20261022-008')
PIN = '6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30'
READSET, CHECKS = {}, []
OUT = None

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return sha(canonical(value))

def witness(path):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and not path.is_symlink(), str(path)
    data = path.read_bytes()
    t = path.lstat()
    assert (s.st_size,s.st_mtime_ns,s.st_ino,s.st_dev,s.st_mode)==(t.st_size,t.st_mtime_ns,t.st_ino,t.st_dev,t.st_mode)
    row = dict(path=str(path), sha256=sha(data), bytes=len(data), mode=stat.S_IMODE(s.st_mode),
               mtime_ns=s.st_mtime_ns, inode=s.st_ino, device=s.st_dev)
    if str(path) in READSET:
        assert READSET[str(path)] == row, 'input changed: '+str(path)
    READSET[str(path)] = row
    return data

def load(path):
    return json.loads(witness(path))

def copy_input(path, member):
    data = witness(path)
    p = OUT/'inputs'/member
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(data)
    return data

def check(name, condition, details=None):
    row = dict(name=name, passed=bool(condition))
    if details is not None: row['details']=details
    CHECKS.append(row)
    if not condition: raise AssertionError(name)

def sql_snapshot(rel, tables):
    path = FIXTURE/rel
    before = witness(path)
    check('closed DB has no SQLite sidecars: '+rel,
          not any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')))
    c = sqlite3.connect('file:'+quote(str(path))+'?mode=ro&immutable=1',uri=True)
    c.row_factory = sqlite3.Row
    try:
        c.execute('PRAGMA query_only=ON')
        check('query_only: '+rel,c.execute('PRAGMA query_only').fetchone()[0]==1)
        c.execute('BEGIN')
        values = {t:[dict(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
    finally:
        if c.in_transaction:c.rollback()
        c.close()
    check('DB unchanged after explicit close: '+rel,witness(path)==before)
    copy_input(path, 'fixture/'+rel)
    return values

def archive(descriptor, active=()):
    name=descriptor['file']
    check('archive basename safe: '+name,Path(name).name==name and name not in active)
    raw=copy_input(FIXTURE/'run/archive'/name,'fixture/run/archive/'+name)
    idxname=Path(name).with_suffix('.index.json').name
    idx=copy_input(FIXTURE/'run/archive'/idxname,'fixture/run/archive/'+idxname) if not (OUT/'inputs/fixture/run/archive'/idxname).exists() else witness(FIXTURE/'run/archive'/idxname)
    check('archive hash: '+name,sha(raw)==descriptor['sha256'])
    check('archive index hash: '+name,sha(idx)==descriptor['index_sha256'])
    index=json.loads(idx);parts=[];position=0
    for entry in index:
        offset,length=entry['offset'],entry['length']
        check('archive reference offsets: '+name,type(offset)is int and type(length)is int and offset>=position and offset+length<=len(raw))
        marker=json.loads(raw[offset:offset+length])
        check('archive marker matches index: '+name,marker=={'$archive':entry['reference']})
        parts.extend([raw[position:offset],canonical(archive(entry['reference'],(*active,name)))])
        position=offset+length
    parts.append(raw[position:])
    return json.loads(b''.join(parts))

def main():
    global OUT
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    output=Path(args.output);OUT=output.parent
    assert not output.exists()
    result={'version':'direct_hmmer_root004_offline_verification_v1','started_at_utc':now(),
            'status':'failed_preserve_partial','source_pin':PIN,'fixture':str(FIXTURE),'checks':CHECKS}
    try:
        metadata={}
        for rel in ['COMMAND.json','INPUTS_BEFORE.json','INPUTS_AFTER.json','RESULTS.json','ORIGINAL_PRESERVATION.json','results.xml','pytest.log']:
            raw=copy_input(INV/rel,'invocation-004/'+rel)
            if rel.endswith('.json'):metadata[rel]=json.loads(raw)
        coherent=json.loads(copy_input(EVIDENCE/'COHERENT_SOURCE001.json','COHERENT_SOURCE001.json'))
        copy_input(EVIDENCE/'run_checks.py','run_checks.py')
        before,after=metadata['INPUTS_BEFORE.json'],metadata['INPUTS_AFTER.json']
        check('all365 invocation source/test witness maps identical',before==after and len(before)==365)
        check('actual invocation exit0 and unchanged',metadata['RESULTS.json']['exit_code']==0 and metadata['RESULTS.json']['changed_inputs']==[] and metadata['RESULTS.json']['source_and_tests_unchanged'] is True)
        command=metadata['COMMAND.json']
        selected=['tests/test_direct_hmmer_timing_connected.py','tests/test_direct_hmmer_timing_reconstruction.py','tests/test_api_timing_reconstruction.py','tests/test_api_execution_planning_reconstruction.py']
        check('exact isolated invocation argv/cwd/environment',command['argv']==['/home/chia/repos/gene_annotation_episode/.venv/bin/python','-m','pytest','-q',*selected,'--basetemp',str(INV/'pytest-fixtures'),'--junitxml',str(INV/'results.xml')] and command['cwd']==str(SOURCE) and command['environment_overrides']=={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(SOURCE/'tests')+':'+str(SOURCE)})
        xml=ET.fromstring(witness(INV/'results.xml'))
        cases=xml.findall('.//testcase')
        nodeids=[x.attrib.get('classname','')+'.'+x.attrib['name'] for x in cases]
        check('XML exact five passing cases with one selected detached case',len(cases)==5 and not xml.findall('.//failure') and not xml.findall('.//error') and not xml.findall('.//skipped') and sum(n.endswith('test_real_detached_direct_search_restores_caller_map_timing_and_original_forecast') for n in nodeids)==1)
        check('retained pytest log says5passed',b'5 passed' in witness(INV/'pytest.log'))
        result['pytest']={'nodeids':nodeids,'passing_cases':5,'scope':'one invocation, no summed overlap','xml_testcase_times':[x.attrib.get('time') for x in cases]}
        check('coherent138 runtime file inventory',coherent['source_pin']==PIN and coherent['runtime_files']==len(coherent['files'])==138)
        runtime=sorted(coherent['files'],key=lambda x:x['path']);pin=hashlib.sha256()
        for row in runtime:
            raw=witness(SOURCE/row['path'])
            check('runtime source matches coherent and invocation: '+row['path'],sha(raw)==row['sha256']==before[row['path']]['sha256'] and len(raw)==row['bytes']==before[row['path']]['bytes'])
            pin.update(row['path'].encode()+b'\0');pin.update(hashlib.sha256(raw).digest())
        check('independently recomputed138 runtime pin',pin.hexdigest()==PIN)
        source_paths=selected+['gene_annotation_episode/public_search_operations.py','gene_annotation_episode/direct_hmmer_timing.py','gene_annotation_episode/tools.py','gene_annotation_episode/api_timing_information.py','gene_annotation_episode/api_execution_planning.py','gene_annotation_episode/episode_commissions.py','gene_annotation_episode/episode_admission.py','gene_annotation_episode/independent_execution.py','gene_annotation_episode/case_execution.py','gene_annotation_episode/runtime.py','method_loop/archive.py','method_loop/durable.py','tests/test_direct_hmmer_timing_binding.py']
        for rel in source_paths:
            raw=copy_input(SOURCE/rel,'source/'+rel)
            check('reviewed source matches actual invocation: '+rel,sha(raw)==before[rel]['sha256'])
        state=sql_snapshot('case/workspace/state.sqlite3',[
            'runtime_commission_intents','runtime_episodes','runtime_actions','runtime_observations',
            'runtime_return_admissions','runtime_report_attempts','runtime_forms','runtime_record_receipts',
            'runtime_receipt_inheritance','runtime_completion_slots','runtime_model_calls','runtime_runs',
            'runtime_execution_bindings','records','artifacts','provider_jobs','public_search_orders',
            'public_search_operations','public_search_order_scopes','public_search_claims','public_search_results','tool_operations'])
        backend=sql_snapshot('run/episode-execution/executions.sqlite',['commissions','returns','events'])
        save(OUT/'RAW_STATE_FINAL001.json',state);save(OUT/'RAW_EXECUTION_FINAL001.json',backend)
        check('single C1, return and C4 admission',len(state['runtime_commission_intents'])==len(state['runtime_return_admissions'])==len(backend['commissions'])==len(backend['returns'])==1)
        intent=state['runtime_commission_intents'][0];spec=json.loads(intent['spec']);bc=backend['commissions'][0];retrow=backend['returns'][0];ret=json.loads(retrow['envelope']);adrow=state['runtime_return_admissions'][0];ad=json.loads(adrow['admission']);ack=json.loads(bc['acknowledgment'])
        run,parent,child=spec['run_id'],spec['parent']['episode_id'],spec['child']['episode_id']
        episodes={x['episode_id']:x for x in state['runtime_episodes']};pr=json.loads(episodes[parent]['request']);cr=json.loads(episodes[child]['request']);selection=json.loads(intent['selection'])
        check('C1 original exact saved ownership/request',json.loads(bc['spec'])==spec and digest(spec)==intent['commission_sha256']==bc['commission_sha256']==ret['commission_sha256'] and cr==spec['child']['request'] and cr['goal']['parent_goal_id']==pr['goal']['goal_id']==spec['parent']['goal_id'] and json.loads(episodes[child]['path'])==spec['child']['path'] and spec['child']['path'][:-1]==spec['parent']['path'] and spec['child']['role']=='scientific_process')
        original_schema=json.loads(selection['schema_json']);contract=cr['report_contract']
        check('original parent-defined typed form retained',set(contract['information'])=={'timing','forecasts'} and original_schema==contract['measurements']['schema']==cr['goal']['result_contract'] and original_schema['properties']['timing']['x-source']=='api_execution_measurements' and original_schema['properties']['forecasts']['x-source']=='api_reported_execution_forecasts')
        check('C3 closed immutable returned envelope',ret['outcome']=='closed' and ret['failure'] is None and ret['completion']['units_consumed']==3 and ret['pending_handles']==[] and digest({k:v for k,v in ret.items() if k!='return_id'})==ret['return_id']==retrow['return_id']==bc['return_id'])
        check('C4 original single admission and matching acknowledgment',ad['state']=='admitted' and ad['report']==ret['form'] and ad['handle']==ack['handle']==spec['handle'] and ad['return_id']==ack['return_id']==ret['return_id'] and ad['admission_id']==ack['admission_id'] and bc['lifecycle_state']=='admitted' and adrow['selection_sha256']==digest(selection) and ad['original_decision_index']==intent['original_decision_index']==0 and adrow['parent_episode_id']==parent)
        check('one original report attempt',len(state['runtime_report_attempts'])==1 and json.loads(state['runtime_report_attempts'][0]['form'])==ret['form'] and json.loads(state['runtime_report_attempts'][0]['contract'])==contract and state['runtime_report_attempts'][0]['failure'] is None)
        forms=state['runtime_forms'];check('recorded source fields exactly returned',len(forms)==1 and json.loads(forms[0]['form'])==ret['form'] and all(json.loads(forms[0]['facts'])[src]==ret['form'][name] for name,src in [('timing','api_execution_measurements'),('forecasts','api_reported_execution_forecasts')]))
        fact,=ret['form']['timing'];forecast,=ret['form']['forecasts']
        check('returned original timing2.75 and future support1',fact['elapsed_seconds']==forecast['expected_total_seconds']==2.75 and fact['duration_measure']==forecast['forecast_duration_measure']=='hmmer_reported_search_elapsed_seconds' and fact['observation_unit']==forecast['observation_unit']=='logical_provider_job_reported_result' and forecast['reported_result_support']=={'reported_result_count':1} and forecast['job_ref'] is None and forecast['sample_ref'] is None and forecast['elapsed_seconds'] is None and forecast['timing_relation']=='unknown')
        actions={(x['episode_id'],x['decision_index']):x for x in state['runtime_actions']}
        check('six original actions in correct owners',len(actions)==6 and json.loads(actions[parent,0]['action'])==selection and [json.loads(actions[child,i]['action'])['tool'] for i in range(3)]==['public.hmmer.search','execution.estimate','episode.history'] and [json.loads(actions[parent,i]['action'])['tool'] for i in (1,2)]==['execution.estimate','episode.history'])
        bycall={(x['episode_id'],x['call_index']):json.loads(x['request']) for x in state['runtime_model_calls']}
        observations={}
        for episode in (child,parent):
            obs=sorted((x for x in state['runtime_observations'] if x['episode_id']==episode),key=lambda x:x['unit_index'])
            check('three own observations and scientificzero: '+episode,len(obs)==3 and [x['unit_index'] for x in obs]==[0,1,2] and all(json.loads(x['observation'])['credit']['credit']==json.loads(x['observation'])['step']['credit']==0 for x in obs))
            check('closed episode retained3units: '+episode,episodes[episode]['state']=='yielded' and json.loads(episodes[episode]['completion'])=={'actions':3,'ended_by':'yield_stop'})
            for x in obs:
                value=json.loads(x['observation']);check('observation own identity '+value['unit_ref']['unit_id'],value['unit_ref']['episode_id']==episode and value['unit_ref']['unit_index']==x['unit_index'])
            observations[episode]=[json.loads(x['observation']) for x in obs]
        check('scientific and monitoring distinct in childsavedcontexts',[bycall[child,i]['context']['current_credit'] for i in range(3)]==[0,0,0] and [bycall[child,i]['context']['monitoring_information_credit'] for i in range(3)]==[0,1,1])
        check('parent receives once and retained monitoringone',all(bycall[parent,i]['context']['child_reports']==[ret['form']] and bycall[parent,i]['context']['current_credit']==0 and bycall[parent,i]['context']['monitoring_information_credit']==1 for i in (1,2)))
        check('no initial proposal fabricated before choices',all('api_execution_proposal' not in bycall[e,i]['context'] for e,i in [(child,0),(child,1),(parent,1)]))
        assignment=cr['message']['episode_assignment'];estimate=assignment['context']['estimate_input']
        for episode in (child,parent):
            proposed=json.loads(actions[episode,1]['result'])['result'];context=bycall[episode,2]['context']
            check('original explicit proposal replay '+episode,json.loads(actions[episode,1]['action'])['arguments']==estimate and proposed==context['api_execution_proposal'] and proposed['api_reported_execution_forecasts']==context['api_reported_execution_forecasts']==[forecast] and proposed['request_sha256']==digest(proposed['request']))
        check('child outer tool contracts stable across3savedcalls',*[False] if False else [True]) if False else None
        toolmaps=[{t['name']:t for t in bycall[child,i]['context']['tools']} for i in range(3)]
        check('child outer catalog same across savedcalls',toolmaps[0]==toolmaps[1]==toolmaps[2])
        check('parent outer catalog retained across resumedcalls',bycall[parent,1]['context']['tools']==bycall[parent,2]['context']['tools'])
        outer=f'{run}:{child}:0';toolrows={x['operation_key']:x for x in state['tool_operations']};search=json.loads(actions[child,0]['result']);order=json.loads(state['public_search_orders'][0]['data']);job=state['provider_jobs'][0]
        check('single actual order bound to original outertool',len(state['provider_jobs'])==len(state['public_search_orders'])==1 and job['operation_key']==order['order_operation_key']==outer and json.loads(toolrows[outer]['arguments'])==assignment['context']['search_arguments']==json.loads(actions[child,0]['action'])['arguments'] and search['operation_ref']==toolrows[outer]['id'] and json.loads(toolrows[outer]['result'])['api_timing_refs']==search['api_timing_refs']==[fact['receipt_ref']] and fact['job_ref']==job['id']==order['job_ref'])
        base=digest({'version':'ordinary_hmmer_protocol_key_v1','registry_ref':order['registry_ref'],'job_ref':job['id'],'parent_operation_key':outer})
        ops=[json.loads(x['data']) for x in state['public_search_operations']]
        keys=[f'ordinary-hmmer-v1:{base}:{suffix}' for suffix in ('submit:0:-:-','status:0:-:-','result:0:1:2')]
        check('exact three protocol receipts deterministic replaykeys',len(ops)==3 and {x['operation_key'] for x in ops}==set(keys) and {x['receipt_ref'] for x in ops}==set(search['provider_operation_refs']) and all(x['job_ref']==job['id'] and x['outcome']=='completed' and x['failure'] is None for x in ops))
        check('one cached result selector',len(state['public_search_results'])==1 and state['public_search_results'][0]['page']==1 and state['public_search_results'][0]['page_size']==2)
        receipts=state['runtime_record_receipts'];check('parent timing childform receipt exactlyonce',sum(x['episode_id']==parent and x['record_ref']==fact['receipt_ref'] and x['receipt_kind']=='child_form' for x in receipts)==1)
        identity=json.loads(bc['execution_identity']);childowners=[json.loads(actions[child,i]['timing'])['intervals'][0]['owner'] for i in range(3)];parentowners=[json.loads(actions[parent,i]['timing'])['intervals'][0]['owner'] for i in range(3)]
        check('actual durable workerincarnation separate fromparent',set(identity)=={'pid','boot_id','start_ticks'} and type(identity['pid'])is int and identity['pid']>0 and all(x==identity for x in childowners) and len({x['pid'] for x in parentowners})==1 and parentowners[0]['pid']!=identity['pid'])
        check('one returned backendevent and one ackevent',sum(x['event']=='returned' for x in backend['events'])==1 and sum(x['record_ref']==ad['admission_id'] for x in backend['events'])==1)
        archives={name:archive(ret[name]) for name in ('episode_archive','result_archive','facts_archive')}
        parent_archive=archive(json.loads(episodes[parent]['archive']))
        check('child archive raw units match ownobservations',archives['episode_archive']['request']==cr and archives['episode_archive']['episode_id']==child and archives['episode_archive']['units_consumed']==3 and all(u['unit_ref']==o['unit_ref'] and u['controller_step']==o['step'] for u,o in zip(archives['episode_archive']['units'],observations[child])))
        check('parent archive3units embeds original child once',parent_archive['units_consumed']==len(parent_archive['units'])==3 and parent_archive['units'][0]['child']==archives['episode_archive'] and parent_archive['units'][0]['child_result']==archives['result_archive'])
        check('archived returned form and separate credit facts',archives['result_archive']=={'form':ret['form']} and archives['facts_archive']['api_execution_measurements']==[fact] and archives['facts_archive']['api_reported_execution_forecasts']==[forecast] and archives['facts_archive']['credit']==0 and archives['facts_archive']['monitoring_information_credit']==1)
        artifactrows={x['id']:x for x in state['artifacts']};artifact_data={}
        for ref,row in artifactrows.items():
            p=FIXTURE/'case/workspace/artifacts'/row['sha256'][:2]/row['sha256']
            raw=copy_input(p,'fixture/case/workspace/artifacts/'+row['sha256'][:2]+'/'+row['sha256'])
            check('immutable artifact hash/size '+ref,sha(raw)==row['sha256'] and len(raw)==row['size'])
            artifact_data[ref]=raw
        record=next(json.loads(x['data']) for x in state['records'] if x['id']==fact['receipt_ref']);body=json.loads(artifact_data[record['artifact_ref']]);w=body['witness']
        check('returned fact bound to immutable timing source',body['version']=='api_reported_timing_source_v1' and body['run_id']==run and body['scope']==spec['child']['scope'] and {k:w[k] for k in ('job_ref','duration_measure','observation_unit','elapsed_seconds','observed_at')}=={k:fact[k] for k in ('job_ref','duration_measure','observation_unit','elapsed_seconds','observed_at')} and w['acquisition_receipt_ref'] in search['provider_operation_refs'])
        settings=json.loads(state['runtime_runs'][0]['settings']);binding=spec['runtime_binding'];check('worker original runtime bindings/source pinned',binding['implementation_sha256']==PIN and binding['settings_sha256']==digest(settings) and binding['arguments']['kind']=='fixed_case')
        for name,pinvalue in binding['arguments']['caller_binding_pins'].items():
            v=json.loads(copy_input(FIXTURE/'run'/name,'fixture/run/'+name));check('original caller file pin '+name,digest(v)==pinvalue)
        check('runtime manifest matches original saved settings',json.loads(copy_input(FIXTURE/'run/run.json','fixture/run/run.json'))=={'run_id':run,**settings})
        controls=metadata['ORIGINAL_PRESERVATION.json'];prefix='test_real_detached_direct_sear0/'
        controlmap={x['path'][len(prefix):]:x for x in controls['members'] if x['path'].startswith(prefix)}
        for path,row in list(READSET.items()):
            p=Path(path)
            if p.is_relative_to(FIXTURE):
                rel=p.relative_to(FIXTURE).as_posix();orig=controlmap[rel]
                check('opened preserved fixture byte/mode control '+rel,orig['kind']=='file' and orig['sha256']==row['sha256'] and orig['bytes']==row['bytes'] and orig['mode']==row['mode'])
        result.update(status='verified_closed_scripted_worker_fixture',identities={'run_id':run,'parent_episode_id':parent,'child_episode_id':child,'handle':spec['handle'],'return_id':ret['return_id'],'admission_id':ad['admission_id'],'worker_execution_identity':identity,'parent_execution_identity':parentowners[0]},timing_fact=fact,forecast=forecast,observation_counts={'child':3,'parent':3},scientific_credit=[0,0,0],monitoring_information_credit_contexts={'child':[0,1,1],'parent_resume':[1,1]},limits=[
            'Scripted engineering fixture: no claim about configured-model scientific choices or biological conclusions.',
            'Three-action continuation law and60second deadline are explicit fixture controls; no production numerical policy inferred.',
            '2.75 is reported provider search elapsed time; queue wait, total turnaround and attempt duration are not inferred.',
            'Original initial provider was configured but unentered; no claim it made a scientific decision.',
            'Durable rows plus held test/XML support replay checks; this verifier did not replay start/load_return or perform HTTP.',
            'Root test asserts POST/GET/GET and in-memory shared-owner identities; this verifier checks saved receipt/request/archive bindings and passing test authority, not a new transport capture or Python object identity.',
            'Saved observations and forecasts compared as facts only; no score/forecast projector or estimator executed.',
            'No original fixture DB, live scientific DB, provider private logs/events, app/native/model/service/test calls read or run.',
            'Initial003 fixture failure is historical root-reported context; only invocation004 and selected closed copy independently reviewed here.',
            'Metadata discovery initially used .items() on coherent.files list; AttributeError preserved as authoring-only error, corrected without input mutation.'
        ])
    except BaseException as error:
        result['error']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
    finally:
        result['finished_at_utc']=now()
        save(OUT/'READSET_FINAL001.json',{'version':'offline_review_exact_readset_v1','files':list(READSET.values())})
        # Every opened original is rehashed after all SQL handles have closed.
        unchanged=True
        for path,row in list(READSET.items()):
            if witness(Path(path))!=row:unchanged=False
        result['all_opened_inputs_unchanged_after_explicit_close']=unchanged
        result['check_count']=len(CHECKS)
        save(output,result)
        print(json.dumps({'status':result['status'],'checks':len(CHECKS),'result':str(output),'sha256':sha(output.read_bytes()),'error':result.get('error',{}).get('message')},sort_keys=True))
    return 0 if result['status']=='verified_closed_scripted_worker_fixture' else 1

if __name__=='__main__':raise SystemExit(main())
