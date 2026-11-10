"""General terminal actions with durable command and scheduler observations.

The model authors the shell command. This module supplies transport and factual
custody only; it neither prepares a scientific job nor chooses a next action.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys

from .acquisition import AcquisitionError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


# Executed on the selected resource, inside its existing authenticated transport.
# The command's durable intent is published before any selected shell code runs.
# A missing result after that point means uncertain execution, never permission
# to repeat the shell command (which may already have submitted a native job).
_WORKER = r'''
import base64,datetime,fcntl,hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def publish(path,value):
    descriptor,temporary=tempfile.mkstemp(prefix='.receipt-',dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor,'w') as stream:
            stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
def confined(path,root):
    resolved=os.path.realpath(path)
    if not os.path.isabs(path) or os.path.commonpath([root,resolved])!=root:
        raise ValueError('execution_path_outside_workspace')
    return resolved
def tail(path):
    if not os.path.isfile(path):return {'path':path,'available':False}
    size=os.path.getsize(path);offset=max(0,size-32768)
    with open(path,'rb') as stream:stream.seek(offset);raw=stream.read()
    return {'path':path,'available':True,'bytes':size,'tail_byte_offset':offset,
        'tail_utf8':raw.decode('utf-8','replace'),'bytes_base64':base64.b64encode(raw).decode()}
def paths(assignment):
    selected={};rows=[]
    for item in assignment['progress_requirements']:
        predicate=item['predicate'];kind=predicate['kind']
        if kind in ('path_exists','file_sha256'):selected[predicate['path']]=kind=='file_sha256'
        elif kind=='requested_job_outputs':
            for name in predicate.get('output_paths',[]):selected.setdefault(name,False)
    for name,hash_required in sorted(selected.items()):
        path=confined(name,workspace);file=os.path.isfile(path);exists=os.path.exists(path)
        sha=None
        if file and hash_required:
            hasher=hashlib.sha256()
            with open(path,'rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
            sha=hasher.hexdigest()
        rows.append({'path':name,'exists':exists,'object_type':'file' if file else
            'directory' if os.path.isdir(path) else 'other' if exists else 'missing','sha256':sha})
    return rows
request=json.load(sys.stdin);configuration=request['configuration'];assignment=request['assignment']
workspace=os.path.realpath(request.get('terminal_workspace',assignment['workspace']))
confined(workspace,os.path.realpath(configuration['workspace']))
run_root=os.path.join(workspace,'.episode-execution',digest(request['run_id']))
audit_root=os.path.join(run_root,'scheduler')
if request.get('observation'):
    job_id=request['execution_id']
    job_path=os.path.join(audit_root,'jobs',hashlib.sha256(job_id.encode()).hexdigest()+'.json')
    job=json.load(open(job_path))
    if (job['job_id']!=job_id or job['requested_job_sha256']!=digest(assignment['requested_job'])
            or job['assignment_sha256']!=digest(assignment)):
        raise ValueError('execution_original_job_identity_conflict')
    expected=request.get('expected_actual_job')
    if expected is not None and any(expected.get(key)!=job.get(key) for key in
            ('job_id','argv','environment','script','submission_event','assignment_sha256','requested_job_sha256')):
        raise ValueError('execution_received_job_custody_conflict')
    event_path=confined(job['submission_event'],workspace)
    event=json.load(open(event_path));original=json.load(open(confined(event['command_intent'],workspace)))
    if (event['command']!='qsub' or event['returncode']!=0 or event['native_job']['job_id']!=job_id
            or original['run_id']!=request['run_id'] or original['assignment']!=assignment):
        raise ValueError('execution_original_submission_custody_conflict')
    script=event['script'];script_path=confined(script['path'],workspace)
    if hashlib.sha256(open(script_path,'rb').read()).hexdigest()!=script['sha256']:
        raise ValueError('execution_submitted_script_changed')
    if request['observation']=='allocation_control':
        # This is the existing scientific portfolio's selected unit ordering,
        # authenticated to the actual submitted job. It is not a Launch step.
        argv=assignment['requested_job']['argv']
        if (len(argv)!=5 or argv[2]!=workspace+'/runner.py'
                or argv[3]!=workspace+'/manifest.json'):
            raise ValueError('original_hpc_portfolio_required')
        manifest=json.load(open(confined(argv[3],workspace)))
        # The existing allocation manifest uses its own canonical encoding.
        manifest_sha=hashlib.sha256(json.dumps(manifest,sort_keys=True,
            separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if manifest_sha!=argv[4] or manifest['workspace']!=workspace:
            raise ValueError('allocation_manifest_changed')
        allowed={unit['unit_id'] for unit in manifest['units']};selected=request['unit_ids']
        if (not isinstance(selected,list) or any(not isinstance(item,str) for item in selected)
                or len(set(selected))!=len(selected) or not set(selected)<=allowed):
            raise ValueError('allocation_control_not_in_original_manifest')
        status=json.load(open(confined(workspace+'/allocation-status.json',workspace)))
        if (status['job_id']!=job_id or status['state']!='running'
                or status['plan_id']!=manifest['plan_id'] or status['manifest_sha256']!=manifest_sha):
            raise ValueError('original_allocation_not_running')
        begun={row['unit_id'] for row in status['units']}
        if not allowed-begun<=set(selected):
            raise ValueError('allocation_order_must_retain_all_unstarted_units')
        control={'manifest_sha256':manifest_sha,'unit_ids':selected,
            'operation_key':request['control_operation_key']}
        controls=os.path.join(run_root,'allocation-controls');os.makedirs(controls,exist_ok=True)
        receipt=os.path.join(controls,digest({'job_id':job_id,
            'operation_key':request['control_operation_key']})+'.json')
        if os.path.exists(receipt):
            if json.load(open(receipt))!=control:raise ValueError('allocation_control_identity_conflict')
        else:
            publish(os.path.join(workspace,'allocation-control.json'),control);publish(receipt,control)
        result={'facts':{},'native_outcome':control}
    elif request['observation']=='read_output':
        path=confined(request['path'],workspace)
        try:
            with open(path,'rb') as stream:
                size=os.fstat(stream.fileno()).st_size;stream.seek(request['offset'])
                raw=stream.read(request['limit'])
        except FileNotFoundError:
            result={'facts':{},'native_outcome':{'path':path,'read_failure':'file_missing'}}
        else:
            result={'facts':{},'native_outcome':{'path':path,'offset':request['offset'],
                'returned_bytes':len(raw),'size_bytes':size,'bytes_base64':base64.b64encode(raw).decode(),
                'text_utf8':raw.decode('utf-8','replace')}}
    else:
        completed=subprocess.run(['qstat','-x','-f','-F','json',job_id],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,TZ='UTC'))
        try:record=json.loads(completed.stdout).get('Jobs',{}).get(job_id)
        except (ValueError,AttributeError):record=None
        if record is not None:
            submitted=record.get('Submit_arguments');account=record.get('Account_Name')
            if account is not None and account!=configuration.get('account'):
                raise ValueError('execution_observed_account_conflict')
            if submitted is not None:
                import shlex
                if shlex.split(submitted)!=event['actual_argv'][1:]:
                    raise ValueError('execution_observed_submission_arguments_conflict')
        state=record.get('job_state') if record else None
        code=int(record['Exit_status']) if record and state in ('F','C') and 'Exit_status' in record else None
        status='completed' if code==0 else 'failed' if code is not None else 'running' if state=='R' else 'submitted' if state in ('Q','H','W','S','T') else 'unknown'
        requested_paths={path for requirement in assignment['progress_requirements']
            if requirement['predicate']['kind']=='requested_job_outputs'
            for path in requirement['predicate'].get('output_paths',[])}
        outputs=[];logs=[];log_failures=[];terminal=status in ('completed','failed')
        for name in sorted(requested_paths):
            path=confined(name,workspace);available=os.path.isfile(path)
            outputs.append({'role':'requested_output:'+name,'available':available,
                'bytes':os.path.getsize(path) if available else None,'writer_closed':terminal and available})
        for role in request.get('log_roles',[]):
            name=(record or {}).get('Output_Path' if role=='stdout' else 'Error_Path')
            if not isinstance(name,str):continue
            path=name.split(':',1)[1] if ':' in name else name
            try:path=confined(path,workspace)
            except ValueError:
                log_failures.append({'role':role,'path':name,'code':'execution_log_outside_workspace'});continue
            available=os.path.isfile(path);size=os.path.getsize(path) if available else None
            outputs.append({'role':role,'available':available,'bytes':size,'writer_closed':terminal and available})
            if available:
                offset=max(0,size-request['log_window_bytes'])
                with open(path,'rb') as stream:stream.seek(offset);raw=stream.read(request['log_window_bytes'])
                logs.append({'role':role,'path':path,'offset':offset,'observed_size':size,
                    'bytes_base64':base64.b64encode(raw).decode()})
        result={'facts':{},'native_outcome':{'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'execution_id':job_id,'status':status,'returncode':code,'pbs_fields':record or {},
            'qstat':{'argv':['qstat','-x','-f','-F','json',job_id],'returncode':completed.returncode,
                'stdout':completed.stdout.decode('utf-8','replace'),'stderr':completed.stderr.decode('utf-8','replace')},
            'submitted_script':script,'original_submission_event':event_path,
            'observed_outputs':outputs,'logs':logs,'log_failures':log_failures,
            'result_available':any(row['available'] for row in outputs
                if row['role'].startswith('requested_output:'))}}
    print(canonical(result));sys.exit(0)
arguments=request['arguments'];cwd=confined(arguments['workdir'],os.path.realpath(configuration['workspace']))
owner=digest({'run_id':request['run_id'],'episode_id':request['episode_id']})
owner_root=os.path.join(workspace,'.episode-execution',owner)
root=os.path.join(owner_root,'commands',digest(request['operation_key']))
os.makedirs(root,exist_ok=True)
with open(os.path.join(root,'lock'),'a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    intent=os.path.join(root,'intent.json');result_path=os.path.join(root,'result.json')
    if os.path.isfile(result_path):
        if json.load(open(intent))!=request:raise ValueError('execution_command_identity_conflict')
        print(canonical(json.load(open(result_path))));sys.exit(0)
    if os.path.isfile(intent):
        if json.load(open(intent))!=request:raise ValueError('execution_command_identity_conflict')
        result={'facts':{},'native_outcome':{'failure':{
            'code':'execution_command_outcome_unknown_no_reexecution','intent_path':intent},
            'stdout':tail(os.path.join(root,'stdout')),'stderr':tail(os.path.join(root,'stderr'))}}
        print(canonical(result));sys.exit(0)
    publish(intent,request)
    environment=dict(os.environ);environment.update(arguments['env'])
    for name in ('tmp','cache'):os.makedirs(os.path.join(root,name),exist_ok=True)
    defaults={'TMPDIR':os.path.join(root,'tmp'),'TMP':os.path.join(root,'tmp'),
        'TEMP':os.path.join(root,'tmp'),'XDG_CACHE_HOME':os.path.join(root,'cache'),
        'PIP_CACHE_DIR':os.path.join(root,'cache','pip')}
    for name,value in defaults.items():
        selected=arguments['env'].get(name,value)
        environment[name]=confined(selected,workspace)
    environment['PYTHONDONTWRITEBYTECODE']='1'
    environment['EPISODE_COMMAND_INTENT']=intent
    def snapshot(selected,phase):
        rows=[]
        destination=os.path.join(root,'artifacts',phase);os.makedirs(destination,exist_ok=True)
        for name in selected:
            path=confined(name,workspace) if phase=='outputs' else os.path.realpath(name)
            if not os.path.isfile(path):
                rows.append({'path':name,'phase':phase,'available':False,'captured_path':None,
                    'sha256':None,'size_bytes':None,'source_stable_during_read':False})
                continue
            saved=os.path.join(destination,hashlib.sha256(name.encode()).hexdigest())
            hasher=hashlib.sha256();size=0
            with open(path,'rb') as source,open(saved,'xb') as target:
                before=os.fstat(source.fileno())
                for block in iter(lambda:source.read(1024*1024),b''):
                    target.write(block);hasher.update(block);size+=len(block)
                target.flush();os.fsync(target.fileno());after=os.fstat(source.fileno())
            stable=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(
                after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
            rows.append({'path':name,'phase':phase,'available':True,'captured_path':saved,
                'sha256':hasher.hexdigest(),'size_bytes':size,'source_stable_during_read':stable})
        return rows
    artifacts=request.get('artifact_paths',{'inputs':[],'outputs':[]})
    inputs=snapshot(artifacts['inputs'],'inputs')
    scheduler=configuration.get('scheduler')
    if scheduler:
        if scheduler.get('kind')!='pbs':raise ValueError('execution_scheduler_adapter_unavailable')
        os.makedirs(audit_root,exist_ok=True)
        shim_dir=os.path.join(root,'bin');os.makedirs(shim_dir,exist_ok=True)
        for command in ('qsub','qstat'):
            executable=shutil.which(command,path=environment.get('PATH'))
            if executable:
                path=os.path.join(shim_dir,command)
                with open(path,'w') as stream:
                    stream.write('#!'+sys.executable+'\n'+request['scheduler_shim'])
                os.chmod(path,0o700)
                environment['EPISODE_NATIVE_'+command.upper()]=executable
        environment.update({'EPISODE_SCHEDULER_AUDIT':audit_root,
            'EPISODE_COMMAND_INTENT':intent,'EPISODE_ASSIGNMENT_SHA256':digest(assignment),
            'EPISODE_REQUESTED_JOB_SHA256':digest(assignment['requested_job']),
            'EPISODE_WORKSPACE':workspace,'EPISODE_ACCOUNT':configuration.get('account',''),
            'PATH':shim_dir+os.pathsep+environment.get('PATH','')})
    stdout=os.path.join(root,'stdout');stderr=os.path.join(root,'stderr')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    failure=None;returncode=None
    selected_argv=arguments['cmd'] if isinstance(arguments['cmd'],list) else ['/bin/bash','-c',arguments['cmd']]
    try:
        with open(stdout,'wb') as out,open(stderr,'wb') as err:
            completed=subprocess.run(selected_argv,cwd=cwd,env=environment,
                stdout=out,stderr=err)
        returncode=completed.returncode
    except OSError as error:failure={'code':'execution_command_failed','exception_type':type(error).__name__}
    command={'argv':selected_argv,'environment':arguments['env'],
        'returncode':returncode,'execution_id':intent}
    events=[]
    if scheduler:
        for path in pathlib.Path(audit_root).glob('events/*/result.json'):
            event=json.load(open(path))
            if event['command_intent']==intent:events.append(event)
        events.sort(key=lambda event:event['started_at'])
    facts={'command':command,'paths':[] if request.get('terminal_workspace') else paths(assignment)}
    detail={'execution_command':{'cmd':arguments['cmd'],'workdir':arguments['workdir'],
        'actual_workdir':cwd,'env':arguments['env'],'target':arguments.get('target','resource'),
        'command_sha256':digest({key:arguments[key] for key in ('cmd','workdir','env')}),
        'intent_path':intent,'returncode':returncode,
        'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},
        'stdout':tail(stdout),'stderr':tail(stderr),'scheduler_events':events,
        'input_snapshots':inputs,'output_snapshots':snapshot(artifacts['outputs'],'outputs')}
    if failure:detail['failure']=failure
    # A native job is reported only when an actual scheduler event identifies it.
    # A shell command finishing does not establish that a scientific job ran.
    observed=[event for event in events if event.get('native_job') is not None]
    if observed:
        actual=observed[-1]['native_job'];detail['actual_job']=actual
        facts['requested_job']={'argv':actual['argv'],'environment':actual['environment'],
            'returncode':actual['returncode'],'execution_id':actual['job_id'],
            'requested_job_sha256':actual['requested_job_sha256'],'resource_kind':'hpc',
            'status':actual['status'],'output_paths':[row['path'] for row in facts['paths']
                if row['exists'] and row['object_type']=='file'],
            'handoff':{'execution_id':actual['job_id'],'monitor_operation':'exec_command',
                'results_operation':'exec_command'}}
    result={'facts':facts,'native_outcome':detail};publish(result_path,result)
    print(canonical(result))
'''


# Standard scheduler commands keep their ordinary CLI. These adapters record the
# command the agent actually selected, script bytes actually submitted, and the
# scheduler reply. They do not submit, inspect, or retry anything independently.
_PBS_SHIM = r'''
import datetime,hashlib,json,os,pathlib,re,shlex,shutil,subprocess,sys,tempfile,uuid
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def publish(path,value):
    descriptor,temporary=tempfile.mkstemp(prefix='.scheduler-',dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor,'w') as stream:
            stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
name=os.path.basename(sys.argv[0]);real=os.environ['EPISODE_NATIVE_'+name.upper()]
root=os.environ['EPISODE_SCHEDULER_AUDIT'];event_root=os.path.join(root,'events',uuid.uuid4().hex)
os.makedirs(event_root);argv=[real,*sys.argv[1:]]
event={'version':'native_scheduler_command_v1','command':name,'selected_argv':sys.argv[1:],
    'actual_argv':argv,'cwd':os.getcwd(),'command_intent':os.environ['EPISODE_COMMAND_INTENT'],
    'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script':None,
    'native_job':None}
input_data=None;rejection=None
if name=='qsub':
    # qsub accepts either a script file or script bytes on stdin. Submit the
    # captured immutable bytes so the receipt names the actual script version.
    script=sys.argv[-1] if len(sys.argv)>1 and os.path.isfile(sys.argv[-1]) else None
    raw=open(script,'rb').read() if script else sys.stdin.buffer.read()
    script_path=os.path.join(event_root,os.path.basename(script) if script else 'stdin.pbs')
    with open(script_path,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    event['script']={'path':script_path,'original_path':os.path.abspath(script) if script else None,
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if script:argv[-1]=script_path
    else:input_data=raw
    event['actual_argv']=argv
    original=json.load(open(event['command_intent']))
    constraints=original['assignment']['constraints'];configuration=original['configuration']
    options={};resources={}
    def read_options(tokens):
        index=0
        while index<len(tokens):
            token=tokens[index]
            if len(token)>1 and token[:2] in ('-A','-q','-l'):
                flag=token[:2];value=token[2:]
                if not value:
                    index+=1
                    if index>=len(tokens):raise ValueError('scheduler_option_value_missing')
                    value=tokens[index]
                if flag=='-l':
                    for part in value.split(','):
                        key,separator,item=part.partition('=')
                        if not separator:raise ValueError('scheduler_resource_option_invalid')
                        resources[key]=item
                else:options[flag]=value
            index+=1
    try:
        for line in raw.decode('utf-8').splitlines():
            if line.startswith('#PBS '):read_options(shlex.split(line[5:]))
        read_options(sys.argv[1:])
        if options.get('-A')!=configuration.get('account'):
            raise ValueError('scheduler_account_constraint_conflict')
        if 'queue' in constraints and options.get('-q')!=constraints['queue']:
            raise ValueError('scheduler_queue_constraint_conflict')
        if 'allowed_queues' in constraints and options.get('-q') not in constraints['allowed_queues']:
            raise ValueError('scheduler_queue_constraint_conflict')
        required=dict(item.split('=',1) for item in configuration.get('scheduler',{}).get('required_resources',[]))
        required.update(dict(item.split('=',1) for item in constraints.get('resources',[])))
        if any(resources.get(key)!=value for key,value in required.items()):
            raise ValueError('scheduler_allocation_constraint_conflict')
    except (ValueError,UnicodeError) as error:rejection=str(error)
publish(os.path.join(event_root,'intent.json'),event)
if rejection:
    event['submission_rejection']=rejection
    completed=subprocess.CompletedProcess(argv,2,b'',(rejection+'\n').encode())
else:completed=subprocess.run(argv,input=input_data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
event.update({'returncode':completed.returncode,'stdout':completed.stdout.decode('utf-8','replace'),
    'stderr':completed.stderr.decode('utf-8','replace'),
    'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
jobs=os.path.join(root,'jobs');os.makedirs(jobs,exist_ok=True)
if name=='qsub' and completed.returncode==0:
    reply=event['stdout'].strip()
    if re.fullmatch(r'[0-9]+(?:\[[^\]]*\])?(?:\.[A-Za-z0-9_.-]+)?',reply):
        job={'job_id':reply,'argv':argv,'environment':{},'returncode':None,'status':'submitted',
            'requested_job_sha256':os.environ['EPISODE_REQUESTED_JOB_SHA256'],
            'assignment_sha256':os.environ['EPISODE_ASSIGNMENT_SHA256'],
            'submission_event':os.path.join(event_root,'result.json'),'script':event['script']}
        publish(os.path.join(jobs,hashlib.sha256(reply.encode()).hexdigest()+'.json'),job)
        event['native_job']=job
elif name=='qstat' and completed.returncode==0:
    try:records=json.loads(event['stdout']).get('Jobs',{})
    except (ValueError,AttributeError):records={}
    observations=[]
    for job_id,record in records.items():
        path=os.path.join(jobs,hashlib.sha256(job_id.encode()).hexdigest()+'.json')
        if not os.path.isfile(path):continue
        job=json.load(open(path));state=record.get('job_state')
        job['returncode']=int(record['Exit_status']) if state in ('F','C') and 'Exit_status' in record else None
        job['status']=('failed' if job['returncode']!=0 else 'completed') if job['returncode'] is not None else 'running' if state=='R' else 'submitted' if state in ('Q','H','W','S','T') else 'unknown'
        job['scheduler_record']=record;job['observation_event']=os.path.join(event_root,'result.json')
        publish(path,job);observations.append(job)
    event['native_jobs']=observations
    if len(observations)==1:event['native_job']=observations[0]
publish(os.path.join(event_root,'result.json'),event)
sys.stdout.buffer.write(completed.stdout);sys.stderr.buffer.write(completed.stderr)
sys.exit(completed.returncode)
'''


class TerminalExecution:
    """One selected general shell command, through a configured transport."""

    def __init__(self, configuration, *, coordinator_workspace=None, artifact_selector=None):
        self.configuration = json.loads(canonical(configuration))
        self.coordinator_workspace = (None if coordinator_workspace is None
            else str(Path(coordinator_workspace).resolve()))
        self._validate_configuration()
        if artifact_selector is not None and not callable(artifact_selector):
            raise TypeError('execution_artifact_selector_must_be_callable')
        self.artifact_selector=artifact_selector

    def _validate_configuration(self):
        configuration=self.configuration
        if configuration.get('kind') not in {'local','pbs_ssh'}:
            raise ValueError('execution_resource_kind_invalid')
        workspace=configuration.get('workspace')
        if (not isinstance(workspace,str) or not PurePosixPath(workspace).is_absolute()
                or '..' in PurePosixPath(workspace).parts or '\x00' in workspace):
            raise ValueError('execution_resource_workspace_invalid')
        for key in ('launch_prompt_entry','launch_prompt_sections'):
            if key=='launch_prompt_entry' and key in configuration and (
                    not isinstance(configuration[key],str) or not configuration[key]):
                raise ValueError('execution_resource_prompt_invalid')
            if key=='launch_prompt_sections' and key in configuration and (
                    not isinstance(configuration[key],list) or not configuration[key]
                    or any(not isinstance(value,str) or not value for value in configuration[key])
                    or len(set(configuration[key]))!=len(configuration[key])):
                raise ValueError('execution_resource_prompt_sections_invalid')
        if configuration['kind']=='local':
            from .practical_execution_operations import LocalPracticalOperations
            # Reuse existing scientific binding/policy qualification, not its
            # removed operation dispatcher or host-authored job preparation.
            LocalPracticalOperations({key:value for key,value in configuration.items()
                if key not in {'launch_prompt_entry','launch_prompt_sections','scheduler'}})
        else:
            expected={'kind','workspace','ssh_argv','python_executable','account','scheduler'}
            allowed=expected|{'native_blast_database','native_blast_standard_database',
                'launch_prompt_entry','launch_prompt_sections'}
            if not expected<=set(configuration) or set(configuration)-allowed:
                raise ValueError('explicit_execution_transport_configuration_required')
            command=configuration['ssh_argv']
            if (not isinstance(command,list) or not command
                    or any(not isinstance(value,str) or not value or '\x00' in value for value in command)
                    or not isinstance(configuration['python_executable'],str)
                    or not PurePosixPath(configuration['python_executable']).is_absolute()
                    or not isinstance(configuration['account'],str)
                    or re.fullmatch(r'[A-Za-z0-9_.-]+',configuration['account']) is None):
                raise ValueError('execution_transport_configuration_invalid')
            scheduler=configuration['scheduler']
            if (not isinstance(scheduler,dict) or scheduler.get('kind')!='pbs'
                    or set(scheduler)-{'kind','required_resources'}
                    or not isinstance(scheduler.get('required_resources',[]),list)
                    or any(not isinstance(value,str) or '=' not in value or '\x00' in value
                        for value in scheduler.get('required_resources',[]))):
                raise ValueError('execution_scheduler_configuration_invalid')
            from .native_database_terminal_custody import validate_native_database_resource, PROFILES
            for key in PROFILES:
                if key in configuration:
                    validate_native_database_resource(configuration,key)

    def validate_assignment(self, assignment):
        workspace = PurePosixPath(assignment['workspace'])
        if not workspace.is_absolute() or not workspace.is_relative_to(self.configuration['workspace']):
            raise ValueError('execution_workspace_configuration_conflict')
        if self.configuration['kind']=='local':
            from .practical_execution_operations import LocalPracticalOperations
            LocalPracticalOperations({key:value for key,value in self.configuration.items()
                if key not in {'launch_prompt_entry','launch_prompt_sections','scheduler'}}).validate_assignment(assignment)
        else:
            from .native_database_terminal_custody import validate_native_database_assignment
            validate_native_database_assignment(self.configuration,assignment)
            constraints=assignment['constraints']
            if constraints.get('account',self.configuration['account'])!=self.configuration['account']:
                raise ValueError('execution_account_constraint_conflict')
            if 'allowed_accounts' in constraints and self.configuration['account'] not in constraints['allowed_accounts']:
                raise ValueError('execution_account_constraint_conflict')
            if set(constraints)-{'account','queue','resources','allowed_accounts','allowed_queues','allocation'}:
                raise ValueError('execution_scheduler_constraint_unsupported')
            allocation=constraints.get('allocation',{})
            if not isinstance(allocation,dict) or set(allocation)-{'account','queue','resources'}:
                raise ValueError('execution_scheduler_allocation_invalid')
            if any(constraints.get(name,self.configuration.get(name))!=value for name,value in allocation.items()):
                raise ValueError('execution_scheduler_allocation_constraint_conflict')
        return assignment

    def validate_action(self, assignment, tool_name, arguments):
        self.validate_assignment(assignment)
        if tool_name != 'exec_command':
            raise ValueError('execution_tool_not_available')
        if set(arguments)-{'cmd','workdir','env','target'} or not {'cmd','workdir','env'}<=set(arguments):
            raise ValueError('invalid_exec_command_arguments')
        target=arguments.get('target','resource')
        if target not in {'resource','coordinator'} or target=='coordinator' and self.coordinator_workspace is None:
            raise ValueError('execution_terminal_target_unavailable')
        command=arguments['cmd']
        if not (isinstance(command,str) and command.strip() and '\x00' not in command
                or isinstance(command,list) and command and all(isinstance(value,str) and value
                    and '\x00' not in value for value in command)):
            raise ValueError('invalid_exec_command_text')
        path = PurePosixPath(arguments['workdir'])
        root=self.coordinator_workspace if target=='coordinator' else self.configuration['workspace']
        if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(root):
            raise ValueError('execution_workdir_outside_workspace')
        if not isinstance(arguments['env'], dict) or any(not isinstance(key,str) or not key or
                '=' in key or '\x00' in key or not isinstance(value,str) or '\x00' in value
                for key,value in arguments['env'].items()):
            raise ValueError('invalid_exec_command_environment')

    def initial_outcome(self, assignment, **_):
        self.validate_assignment(assignment)
        # Reading instructions or choosing a resource is not a native observation.
        return {'facts': {}}

    async def execute(self, state, tool_name, arguments, operation_key):
        self.validate_action(state.assignment, tool_name, arguments)
        request = {'configuration':self.configuration,'assignment':state.assignment,
            'arguments':arguments,'run_id':state.run_id,'episode_id':state.episode_id,
            'operation_key':operation_key,'scheduler_shim':_PBS_SHIM}
        if arguments.get('target')=='coordinator':
            request['configuration']={'kind':'local','workspace':self.coordinator_workspace}
            request['terminal_workspace']=self.coordinator_workspace
        elif self.artifact_selector is not None:
            artifacts=self.artifact_selector(state.assignment,arguments)
            if (not isinstance(artifacts,dict) or set(artifacts)!={'inputs','outputs'}
                    or any(not isinstance(values,list) or any(not isinstance(path,str)
                        or not PurePosixPath(path).is_absolute() for path in values)
                        for values in artifacts.values())):
                raise ValueError('execution_artifact_paths_invalid')
            request['artifact_paths']=artifacts
        return await asyncio.to_thread(self._invoke,request),None

    def _invoke(self,request):
        configuration=request['configuration']
        if configuration['kind']=='local':
            command=[sys.executable,'-B','-c',_WORKER]
        else:
            command=[*configuration['ssh_argv'],shlex.quote(configuration['python_executable'])+
                ' -B -c '+shlex.quote(_WORKER)]
        try:
            from .workflow_budget import active_budget
            active_budget()
            if configuration['kind']=='local':
                from . import native_lifecycle as native
                from .local_jobs import LocalJobPolicy
                from .practical_execution_state import _immutable
                policy=(LocalJobPolicy(**self.configuration['policy']) if self.configuration['kind']=='local'
                    else LocalJobPolicy.from_config())
                transport_root=Path(self.coordinator_workspace or configuration['workspace'])/'terminal-transports'/digest(request)
                transport_root.mkdir(parents=True,exist_ok=True)
                input_path=transport_root/'request.json';_immutable(input_path,request)
                handle=native.NativeJobHandle(transport_root/'native.json')
                if not handle.path.exists():
                    native.prepare_job(command,cwd=transport_root,policy=policy,handle_path=handle.path,
                        stdin_path=input_path,stdout_path=transport_root/'stdout',
                        stderr_path=transport_root/'stderr',cpu_threads=1,
                        env={'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(transport_root),
                            'XDG_CACHE_HOME':str(transport_root/'cache')})
                if handle.read()['stage']=='prepared':native.start_prepared(handle)
                try:result=native.wait_job(handle)
                finally:
                    if native.status(handle)['quiescent']:native.release(handle)
                completed=subprocess.CompletedProcess(command,result.returncode,
                    result.stdout_path.read_bytes(),result.stderr_path.read_bytes())
            else:
                completed=subprocess.run(command,input=canonical(request).encode(),
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        except (OSError,ValueError,AcquisitionError) as error:
            return {'facts':{},'native_outcome':{'failure':{'code':'execution_transport_failed',
                'exception_type':type(error).__name__,'detail':str(error)}}}
        if completed.returncode:
            return {'facts':{},'native_outcome':{'failure':{'code':'execution_transport_or_worker_failed',
                'returncode':completed.returncode,'stderr':completed.stderr.decode('utf-8','replace')}}}
        try:
            outcome=json.loads(completed.stdout)
            if configuration['kind']=='local':
                outcome.setdefault('native_outcome',{})['transport_native_handle']=str(handle.path)
                outcome['native_outcome']['transport_policy']=policy.to_dict()
            return outcome
        except (ValueError,UnicodeError):
            return {'facts':{},'native_outcome':{'failure':{'code':'execution_reply_invalid',
                'stdout':completed.stdout.decode('utf-8','replace'),
                'stderr':completed.stderr.decode('utf-8','replace')}}}

    def _observation_request(self,assignment,execution_id,*,run_id,episode_id=None,
                             origin_episode_id=None,resource_id=None,attempt_id=None,
                             original_operation_key=None,requested_job_sha256=None,
                             actual_job=None,**fields):
        self.validate_assignment(assignment)
        if resource_id is not None and assignment.get('resource_id')!=resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if requested_job_sha256 is not None and requested_job_sha256!=digest(assignment['requested_job']):
            raise ValueError('execution_requested_job_identity_conflict')
        return {'configuration':self.configuration,'assignment':assignment,'execution_id':execution_id,
            'run_id':run_id,'episode_id':episode_id or origin_episode_id,
            'expected_actual_job':actual_job,**fields}

    def observe_execution(self,assignment,execution_id,*,log_window_bytes=8192,
                          log_roles=('stdout','stderr'),**identity):
        """Infrastructure for a selected original monitor action; one observation."""
        result=self._invoke(self._observation_request(assignment,execution_id,
            observation='observe_execution',log_window_bytes=log_window_bytes,
            log_roles=list(log_roles),**identity))
        detail=result.get('native_outcome',{})
        if 'failure' in detail:raise ValueError(canonical(detail['failure']))
        status=detail['status'];terminal=status in {'completed','failed'}
        outputs=detail['observed_outputs']
        fields=detail['pbs_fields'];measurements=[]
        for name,start,finish in (('pbs_queue_wait_seconds','qtime','stime'),
                ('pbs_total_turnaround_seconds','qtime','obittime')):
            if type(fields.get(start)) in (int,float) and type(fields.get(finish)) in (int,float):
                measurements.append({'measure':name,'seconds':fields[finish]-fields[start]})
        return {'observed_at':detail['observed_at'],'state':status,'returncode':detail['returncode'],
            'failure_code':'native_nonzero_returncode' if status=='failed' else None,
            'result_available':detail['result_available'],
            'measurements':measurements,'outputs':outputs,'logs':detail['logs'],'provenance_refs':[],'native':detail}

    def read_output(self,assignment,execution_id,*,path,offset,limit,**identity):
        """Read original job output for a selected result/monitor action."""
        selected=PurePosixPath(path)
        if (not selected.is_absolute() or '..' in selected.parts
                or not selected.is_relative_to(assignment['workspace'])
                or type(offset) is not int or offset<0 or type(limit) is not int or limit<1):
            raise ValueError('invalid_execution_output_window')
        result=self._invoke(self._observation_request(assignment,execution_id,
            observation='read_output',path=path,offset=offset,limit=limit,**identity))
        detail=result.get('native_outcome',{})
        if detail.get('read_failure')=='file_missing':raise FileNotFoundError(path)
        if 'failure' in detail:
            if 'FileNotFoundError' in str(detail['failure']):raise FileNotFoundError(path)
            raise ValueError(canonical(detail['failure']))
        return detail

    def write_allocation_control(self,assignment,execution_id,*,unit_ids,operation_key,**identity):
        """Apply selected original-unit ordering with actual job custody.

        The existing HPC parent chooses the scientific units. This host helper
        authenticates that choice and writes its original allocation control;
        it is never an operation in the execution agent's tool catalog.
        """
        if not isinstance(operation_key,str) or not operation_key:
            raise ValueError('allocation_control_operation_identity_required')
        result=self._invoke(self._observation_request(assignment,execution_id,
            observation='allocation_control',unit_ids=unit_ids,
            control_operation_key=operation_key,**identity))
        detail=result.get('native_outcome',{})
        if 'failure' in detail:raise ValueError(canonical(detail['failure']))
        return detail
