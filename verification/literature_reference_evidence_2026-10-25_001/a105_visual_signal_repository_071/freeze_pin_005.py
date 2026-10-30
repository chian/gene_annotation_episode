"""Freeze actual repository/tests/runtime/assets; no scientific state copy."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
output=Path(__file__).resolve().parent
pin=output/'pin_005'
paths=[]
for package in ('gene_annotation_episode','method_loop'):
 paths.extend(p for p in (root/package).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
paths.extend(root/'tests'/f'test_literature_ratio_source_{part}.py' for part in ('inputs','calculations','validation','storage','readonly'))
paths.append(root/'pyproject.toml')
for directory in ('visual_signal_parent_review_067/text_locator_declarations_008','a105_visual_signal_reader_070/normative'):
 paths.extend(p for p in (root/'verification/literature_reference_evidence_2026-10-25_001'/directory).rglob('*') if p.is_file() and p.suffix in ('.json','.md','.py'))
paths.extend(output/name for name in ('verify_joined_005.py','freeze_pin_005.py'))
paths=list(dict.fromkeys(paths))
def sha(data):return hashlib.sha256(data).hexdigest()
before={str(p.relative_to(root)):sha(p.read_bytes()) for p in paths}
if pin.exists():raise SystemExit('never overwrite frozen pin')
for p in paths:
 target=pin/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
after={str(p.relative_to(root)):sha(p.read_bytes()) for p in paths}
frozen={name:sha((pin/name).read_bytes()) for name in before}
result={'evidence_class':'code/assets only; no live/private database copied','file_count':len(paths),'before':before,'after':after,'frozen':frozen,'coherent':before==after==frozen}
(output/'PIN_MANIFEST_005.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['coherent']
print(json.dumps({'pin':str(pin),'files':len(paths),'coherent':True}))
