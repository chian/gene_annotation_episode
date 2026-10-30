import hashlib,json,sys
from pathlib import Path
root=Path('/tmp/gene-annotation-api-caller-20261022-006p-001')
expected=json.loads((root/'FROZEN_INPUTS001.json').read_text())
assert hashlib.sha256((root/'FROZEN_INPUTS001.json').read_bytes()).hexdigest()=='4f05f71ebc0e95e7d6b20c671d66dab917dbd366c50b86bac66ac38a38391c9d'
assert not (root/'gene_annotation_episode/scientific_checkpoint_fork.py').exists()
files={}
for rel,row in expected['files'].items():
 body=(root/rel).read_bytes();actual={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
 assert actual['sha256']==row['sha256'] and actual['bytes']==row['bytes'],rel
 files[rel]=actual
runtime=sorted(p.relative_to(root).as_posix() for package in ['gene_annotation_episode','method_loop'] for p in(root/package).rglob('*.py'))
tests=sorted(p.relative_to(root).as_posix() for p in(root/'tests').rglob('*.py'))
assert len(runtime)==135 and len(tests)==216
pin=hashlib.sha256()
for rel in runtime:pin.update(rel.encode()+b'\0'+bytes.fromhex(files[rel]['sha256']))
assert pin.hexdigest()=='515d23ed50bd84cfa518ea5a4cf56d84ffca1ad052ac775c5acb1187f2520a49'
out=Path(__file__).parent/('calleronly001-'+sys.argv[1]+'.json')
with out.open('x')as handle:handle.write(json.dumps({'status':'frozen_calleronly_input_verified','phase':sys.argv[1],'checkout':str(root),'runtime_pin':pin.hexdigest(),'runtime_count':135,'test_count':216,'all678_declared_files_match':True,'files':files},sort_keys=True,indent=2)+'\n')
print(json.dumps({'phase':sys.argv[1],'runtime_pin':pin.hexdigest(),'runtime_count':135,'test_count':216,'declared_files_verified':len(files)},sort_keys=True))
