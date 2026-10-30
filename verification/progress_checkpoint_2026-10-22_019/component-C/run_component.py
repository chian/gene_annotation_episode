from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys,time
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-008')
EVIDENCE=Path('/tmp/direct-hmmer-C008-evidence-20261022-UHU41U')
PYTHON='/home/chia/repos/gene_annotation_episode/.venv/bin/python'
SELECTED='tests/test_direct_hmmer_timing_binding.py'
def snapshot():
    files={}
    for p in sorted([*ROOT.glob('gene_annotation_episode/**/*.py'),*ROOT.glob('tests/test_*.py')]):
        if p.is_symlink(): raise RuntimeError('unexpected_symlink')
        b=p.read_bytes();s=p.stat()
        files[str(p.relative_to(ROOT))]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
    return files
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
index=sys.argv[1]
out=EVIDENCE/('invocation-'+index);out.mkdir()
before=snapshot();write(out/'INPUTS_BEFORE.json',before)
command=[PYTHON,'-m','pytest','-q',SELECTED,'--basetemp',str(out/'pytest-fixtures'),'--junitxml',str(out/'results.xml')]
env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'tests')+os.pathsep+str(ROOT);env['PYTHONDONTWRITEBYTECODE']='1'
write(out/'COMMAND.json',{'argv':command,'cwd':str(ROOT),'PYTHONPATH':env['PYTHONPATH'],'limit':'C component only; concurrent A/B source is captured before/after, not a coherent full-worker pin claim'})
start=time.time()
with (out/'pytest.log').open('xb') as log:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
after=snapshot();write(out/'INPUTS_AFTER.json',after)
changed=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
owned=['gene_annotation_episode/'+name for name in ['assembled_service_setup.py','resource_service_setup.py','hmmer_resource_adapter.py','episode_services.py','episode_composition.py','api_planning_case_policy.py']]+[SELECTED]
write(out/'RESULTS.json',{'exit_code':result.returncode,'elapsed_seconds':time.time()-start,'changed_inputs':changed,'owned_inputs_unchanged':all(before[p]==after[p] for p in owned),'whole_snapshot_unchanged':not changed,'limits':'component invocation only; source-sensitive worker proof belongs to root after coherent freeze'})
# Explicit fresh basetemp is the retained original. A separate copy immediately
# captures membership and controls, including original alias target metadata.
fixtures=out/'pytest-fixtures'
if fixtures.exists():
    controls=[]
    for p in sorted(fixtures.rglob('*')):
        s=p.lstat();entry={'path':str(p.relative_to(fixtures)),'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev,'size':s.st_size}
        if p.is_symlink():entry.update(kind='symlink',target=os.readlink(p))
        elif p.is_file():entry.update(kind='file',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        elif p.is_dir():entry.update(kind='directory')
        else:raise RuntimeError('unexpected_special_fixture')
        controls.append(entry)
    shutil.copytree(fixtures,out/'preserved-fixtures',symlinks=True)
    write(out/'ORIGINAL_PRESERVATION.json',{'original':str(fixtures),'copy':str(out/'preserved-fixtures'),'members':controls})
print(json.dumps({'directory':str(out),'exit_code':result.returncode,'changed_inputs':changed}))
sys.exit(result.returncode)
