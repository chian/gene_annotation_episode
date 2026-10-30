"""Record exact owned deltas and preservation, then seal the076 artifact tree."""
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
import runpy
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PIN = OUT / 'pin_001'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((OUT / 'BEFORE_001.json').read_text())
proof = {path: {'before': digest, 'after': sha(ROOT / path)} for path, digest in before['protected'].items()}
assert all(p['before'] == p['after'] for p in proof.values())
(OUT / 'PROTECTED_HISTORY_PROOF_001.json').write_text(json.dumps({'all_match': True, 'files': proof}, indent=2) + '\n')
owned = {}
diff = []
for name, previous in before['owned_actual_current'].items():
    old = OUT / 'before_001' / name
    current = ROOT / name
    assert sha(old) == previous
    assert sha(current) == sha(PIN / name)
    delta = list(difflib.unified_diff(old.read_text().splitlines(keepends=True), current.read_text().splitlines(keepends=True),
        fromfile='actual_before/' + name, tofile='actual_after/' + name))
    owned[name] = {'before': previous, 'after': sha(current), 'added_lines': sum(s.startswith('+') and not s.startswith('+++') for s in delta),
        'removed_lines': sum(s.startswith('-') and not s.startswith('---') for s in delta)}
    diff.extend(delta)
(OUT / 'OWNED_TWO_FILE_DELTA_001.patch').write_text(''.join(diff))
(OUT / 'OWNED_TWO_FILE_DELTA_001.json').write_text(json.dumps(owned, indent=2) + '\n')
# Execute constructed examples from the pin, never from a source-reader packet.
sys.path.insert(0, str(PIN))
f = runpy.run_path(str(PIN / 'tests/test_literature_controlled_response_owner_calculations.py'))
examples = {}
for index in (0, 3):
    inputs = f['shared']()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    row = inputs['arms'][f['ROLES'][index]]
    f['graph'](row, 10, 9.9, 10.1) if index == 0 else f['graph'](row)
    row['origin'] = 'synthetic'
    examples['active_synthetic_graph' if index == 0 else 'canceled_synthetic_graph'] = f['calculate'](inputs)
inputs = deepcopy(examples['canceled_synthetic_graph']['inputs'])
row = inputs['arms'][f['ROLES'][3]]
row['normalization_id'] = None
row['meaning_statuses']['normalization'] = 'unknown'
examples['canceled_synthetic_graph_unknown_science'] = f['calculate'](inputs)
(OUT / 'ACTUAL_PIN_EXAMPLES_001.json').write_text(json.dumps({'constructed_only': True, 'examples': examples}, indent=2, allow_nan=False) + '\n')
imports = {n: str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if n.startswith('gene_annotation_episode') and getattr(m,'__file__',None)}
assert all(Path(p).is_relative_to(PIN) for p in imports.values())
(OUT / 'EXAMPLE_IMPORT_PROOF_001.json').write_text(json.dumps(imports, indent=2) + '\n')
files = [p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('ARTIFACT_MANIFEST_001.json', 'SHA256SUMS_001.txt')]
manifest = {str(p.relative_to(OUT)): sha(p) for p in files}
(OUT / 'ARTIFACT_MANIFEST_001.json').write_text(json.dumps(manifest, indent=2) + '\n')
files.append(OUT / 'ARTIFACT_MANIFEST_001.json')
(OUT / 'SHA256SUMS_001.txt').write_text(''.join(sha(p)+'  '+str(p.relative_to(OUT))+'\n' for p in sorted(files)))
print(json.dumps({'owned_delta':owned,'protected_count':len(proof),'manifest_payloads':len(manifest),'checksum_lines':len(files)},indent=2))
