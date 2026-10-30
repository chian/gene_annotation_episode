"""Reproduce selected shared regressions using immutable pre-360 modules."""
from pathlib import Path
import hashlib
import importlib
import json
import sys

import gene_annotation_episode
import pytest

packet = Path(__file__).resolve().parent
baseline = packet / 'baseline'
pins = json.loads((baseline / 'pins.json').read_bytes())
for name, expected in pins.items():
    assert hashlib.sha256((baseline / name).read_bytes()).hexdigest() == expected
gene_annotation_episode.__path__.insert(0, str(baseline))
loaded = {}
for name, expected in pins.items():
    module = importlib.import_module('gene_annotation_episode.' + name.removesuffix('.py'))
    path = Path(module.__file__).resolve()
    assert path == baseline / name
    loaded[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
Path('baseline_modules.json').write_text(json.dumps(loaded, indent=2) + '\n')
print(json.dumps({'baseline_modules': loaded}), flush=True)
raise SystemExit(pytest.main(sys.argv[1:]))
