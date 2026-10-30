"""Execute the frozen closure and prove actual imports; no scientific run."""
from pathlib import Path
import hashlib
import json
import os
import sys

PIN = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
os.chdir(PIN)
sys.path.insert(0, str(PIN))
import pytest
code = pytest.main(['-q', '-p', 'no:cacheprovider', 'tests/test_literature_controlled_response_owner_calculations.py',
                    'tests/test_literature_controlled_response_calculations.py'])
imports = {}
for name, module in sorted(sys.modules.items()):
    location = getattr(module, '__file__', None)
    if location and Path(location).is_file() and (name.startswith('gene_annotation_episode') or '/site-packages/' in str(location)):
        path = Path(location).resolve()
        imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
local = {n:r for n,r in imports.items() if n.startswith('gene_annotation_episode')}
assert len(local) == 4
assert all(Path(r['path']).is_relative_to(PIN) for r in local.values())
manifest = json.loads((OUT / 'PIN_MANIFEST_001.json').read_text())
actual = {str(p.relative_to(PIN)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PIN.rglob('*')) if p.is_file()}
assert actual == manifest, 'Pin changed during execution or includes undeclared files'
(OUT / 'PIN_EXECUTION_RECEIPT_001.json').write_text(json.dumps({'pytest_exit_code': int(code),
    'cwd': str(Path.cwd()), 'sys_path': sys.path, 'python': sys.executable, 'version': sys.version,
    'project_imports': local, 'loaded_external_files': imports, 'pin_manifest_matches_after_execution': actual == manifest}, indent=2) + '\n')
raise SystemExit(code)
