"""Research arithmetic only; fixed manual table transcription, no source reader/grader."""
import json, math, statistics
from fractions import Fraction as F
from pathlib import Path
p=Path(__file__).parent
rows=[]
for i in range(1,33):
    rows.append({'row_1_based':i,'source':'plasmid' if i<=26 else 'genomic','length_bp':34 if i in (20,24) else 33,
                 'origin':'manual_table_transcription','locator':f'NIHMS583201-supplement-1.pdf physical page 7, Supplementary Table 1 row {i}',
                 'reading_tolerance':{'source_label':'exact legible text','length_bp':0},'independent_acquisition_identity':None})
transcription={'method':'Manual reading of original rendered supplementary PDF page 7; not OCR-derived scientific values',
 'rows':rows,'table_denominator_meaning':'listed selected expanded-clone spacer entries',
 'independent_sampling_denominator':None,'duplicate_sequence_rows':[[16,26]],
 'duplicate_sequence':'GGGAAACGGTCTGATAAGAGACACCGGCATACT',
 'duplicate_policy':'Retain both listed rows; no inferred independence or deduplication of acquisitions',
 'graph_numeric_transcription':None,
 'graph_numeric_transcription_reason':'Main acquisition panels are uncalibrated gels; no numerical per-cell endpoint is read from band darkness or visible-band count'}
(p/'MANUAL_TABLE_TRANSCRIPTION_001.json').write_text(json.dumps(transcription,indent=2)+'\n')
checks=[]
def check(name,a,b):
 assert a==b,(name,a,b)
 checks.append({'name':name,'actual':str(a),'expected':str(b),'pass':True})
check('listed rows',len(rows),32)
check('33 bp count',sum(r['length_bp']==33 for r in rows),30)
check('34 bp count',sum(r['length_bp']==34 for r in rows),2)
check('plasmid count',sum(r['source']=='plasmid' for r in rows),26)
check('genomic count',sum(r['source']=='genomic' for r in rows),6)
check('length fractions exhaustive',F(30,32)+F(2,32),F(1))
check('source fractions exhaustive',F(26,32)+F(6,32),F(1))
check('typical locus increment',33+28,61)
w,d,c=F(100),F(20),F(90)
loss=w-d;raw=(c-d)/loss;theta=loss/(w+d);r=1-abs(c-w)/abs(loss);C=F(9,10)
Ip=1-F(8)/abs(loss);Ir=1-F(7)/abs(c-d);I=min(Ip,Ir);q=theta*r*C*I
check('synthetic loss',loss,F(80))
check('synthetic restoration fraction',raw,F(7,8))
check('synthetic theta',theta,F(2,3))
check('synthetic restoration agreement',r,F(7,8))
check('synthetic distinct isolation bounds agree',Ip,Ir)
check('synthetic q_reference',q,F(189,400))
def rescue(ww,dd,cc):
 if any(x is None for x in (ww,dd,cc)): return None
 if ww==dd:return None
 return (cc-dd)/(ww-dd)
check('absent native WT remains null',rescue(None,d,c),None)
check('zero restoration denominator remains null',rescue(w,w,c),None)
check('published frequency score remains unavailable',None,None)
kd=[308,212,351]
out={'status':'pass','checks_count':len(checks),'checks':checks,
 'origin_scope':'Fixed manual transcription and synthetic arithmetic; no scientific-reader or statistical inference validation',
 'descriptive_list_fractions':{'length33':float(F(30,32)),'length34':float(F(2,32)),'plasmid':float(F(26,32)),'genomic':float(F(6,32))},
 'itc_numeric_audit':{'reported_values_nM':kd,'arithmetic_mean_nM':statistics.mean(kd),'author_reported_sd_nM':58,'population_sd_nM':statistics.pstdev(kd),'sample_sd_nM':statistics.stdev(kd),'qualifier':'Author SD resembles population-divisor spread; neither replaced nor treated as SEM. These are not acquisition measurements.'},
 'synthetic_reference_only':{'q_reference':float(q),'target_transfer':None,'sampling_uncertainty':None},
 'published_restoration':{'rWT':None,'rD':None,'rC':None,'restoration_fraction_raw':None,'q_reference':None,'reason':'No calibrated matching native WT/deletion/complement endpoints'}}
(p/'ARITHMETIC_CHECKS_001.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'status':'pass','itc':out['itc_numeric_audit']}))
