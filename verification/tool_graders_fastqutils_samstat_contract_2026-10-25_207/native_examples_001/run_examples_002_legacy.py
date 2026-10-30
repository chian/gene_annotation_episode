"""Additive legacy runs against the retained 001 tiny inputs."""
from pathlib import Path
import hashlib,json,os,resource,subprocess,time
W=Path(__file__).resolve().parents[1];D=W/'native_examples_001';I=D/'inputs';O=D/'2_2_3';O.mkdir(exist_ok=True)
resource.setrlimit(resource.RLIMIT_AS,(20*1024**3,20*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(W/'sources/deps/root/usr/lib/x86_64-linux-gnu');env['TMPDIR']=str(D)
exe=W/'sources/build_2_2_3/src/samstat';receipts=[]
def run(args,stem):
 cmd=[str(exe),*map(str,args)];t=time.time()
 with (D/(stem+'.stdout')).open('wb') as out,(D/(stem+'.stderr')).open('wb') as err:r=subprocess.run(cmd,cwd=D,env=env,stdout=out,stderr=err)
 receipts.append(dict(command=cmd,cwd=str(D),exit_code=r.returncode,elapsed_seconds=time.time()-t,max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,stdout=stem+'.stdout',stderr=stem+'.stderr'))
run(['--version'],'2_2_3_version');run(['--help'],'2_2_3_help')
for source in sorted(I.iterdir()):run(['-t','1','-d',O,source],'2_2_3_'+source.name)
P=O/'peek';P.mkdir(exist_ok=True);run(['-t','1','-p','3','-d',P,I/'mixed.sam'],'2_2_3_peek')
P=O/'optional';P.mkdir(exist_ok=True);run(['-t','1','--norm','--plotend','-d',P,I/'qualities.fastq'],'2_2_3_optional')
(D/'RUN_RECEIPTS_002.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps([{'input':r['command'][-1],'exit':r['exit_code'],'seconds':r['elapsed_seconds']} for r in receipts],indent=2))
