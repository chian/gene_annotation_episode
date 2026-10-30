from pathlib import Path
import hashlib,json,os,stat
BASE=Path('/tmp/direct-hmmer-008-static-snapshot-20261022-001-zoe7igsh')
OUT=Path(__file__).parent

def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 raw=(BASE/'MANIFEST001.json').read_bytes()
 assert sha(raw)=='b0b92291abf520876f97524e887d8a5b4b242498183a492ed84195752d6fb90b'
 manifest=json.loads(raw);rows=manifest['files']
 members=set();dirs=[]
 for d,sub,files in os.walk(BASE,followlinks=False):
  d=Path(d);dirs.append(d)
  assert not d.is_symlink() and stat.S_IMODE(d.stat().st_mode)==0o555
  for name in sub:assert not (d/name).is_symlink()
  for name in files:
   p=d/name;assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink()
   members.add(str(p.relative_to(BASE)))
 assert members=={r['relative_path'] for r in rows}|{'MANIFEST001.json'} and len(rows)==725
 for row in rows:
  p=BASE/row['relative_path'];b=p.read_bytes()
  assert len(b)==row['bytes'] and sha(b)==row['sha256'] and stat.S_IMODE(p.stat().st_mode)==row['mode']
 source=read(BASE/'SOURCE_MANIFEST001.json')
 assert source['source_before_after_hash_stat_and_membership_equal'] and source['file_count']==707
 snapshot=BASE/'snapshot';copies=source['files'];runtime=[]
 for row in copies:
  p=BASE/row['copied_relative_path'];b=p.read_bytes()
  assert sha(b)==row['sha256'] and len(b)==row['bytes']
  assert stat.S_IMODE(p.stat().st_mode)==row['copied_mode']
  if row['relative_path'].endswith('.py') and row['relative_path'].split('/')[0] in {'gene_annotation_episode','method_loop'}:runtime.append(row)
 value=hashlib.sha256()
 for row in sorted(runtime,key=lambda x:x['relative_path']):value.update(row['relative_path'].encode()+b'\0'+bytes.fromhex(row['sha256']))
 assert len(runtime)==138 and value.hexdigest()=='6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30'
 assert read(BASE/'SOURCE_BEFORE001.json')['files']==read(BASE/'SOURCE_AFTER001.json')['files']
 result={'status':'verified_static_preservation_not_execution','manifest_sha256':sha(raw),'members_including_manifest':len(members),'directories':len(dirs),'snapshot_files':len(copies),'runtime_files':len(runtime),'runtime_pin':value.hexdigest(),'application_database_test_transport_control_calls':0,'limit':'Checks preserved copies and recorded before/after guards only; no current source reexecution or scientific validation.'}
 with (OUT/'RESULT001.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 (OUT/'RESULT001.json').chmod(0o444)
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
