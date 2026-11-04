"""Selected project-storage operations and actual PBS jobs through explicit SSH.

The remote worker executes one selected operation. It contains no episode,
model, polling policy or repair loop. Original intents and outcomes survive a
lost SSH reply; an uncertain command or submission is never run a second time.
"""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
import re
import shlex
import subprocess

from .practical_execution_records import validate_assignment, validate_context, validate_outcome
from .execution_inventory import _decode as _decode_inventory, validate_catalog


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


_JOB_DRIVER = r'''
import datetime,hashlib,json,os,subprocess,sys,time
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def publish(path,value):
    temporary=path+'.writing'
    with open(temporary,'w') as stream:
        stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
request=json.load(open(sys.argv[1]))
started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
os.chdir(request['cwd'])
environment=dict(os.environ);environment.update(request['environment'])
try:
    result=subprocess.run(request['argv'],env=environment)
    returncode=result.returncode;failure=None
except OSError as error:
    returncode=127;failure=type(error).__name__
publish(sys.argv[2],{'version':'practical_pbs_exit_v1','job_id':os.environ.get('PBS_JOBID'),
    'job_request_sha256':request['job_request_sha256'],'submission_token':request['submission_token'],
    'returncode':returncode,'started_at':started,
    'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'duration_seconds':time.monotonic()-clock,'failure':failure})
sys.exit(returncode if 0<=returncode<=255 else 1)
'''


_REMOTE_WORKER = r'''
import base64,datetime,fcntl,hashlib,json,os,re,shlex,stat,subprocess,sys,tempfile

path_observation_failures=[]

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,value):
    descriptor,temporary=tempfile.mkstemp(prefix='.'+os.path.basename(path)+'-',dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor,'w') as stream:
            stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory=os.open(os.path.dirname(path),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
def confined(path):
    if not isinstance(path,str) or not os.path.isabs(path):raise ValueError('practical_write_outside_workspace')
    result=os.path.realpath(path)
    if os.path.commonpath([workspace,result])!=workspace:raise ValueError('practical_write_outside_workspace')
    return result
def filesystem_failure(path,error):
    return {'status':'failed','failure':{'code':'practical_filesystem_operation_failed',
        'path':path,'exception_type':type(error).__name__,'errno':error.errno}}
def paths():
    selected=set();hash_paths=set()
    for requirement in assignment['progress_requirements']:
        predicate=requirement['predicate']
        if predicate['kind'] in ('path_exists','file_sha256'):selected.add(predicate['path'])
        elif predicate['kind']=='requested_job_outputs':selected.update(predicate['output_paths'])
        if predicate['kind']=='file_sha256':hash_paths.add(predicate['path'])
    result=[]
    for name in sorted(selected):
        path=confined(name)
        try:
            observed=os.stat(path);exists=True
            kind='file' if stat.S_ISREG(observed.st_mode) else 'directory' if stat.S_ISDIR(observed.st_mode) else 'other'
        except (FileNotFoundError,NotADirectoryError):exists=False;kind='missing'
        except OSError as error:
            path_observation_failures.append(filesystem_failure(name,error)['failure']);continue
        sha=None
        if kind=='file' and name in hash_paths:
            try:
                hasher=hashlib.sha256()
                with open(path,'rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
                sha=hasher.hexdigest()
            except OSError as error:path_observation_failures.append(filesystem_failure(name,error)['failure'])
        result.append({'path':name,'exists':exists,'object_type':kind,'sha256':sha})
    return result
def environment(overrides,directory):
    project_tmp=confined(os.path.join(directory,'tmp'));project_cache=confined(os.path.join(directory,'cache'))
    result=dict(os.environ)
    result.update({'TMPDIR':project_tmp,'TMP':project_tmp,'TEMP':project_tmp,
        'XDG_CACHE_HOME':project_cache,'PIP_CACHE_DIR':os.path.join(project_cache,'pip'),
        'PYTHONUSERBASE':os.path.join(directory,'python-user'),'PYTHONDONTWRITEBYTECODE':'1',
        'CONDA_PKGS_DIRS':os.path.join(project_cache,'conda'),'NUMBA_CACHE_DIR':os.path.join(project_cache,'numba')})
    result.update(overrides)
    for key in ('TMPDIR','TMP','TEMP','XDG_CACHE_HOME','PIP_CACHE_DIR','PYTHONUSERBASE','CONDA_PKGS_DIRS','NUMBA_CACHE_DIR'):
        confined(result[key])
    os.makedirs(project_tmp,exist_ok=True);os.makedirs(project_cache,exist_ok=True)
    return result
def native(argv,env=None):
    completed=subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return {'argv':argv,'returncode':completed.returncode,
        'stdout':completed.stdout.decode('utf-8','replace'),'stderr':completed.stderr.decode('utf-8','replace')}
def qstat(job_id):
    observed=native(['qstat','-x','-f','-F','json',job_id])
    record=None
    if observed['returncode']==0:
        try:record=json.loads(observed['stdout']).get('Jobs',{}).get(job_id)
        except (ValueError,AttributeError):pass
    return record,observed
def token_matches(record,ledger):
    if not isinstance(record,dict) or record.get('Job_Name')!=ledger['job_name'] or record.get('Account_Name')!=configuration['account']:return False
    variables=record.get('Variable_List',{})
    if isinstance(variables,str):variables=dict(item.split('=',1) for item in variables.split(',') if '=' in item)
    return isinstance(variables,dict) and variables.get('EPISODE_SUBMISSION_TOKEN')==ledger['submission_token']
def recover_submission(ledger,ledger_path):
    if ledger.get('job_id') is not None:return ledger
    observation=native(['qselect','-N',ledger['job_name']])
    matches=[]
    if observation['returncode']==0:
        for candidate in observation['stdout'].split():
            if re.fullmatch(r'[0-9]+(?:\.[A-Za-z0-9_.-]+)?',candidate):
                record,detail=qstat(candidate)
                if token_matches(record,ledger):matches.append(candidate)
    if len(matches)==1:
        ledger=dict(ledger,job_id=matches[0],phase='submitted',recovery_observation=observation)
        write(ledger_path,ledger)
    return ledger
def log(path):
    path=confined(path)
    if not os.path.isfile(path):return {'path':path,'available':False}
    limit=request.get('log_window_bytes',8192)
    size=os.path.getsize(path);offset=max(0,size-limit)
    with open(path,'rb') as stream:stream.seek(offset);data=stream.read(min(limit,max(0,size-offset)))
    return {'path':path,'available':True,'observed_at':now(),'size_bytes':size,
        'offset_bytes':offset,'returned_bytes':len(data),'bytes_base64':base64.b64encode(data).decode('ascii'),
        'text':data.decode('utf-8','replace')}
def job_result(ledger):
    job_id=ledger.get('job_id');record=None;observation=None;exit_receipt=None
    if job_id is not None:record,observation=qstat(job_id)
    exit_path=os.path.join(job_directory,'exit.json')
    if os.path.isfile(exit_path):
        value=json.load(open(exit_path))
        if (value.get('version')!='practical_pbs_exit_v1' or value.get('job_id')!=job_id
                or value.get('job_request_sha256')!=digest(assignment['requested_job'])
                or value.get('submission_token')!=ledger['submission_token']):raise ValueError('practical_pbs_exit_identity_conflict')
        exit_receipt=value
    status='unknown';returncode=None
    if record is not None:
        if not token_matches(record,ledger):raise ValueError('practical_pbs_job_identity_conflict')
        code=record.get('job_state')
        if code in ('Q','H','W','T'):status='submitted'
        elif code in ('R','E','B'):status='running'
        elif code in ('F','C') and type(record.get('Exit_status')) is int:
            returncode=record['Exit_status'];status='completed' if returncode==0 else 'failed'
    if exit_receipt is not None:
        returncode=exit_receipt['returncode'];status='completed' if returncode==0 else 'failed'
    outputs=sorted(set(path for item in assignment['progress_requirements']
        if item['predicate']['kind']=='requested_job_outputs' for path in item['predicate']['output_paths']))
    execution_id=job_id if job_id is not None else 'pbs-submission:'+ledger['submission_token']
    handoff=None if job_id is None else {'execution_id':job_id,
        'monitor_operation':'practical.job.status','results_operation':'practical.job.collect'}
    fact={'requested_job_sha256':digest(assignment['requested_job']),
        'argv':assignment['requested_job']['argv'],'environment':assignment['requested_job']['environment'],
        'resource_kind':'hpc','execution_id':execution_id,'status':status,
        'returncode':returncode,'output_paths':outputs,'handoff':handoff}
    fields=('Job_Name','Account_Name','job_state','queue','Priority','base_score','project_priority','estimated','Resource_List',
        'resources_used','qtime','ctime','etime','stime','obittime','eligible_time','Exit_status','comment')
    detail={'pbs_job_id':job_id,'submission_phase':ledger['phase'],'account':configuration['account'],
        'queue':ledger['queue'],'resources':ledger['resources'],'observed_at':now(),
        'attempt_id':ledger['attempt_id'],'attempt_operation_key':ledger['operation_key'],
        'retry_of_execution_id':ledger['retry_of_execution_id'],
        'pbs_fields':{key:record[key] for key in fields if record is not None and key in record},
        'status_query_returncode':None if observation is None else observation['returncode'],
        'status_query_stderr':None if observation is None else observation['stderr'],
        'exit_receipt':exit_receipt,'stdout':log(os.path.join(job_directory,'stdout')),
        'stderr':log(os.path.join(job_directory,'stderr')),
        'submission_outcome':ledger.get('submission_outcome')}
    for key in ('native_blast_database_plan_path','native_blast_database_plan_sha256'):
        if key in ledger:detail[key]=ledger[key]
    return fact,detail
def prepare_attempt(directory,selected,retry_of):
    os.makedirs(directory,exist_ok=True)
    token=digest({'run_id':request['run_id'],'episode_id':request['episode_id'],
        'assignment_sha256':digest(assignment),'operation_key':request['operation_key']})
    ledger={'version':'practical_pbs_submission_v2','selection':selected,'phase':'prepared',
        'job_id':None,'submission_token':token,'job_name':'ep'+token[:24],
        'queue':arguments['queue'],'resources':arguments['resources'],
        'attempt_id':digest(request['operation_key']),'operation_key':request['operation_key'],
        'assignment_sha256':digest(assignment),'retry_of_execution_id':retry_of}
    logical=assignment['requested_job']
    argv=logical['argv'];extra={}
    overrides=logical['environment']
    if 'native_blast_database' in logical:
        binding=configuration['native_blast_database'];job=logical['native_blast_database']
        plan={'version':'native_blast_database_run_plan_v1',
            'identity':{'run_id':request['run_id'],'episode_id':request['episode_id'],
                'resource_id':assignment['resource_id'],'operation_key':request['operation_key'],
                'attempt_id':ledger['attempt_id'],'assignment_sha256':digest(assignment),
                'requested_job_sha256':digest(logical),'submission_token':token,'execution_id':None},
            'requested_job':logical,'attempt_directory':directory,
            'input_paths':{row['input_key']:os.path.join(directory,'inputs',row['input_key']) for row in job['inputs']},
            'database_paths':{row['database_key']:row['native_paths'] for row in job['databases']},
            'output_directory':os.path.join(directory,'outputs'),
            'resource_environment':binding['environment'],'producer_manifest':binding['producer']['manifest']}
        plan_path=os.path.join(directory,'native-blast-database-plan.json')
        write(plan_path,plan)
        extra={'native_blast_database_plan_path':plan_path,'native_blast_database_plan_sha256':digest(plan)}
        ledger.update(extra)
        argv=[configuration['python_executable'],'-B','-m','gene_annotation_episode.native_blast_database_driver',plan_path]
        overrides={**binding['environment'],**logical['environment'],
            'PYTHONPATH':binding['producer']['module_root'],'PYTHONDONTWRITEBYTECODE':'1'}
    env=environment(overrides,directory)
    job_request=os.path.join(directory,'job-request.json')
    write(job_request,{'argv':argv,'environment':env,
        'cwd':cwd,'job_request_sha256':digest(logical),'submission_token':token,**extra})
    driver=os.path.join(directory,'job-driver.py')
    with open(driver,'w') as stream:stream.write(request['job_driver']);stream.flush();os.fsync(stream.fileno())
    script=os.path.join(directory,'job.sh')
    with open(script,'w') as stream:
        stream.write('#!/bin/bash\nset -e\ncd '+shlex.quote(cwd)+'\nexec '+shlex.quote(configuration['python_executable'])
            +' -B '+shlex.quote(driver)+' '+shlex.quote(job_request)+' '+shlex.quote(os.path.join(directory,'exit.json'))+'\n')
        stream.flush();os.fsync(stream.fileno())
    command=['qsub','-A',configuration['account'],'-q',arguments['queue'],'-N',ledger['job_name'],
        '-o',os.path.join(directory,'stdout'),'-e',os.path.join(directory,'stderr'),
        '-v','EPISODE_SUBMISSION_TOKEN='+token]
    for resource in arguments['resources']:command.extend(['-l',resource])
    command.append(script);ledger['submission_command']=command
    write(os.path.join(directory,'submission.json'),ledger)
    return ledger
def load_attempt(pointer):
    if (not isinstance(pointer,dict) or set(pointer)!={'version','attempt_id','operation_key'}
            or pointer['version']!='practical_pbs_current_v1'
            or pointer['attempt_id']!=digest(pointer['operation_key'])):
        raise ValueError('practical_pbs_current_attempt_identity_conflict')
    directory=confined(os.path.join(job_root,'attempts',pointer['attempt_id']))
    ledger=json.load(open(os.path.join(directory,'submission.json')))
    if (ledger.get('version')!='practical_pbs_submission_v2' or ledger.get('attempt_id')!=pointer['attempt_id']
            or ledger.get('operation_key')!=pointer['operation_key'] or ledger.get('assignment_sha256')!=digest(assignment)):
        raise ValueError('practical_pbs_attempt_identity_conflict')
    return directory,ledger
def submit_attempt(ledger,ledger_path,directory):
    ledger=dict(ledger,phase='submitting');write(ledger_path,ledger)
    submitted=native(ledger['submission_command'],env=environment(assignment['requested_job']['environment'],directory))
    ledger['submission_outcome']=submitted
    if submitted['returncode']==0 and re.fullmatch(r'[0-9]+(?:\.[A-Za-z0-9_.-]+)?',submitted['stdout'].strip()):
        ledger['job_id']=submitted['stdout'].strip();ledger['phase']='submitted'
    write(ledger_path,ledger)
    return ledger

request=json.load(sys.stdin);configuration=request['configuration']
workspace=os.path.realpath(configuration['workspace'])
if request['mode']=='read_inventory':
    path=confined(request['path'])
    with open(path,'rb') as stream:data=stream.read()
    reply={'outcome':{'facts':{},'inventory_bytes_base64':base64.b64encode(data).decode('ascii')},'context_after':None}
    print(canonical({'version':'practical_pbs_reply_v1','request_sha256':digest(request),'result':reply}));sys.exit(0)
assignment=request['assignment']
if not os.path.isabs(configuration['workspace']) or os.path.commonpath([workspace,os.path.realpath(assignment['workspace'])])!=workspace:
    raise ValueError('practical_workspace_configuration_conflict')
workspace=os.path.realpath(assignment['workspace']);context=request['context'];cwd=confined(context['cwd'])
if request['mode'] in ('observe_execution','read_output','native_blast_database_attempt'):
    # This branch is deliberately before the operation-intent/working-directory
    # branch. Observations neither edit launch history nor follow current.json.
    owner=digest({'run_id':request['run_id'],'episode_id':request['episode_id']})
    job_root=confined(os.path.join(workspace,'.episode-jobs',owner,digest(assignment)))
    original_key=request['original_operation_key']
    if original_key is None:
        pinned=confined(os.path.join(job_root,'attempts',request['attempt_id'],'submission.json'))
        original_key=json.load(open(pinned))['operation_key']
    pointer={'version':'practical_pbs_current_v1','attempt_id':request['attempt_id'],
        'operation_key':original_key}
    job_directory,ledger=load_attempt(pointer)
    expected_token=digest({'run_id':request['run_id'],'episode_id':request['episode_id'],
        'assignment_sha256':digest(assignment),'operation_key':original_key})
    if (ledger.get('job_id')!=request['execution_id'] or ledger.get('job_id') is None
            or ledger.get('submission_token')!=expected_token
            or ledger.get('job_name')!='ep'+expected_token[:24]
            or ledger.get('selection',{}).get('account')!=configuration['account']
            or ledger.get('selection',{}).get('requested_job_sha256')!=digest(assignment['requested_job'])):
        raise ValueError('practical_pbs_execution_identity_conflict')
    database_attempt='native_blast_database' in assignment['requested_job']
    if database_attempt:
        plan_path=os.path.join(job_directory,'native-blast-database-plan.json')
        job_request_path=os.path.join(job_directory,'job-request.json')
        if confined(job_request_path)!=job_request_path:
            raise ValueError('native_blast_database_original_request_path_conflict')
        job_request=json.load(open(job_request_path))
        plan_sha256=ledger.get('native_blast_database_plan_sha256')
        for value in (ledger,job_request):
            if (value.get('native_blast_database_plan_path')!=plan_path
                    or value.get('native_blast_database_plan_sha256')!=plan_sha256
                    or not isinstance(plan_sha256,str) or re.fullmatch('[0-9a-f]{64}',plan_sha256) is None):
                raise ValueError('native_blast_database_original_plan_identity_conflict')
        original_identity={'run_id':request['run_id'],'episode_id':request['episode_id'],
            'resource_id':assignment['resource_id'],'operation_key':original_key,
            'attempt_id':ledger['attempt_id'],'assignment_sha256':digest(assignment),
            'requested_job_sha256':digest(assignment['requested_job']),
            'submission_token':expected_token,'execution_id':request['execution_id']}
        if (job_request.get('job_request_sha256')!=original_identity['requested_job_sha256']
                or job_request.get('submission_token')!=expected_token):
            raise ValueError('native_blast_database_original_attempt_identity_conflict')
    if request['mode']=='native_blast_database_attempt':
        if not database_attempt:raise ValueError('native_blast_database_target_required')
        detail={'authenticated_attempt':{'identity':original_identity,'attempt_directory':job_directory,
            'plan_sha256':plan_sha256},'plan_path':plan_path,'ledger':ledger,'job_request':job_request}
        reply={'outcome':{'facts':{},'native_outcome':detail},'context_after':None}
    elif request['mode']=='observe_execution':
        fact,detail=job_result(ledger)
        observed_outputs=[]
        for path in fact['output_paths']:
            name=confined(path);available=os.path.isfile(name)
            observed_outputs.append({'role':'requested_output:'+path,'available':available,
                'bytes':os.path.getsize(name) if available else None,
                'writer_closed':available and fact['status'] in ('completed','failed')})
        detail['observed_outputs']=observed_outputs
        reply={'outcome':{'facts':{'requested_job':fact},'native_outcome':detail},'context_after':None}
    else:
        path=confined(request['path'])
        if database_attempt:
            bundle_path=os.path.join(job_directory,'bundle.json')
            permitted={plan_path,bundle_path}
            if path not in permitted:
                if confined(bundle_path)!=bundle_path:
                    raise ValueError('native_blast_database_original_bundle_path_conflict')
                bundle=json.load(open(bundle_path))
                if bundle.get('identity')!=original_identity or digest(bundle.get('plan'))!=plan_sha256:
                    raise ValueError('native_blast_database_read_manifest_identity_conflict')
                for row in bundle.get('artifacts',[]):
                    relative=row['relative_path']
                    if os.path.isabs(relative) or '..' in relative.split('/'):
                        raise ValueError('native_blast_database_read_path_escape')
                    permitted.add(os.path.join(job_directory,relative))
            if request['path']!=path or path not in permitted:
                raise ValueError('native_blast_database_unselected_output_path')
        try:
            with open(path,'rb') as stream:
                size=os.fstat(stream.fileno()).st_size;stream.seek(request['offset'])
                data=stream.read(min(request['limit'],max(0,size-request['offset'])))
        except FileNotFoundError:
            if not database_attempt:raise
            detail={'path':path,'read_failure':'file_missing'}
        else:
            detail={'path':path,'offset':request['offset'],'returned_bytes':len(data),'size_bytes':size,
                'bytes_base64':base64.b64encode(data).decode('ascii'),'text_utf8':data.decode('utf-8','replace')}
        reply={'outcome':{'facts':{},'native_outcome':detail},'context_after':None}
elif request['mode']=='initial':
    reply={'outcome':{'facts':{'paths':paths()}},'context_after':None}
    if path_observation_failures:reply['outcome']['path_observation_failures']=path_observation_failures
else:
    operation=request['operation_key'];tool=request['tool_name'];arguments=request['arguments']
    owner=digest({'run_id':request['run_id'],'episode_id':request['episode_id']})
    root=confined(os.path.join(workspace,'.episode-operations',owner,digest(operation)))
    os.makedirs(root,exist_ok=True)
    lock=open(os.path.join(root,'lock'),'a+');fcntl.flock(lock,fcntl.LOCK_EX)
    intent_path=os.path.join(root,'intent.json');result_path=os.path.join(root,'result.json')
    if os.path.isfile(intent_path):
        if json.load(open(intent_path))!=request:raise ValueError('practical_pbs_operation_identity_conflict')
        if os.path.isfile(result_path):
            reply=json.load(open(result_path))
            print(canonical({'version':'practical_pbs_reply_v1','request_sha256':digest(request),'result':reply}));sys.exit(0)
        recovering=True
    else:write(intent_path,request);recovering=False
    outcome={'facts':{},'native_outcome':None};after=None
    job_root=confined(os.path.join(workspace,'.episode-jobs',owner,digest(assignment)))
    if tool=='practical.context.set':
        selected=confined(arguments['cwd'])
        if not os.path.isdir(selected):
            outcome['native_outcome']={'status':'failed','failure':{
                'code':'practical_working_directory_missing','path':selected}}
        else:
            changed=selected!=context['cwd'] or arguments['environment']!=context['environment']
            after={'revision':context['revision']+int(changed),'cwd':selected,'environment':arguments['environment']}
    elif tool=='practical.directory.create':
        path=confined(arguments['path'])
        try:
            os.makedirs(path,exist_ok=True)
            outcome['native_outcome']={'path':path,'is_directory':os.path.isdir(path)}
        except OSError as error:outcome['native_outcome']=filesystem_failure(path,error)
    elif tool=='practical.file.write':
        path=confined(arguments['path']);data=arguments['text'].encode('utf-8')
        try:
            if recovering and os.path.isfile(path):
                if open(path,'rb').read()!=data:raise ValueError('practical_pbs_write_recovery_conflict')
            else:
                descriptor,temporary=tempfile.mkstemp(prefix='.'+os.path.basename(path)+'-',dir=os.path.dirname(path))
                try:
                    with os.fdopen(descriptor,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
                    os.replace(temporary,path)
                finally:
                    if os.path.exists(temporary):os.unlink(temporary)
            outcome['native_outcome']={'path':path,'sha256':hashlib.sha256(data).hexdigest()}
        except OSError as error:outcome['native_outcome']=filesystem_failure(path,error)
    elif tool=='practical.file.read':
        path=confined(arguments['path'])
        try:
            with open(path,'rb') as stream:
                size=os.fstat(stream.fileno()).st_size;stream.seek(arguments['offset'])
                data=stream.read(min(arguments['limit'],max(0,size-arguments['offset'])))
            outcome['native_outcome']={'path':path,'offset':arguments['offset'],
                'returned_bytes':len(data),'size_bytes':size,
                'bytes_base64':base64.b64encode(data).decode('ascii'),
                'text_utf8':data.decode('utf-8','replace')}
        except OSError as error:outcome['native_outcome']=filesystem_failure(path,error)
    elif tool=='practical.inspect':pass
    elif tool=='practical.inventory.refresh':
        path=confined(arguments['path'])
        try:
            with open(path,'rb') as stream:data=stream.read()
            outcome['inventory_bytes_base64']=base64.b64encode(data).decode('ascii')
        except OSError as error:
            outcome['native_outcome']=filesystem_failure(path,error)
            outcome['inventory_failure']={'code':'inventory_read_failed','exception_type':type(error).__name__}
    elif tool=='practical.command.run':
        env=dict(context['environment']);env.update(arguments['environment']);effective=environment(env,root)
        stdout=os.path.join(root,'stdout');stderr=os.path.join(root,'stderr')
        command_path=os.path.join(root,'command-result.json')
        if os.path.isfile(command_path):
            saved=json.load(open(command_path))
            if (saved.get('version')!='practical_pbs_command_v1' or saved.get('request_sha256')!=digest(request)
                    or saved.get('command',{}).get('argv')!=arguments['argv']
                    or saved.get('command',{}).get('environment')!=env
                    or saved.get('command',{}).get('execution_id')!=intent_path):
                raise ValueError('practical_pbs_command_receipt_identity_conflict')
        else:
            if recovering:raise ValueError('practical_pbs_command_outcome_unknown_no_reexecution')
            with open(stdout,'wb') as out,open(stderr,'wb') as err:
                completed=subprocess.run(arguments['argv'],cwd=cwd,env=effective,stdout=out,stderr=err)
            saved={'version':'practical_pbs_command_v1','request_sha256':digest(request),
                'command':{'argv':arguments['argv'],'environment':env,
                    'returncode':completed.returncode,'execution_id':intent_path},
                'native_outcome':{'returncode':completed.returncode,
                    'stdout':log(stdout),'stderr':log(stderr),'cwd':cwd}}
            write(command_path,saved)
        outcome['facts']['command']=saved['command'];outcome['native_outcome']=saved['native_outcome']
    elif tool in ('practical.job.start','practical.job.status','practical.job.collect'):
        os.makedirs(job_root,exist_ok=True)
        job_lock=open(os.path.join(job_root,'lock'),'a+');fcntl.flock(job_lock,fcntl.LOCK_EX)
        pointer_path=os.path.join(job_root,'current.json')
        pointer=json.load(open(pointer_path)) if os.path.isfile(pointer_path) else None
        ledger=None;rejection=None
        if pointer is not None:job_directory,ledger=load_attempt(pointer)
        if tool=='practical.job.start':
            selected={'queue':arguments['queue'],'resources':arguments['resources'],
                'account':configuration['account'],'cwd':cwd,'requested_job_sha256':digest(assignment['requested_job'])}
            attempt_id=digest(operation);attempt_directory=confined(os.path.join(job_root,'attempts',attempt_id))
            original_path=os.path.join(attempt_directory,'submission.json')
            retry_of=arguments.get('retry_failed_execution_id')
            if os.path.isfile(original_path):
                job_directory,ledger=load_attempt({'version':'practical_pbs_current_v1',
                    'attempt_id':attempt_id,'operation_key':operation})
                if ledger['selection']!=selected or ledger['retry_of_execution_id']!=retry_of:
                    raise ValueError('practical_pbs_submission_identity_conflict')
                if pointer is None:
                    pointer={'version':'practical_pbs_current_v1','attempt_id':attempt_id,'operation_key':operation}
                    write(pointer_path,pointer)
            elif retry_of is not None:
                if ledger is None:rejection='practical_pbs_retry_without_previous_attempt'
                elif ledger.get('job_id') is None:rejection='practical_pbs_retry_requires_actual_job_id'
                elif retry_of!=ledger['job_id']:rejection='practical_pbs_retry_execution_identity_conflict'
                else:
                    prior_fact,prior_detail=job_result(ledger)
                    if prior_fact['status']!='failed' or prior_fact['returncode'] is None:
                        rejection='practical_pbs_retry_requires_verified_terminal_failure'
                if rejection is None:
                    job_directory=attempt_directory;ledger=prepare_attempt(job_directory,selected,retry_of)
                    pointer={'version':'practical_pbs_current_v1','attempt_id':attempt_id,'operation_key':operation}
                    write(pointer_path,pointer)
            elif ledger is not None:
                if ledger['selection']!=selected:raise ValueError('practical_pbs_submission_identity_conflict')
            else:
                job_directory=attempt_directory;ledger=prepare_attempt(job_directory,selected,None)
                pointer={'version':'practical_pbs_current_v1','attempt_id':attempt_id,'operation_key':operation}
                write(pointer_path,pointer)
        if ledger is None:
            outcome['native_outcome']={'status':'failed','failure':{'code':rejection or 'requested_job_not_started'}}
        else:
            ledger_path=os.path.join(job_directory,'submission.json')
            if rejection is None and ledger['phase']=='prepared' and tool=='practical.job.start':
                if ledger['operation_key']==operation and pointer['attempt_id']==ledger['attempt_id']:
                    ledger=submit_attempt(ledger,ledger_path,job_directory)
            if ledger['phase']=='submitting':ledger=recover_submission(ledger,ledger_path)
            outcome['facts']['requested_job'],outcome['native_outcome']=job_result(ledger)
            if rejection is not None:outcome['native_outcome']['failure']={'code':rejection}
    else:raise ValueError('practical_operation_not_bound')
    outcome['facts']['paths']=paths()
    if path_observation_failures:outcome['path_observation_failures']=path_observation_failures
    reply={'outcome':outcome,'context_after':after};write(result_path,reply)
print(canonical({'version':'practical_pbs_reply_v1','request_sha256':digest(request),'result':reply}))
'''


def validate_native_blast_database_resource(configuration):
    """Validate declared deployment identities; perform no deployment or I/O."""
    from .native_blast_database_tool_info import native_blast_database_tool_contracts
    from .native_blast_database_contracts import FILE_IDENTITY_SCHEMA
    from .domain import validate_schema
    value = configuration['native_blast_database']
    if (type(value) is not dict or set(value) != {'version', 'producer', 'environment', 'bindings'}
            or value['version'] != 'native_blast_database_resource_v1'
            or type(value['producer']) is not dict or set(value['producer']) != {'module_root', 'manifest'}
            or type(value['environment']) is not dict
            or any(type(k) is not str or not k or type(v) is not str or '\0' in k + v
                for k, v in value['environment'].items())):
        raise ValueError('native_blast_database_resource_invalid')
    validate_schema(value['producer']['manifest'], FILE_IDENTITY_SCHEMA)
    native_blast_database_tool_contracts(value['bindings'], resource_kind='hpc', resource_id='configuration-validation')
    paths = [value['producer']['module_root'], value['producer']['manifest']['path']]
    paths.extend(row['software']['executable'] for row in value['bindings'])
    paths.extend(item['path'] for row in value['bindings'] for item in row['database_manifests'])
    if any(type(path) is not str or not PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts
            or '\0' in path for path in paths):
        raise ValueError('native_blast_database_resource_path_invalid')
    aurora = PurePosixPath('/lus/flare/projects/BioReason-Aurora-Test')
    if PurePosixPath(configuration['workspace']).is_relative_to(aurora):
        if configuration['account'] != 'EpiCalib' or any(not PurePosixPath(path).is_relative_to(aurora)
                for path in [*paths, configuration['python_executable']]):
            raise ValueError('native_blast_database_aurora_storage_or_account_conflict')
    return deepcopy(value)


class PBSPracticalOperations:
    def __init__(self, configuration):
        expected = {'kind', 'workspace', 'ssh_argv', 'python_executable', 'account'}
        if (not isinstance(configuration, dict) or set(configuration) - expected - {'native_blast_database'}
                or not expected <= set(configuration)
                or configuration['kind'] != 'pbs_ssh'):
            raise ValueError('explicit_pbs_practical_configuration_required')
        for field in ('workspace', 'python_executable'):
            value = configuration[field]
            if (not isinstance(value, str) or '\0' in value
                    or not PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts):
                raise ValueError('invalid_pbs_practical_configuration_path')
        if (not isinstance(configuration['ssh_argv'], list) or not configuration['ssh_argv']
                or any(not isinstance(value, str) or not value or '\0' in value
                    for value in configuration['ssh_argv'])
                or not isinstance(configuration['account'], str)
                or re.fullmatch(r'[A-Za-z0-9_.-]+', configuration['account']) is None):
            raise ValueError('invalid_pbs_practical_configuration')
        if 'native_blast_database' in configuration:
            validate_native_blast_database_resource(configuration)
        self.configuration = deepcopy(configuration)

    def validate_assignment(self, assignment):
        assignment = validate_assignment(assignment)
        if 'native_blast_database' in assignment['requested_job']:
            binding = self.configuration.get('native_blast_database')
            if binding is None:
                raise ValueError('native_blast_database_hpc_binding_required')
            job = assignment['requested_job']['native_blast_database']
            selected = [row for row in binding['bindings'] if row['program'] == job['program']]
            if (len(selected) != 1 or selected[0]['software'] != job['software']
                    or any(row['manifest_file'] not in selected[0]['database_manifests'] for row in job['databases'])):
                raise ValueError('native_blast_database_selected_binding_conflict')
            root = PurePosixPath(self.configuration['workspace'])
            paths = [job['software']['executable'], *[row['path'] for row in job['inputs']]]
            for db in job['databases']:
                paths.extend(db['native_paths'])
                paths.append(db['manifest_file']['path'])
                paths.extend(row['path'] for row in db['manifest']['files'])
                manifest = db['manifest']
                paths.extend(row['path'] for row in manifest['metadata_manifests'])
                paths.extend(row['path'] for row in (manifest['preparation']['receipt'],
                    manifest['preparation']['input_manifest'], manifest['access']['offline_configuration']) if row is not None)
            if any(not PurePosixPath(path).is_relative_to(root) for path in paths):
                raise ValueError('native_blast_database_selected_path_outside_workspace')
        return assignment

    def _request(self, assignment, context, **fields):
        assignment = self.validate_assignment(assignment)
        if (assignment['resource_kind'] != 'hpc'
                or not PurePosixPath(assignment['workspace']).is_relative_to(self.configuration['workspace'])):
            raise ValueError('practical_resource_assignment_mismatch')
        validate_context(context, workspace=assignment['workspace'])
        constraints = assignment['constraints']
        allowed_constraints = {'account', 'queue', 'resources', 'allowed_accounts', 'allowed_queues',
            'allocation', 'cpu', 'memory_bytes', 'scratch_bytes', 'wall_seconds'}
        if set(constraints) - allowed_constraints:
            raise ValueError('practical_pbs_constraint_unsupported')
        for name in ('allowed_accounts', 'allowed_queues'):
            if name in constraints:
                values = constraints[name]
                if (not isinstance(values, list)
                        or any(not isinstance(value, str) or not value or '\0' in value for value in values)
                        or len(values) != len(set(values))):
                    raise ValueError('practical_pbs_constraint_list_invalid')
        if 'account' in constraints and constraints['account'] != self.configuration['account']:
            raise ValueError('practical_pbs_account_constraint_conflict')
        if 'allowed_accounts' in constraints and self.configuration['account'] not in constraints['allowed_accounts']:
            raise ValueError('practical_pbs_account_constraint_conflict')
        return {'configuration': self.configuration, 'assignment': assignment,
            'context': context, 'job_driver': _JOB_DRIVER, **fields}

    def _invoke(self, request):
        remote_command = shlex.quote(self.configuration['python_executable']) + ' -B -c ' + shlex.quote(_REMOTE_WORKER)
        completed = subprocess.run([*self.configuration['ssh_argv'], remote_command],
            input=_canonical(request).encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode != 0:
            raise ValueError('practical_pbs_transport_or_remote_operation_failed:'
                + completed.stderr.decode('utf-8', 'replace')[-2048:])
        try:
            reply = json.loads(completed.stdout)
        except (ValueError, UnicodeError) as error:
            raise ValueError('practical_pbs_reply_invalid') from error
        if (not isinstance(reply, dict) or set(reply) != {'version', 'request_sha256', 'result'}
                or reply['version'] != 'practical_pbs_reply_v1'
                or reply['request_sha256'] != _digest(request)
                or not isinstance(reply['result'], dict)
                or set(reply['result']) != {'outcome', 'context_after'}):
            raise ValueError('practical_pbs_reply_identity_conflict')
        result = reply['result']
        validate_outcome(result['outcome'])
        return result['outcome'], result['context_after']

    def initial_outcome(self, assignment):
        request = self._request(assignment, assignment['initial_context'], mode='initial')
        outcome, _ = self._invoke(request)
        return outcome

    def _target_request(self, assignment, execution_id, *, attempt_id, run_id,
                        origin_episode_id, original_operation_key, **fields):
        if (not isinstance(attempt_id, str) or re.fullmatch(r'[a-f0-9]{64}', attempt_id) is None
                or original_operation_key is not None and attempt_id != _digest(original_operation_key)
                or not isinstance(run_id, str) or not run_id
                or not isinstance(origin_episode_id, str) or not origin_episode_id
                or re.fullmatch(r'[0-9]+(?:\.[A-Za-z0-9_.-]+)?', execution_id) is None):
            raise ValueError('practical_pbs_exact_attempt_identity_required')
        return self._request(assignment, assignment['initial_context'],
            execution_id=execution_id, attempt_id=attempt_id, run_id=run_id,
            episode_id=origin_episode_id, original_operation_key=original_operation_key, **fields)

    def observe_execution(self, assignment, execution_id, *, log_window_bytes=8192,
                          log_roles=('stdout', 'stderr'), attempt_id=None, **identity):
        """One qstat for the original persisted attempt; no reconciliation/write."""
        if (type(log_window_bytes) is not int or log_window_bytes <= 0
                or any(role not in {'stdout', 'stderr'} for role in log_roles)):
            raise ValueError('bounded_native_log_window_required')
        request = self._target_request(assignment, execution_id, attempt_id=attempt_id,
            mode='observe_execution', log_window_bytes=log_window_bytes, **identity)
        outcome, _ = self._invoke(request)
        fact, detail = outcome['facts']['requested_job'], outcome['native_outcome']
        terminal = fact['status'] in {'completed', 'failed'}
        outputs, logs = [], []
        for role in ('stdout', 'stderr'):
            log = detail[role]
            outputs.append({'role': role, 'available': log['available'],
                'bytes': log.get('size_bytes'), 'writer_closed': log['available'] and terminal})
            if role in log_roles and log['available']:
                logs.append({'role': role, 'path': log['path'], 'offset': log['offset_bytes'],
                    'observed_size': log['size_bytes'], 'bytes_base64': log['bytes_base64']})
        outputs.extend(detail['observed_outputs'])
        fields, measurements = detail['pbs_fields'], []
        def interval(measure, start, finish):
            if (type(start) in (int, float) and type(finish) in (int, float)
                    and finish >= start):
                measurements.append({'measure': measure, 'seconds': finish-start})
        interval('pbs_queue_wait_seconds', fields.get('qtime'), fields.get('stime'))
        if terminal:
            interval('pbs_total_turnaround_seconds', fields.get('qtime'), fields.get('obittime'))
            exit_receipt = detail.get('exit_receipt')
            if exit_receipt is not None:
                measurements.append({'measure': 'pbs_requested_command_wall_seconds',
                    'seconds': exit_receipt['duration_seconds']})
        available = any(row['available'] for row in detail['observed_outputs'])
        if not detail['observed_outputs']:
            available = fact['status'] == 'completed'
        return {'observed_at': detail['observed_at'], 'state': fact['status'],
            'returncode': fact['returncode'], 'failure_code':
                'native_nonzero_returncode' if fact['status'] == 'failed' else None,
            'result_available': available, 'measurements': measurements, 'outputs': outputs,
            'logs': logs, 'provenance_refs': [], 'native': detail}

    def read_output(self, assignment, execution_id, *, path, offset, limit,
                    attempt_id=None, **identity):
        """Read a selected byte window after qualifying the original ledger."""
        if (not isinstance(path, str) or not PurePosixPath(path).is_absolute()
                or not PurePosixPath(path).is_relative_to(assignment['workspace'])
                or type(offset) is not int or offset < 0 or type(limit) is not int
                or not 1 <= limit <= 1024*1024):
            raise ValueError('bounded_native_output_window_required')
        request = self._target_request(assignment, execution_id, attempt_id=attempt_id,
            mode='read_output', path=path, offset=offset, limit=limit, **identity)
        outcome, _ = self._invoke(request)
        if outcome['native_outcome'].get('read_failure') == 'file_missing':
            raise FileNotFoundError(path)
        return outcome['native_outcome']

    def authenticate_native_blast_database_attempt(self, assignment, execution_id, *, attempt_id=None, **identity):
        """Read the actual original ledger, never a bundle's asserted owner."""
        request = self._target_request(assignment, execution_id, attempt_id=attempt_id,
            mode='native_blast_database_attempt', **identity)
        outcome, _ = self._invoke(request)
        return outcome['native_outcome']

    async def read_inventory(self, path):
        """Explicit caller read of exact catalog bytes; no preparation is run."""
        if (not isinstance(path, str) or not PurePosixPath(path).is_absolute()
                or '..' in PurePosixPath(path).parts
                or not PurePosixPath(path).is_relative_to(self.configuration['workspace'])):
            raise ValueError('practical_inventory_path_outside_workspace')
        request = {'configuration': self.configuration, 'mode': 'read_inventory', 'path': path}
        outcome, _ = await asyncio.to_thread(self._invoke, request)
        try:
            return base64.b64decode(outcome['inventory_bytes_base64'], validate=True)
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError('practical_pbs_inventory_bytes_invalid') from error

    def validate_action(self, assignment, tool_name, arguments):
        """Pure checks, callable before the binding freezes an action intent."""
        self._request(assignment, assignment['initial_context'], mode='validation')
        fields = {'practical.inspect': set(), 'practical.context.set': {'cwd', 'environment'},
            'practical.directory.create': {'path'}, 'practical.file.write': {'path', 'text'},
            'practical.file.read': {'path', 'offset', 'limit'},
            'practical.command.run': {'argv', 'environment'}, 'practical.job.start': {'queue', 'resources'},
            'practical.job.status': set(), 'practical.job.collect': set(),
            'practical.inventory.refresh': {'path'}}
        expected = fields.get(tool_name)
        supplied = set(arguments) if isinstance(arguments, dict) else None
        valid_fields = (expected is not None and supplied == expected)
        if tool_name == 'practical.job.start' and supplied == expected | {'retry_failed_execution_id'}:
            valid_fields = True
        if not valid_fields:
            raise ValueError('invalid_practical_pbs_operation_arguments')
        if 'retry_failed_execution_id' in arguments and (not isinstance(arguments['retry_failed_execution_id'], str)
                or not arguments['retry_failed_execution_id'] or '\0' in arguments['retry_failed_execution_id']):
            raise ValueError('invalid_practical_pbs_retry_identity')
        if 'environment' in arguments:
            validate_context({'revision': 0, 'cwd': assignment['initial_context']['cwd'],
                'environment': arguments['environment']}, workspace=assignment['workspace'])
        if 'argv' in arguments and (not isinstance(arguments['argv'], list) or not arguments['argv']
                or any(not isinstance(value, str) or not value or '\0' in value for value in arguments['argv'])):
            raise ValueError('invalid_practical_pbs_operation_arguments')
        for field in ('path', 'cwd'):
            if field in arguments:
                value = arguments[field]
                if (not isinstance(value, str) or '\0' in value or '..' in PurePosixPath(value).parts
                        or not PurePosixPath(value).is_absolute()
                        or not PurePosixPath(value).is_relative_to(assignment['workspace'])):
                    raise ValueError('practical_write_outside_workspace')
        if 'text' in arguments and not isinstance(arguments['text'], str):
            raise ValueError('invalid_practical_pbs_operation_arguments')
        if tool_name == 'practical.file.read' and (type(arguments['offset']) is not int or arguments['offset'] < 0
                or type(arguments['limit']) is not int or arguments['limit'] < 1):
            raise ValueError('invalid_practical_pbs_byte_window')
        if tool_name == 'practical.job.start':
            if (not isinstance(arguments['queue'], str)
                    or re.fullmatch(r'[A-Za-z0-9_.@-]+', arguments['queue']) is None
                    or not isinstance(arguments['resources'], list) or not arguments['resources']
                    or any(not isinstance(value, str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=[^\s\0]+', value) is None
                        for value in arguments['resources'])):
                raise ValueError('explicit_pbs_queue_and_resources_required')
            constraints = assignment['constraints']
            selection = {'account': self.configuration['account'], 'queue': arguments['queue'],
                'resources': arguments['resources']}
            for name in ('account', 'queue', 'resources'):
                if name in constraints and constraints[name] != selection[name]:
                    raise ValueError('practical_pbs_' + name + '_constraint_conflict')
            if 'allowed_queues' in constraints and arguments['queue'] not in constraints['allowed_queues']:
                raise ValueError('practical_pbs_queue_constraint_conflict')
            allocation = constraints.get('allocation', {})
            if (not isinstance(allocation, dict) or set(allocation) - set(selection)
                    or set(constraints) & {'cpu', 'memory_bytes', 'scratch_bytes', 'wall_seconds'}):
                raise ValueError('practical_pbs_allocation_constraint_unsupported')
            if any(selection[name] != value for name, value in allocation.items()):
                raise ValueError('practical_pbs_allocation_constraint_conflict')

    async def execute(self, state, tool_name, arguments, operation_key):
        self.validate_action(state.assignment, tool_name, arguments)
        request = self._request(state.assignment, state.context(), mode='action', run_id=state.run_id,
            episode_id=state.episode_id, operation_key=operation_key, tool_name=tool_name, arguments=arguments)
        outcome, after = await asyncio.to_thread(self._invoke, request)
        if tool_name == 'practical.inventory.refresh':
            if 'inventory_bytes_base64' not in outcome:
                return outcome, after
            try:
                raw = base64.b64decode(outcome['inventory_bytes_base64'], validate=True)
                catalog = _decode_inventory(raw)
                outcome['inventory_catalog'] = validate_catalog(catalog)
            except (KeyError, ValueError, TypeError, UnicodeError) as error:
                outcome['inventory_failure'] = {'code': 'inventory_catalog_invalid',
                    'exception_type': type(error).__name__}
        return outcome, after


__all__ = ['PBSPracticalOperations']
