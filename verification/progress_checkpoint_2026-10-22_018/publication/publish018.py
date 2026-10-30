"""Publish an additive progress record with exact sealed inputs; no application work."""
from pathlib import Path
import ctypes,hashlib,json,os,re,stat,tempfile

ROOT=Path('/home/chia/repos/gene_annotation_episode')
OLD=ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_017.md'
DOC=ROOT/'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_018.md'
OUT=ROOT/'verification/progress_checkpoint_2026-10-22_018'
OLD_SHA='8928c1ec3c5138bf44a46ea200dad283b70a1099543801e65114298c01278e26'
BUNDLES=(
 ('resource-plan','/tmp/configured-resource-investigation-plan-20261022-001-DAGmrtaT','MANIFEST_FINAL001.json','caf0fcfe6c29fcb4e31ddc348ed0d73f0ada022d0d949ecbd8dfeb233038e8c2','members'),
 ('resource-preparation','/tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE','MANIFEST_FINAL001.json','9a1552710f364f918c520ab2c1eb6f58727fbf4a2d2d15d445bcf128f21a5d27','members'),
 ('resource-prepared-output','/tmp/configured-resource-preparation-output-handoff-20261022-001-0c8q1ose','MANIFEST_FINAL001.json','38729c8fe75993301ba1bc5c2a22b037d0508840caf5485b4ee28860b80568f5','members'),
 ('resource-independent-review','/tmp/configured-resource-preparation-independent-review-20261022-001-laR09p2B','MANIFEST_FINAL001.json','9b574abbcef93cbb8d9a693453e89ee621d69122d00e77cf68c8902347878edd','regular_members'),
 ('resource-launch-plan','/tmp/configured-resource-launch-plan-20261022-001-xr3c7got','MANIFEST_FINAL001.json','1f402b96078b27cab129be2ff254bfcc2bbafcb15f7aa27903117664599eb0d7','members'),
 ('literature-technical-feedback','/tmp/configured-literature-technical-feedback-R-20261022-_73palcs','MANIFEST001.json','5926def2e146060c792acb529b01c7b1b967cfdc3daf9ec641a737df54c89ef8','files'),
 ('direct-timing-contract','/tmp/direct-hmmer-timing-contract-R-20261022-hci0ry6b','MANIFEST_FINAL001.json','da577446cfa0d252edb3037b437f49a9d19ff6301e2b1c5229208308509da781','files'))

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def read(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 raw=p.read_bytes();t=p.lstat()
 def witness(v):return {'bytes':v.st_size,'mode':stat.S_IMODE(v.st_mode),'mtime_ns':v.st_mtime_ns,'device':v.st_dev,'inode':v.st_ino,'sha256':sha(raw)}
 assert witness(s)==witness(t) and len(raw)==t.st_size
 return raw,witness(t)
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb',closefd=False) as f:f.write(b);f.flush()
  os.fchmod(fd,0o444);os.fsync(fd)
 finally:os.close(fd)
def sync(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
def main():
 assert not os.path.lexists(DOC) and not os.path.lexists(OUT)
 old,_=read(OLD);assert sha(old)==OLD_SHA
 text=old.decode();fixed=text[text.index('## Retained correction checklist'):text.index('## Additional actual scientific qualifications under frozen006')]
 assert len(re.findall(r'^- \[[ x]\] \*\*',fixed,re.M))==41
 stage=Path(tempfile.mkdtemp(prefix='.'+OUT.name+'-staging-',dir=OUT.parent));controls={};inventories={}
 def copy(p,name):
  b,w=read(p);write(stage/name,b);assert read(p)[1]==w
  controls[name]={'source':str(p),'before':w,'after':w,'copy_equals_source':True}
 for prefix,directory,name,expected,key in BUNDLES:
  directory=Path(directory);raw,_=read(directory/name);assert sha(raw)==expected
  rows=json.loads(raw)[key]
  if isinstance(rows,list):rows={r['path']:r for r in rows}
  actual=set()
  for p in directory.rglob('*'):
   assert not p.is_symlink() and (p.is_dir() or stat.S_ISREG(p.lstat().st_mode))
   if p.is_file():actual.add(p.relative_to(directory).as_posix())
  assert actual==set(rows)|{name},(prefix,actual^(set(rows)|{name}))
  for member,row in rows.items():
   assert not Path(member).is_absolute() and '..' not in Path(member).parts
   b,w=read(directory/member);assert sha(b)==row['sha256'] and len(b)==row.get('bytes',row.get('size'))
   assert not w['mode']&0o222
   copy(directory/member,prefix+'/'+member)
  copy(directory/name,prefix+'/'+name)
  inventories[prefix]={'source':str(directory),'manifest':name,'sha256':expected,'member_count':len(rows)}
 first=Path('/tmp/configured-resource-investigation-first-request-proof-20261022-001')
 names=('RESULT001.json','FIRST_REQUEST_RAW001.json','FIRST_CONTEXT_DERIVED001.json','FIRST_MODEL_CONTEXT_DERIVED001.json','LOCAL_COMMISSION_FRAME_DERIVED001.json','RUNTIME_SETTINGS001.json')
 assert {p.name for p in first.iterdir()}==set(names)
 assert read(first/'RESULT001.json')[1]['sha256']=='1f7622f503c368827cf0023d5b239bb3374f868279c626ad6c0e1b7071cb260b'
 for n in names:copy(first/n,'resource-first-request/'+n)
 launch=Path('/tmp/configured-resource-investigation-launch-20261022-001')
 for n in ('SOURCE_BEFORE001.json','LAUNCH_COMMAND001.json','PROCESS_STARTED001.json'):copy(launch/n,'resource-actual-launch/'+n)
 for n in ('CONFIGURED_RESOURCE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md','CONFIGURED_RESOURCE_CALLER_LAUNCH_2026-10-22_001.md','DIRECT_HMMER_TIMING_SCOPE_2026-10-22_001.md'):copy(ROOT/'docs'/n,'scopes/'+n)
 copy(Path('/tmp/gene-annotation-configured-caller-20261022-008/GENERATION_BASELINE_008.json'),'direct-timing-baseline/GENERATION_BASELINE_008.json')
 copy(OLD,'lineage/PROGRESS017.md');copy(ROOT/'verification/progress_checkpoint_2026-10-22_017/MANIFEST.json','lineage/MANIFEST017.json')
 copy(Path(__file__),'publication/publish018.py');copy(Path(__file__).parent/'NEW_EVIDENCE.md','publication/NEW_EVIDENCE.md')
 body=('# Separate permanent progress record018\n\nThis additive record follows unchanged017, SHA256 '+OLD_SHA+'. Its same41 IDs, order, checked states and historical descriptions follow verbatim. New finite evidence follows them. No whole-goal item is closed by this record.\n\n'+fixed+(Path(__file__).parent/'NEW_EVIDENCE.md').read_text())
 assert body[body.index('## Retained correction checklist'):body.index('## Actual resource preparation, independent verification and launch')]==fixed
 write(stage/'PROGRESS.md',body.encode());write(stage/'EXTERNAL_REFERENCES.json',encoded({'input_bundles':inventories,'goal_status':'active_incomplete','private_scientific_logs_copied':0,'live_databases_copied':0,'older_records_replaced':0}))
 for row in controls.values():assert read(Path(row['source']))[1]==row['before']
 write(stage/'COPY_CONTROLS.json',encoded(controls))
 members={p.relative_to(stage).as_posix():{'sha256':read(p)[1]['sha256'],'bytes':p.stat().st_size,'mode':'0444'} for p in stage.rglob('*') if p.is_file()}
 write(stage/'MANIFEST.json',encoded({'version':'permanent_progress_checkpoint_v1','members':members,'report_sha256':sha(body.encode()),'report_path':str(DOC),'fixed41_verbatim':True,'goal_status':'active_incomplete'}))
 for p in sorted((p for p in stage.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):p.chmod(0o555);sync(p)
 stage.chmod(0o555);sync(stage)
 libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2;rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
 assert rename(-100,os.fsencode(stage),-100,os.fsencode(OUT),1)==0,ctypes.get_errno()
 sync(OUT.parent);os.link(OUT/'PROGRESS.md',DOC,follow_symlinks=False);sync(DOC.parent)
 assert read(OLD)[0]==old and read(DOC)[0]==read(OUT/'PROGRESS.md')[0]
 for n,row in members.items():
  b,w=read(OUT/n);assert sha(b)==row['sha256'] and len(b)==row['bytes'] and w['mode']==0o444
 print(json.dumps({'report':str(DOC),'report_sha256':sha(body.encode()),'manifest_sha256':read(OUT/'MANIFEST.json')[1]['sha256'],'members':len(members),'fixed41_verbatim':True,'goal_status':'active_incomplete'},sort_keys=True))
if __name__=='__main__':main()
