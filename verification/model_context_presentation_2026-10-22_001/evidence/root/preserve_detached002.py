from pathlib import Path
from hashlib import sha256
import json,shutil,stat
BASE=Path('/tmp/model-context-detached-stable-20261022-002'); O=Path('/tmp/model-context-root-005-evidence'); choices=[p for p in BASE.glob('test_opt_in_actual_worker*') if p.is_dir() and not p.is_symlink()];assert len(choices)==1; S=choices[0]; D=O/'PRESERVED_DETACHED002';assert S.is_dir() and not D.exists(); rows={}; h=lambda p:sha256(p.read_bytes()).hexdigest()
for p in S.rglob('*'):
 assert not p.is_symlink(),str(p)
 if p.is_file():
  s=p.stat();rows[p.relative_to(S).as_posix()]={'sha256':h(p),'bytes':s.st_size,'mode':format(stat.S_IMODE(s.st_mode),'04o'),'mtime_ns':s.st_mtime_ns}
assert len(rows)>50
shutil.copytree(S,D/'raw-tree')
for rel,v in rows.items():
 p=S/rel;q=D/'raw-tree'/rel;s=p.stat();assert h(p)==h(q)==v['sha256'] and s.st_size==q.stat().st_size==v['bytes'] and s.st_mtime_ns==v['mtime_ns'] and format(stat.S_IMODE(s.st_mode),'04o')==v['mode']
assert {p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file()}==set(rows)
r={'version':'stable_detached002_preservation_v1','source':str(S),'basetemp':str(BASE),'originals_unchanged':True,'files':rows,'first_passing_pytest906_fixture_preserved':False,'this_fixture_from_separate_repeat':True,'test_log_sha256':h(O/'connected002.log'),'test_xml_sha256':h(O/'connected002.xml'),'runtime_pin':'2c9dc895d0e7c6fa6f6d4df140cb9b88e1274894c8dc7213c46b4580dec68428','original_absolute_paths_retained':True,'copied_databases_claimed_resumable':False}
with (D/'PRESERVATION.json').open('x') as f:f.write(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps({'source':str(S),'raw_files':len(rows),'raw_bytes':sum(v['bytes'] for v in rows.values()),'preservation_sha256':h(D/'PRESERVATION.json')}))
