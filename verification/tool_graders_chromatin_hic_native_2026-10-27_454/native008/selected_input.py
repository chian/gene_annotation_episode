"""Build a packet-only official API harness and preserve each selected result."""
from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys

ROOT=Path.cwd(); PACKET=ROOT.parent; SETUP=PACKET/'prerequisite007'
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pin(path):
    path=Path(path); raw=path.read_bytes()
    return {'path':str(path),'resolved_path':str(path.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
(ROOT/'tmp').mkdir()
env={**os.environ,'TMPDIR':str(ROOT/'tmp'),'PATH':str(SETUP/'build-env/bin')+os.pathsep+os.environ['PATH'],'CONAN_HOME':str(ROOT/'unused_conan'),'CMAKE_BUILD_PARALLEL_LEVEL':'2','HICTK_NO_TELEMETRY':'1'}
def run(path,name,args):
    save(path/(name+'.request.json'),{'argv':args,'cwd':str(path),'environment_overrides':{k:env[k] for k in ['TMPDIR','PATH','CONAN_HOME','CMAKE_BUILD_PARALLEL_LEVEL','HICTK_NO_TELEMETRY']}})
    with (path/(name+'.stdout.txt')).open('wb') as out,(path/(name+'.stderr.txt')).open('wb') as err:
        proc=subprocess.run(args,cwd=path,env=env,stdout=out,stderr=err)
    save(path/(name+'.result.json'),{'returncode':proc.returncode})
    return proc.returncode
for name in ['writer_harness.cpp','byte_inspector.py']:
    (ROOT/name).write_bytes((PACKET/name).read_bytes())
(ROOT/'CMakeLists.txt').write_bytes((PACKET/'HarnessCMakeLists.txt').read_bytes())
save(ROOT/'SELECTED_INPUT_PINS.json',[pin(ROOT/p) for p in ['writer_harness.cpp','byte_inspector.py','CMakeLists.txt']]+[pin(SETUP/'source/conanfile.py'),pin(SETUP/'build-env/bin/cmake')])
cmake=str(SETUP/'build-env/bin/cmake')
args=[cmake,'-S',str(ROOT),'-B',str(ROOT/'build'),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_STANDARD=17','-DCMAKE_C_COMPILER=gcc','-DCMAKE_CXX_COMPILER=g++','-DCMAKE_PREFIX_PATH='+str(SETUP/'build'),'-DPINNED_HICTK_SOURCE='+str(SETUP/'source'),'-DHICTK_ENABLE_TESTING=OFF','-DHICTK_ENABLE_FUZZY_TESTING=OFF','-DHICTK_BUILD_TOOLS=OFF','-DHICTK_BUILD_BENCHMARKS=OFF','-DHICTK_BUILD_EXAMPLES=OFF','-DHICTK_WITH_ARROW=OFF','-DHICTK_WITH_EIGEN=OFF','-DHICTK_ENABLE_TELEMETRY=OFF','-DHICTK_DOWNLOAD_TEST_DATASET=OFF','-DHICTK_ENABLE_GIT_VERSION_TRACKING=OFF','-DHICTK_GIT_TAG=v2.2.0','-DHICTK_GIT_HEAD_SHA1=473017312558cd805f470722c2c91a03b91df807','-DHICTK_GIT_IS_DIRTY=false','-DHICTK_GIT_RETRIEVED_STATE=true','-DHICTK_ASSUME_STD_FILESYSTEM_AVAIL=ON','-DENABLE_INTERPROCEDURAL_OPTIMIZATION=OFF']
if run(ROOT,'configure',args): raise RuntimeError('configure_failed')
if run(ROOT,'build',[cmake,'--build',str(ROOT/'build'),'--target','writer_harness','--parallel','2']): raise RuntimeError('build_failed')
binary=ROOT/'build/writer_harness'; native=PACKET/'prerequisite003/hictk'; original=PACKET/'native004/four.hic'
save(ROOT/'NATIVE_PINS.json',[pin(binary),pin(native),pin(original)])
run(ROOT,'ldd',['/usr/bin/ldd',str(binary)])
dependencies=[]
for token in (ROOT/'ldd.stdout.txt').read_text().split():
    if token.startswith('/') and Path(token).is_file(): dependencies.append(pin(token))
save(ROOT/'RUNTIME_PINS.json',dependencies)
sys.path.insert(0,str(ROOT)); from byte_inspector import inspect
for variant in ['valid','nan','zero','negative','inf','short','long']:
    path=ROOT/variant; path.mkdir()
    rc=run(path,'writer',[str(binary),str(original),str(path/'output.hic'),variant])
    if rc:
        save(path/'OUTCOME.json',{'variant':variant,'writer_exit':rc,'native_vector_written':False,'partial_output_pin':pin(path/'output.hic') if (path/'output.hic').exists() else None}); continue
    audit=inspect(path/'output.hic',path/'blocks'); save(path/'BYTE_AUDIT.json',audit)
    vector=audit['normalization_vectors'][0]
    values={'valid':[1.0,2.0,1.0,2.0],'nan':[1.0,'NaN',1.0,2.0],'zero':[1.0,0.0,1.0,2.0],'negative':[1.0,-2.0,1.0,2.0],'inf':[1.0,'+Inf',1.0,2.0]}
    assert vector['type']=='SYNTHETIC_DIVISIVE' and vector['values']==values[variant]
    dump_rc=run(path,'dump',['%s'%native,'dump','--resolution','10','--range','chrA','--balance','SYNTHETIC_DIVISIVE','--sorted',str(path/'output.hic')])
    raw_rc=run(path,'dump_raw',[str(native),'dump','--resolution','10','--range','chrA','--balance','NONE','--sorted',str(path/'output.hic')])
    weights_rc=run(path,'dump_weights',[str(native),'dump','--resolution','10','--table','weights','--balance','SYNTHETIC_DIVISIVE',str(path/'output.hic')])
    validate_rc=run(path,'validate',[str(native),'validate',str(path/'output.hic')])
    save(path/'OUTCOME.json',{'variant':variant,'writer_exit':rc,'native_vector_written':True,'vector_values':values[variant],'normalized_dump_exit':dump_rc,'raw_dump_exit':raw_rc,'weights_dump_exit':weights_rc,'validate_exit':validate_rc,'file':pin(path/'output.hic'),'scientific_weight_status':'valid' if variant=='valid' else ('masked_bin1' if variant=='nan' else 'invalid_bin1')})
    if variant=='valid':
        dump=[tuple(map(float,row.split())) for row in (path/'dump.stdout.txt').read_text().splitlines()]
        by_pair={(int(x),int(y)):value for x,y,value in dump}
        assert by_pair[0,2]==6 and by_pair[1,3]==0.5
    print(json.dumps({'variant':variant,'file':pin(path/'output.hic'),'vector':values[variant],'dump_exit':dump_rc}),flush=True)
save(ROOT/'INDEPENDENT_EXPECTATIONS.json',{'divisive_vector':[1,2,1,2],'normalization_formula':'C_ij / (w_i*w_j)','raw_anchor_0_2':6,'distance2_values':[6,0.5],'sum':6.5,'sum_squares':36.25,'population_count':2,'mean':3.25,'population_variance':7.5625,'fold_fraction':'24/13','fold':24/13,'nan_at_bin1':{'nominal_distance2_pairs':2,'masked_pairs':1,'valid_pairs':1,'mean':6,'fold':1},'zero_negative_inf':'invalid weight retained; no normalized scientific calculation claimed'})
