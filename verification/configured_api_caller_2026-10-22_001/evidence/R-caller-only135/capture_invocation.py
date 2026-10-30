"""Stdlib evidence capture only; no application imports or SQLite connections."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-006')
OUT=Path(__file__).parent
phase=sys.argv[1]
assert phase in {'before','after'}
files={}
for package in ['gene_annotation_episode','method_loop','tests']:
 for p in sorted((ROOT/package).rglob('*.py')):
  b=p.read_bytes();files[p.relative_to(ROOT).as_posix()]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
pin=hashlib.sha256()
for rel,row in sorted(files.items()):
 if not rel.startswith('tests/'):
  pin.update(rel.encode()+b'\0'+bytes.fromhex(row['sha256']))
baseline_path=ROOT/'GENERATION_BASELINE_006.json'
baseline=json.loads(baseline_path.read_text())
for rel,row in baseline['files'].items():
 assert files[rel]==row, (rel,files[rel],row)
assets={}
for category in ['static_assets','instructions']:
 for rel,row in baseline[category].items():
  body=(ROOT/rel).read_bytes()
  actual={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
  assert actual['sha256']==row['sha256'] and actual['bytes']==row['bytes'],rel
  assets[rel]=actual
record={'phase':phase,'checkout':str(ROOT),'runtime_pin':pin.hexdigest(),'files':files,
 'runtime_count':sum(not name.startswith('tests/') for name in files),
 'test_count':sum(name.startswith('tests/') for name in files),
 'baseline_file_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
 'all348_parent_source_test_bytes_unchanged':True,
 'static_and_instruction_files':assets,
 'all319_parent_assets_and8_instructions_unchanged':True}
target=OUT/(sys.argv[2]+'-'+phase+'.json')
with target.open('x') as handle:handle.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'},sort_keys=True))
