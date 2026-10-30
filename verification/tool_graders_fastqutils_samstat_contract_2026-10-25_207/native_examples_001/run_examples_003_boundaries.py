"""Additional tiny native boundary runs and source-executed caller error stub."""
from pathlib import Path
import ast, hashlib, json, os, resource, subprocess, time
W=Path(__file__).resolve().parents[1];D=W/'native_examples_001';I=D/'inputs';header='@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:refA\tLN:1000\n'
resource.setrlimit(resource.RLIMIT_AS,(20*1024**3,20*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
(I/'quality_pair.sam').write_text(header+'q0\t0\trefA\t1\t30\t1M\t*\t0\t0\tA\t!\tMD:Z:1\tNM:i:0\nq40\t0\trefA\t2\t30\t1M\t*\t0\t0\tA\tI\tMD:Z:1\tNM:i:0\n')
(I/'peek10001.sam').write_text(header+''.join(f'p{i}\t0\trefA\t1\t30\t1M\t*\t0\t0\tA\tI\tMD:Z:1\tNM:i:0\n' for i in range(10001)))
(I/'known_identity.sam').write_text(header+'perfect\t0\trefA\t1\t30\t4M\t*\t0\t0\tACGT\tIIII\tMD:Z:4\tNM:i:0\nsub\t0\trefA\t10\t30\t4M\t*\t0\t0\tACGT\tIIII\tMD:Z:1A2\tNM:i:1\ninsertion\t0\trefA\t20\t30\t2M2I2M\t*\t0\t0\tACGTAA\tIIIIII\tMD:Z:4\tNM:i:2\n')
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(W/'sources/deps/root/usr/lib/x86_64-linux-gnu');env['TMPDIR']=str(D)
receipts=[]
for version in ['2_2_3','2_5_0']:
 exe=W/f'sources/build_{version}/src/samstat';O=D/version/'boundaries';O.mkdir(exist_ok=True)
 for f,extra in [('quality_pair.sam',[]),('peek10001.sam',['-p','10']),('known_identity.sam',[])]:
  cmd=list(map(str,[exe,'-t','1','-d',O,*extra,I/f]));stem=version+'_'+f;t=time.time()
  with (D/(stem+'.stdout')).open('wb') as out,(D/(stem+'.stderr')).open('wb') as err:r=subprocess.run(cmd,cwd=D,env=env,stdout=out,stderr=err)
  receipts.append(dict(command=cmd,cwd=str(D),exit_code=r.returncode,elapsed_seconds=time.time()-t,max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,stdout=stem+'.stdout',stderr=stem+'.stderr'))
# Execute only the caller's exact samstat try/except AST with /bin/false as the
# explicitly injected failing primitive. This is NOT a native SAMstat crash or a service run.
caller=W.parent/'tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/sources/p3_fqutils/lib/fastq_utils.py'
tree=ast.parse(caller.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_alignment');node=next(n for n in ast.walk(fn) if isinstance(n,ast.Try) and 'samstat_cmd' in ast.unparse(n.body[0]))
code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(caller),'exec');bam_path=D/'caller_error_stub.all.bam';env_globals={'subprocess':subprocess,'samstat_cmd':['/bin/false'],'bam_file_all':str(bam_path)}
exec(code,env_globals)
receipts.append(dict(kind='caller_except_block_source_execution',caller=str(caller),caller_sha256=hashlib.sha256(caller.read_bytes()).hexdigest(),injected_primitive=['/bin/false'],native_samstat_crash=False,live_service=False,output='caller_error_stub.all.bam.samstat.html'))
(D/'RUN_RECEIPTS_003.json').write_text(json.dumps(receipts,indent=2)+'\n');print(json.dumps(receipts,indent=2))
