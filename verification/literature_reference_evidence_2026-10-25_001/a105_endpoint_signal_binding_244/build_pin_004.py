"""Additive scoped failed-history/structured-error fix; prior pins unchanged."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
PIN=OWN/'pin_004'
assert not PIN.exists()
old=json.loads((OWN/'PIN_003.json').read_text())
changes={'gene_annotation_episode/literature_endpoint_signal_storage.py',
    'tests/test_literature_endpoint_signal_binding_244.py'}
hashes={}
for relative,digest in old['hashes'].items():
    assert hashlib.sha256((OWN/'pin_003'/relative).read_bytes()).hexdigest()==digest,relative
    source=(ROOT if relative in changes else OWN/'pin_003')/relative
    raw=source.read_bytes();target=PIN/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    hashes[relative]=hashlib.sha256(raw).hexdigest()
(OWN/'PIN_004.json').write_text(json.dumps({'version':'endpoint_signal_joined_pin_v1','base_pin':'PIN_003.json',
    'base_hashes_verified_unchanged':True,'changed_paths':sorted(changes),'hashes':dict(sorted(hashes.items())),
    'changes':'External covariance witness spans join protected projection locations; wrong reference kind keeps ordinary source feedback; two focused controlled tests.',
    'actual_model_execution':False},indent=2)+'\n')
print(json.dumps({'files':len(hashes),'changed_paths':sorted(changes)}))
