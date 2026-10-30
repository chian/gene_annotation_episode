"""Serialize actual full native files; compare to independent official reader."""
from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys

ROOT=Path.cwd(); PACKET=ROOT.parent
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pin(path):
    path=Path(path); data=path.read_bytes(); return {'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}
for name in ['fixture_spec_writer.py','byte_inspector.py']: (ROOT/name).write_bytes((PACKET/name).read_bytes())
sys.path.insert(0,str(ROOT)); from fixture_spec_writer import write
from byte_inspector import inspect,number
native=PACKET/'prerequisite003/hictk'
save(ROOT/'DEPENDENCIES.json',[pin(native),pin(ROOT/'fixture_spec_writer.py'),pin(ROOT/'byte_inspector.py')])
env={**os.environ,'HICTK_NO_TELEMETRY':'1'}
rows=[(0,0,4),(0,1,2),(0,2,6),(1,1,4),(1,2,2),(1,3,2),(2,2,4),(2,3,2),(3,3,4)]
cases=[]
for vf in [False,True]:
    for xf in [False,True]:
        for yf in [False,True]: cases.append((f'rowlist_{"f32" if vf else "i16"}_x{32 if xf else 16}_y{32 if yf else 16}',rows,dict(float_counts=vf,x_int=xf,y_int=yf)))
cases += [('dense_i16_fillers',rows,dict(float_counts=False,dense=True)),('dense_f32_fillers',rows,dict(float_counts=True,dense=True)),
          ('rowlist_explicit_zero',rows+[(0,3,0)],{}),('dense_explicit_zero',rows+[(0,3,0)],dict(dense=True)),
          ('present_zero_block',[],dict(zero_blocks=True)),
          ('rowlist_nonfinite',[(0,0,4),(0,1,float('nan')),(0,2,float('inf')),(0,3,-float('inf')),(1,1,-2),(2,2,0),(3,3,4)],{}),
          ('rowlist_i16_minus32768',[(0,0,4),(0,1,-32768),(1,1,4)],dict(float_counts=False)),
          ('normalization_terminal_padding',rows,dict(weights=[1,2,1,2,99]))]
outcomes=[]
for name,source_rows,options in cases:
    path=ROOT/name; path.mkdir()
    expected=[(x,y,number(value)) for x,y,value in source_rows]
    save(path/'INPUT.json',{'rows':expected,'options':options,'identity':'synthetic native-format fixture; not biological data'})
    layout=write(path/'output.hic',source_rows,**options); save(path/'WIRE_LAYOUT.json',layout)
    audit=inspect(path/'output.hic',path/'blocks'); save(path/'BYTE_AUDIT.json',audit)
    actual=[(r['x'],r['y'],r['value']) for m in audit['matrices'] for z in m['zooms'] for b in z['blocks'] for r in b['records']]
    assert sorted(actual)==sorted(expected)
    def run(command,args):
        argv=[str(native),*args]; save(path/(command+'.request.json'),{'argv':argv,'environment_overrides':{'HICTK_NO_TELEMETRY':'1'},'cwd':str(path)})
        with (path/(command+'.stdout.txt')).open('wb') as out,(path/(command+'.stderr.txt')).open('wb') as err:
            result=subprocess.run(argv,cwd=path,env=env,stdout=out,stderr=err)
        save(path/(command+'.result.json'),{'returncode':result.returncode}); return result.returncode
    validate=run('validate',['validate',str(path/'output.hic')])
    dump=run('dump',['dump','--resolution','10','--range','chrA','--matrix-type','observed','--matrix-unit','BP','--balance','NONE','--sorted',str(path/'output.hic')])
    native_rows=[]
    if dump==0:
        for line in (path/'dump.stdout.txt').read_text().splitlines():
            x,y,value=line.split(); native_rows.append((int(x),int(y),number(float(value))))
    result={'case':name,'writer':'packet454_explicit_whole_native_file_serializer','independent_reader':'official hictk-v2.2.0 release binary','validate_exit':validate,'dump_exit':dump,'native_dump_matches':sorted(native_rows)==sorted(expected),'byte_audit_matches':True,'file':pin(path/'output.hic'),'native_dump_rows':native_rows,'expected_rows':expected,
            'scientific_count_status':'retained_invalid_negative_or_nonfinite' if name in {'rowlist_nonfinite','rowlist_i16_minus32768'} else 'valid_synthetic_counts'}
    if name=='normalization_terminal_padding':
        result['weighted_dump_exit']=run('dump_weighted',['dump','--resolution','10','--range','chrA','--balance','SYNTHETIC_DIVISIVE','--sorted',str(path/'output.hic')])
        result['weights_dump_exit']=run('dump_weights',['dump','--resolution','10','--table','weights','--balance','SYNTHETIC_DIVISIVE',str(path/'output.hic')])
    save(path/'OUTCOME.json',result); outcomes.append(result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'native_dump_rows','expected_rows'}}),flush=True)
save(ROOT/'ALL_OUTCOMES.json',outcomes)
assert all(o['validate_exit']==0 and o['dump_exit']==0 and o['native_dump_matches'] for o in outcomes)
