"""The route of ``job_access`` to a remote resource with a PBS scheduler, through the configured transport.

``PbsSshRoute`` is one resource of the ``JobAccess`` service (``episode_runtime/job_access.py``, which states the
route protocol). Every request is one run of a small Python program (``REMOTE``) on the resource: the configured
transport prefix (``ssh_argv``: the existing authenticated connection; this module opens, renews and repairs
none) followed by one shell command, with the request as JSON on standard input and the reply as JSON on standard
output. A request that cannot be made or that the resource refuses raises ``RouteRequestError``.

A job is ``{'mode', 'script', 'arguments', 'env'}``:

- ``mode: 'batch'``: ``script`` is submitted with ``qsub`` (with ``arguments``; ``env`` is exported with ``-v``)
  from the job's directory; its state is asked with ``qstat -x -f -F json``, it is cancelled with ``qdel``;
- ``mode: 'login'``: ``script`` runs as a detached shell process on the node the transport reaches (a command
  whose result a unit waits for: a queue listing, a file inspection); ``arguments`` must be empty.

The job's directory is ``<workspace>/<handle>`` on the resource. The handle comes from the launching unit's
operation key, so a unit that runs again names the same directory, and ``submit`` returns the recorded submission
instead of submitting again (``adopted``). A submission that began and left no record is looked for by the name
it carries (``qselect -x -N <name>``; the process table for a login command); when it cannot be found its outcome
is unknown and the request fails with ``submission_outcome_unknown``: nothing is submitted a second time on a
guess. Result files are the regular files the job left in its directory, control files apart.
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import PurePosixPath
import shlex
import subprocess

from episode_runtime.job_access import RouteRequestError

CONFIGURATION = ('ssh_argv', 'python_executable', 'workspace', 'scheduler', 'poll_seconds')
SCHEDULER = ('qsub', 'qstat', 'qdel', 'qselect')
MODES = ('batch', 'login')
ENDED = ('finished', 'failed', 'cancelled')
MEDIA_TYPES = {'.json': 'application/json', '.log': 'text/plain', '.txt': 'text/plain'}

# Runs on the resource. Standard library only; one request per process.
REMOTE = r'''
import base64,datetime,json,os,signal,subprocess,sys
CONTROL={'submission.json','submitting','inputs.json','cancelled','exit_code','exit_code.writing','job.pbs','job.sh'}
QUEUED,RUNNING,ENDED=set('QHWTS'),set('REB'),set('FX')
class Refused(Exception):
    def __init__(self,code,detail=None):self.code,self.detail=code,detail
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def publish(path,value):
    with open(path+'.writing','w') as stream:
        json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
    os.replace(path+'.writing',path)
def scheduler(argv,cwd=None):
    try:done=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except FileNotFoundError:raise Refused('scheduler_command_unavailable',{'command':argv[0]})
    if done.returncode:
        raise Refused('scheduler_command_failed',{'command':argv,'returncode':done.returncode,
            'stderr':done.stderr.decode('utf-8','replace')})
    return done.stdout.decode('utf-8','replace')
def confined(directory,name):
    path=os.path.realpath(os.path.join(directory,name))
    if not name or os.path.commonpath([directory,path])!=directory or path==directory:
        raise Refused('file_name_outside_the_job_directory',{'name':name})
    return path
def running(handle):
    for entry in os.listdir('/proc'):
        if entry.isdigit() and int(entry)!=os.getpid():
            try:
                words=open('/proc/'+entry+'/cmdline','rb').read().split(b'\0')
            except OSError:continue
            if handle.encode() in words:return int(entry)
    return None
def submission(directory):
    path=os.path.join(directory,'submission.json')
    if not os.path.exists(path):raise Refused('job_not_found',{'directory':directory})
    return json.load(open(path))
def submit(request,directory):
    handle,job,commands=request['handle'],request['job'],request['scheduler']
    name='ep'+handle[-13:]
    os.makedirs(directory,exist_ok=True)
    recorded=os.path.join(directory,'submission.json')
    if os.path.exists(recorded):return {'submission':json.load(open(recorded)),'adopted':True}
    began=os.path.exists(os.path.join(directory,'submitting'))
    found=None
    if began and job['mode']=='batch':
        listed=scheduler([commands['qselect'],'-x','-N',name]).split()
        if not listed:raise Refused('submission_outcome_unknown',{'name':name})
        found={'mode':'batch','name':name,'job_id':listed[0],'submitted_at':now()}
    elif began:
        pid=running(handle)
        if pid is None:raise Refused('submission_outcome_unknown',{'name':handle})
        found={'mode':'login','name':name,'pid':pid,'submitted_at':now()}
    if found is None:
        for item,encoded in request['files'].items():
            path=confined(directory,item);os.makedirs(os.path.dirname(path),exist_ok=True)
            with open(path,'wb') as stream:stream.write(base64.b64decode(encoded))
        publish(os.path.join(directory,'inputs.json'),sorted(request['files']))
        script=os.path.join(directory,'job.pbs' if job['mode']=='batch' else 'job.sh')
        with open(script,'w') as stream:stream.write(job['script'])
        open(os.path.join(directory,'submitting'),'w').close()
        if job['mode']=='batch':
            exported=['-v',','.join(key+'='+value for key,value in sorted(job['env'].items()))] if job['env'] else []
            reply=scheduler([commands['qsub'],'-N',name,'-o',os.path.join(directory,'stdout.log'),
                '-e',os.path.join(directory,'stderr.log'),*exported,*job['arguments'],script],cwd=directory)
            found={'mode':'batch','name':name,'job_id':reply.strip(),'submitted_at':now()}
        else:
            wrapper=('sh job.sh > stdout.log 2> stderr.log; echo $? > exit_code.writing; '
                     'mv exit_code.writing exit_code')
            child=subprocess.Popen(['sh','-c',wrapper,handle],cwd=directory,env={**os.environ,**job['env']},
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                start_new_session=True)
            found={'mode':'login','name':name,'pid':child.pid,'submitted_at':now()}
    publish(recorded,found)
    return {'submission':found,'adopted':began}
def state(request,directory):
    made=submission(directory)
    cancelled=os.path.exists(os.path.join(directory,'cancelled'))
    if made['mode']=='batch':
        listing=json.loads(scheduler([request['scheduler']['qstat'],'-x','-f','-F','json',made['job_id']]))
        fields=listing['Jobs'][made['job_id']]
        letter=fields['job_state']
        if letter in ENDED:
            value='cancelled' if cancelled else 'finished' if fields.get('Exit_status')==0 else 'failed'
        elif letter in RUNNING:value='running'
        elif letter in QUEUED:value='queued'
        else:value='unknown'
        return {'state':value,'observed_at':now(),'native':fields}
    code=os.path.join(directory,'exit_code')
    if os.path.exists(code):
        returncode=int(open(code).read().strip())
        return {'state':'finished' if returncode==0 else 'failed','observed_at':now(),
            'native':{'pid':made['pid'],'returncode':returncode}}
    alive=running(request['handle']) is not None
    value='running' if alive else 'cancelled' if cancelled else 'unknown'
    return {'state':value,'observed_at':now(),'native':{'pid':made['pid'],'returncode':None}}
def results(request,directory):
    seen=state(request,directory)
    if seen['state'] not in ('finished','failed','cancelled'):
        raise Refused('results_not_available',{'state':seen['state']})
    staged=set(json.load(open(os.path.join(directory,'inputs.json'))))|CONTROL
    found=[]
    for root,_,names in os.walk(directory):
        for item in names:
            path=os.path.join(root,item);name=os.path.relpath(path,directory)
            if name not in staged and os.path.isfile(path) and not os.path.islink(path):
                found.append({'name':name,'bytes':os.path.getsize(path)})
    return {'results':sorted(found,key=lambda item:item['name'])}
def read(request,directory):
    path=confined(directory,request['name'])
    if not os.path.isfile(path):raise Refused('result_file_missing',{'name':request['name']})
    with open(path,'rb') as stream:
        stream.seek(request['offset'])
        return {'base64':base64.b64encode(stream.read(request['limit'])).decode()}
def cancel(request,directory):
    made=submission(directory)
    open(os.path.join(directory,'cancelled'),'w').close()
    if made['mode']=='batch':scheduler([request['scheduler']['qdel'],made['job_id']])
    else:
        try:os.killpg(made['pid'],signal.SIGKILL)
        except ProcessLookupError:pass
    return {'cancelled_at':now()}
request=json.load(sys.stdin)
workspace=os.path.realpath(request['workspace'])
try:
    operation={'submit':submit,'state':state,'results':results,'read':read,'cancel':cancel}[request['operation']]
    reply=operation(request,confined(workspace,request['handle']))
    print(json.dumps({'ok':True,'reply':reply}))
except Refused as refusal:
    print(json.dumps({'ok':False,'code':refusal.code,'detail':refusal.detail}))
'''


class PbsSshRoute:
    """Jobs below one workspace directory of a remote resource, through one configured transport."""

    kind = 'pbs'

    def __init__(self, configuration, *, resource_id):
        if not isinstance(configuration, dict) or set(configuration) != set(CONFIGURATION):
            raise ValueError('pbs_route_configuration_requires_exactly:' + ','.join(CONFIGURATION))
        transport, scheduler = configuration['ssh_argv'], configuration['scheduler']
        if (not isinstance(transport, list) or not transport
                or any(type(word) is not str or not word or '\x00' in word for word in transport)):
            raise ValueError('pbs_route_transport_must_be_a_list_of_words')
        if not isinstance(scheduler, dict) or set(scheduler) != set(SCHEDULER) or any(
                type(word) is not str or not word for word in scheduler.values()):
            raise ValueError('pbs_route_scheduler_requires_exactly:' + ','.join(SCHEDULER))
        for name in ('python_executable', 'workspace'):
            path = configuration[name]
            if type(path) is not str or not PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts:
                raise ValueError('pbs_route_' + name + '_must_be_an_absolute_path')
        if type(configuration['poll_seconds']) not in (int, float) or not configuration['poll_seconds'] > 0:
            raise ValueError('pbs_route_poll_seconds_must_be_positive')
        if type(resource_id) is not str or not resource_id:
            raise ValueError('pbs_route_resource_id_must_be_text')
        self.configuration, self.resource_id = json.loads(json.dumps(configuration)), resource_id

    def describe(self):
        return {'resource_id': self.resource_id, 'kind': self.kind, 'workspace': self.configuration['workspace'],
                'scheduler': 'pbs', 'modes': list(MODES)}

    def _request(self, operation, handle, **fields):
        configuration = self.configuration
        command = [*configuration['ssh_argv'],
                   shlex.quote(configuration['python_executable']) + ' -B -c ' + shlex.quote(REMOTE)]
        request = {'operation': operation, 'handle': handle, 'workspace': configuration['workspace'],
                   'scheduler': configuration['scheduler'], **fields}
        try:
            done = subprocess.run(command, input=json.dumps(request).encode(), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, check=False)
        except OSError as error:
            raise RouteRequestError('transport_unavailable', {'exception_type': type(error).__name__,
                                                              'detail': str(error)}) from error
        if done.returncode:
            raise RouteRequestError('transport_or_remote_program_failed', {
                'returncode': done.returncode, 'stderr': done.stderr.decode('utf-8', 'replace')[-4000:]})
        reply = json.loads(done.stdout)
        if not reply['ok']:
            raise RouteRequestError(reply['code'], reply['detail'])
        return reply['reply']

    def submit(self, handle, job, files, owner):
        if (not isinstance(job, dict) or set(job) != {'mode', 'script', 'arguments', 'env'}
                or job['mode'] not in MODES or type(job['script']) is not str or not job['script']
                or not isinstance(job['arguments'], list) or not isinstance(job['env'], dict)
                or (job['mode'] == 'login' and job['arguments'])):
            raise ValueError('pbs_job_requires_mode_script_arguments_env')
        reply = self._request('submit', handle, job=job,
                              files={name: base64.b64encode(data).decode() for name, data in files.items()})
        made = reply['submission']
        return {'native': made, 'submitted_at': made['submitted_at'], 'adopted': reply['adopted'], 'reply': reply}

    def status(self, handle, native_identity):
        reply = self._request('state', handle)
        return {'state': reply['state'], 'result_available': reply['state'] in ENDED,
                'observed_at': reply['observed_at'], 'reply': reply}

    async def wait(self, handle, native_identity):
        """Return when the job has ended; one status request every ``poll_seconds``. No deadline."""
        while True:
            status = self.status(handle, native_identity)
            if status['state'] in ENDED:
                return
            if status['state'] == 'unknown':
                raise RouteRequestError('job_state_unknown', status['reply'])
            await asyncio.sleep(self.configuration['poll_seconds'])

    def results(self, handle, native_identity):
        return [{**item, 'media_type': MEDIA_TYPES.get(PurePosixPath(item['name']).suffix,
                                                       'application/octet-stream')}
                for item in self._request('results', handle)['results']]

    def read(self, handle, native_identity, name, offset, limit):
        return base64.b64decode(self._request('read', handle, name=name, offset=offset, limit=limit)['base64'])

    def cancel(self, handle, native_identity):
        return {'reply': self._request('cancel', handle)}


__all__ = ['PbsSshRoute', 'REMOTE']
