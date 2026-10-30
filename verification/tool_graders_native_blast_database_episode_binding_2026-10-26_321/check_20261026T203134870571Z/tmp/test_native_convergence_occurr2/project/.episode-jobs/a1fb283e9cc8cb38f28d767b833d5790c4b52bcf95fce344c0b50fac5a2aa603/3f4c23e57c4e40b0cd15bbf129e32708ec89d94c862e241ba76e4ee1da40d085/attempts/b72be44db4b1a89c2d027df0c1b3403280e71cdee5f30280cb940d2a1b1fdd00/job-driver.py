
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
