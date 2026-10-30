"""Checks fixed retained evidence files. This is not a general SAMstat parser."""
from pathlib import Path
import json,re,hashlib
D=Path(__file__).resolve().parent
checks=[]
def check(name, observed, expected):
 assert observed==expected,(name,observed,expected)
 checks.append(dict(check=name,observed=observed,expected=expected,result='pass'))
def read(p):return (D/p).read_text()
def legacy_mapping(p):
 t=read(p);s=t.split('var mappingtableval = ',1)[1].split('\nvar mappingtable_data',1)[0].strip()
 return json.loads(s)
def series(p,name,key):
 t=read(p);s=t.split('var '+name+'  = {',1)[1].split('\n};',1)[0]
 pat=r'\b'+re.escape(key)+r'\s*:\s*(\[[^\]]*\])'
 return json.loads(re.search(pat,s).group(1))
def card(p,label):
 s=re.search(r'<dt>'+re.escape(label)+r'</dt><dd>(.*?)</dd>',read(p),re.S).group(1)
 return s.split('<span',1)[0]
def modern_bins(p):
 t=read(p).split('<tbody>',1)[1].split('</tbody>',1)[0]
 return [[int(n.replace(',','')) if '.' not in n else float(n) for n in re.findall(r'<td class="num">([^<]+)</td>',r)] for r in re.findall(r'<tr>(.*?)</tr>',t,re.S)]
l=legacy_mapping('2_2_3/mixed.sam.samstat.html');b=legacy_mapping('2_2_3/mixed.bam.samstat.html')
check('legacy SAM/BAM mapping payload identical',l,b)
check('legacy R1 counts',l[1],[5,2,2,1,10]);check('legacy R2 counts',l[3],[0,1,0,0,1])
m=modern_bins('2_5_0/mixed.sam.samstat.html');check('modern table rows',m,[[4,40.0,4,0],[3,30.0,2,1],[2,20.0,2,0],[1,10.0,1,0]])
check('modern SAM/BAM mapping payload identical',m,modern_bins('2_5_0/mixed.bam.samstat.html'))
check('modern Reads',card('2_5_0/mixed.sam.samstat.html','Reads (R1+R2)'),'10')
check('modern Bases',card('2_5_0/mixed.sam.samstat.html','Bases'),'50 bp')
check('modern Mean Q rounded',card('2_5_0/mixed.sam.samstat.html','Mean Q'),'16.2')
check('legacy length density x',series('2_2_3/lengths.fastq.samstat.html','len_R1__Unmapped','x'),['4.000000','8.000000'])
check('legacy length density y',series('2_2_3/lengths.fastq.samstat.html','len_R1__Unmapped','y'),[0.090324,0.169574])
for b,values in {'A':[2,1,0,0,0],'C':[0,1,1,0,0],'G':[0,0,1,1,0],'T':[0,0,0,1,1],'N':[0,0,0,0,1]}.items():
 check('legacy base count '+b,series('2_2_3/qualities.fastq.samstat.html','bc_R1_Unmapped_'+b,'y'),values)
check('legacy native quality index defect',series('2_2_3/qualities.fastq.samstat.html','bq_R1_Unmapped_126','y'),[37,41,41,41,41])
check('legacy Q0 Q40 mean',series('2_2_3/boundaries/quality_pair.sam.samstat.html','bq_R1_MAPQ_gt_30_0','y'),[20.0])
check('legacy Q0 Q40 SEM',series('2_2_3/boundaries/quality_pair.sam.samstat.html','bq_R1_MAPQ_gt_30_0','array'),[14.142136])
check('modern Q0 Q40 mean',card('2_5_0/boundaries/quality_pair.sam.samstat.html','Mean Q'),'3.0')
check('modern known gap-compressed identity',card('2_5_0/boundaries/known_identity.sam.samstat.html','Median identity'),'80.0%')
check('modern clipping',card('2_5_0/errors.sam.samstat.html','% bases clipped'),'15.4%')
check('legacy partial prefix count',legacy_mapping('2_2_3/boundaries/peek10001.sam.samstat.html')[1][-1],10000)
check('modern partial prefix count',card('2_5_0/boundaries/peek10001.sam.samstat.html','Reads'),'10')
check('legacy native report-wide total','<p>11 - reads <br>' in read('2_2_3/mixed.sam.samstat.html'),True)
check('legacy empty fractions are nonfinite native tokens',read('2_2_3/empty.sam.samstat.html').count('-nan'),5)
check('legacy malformed-input report retained first record',legacy_mapping('2_2_3/malformed_after_record.sam.samstat.html')[1][-1],1)
check('legacy malformed-input warning retained','Parse error' in read('2_2_3_malformed_after_record.sam.stderr'),True)
check('modern malformed-input has no HTML',(D/'2_5_0/malformed_after_record.sam.samstat.html').exists(),False)
check('missing-sequence Bases is not numeric zero',card('2_5_0/missing_sequence.sam.samstat.html','Bases'),'n/a')
check('legacy empty FASTQ has no HTML',(D/'2_2_3/empty.fastq.samstat.html').exists(),False)
check('modern SVG HTML has no script data arrays','<script' in read('2_5_0/mixed60.sam.samstat.html'),False)
check('caller error wording does not match exit code semantics','<b>return code:</b> 1' in read('caller_error_stub.all.bam.samstat.html'),True)
xs=series('2_2_3/long_binned.fastq.samstat.html','bc_R1_Unmapped_A','x');ys=series('2_2_3/long_binned.fastq.samstat.html','bc_R1_Unmapped_A','y')
check('legacy clustered x first label',xs[0],'0');check('legacy clustered first range',next(v for v in xs if '-' in v),'250-255');check('legacy clustered mean value',ys[xs.index('250-255')],1)
report=dict(status='native_evidence_checks_passed',scope='Fixed native files only; no candidate parser/calculator/import/service path tested',check_count=len(checks),checks=checks)
(D/'NATIVE_EVIDENCE_CHECKS_002.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'check_count':len(checks),'status':'passed'}))
