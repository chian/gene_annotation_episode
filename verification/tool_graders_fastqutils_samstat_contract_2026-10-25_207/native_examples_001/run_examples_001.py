"""Evidence-only tiny source executions. No report JS is evaluated or rendered."""
from pathlib import Path
import hashlib, json, os, resource, subprocess, time
W=Path(__file__).resolve().parents[1]; D=W/'native_examples_001'; I=D/'inputs'; I.mkdir(exist_ok=True)
resource.setrlimit(resource.RLIMIT_AS,(20*1024**3,20*1024**3))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
header='@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:refA\tLN:1000\n@SQ\tSN:refB\tLN:1000\n'
def rec(name, flag, pos, mq, seq, qual=None, cigar=None, md=None, mate='*', mpos=0):
    if qual is None: qual='I'*len(seq)
    if cigar is None: cigar=f'{len(seq)}M' if not flag&4 else '*'
    fields=[name,flag,'refA' if not flag&4 else '*',pos if not flag&4 else 0,mq,cigar,mate,mpos,0,seq,qual]
    if md is not None: fields += [f'MD:Z:{md}']
    return '\t'.join(map(str,fields))+'\n'
rows=[rec('u0',0,1,0,'ACGT',md='4'),rec('u9',0,10,9,'AACGT',md='5'),rec('u10',0,20,10,'AAACGT',md='6'),rec('u29',0,30,29,'AAAACGT',md='7'),rec('u30',0,40,30,'AAAAACGT',md='8'),rec('u255',0,50,255,'ACGT',md='4'),rec('unmapped',4,0,0,'NNNN'),rec('pairA',99,60,30,'ACGT',md='4',mate='=',mpos=70),rec('pairA',147,70,10,'ACGT',qual='!+5?',md='4',mate='=',mpos=60),rec('missingq',0,80,30,'ACGT',qual='*',md='4'),rec('u30',2048,100,30,'AAAAACGT',md='8'),rec('u30',256,110,30,'AAAAACGT',md='8')]
(I/'mixed.sam').write_text(header+''.join(rows))
(I/'empty.sam').write_text(header)
(I/'empty.fastq').write_bytes(b'')
(I/'unmapped.sam').write_text(header+rec('unmapped',4,0,0,'ACGT'))
(I/'missing_quality.sam').write_text(header+rec('qmissing',0,1,30,'ACGT',qual='*',md='4'))
(I/'missing_sequence.sam').write_text(header+'noseq\t4\t*\t0\t0\t*\t*\t0\t0\t*\t*\n')
(I/'malformed_after_record.sam').write_text(header+rows[0]+'broken\tSAM\n')
(I/'qualities.fastq').write_text('@r1\nACGTN\n+\n!+5?I\n@r2\nAACGT\n+\nIIIII\n')
(I/'lengths.fastq').write_text('@r1\nACGT\n+\nIIII\n@r2\nACGTACGT\n+\n!!!!!!!!\n@r3\nACGTACGT\n+\nIIIIIIII\n')
(I/'long_binned.fastq').write_text('@long\n'+'A'*300+'\n+\n'+'I'*300+'\n')
errors=[rec('mismatch',0,1,30,'ACGT',md='1A2'),rec('insertion',0,10,30,'ACGTAA',cigar='2M2I2M',md='4'),rec('deletion',0,20,30,'ACGT',cigar='2M2D2M',md='2^AA2'),rec('softclip',16,30,30,'TTACGTAA',cigar='2S4M2S',md='4'),rec('no_md',0,40,30,'ACGT')]
(I/'errors.sam').write_text(header+''.join(errors))
rep=[]
for i in range(6):
 for row in rows:
  cols=row.rstrip('\n').split('\t');cols[0]=str(i)+'_'+cols[0];rep.append('\t'.join(cols)+'\n')
(I/'mixed60.sam').write_text(header+''.join(rep))
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(W/'sources/deps/root/usr/lib/x86_64-linux-gnu'); env['TMPDIR']=str(D)
receipts=[]
def run(cmd, stem, cwd=None):
 t=time.time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 with (D/(stem+'.stdout')).open('wb') as out,(D/(stem+'.stderr')).open('wb') as err:p=subprocess.run(list(map(str,cmd)),cwd=cwd or D,env=env,stdout=out,stderr=err)
 receipts.append(dict(command=list(map(str,cmd)),cwd=str(cwd or D),exit_code=p.returncode,elapsed_seconds=time.time()-t,max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,stdout=stem+'.stdout',stderr=stem+'.stderr'))
 return p.returncode
converter=W/'sources/build_2_5_0/htslib/src/htslib/test/test_view'
run([converter,'-b','-p',I/'mixed.bam',I/'mixed.sam'],'convert_mixed_bam')
for version in ['2_5_0','2_2_3']:
 exe=W/f'sources/build_{version}/src/samstat'
 if not exe.exists():continue
 outdir=D/version;outdir.mkdir(exist_ok=True)
 run([exe,'--version'],version+'_version')
 run([exe,'--help'],version+'_help')
 for source in sorted(I.iterdir()):
  run([exe,'-t','1','-d',outdir,source],version+'_'+source.name)
 partial=outdir/'peek'; partial.mkdir(exist_ok=True)
 run([exe,'-t','1','-p','3','-d',partial,I/'mixed.sam'],version+'_peek')
 if version=='2_5_0':
  side=outdir/'json_comparison';side.mkdir(exist_ok=True)
  run([exe,'-t','1','--json','-d',side,I/'mixed.sam'],version+'_json_comparison')
 else:
  opt=outdir/'optional';opt.mkdir(exist_ok=True)
  run([exe,'-t','1','--norm','--plotend','-d',opt,I/'qualities.fastq'],version+'_optional')
manifest=[]
for p in sorted(D.rglob('*')):
 if p.is_file() and p.name not in ('RUN_RECEIPTS_001.json','FILE_HASHES_001.json'):
  b=p.read_bytes();manifest.append(dict(path=str(p.relative_to(D)),byte_count=len(b),sha256=hashlib.sha256(b).hexdigest()))
(D/'RUN_RECEIPTS_001.json').write_text(json.dumps(receipts,indent=2)+'\n')
(D/'FILE_HASHES_001.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(receipts,indent=2))
