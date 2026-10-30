"""Generate and independently inspect the exact first selected native fixture."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path.cwd(); PACKET=ROOT.parent
def save(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pin(path):
    path=Path(path); raw=path.read_bytes()
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
native=PACKET/'prerequisite003/hictk'
assert pin(native)['sha256']=='aaae1ec459a63ff8be922b026c4799da4135bb81df78c756feae9dc7a8176afe'
inspector=ROOT/'byte_inspector.py'; inspector.write_bytes((PACKET/'byte_inspector.py').read_bytes())
sys.path.insert(0,str(ROOT))
from byte_inspector import inspect
save('SELECTED_DEPENDENCIES.json',[pin(native),pin(inspector)])
rows=[(0,0,4),(0,1,2),(0,2,6),(1,1,4),(1,2,2),(1,3,2),(2,2,4),(2,3,2),(3,3,4)]
(ROOT/'four.chrom.sizes').write_text('chrA\t40\n')
(ROOT/'four.coo').write_text(''.join('\t'.join(map(str,row))+'\n' for row in rows))
(ROOT/'tmp').mkdir()
env={**os.environ,'HICTK_NO_TELEMETRY':'1','TMPDIR':str(ROOT/'tmp')}
def run(name,args):
    argv=[str(native),*args]
    save(name+'.request.json',{'argv':argv,'cwd':str(ROOT),'environment_overrides':{'HICTK_NO_TELEMETRY':'1','TMPDIR':str(ROOT/'tmp')}})
    with (ROOT/(name+'.stdout.txt')).open('wb') as out,(ROOT/(name+'.stderr.txt')).open('wb') as err:
        proc=subprocess.run(argv,env=env,stdout=out,stderr=err)
    save(name+'.result.json',{'returncode':proc.returncode})
    if proc.returncode: raise RuntimeError(f'{name}: exit {proc.returncode}')
run('load',['load','--format','coo','--output-fmt','hic','--bin-size','10','--chrom-sizes',str(ROOT/'four.chrom.sizes'),'--assembly','synthetic_four_bin','--zero-based','--validate-pixels','--no-transpose-lower-triangular-pixels','--skip-all-vs-all','--threads','2','--chunk-size','32','--tmpdir',str(ROOT/'tmp'),str(ROOT/'four.coo'),str(ROOT/'four.hic')])
run('dump',['dump','--resolution','10','--matrix-type','observed','--matrix-unit','BP','--range','chrA','--balance','NONE','--sorted',str(ROOT/'four.hic')])
run('metadata',['metadata','--output-format','json',str(ROOT/'four.hic')])
run('validate',['validate','--output-format','json',str(ROOT/'four.hic')])
dump=[tuple(map(float,line.split())) for line in (ROOT/'dump.stdout.txt').read_text().splitlines()]
assert sorted(dump)==sorted(rows), (dump,rows)
audit=inspect(ROOT/'four.hic',ROOT/'blocks')
save('BYTE_AUDIT.json',audit)
records=[(r['x'],r['y'],r['value']) for m in audit['matrices'] for z in m['zooms'] for b in z['blocks'] for r in b['records']]
assert sorted(records)==sorted(rows)
save('EXPECTED.json',{'origin':'independently authored synthetic input; not a biological measurement',
 'upper_rows':rows,'matrix':[[4,2,6,0],[2,4,2,2],[6,2,4,2],[0,2,2,4]],
 'raw_anchor_0_2':6,'distance2':{'values':[6,2],'count':2,'sum':8,'sum_squares':40,'mean':4,'population_variance':4,'fold':1.5},
 'stored_rows':9,'diagonal_rows':4,'offdiagonal_rows':5,'directed_cells':16,'unique_unordered_cells':10,'implicit_zero_directed_cells':2,
 'independent_native_dump_matches':True,'independent_byte_decoder_matches':True})
save('FIXTURE_PINS.json',[pin(ROOT/name) for name in ['four.chrom.sizes','four.coo','four.hic','dump.stdout.txt','BYTE_AUDIT.json','EXPECTED.json']])
print(json.dumps({'native':pin(ROOT/'four.hic'),'version':audit['version'],'blocks':[{k:v for k,v in b.items() if k not in {'records','filler_slots'}} for m in audit['matrices'] for z in m['zooms'] for b in z['blocks']]}))
