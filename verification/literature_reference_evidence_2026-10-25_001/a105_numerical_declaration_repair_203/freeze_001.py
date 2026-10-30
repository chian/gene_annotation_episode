"""Freeze code/assets only, excluding unrelated unbound205 construction."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
base=Path(__file__).resolve().parent
pin=base/'pin_001'
if pin.exists():raise RuntimeError('Preserve original frozen pin')
pin.mkdir();manifest={};excluded=[]
for directory in ('gene_annotation_episode','method_loop'):
 for path in (root/directory).rglob('*'):
  if not path.is_file() or '__pycache__' in path.parts or path.name=='GOAL.md':continue
  relative=path.relative_to(root)
  if 'literature_measurement_validation_' in path.name:
   excluded.append(str(relative));continue
  destination=pin/relative;destination.parent.mkdir(parents=True,exist_ok=True)
  content=path.read_bytes();destination.write_bytes(content);manifest[str(relative)]=hashlib.sha256(content).hexdigest()
for path in (root/'tests').glob('*.py'):
 if 'measurement_validation_' in path.name or '_205' in path.stem:
  excluded.append(str(path.relative_to(root)));continue
 relative=path.relative_to(root);destination=pin/relative;destination.parent.mkdir(exist_ok=True)
 content=path.read_bytes();destination.write_bytes(content);manifest[str(relative)]=hashlib.sha256(content).hexdigest()
(pin/'pytest.ini').write_text('[pytest]\npythonpath = . tests\n')
manifest['pytest.ini']=hashlib.sha256((pin/'pytest.ini').read_bytes()).hexdigest()
record={'scope':'Code-only fixed203 implementation/presentation proof after final199 handoff and announced206 display correction. No original papers, source packets, actual model/provider logs or run databases copied. Unbound205modules/tests excluded; no205imports or integration claimed.','excluded_unbound_205':excluded,'hashes':manifest}
(base/'FINAL_PIN_001.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'fixed_files':len(manifest),'excluded_unbound_205':excluded,'pin':str(pin)}))
