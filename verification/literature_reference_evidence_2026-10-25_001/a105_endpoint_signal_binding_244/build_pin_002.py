"""Additive current-dependency snapshot; all production mutation remains owned."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
PIN=OWN/'pin_002'
assert not PIN.exists()
old=json.loads((OWN/'PIN_001.json').read_text())
for relative,digest in old['hashes'].items():
    assert hashlib.sha256((OWN/'pin_001'/relative).read_bytes()).hexdigest()==digest,relative
current=set()
for package in ('gene_annotation_episode','method_loop'):
    current.update(str(p.relative_to(ROOT)) for p in (ROOT/package).rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix in ('.py','.json','.toml','.txt','.md'))
current.update(['tests/test_literature_endpoint_signal_binding_244.py'])
extra=set()
fixture=ROOT/'verification/literature_reference_evidence_2026-10-25_001/figure_examples_001/cropped_first/state'
extra.update(str(p.relative_to(ROOT)) for p in fixture.rglob('*') if p.is_file())
hashes={}
for relative in set(old['hashes'])|current|extra:
    assert Path(relative).name!='GOAL.md'
    source=ROOT/relative if relative in current|extra else OWN/'pin_001'/relative
    raw=source.read_bytes();target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    hashes[relative]=hashlib.sha256(raw).hexdigest()
result={'version':'endpoint_signal_joined_pin_v1','base_pin':'PIN_001.json','base_hashes_verified_unchanged':True,
    'hashes':dict(sorted(hashes.items())), 'current_dependency_snapshot':sorted(current),
    'current_dependency_note':'Read-only copies of current local dependency files; no production ownership expansion or edits to those files.',
    'additional_controlled_fixture':sorted(extra),'production_owned':old['production_owned'],
    'actual_model_execution':False,'private_provider_payloads_inspected':False}
(OWN/'PIN_002.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'files':len(hashes),'pin':str(PIN),'controlled_old_fixture_files':len(extra)}))
