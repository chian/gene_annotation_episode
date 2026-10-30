"""Immediately preserve one unique pytest basetemp without opening its DBs."""
import hashlib,json,shutil,stat,sys
from pathlib import Path
source=Path(sys.argv[1]);destination=Path(sys.argv[2]);assert source.is_dir() and not destination.exists()
destination.mkdir()
rows={};symlinks={};stable=True
for path in sorted(source.rglob('*')):
 rel=path.relative_to(source).as_posix()
 if path.is_symlink():
  symlinks[rel]=str(path.readlink());continue
 if not path.is_file():continue
 before=path.stat();body=path.read_bytes();sha=hashlib.sha256(body).hexdigest()
 target=destination/'raw-tree'/rel;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as handle:handle.write(body)
 shutil.copystat(path,target)
 after=path.stat()
 unchanged=(before.st_size==after.st_size==len(body) and before.st_mtime_ns==after.st_mtime_ns
  and stat.S_IMODE(before.st_mode)==stat.S_IMODE(after.st_mode)
  and hashlib.sha256(path.read_bytes()).hexdigest()==sha)
 stable &= unchanged
 rows[rel]={'sha256':sha,'bytes':len(body),'mode':f'{stat.S_IMODE(before.st_mode):04o}',
  'mtime_ns':before.st_mtime_ns,'source_stable_during_copy':unchanged}
current={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file() and not p.is_symlink()}
stable &= current==set(rows)
record={'source':str(source),'files':rows,'file_count':len(rows),'total_bytes':sum(x['bytes']for x in rows.values()),
 'source_membership_and_bytes_sizes_modes_mtimes_stable':stable,'pytest_alias_symlinks_not_followed':symlinks,
 'databases_opened':0,'claim_limit':'Isolated synthetic fixture evidence; original paths preserved as provenance, no relocated resumability claim.'}
(destination/'PRESERVATION.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items()if k not in {'files','pytest_alias_symlinks_not_followed'}},sort_keys=True))
assert rows and stable, 'Raw fixture is absent or unstable; retain output but do not claim complete preservation'
