"""Additive native precision-boundary evidence; no JS execution."""
from pathlib import Path
import json,os,resource,subprocess,time
W=Path(__file__).resolve().parents[1];D=W/'native_examples_001';I=D/'inputs'
resource.setrlimit(resource.RLIMIT_AS,(20*1024**3,20*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
rows=['@HD\tVN:1.6\tSO:unsorted\n','@SQ\tSN:refA\tLN:1000\n']
for i in range(501):
 for flag,pos,mq,mp in [(99,10,30,20),(147,20,10,10)]:
  rows.append(f'p{i}\t{flag}\trefA\t{pos}\t{mq}\t1M\t=\t{mp}\t0\tA\tI\tMD:Z:1\tNM:i:0\n')
(I/'paired1002.sam').write_text(''.join(rows))
(I/'long_lengths.fastq').write_text(''.join('@r'+str(i)+'\n'+'A'*n+'\n+\n'+'I'*n+'\n' for i,n in enumerate([10123,10987])))
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(W/'sources/deps/root/usr/lib/x86_64-linux-gnu');env['TMPDIR']=str(D)
receipts=[]
for v,files in [('2_2_3',['paired1002.sam']),('2_5_0',['paired1002.sam','peek10001.sam','long_lengths.fastq'])]:
 O=D/v/'precision';O.mkdir(exist_ok=True)
 for f in files:
  cmd=[str(W/f'sources/build_{v}/src/samstat'),'-t','1','-d',str(O),str(I/f)];stem=v+'_precision_'+f;t=time.monotonic()
  with (D/(stem+'.stdout')).open('wb') as out,(D/(stem+'.stderr')).open('wb') as err:r=subprocess.run(cmd,cwd=D,env=env,stdout=out,stderr=err)
  receipts.append(dict(command=cmd,cwd=str(D),exit_code=r.returncode,elapsed_seconds=time.monotonic()-t,max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,stdout=stem+'.stdout',stderr=stem+'.stderr'))
(D/'RUN_RECEIPTS_004.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps([{'file':r['command'][-1],'exit':r['exit_code']} for r in receipts]))
