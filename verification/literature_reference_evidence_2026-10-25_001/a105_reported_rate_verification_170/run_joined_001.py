"""Independent root verification, frozen imports and retained raw test evidence."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_001'
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
os.chdir(PIN)
os.environ['RATE_OBSERVATION_PROOF_DIR'] = str(HERE / 'original_source_episode_001')
import pytest

SELECTION = [
    'tests/test_literature_rate_observations_166.py',
    'tests/test_literature_rate_replicate_binding_163.py',
    'tests/test_communication.py',
    'tests/test_literature_experimental_prompt.py',
    'tests/test_literature_rate_replicates.py',
]

def main():
    report = HERE / 'ROOT_JOINED_001.xml'
    if report.exists():
        raise RuntimeError('Never overwrite a retained invocation')
    files = json.loads((HERE / 'PIN_001.json').read_text())['files']
    started = time.monotonic()
    code = pytest.main(['-q', '--tb=short', '-p', 'no:cacheprovider',
        '--basetemp=' + str(HERE / 'run001'), '--junitxml=' + str(report), *SELECTION])
    imports = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and name.startswith(('gene_annotation_episode', 'method_loop', 'test_')):
            imports[name] = str(Path(filename).resolve())
    outside = {name: filename for name, filename in imports.items()
        if not Path(filename).is_relative_to(PIN)}
    changed = [name for name, digest in files.items()
        if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
    result = {'pytest_exit_code': int(code), 'elapsed_seconds': time.monotonic() - started,
        'selection': SELECTION, 'pinned_file_count': len(files),
        'changed_pinned_files': changed, 'imported_module_count': len(imports),
        'imports_outside_pin': outside,
        'scope': 'Frozen final source-bound XLSX operation, numerical partials, scoped typed admission, original-source controlled shared-loop and cold read-only reconstruction, plus focused existing regressions. Controlled choices are not actual model science or A105 scientific adequacy.'}
    (HERE / 'ROOT_IMPORTS_001.json').write_text(json.dumps(imports, indent=2) + '\n')
    (HERE / 'ROOT_RESULT_001.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return int(code) or bool(outside) or bool(changed)

if __name__ == '__main__':
    raise SystemExit(main())
