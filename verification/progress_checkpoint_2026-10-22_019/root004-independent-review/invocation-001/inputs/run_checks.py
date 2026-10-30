"""One explicit engineering pytest invocation with retained input/output evidence."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys,time
from datetime import datetime,timezone

ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-008')
EVIDENCE=Path(__file__).parent
PYTHON='/home/chia/repos/gene_annotation_episode/.venv/bin/python'
def snapshot():
 rows={}
 for name in ('gene_annotation_episode','method_loop','tests'):
  for p in sorted((ROOT/name).rglob('*.py')):
   assert not p.is_symlink()
   b=p.read_bytes();s=p.stat()
   rows[p.relative_to(ROOT).as_posix()]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev}
 return rows
def save(p,x):
 with p.open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
def now():return datetime.now(timezone.utc).isoformat()
def main():
 index=sys.argv[1];selected=sys.argv[2:]
 assert selected and all(s.startswith('tests/') and '..' not in Path(s.split('::')[0]).parts for s in selected)
 out=EVIDENCE/('invocation-'+index);out.mkdir()
 before=snapshot();save(out/'INPUTS_BEFORE.json',before)
 argv=[PYTHON,'-m','pytest','-q',*selected,'--basetemp',str(out/'pytest-fixtures'),'--junitxml',str(out/'results.xml')]
 env={**os.environ,'PYTHONPATH':str(ROOT/'tests')+os.pathsep+str(ROOT),'PYTHONDONTWRITEBYTECODE':'1'}
 save(out/'COMMAND.json',{'argv':argv,'cwd':str(ROOT),'environment_overrides':{k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE')},'started_at_utc':now(),'scope':'Explicit isolated engineering checks; no public service or configured model. Input changes are reported, not hidden.'})
 begin=time.monotonic()
 with (out/'pytest.log').open('xb') as stream:
  process=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
 after=snapshot();save(out/'INPUTS_AFTER.json',after)
 changed=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
 fixture=out/'pytest-fixtures'
 if fixture.exists():
  controls=[]
  for p in sorted(fixture.rglob('*')):
   s=p.lstat();r={'path':p.relative_to(fixture).as_posix(),'mode':stat.S_IMODE(s.st_mode),'bytes':s.st_size,'inode':s.st_ino,'device':s.st_dev,'mtime_ns':s.st_mtime_ns}
   if p.is_symlink():r.update(kind='symlink',target=os.readlink(p))
   elif stat.S_ISREG(s.st_mode):r.update(kind='file',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
   elif stat.S_ISDIR(s.st_mode):r.update(kind='directory')
   else:raise RuntimeError('unexpected_special_fixture_preserved_in_place')
   controls.append(r)
  shutil.copytree(fixture,out/'preserved-fixtures',symlinks=True)
  save(out/'ORIGINAL_PRESERVATION.json',{'original':str(fixture),'copy':str(out/'preserved-fixtures'),'members':controls})
 result={'exit_code':process.returncode,'finished_at_utc':now(),'elapsed_seconds':time.monotonic()-begin,'changed_inputs':changed,'source_and_tests_unchanged':not changed,'selected':selected,'directory':str(out)}
 save(out/'RESULTS.json',result);print(json.dumps(result,sort_keys=True),flush=True)
 return process.returncode
if __name__=='__main__':raise SystemExit(main())
