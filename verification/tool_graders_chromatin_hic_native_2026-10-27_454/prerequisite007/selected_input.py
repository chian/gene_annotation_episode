"""Isolated official-source build prerequisites for a tiny native writer harness."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT=Path.cwd(); PACKET=ROOT.parent
def save(name,value): (ROOT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
(ROOT/'tmp').mkdir()
env={**os.environ,'TMPDIR':str(ROOT/'tmp'),'CONAN_HOME':str(ROOT/'conan'),'CONAN_CPU_COUNT':'2','CMAKE_BUILD_PARALLEL_LEVEL':'2','CMAKE_POLICY_VERSION_MINIMUM':'3.5','CC':'gcc','CXX':'g++','HICTK_NO_TELEMETRY':'1'}
def run(name,args):
    save(name+'.request.json',{'argv':args,'cwd':str(ROOT),'environment_overrides':{k:env[k] for k in ['TMPDIR','CONAN_HOME','CONAN_CPU_COUNT','CMAKE_BUILD_PARALLEL_LEVEL','CMAKE_POLICY_VERSION_MINIMUM','CC','CXX','HICTK_NO_TELEMETRY']}})
    with (ROOT/(name+'.stdout.txt')).open('wb') as out,(ROOT/(name+'.stderr.txt')).open('wb') as err:
        proc=subprocess.run(args,cwd=ROOT,env=env,stdout=out,stderr=err)
    save(name+'.result.json',{'returncode':proc.returncode})
    if proc.returncode: raise RuntimeError(f'{name}: exit {proc.returncode}')
run('venv',[sys.executable,'-m','venv',str(ROOT/'build-env')])
python=ROOT/'build-env/bin/python'
run('pip',[str(python),'-m','pip','install','--no-input','--disable-pip-version-check','--no-cache-dir','--report',str(ROOT/'pip-report.json'),'cmake==3.31.10','conan==2.22.1','ninja==1.13.0'])
env['PATH']=str(ROOT/'build-env/bin')+os.pathsep+env['PATH']
source=ROOT/'source'
shutil.copytree(PACKET/'prerequisite002/source/hictk-473017312558cd805f470722c2c91a03b91df807',source)
run('conan-version',[str(ROOT/'build-env/bin/conan'),'--version'])
run('cmake-version',[str(ROOT/'build-env/bin/cmake'),'--version'])
run('profile',[str(ROOT/'build-env/bin/conan'),'profile','detect'])
run('conan-install',[str(ROOT/'build-env/bin/conan'),'install',str(source),'--build=missing','-pr','default','-s','build_type=Release','-s','compiler.cppstd=17','--output-folder='+str(ROOT/'build'),'-o','hictk/*:with_cli_tool_deps=False','-o','hictk/*:with_telemetry_deps=False','-o','hictk/*:with_unit_testing_deps=False','-o','hictk/*:with_arrow=False','-o','hictk/*:with_eigen=False','--format=json'])
print(json.dumps({'build_env':str(ROOT/'build-env'),'source':str(source),'conan_home':str(ROOT/'conan')}))
