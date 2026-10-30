"""Record this boundary's tests and hashes of the actual loaded repository code."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FILES = [
    'tests/test_scientific_process_return_runtime.py',
    'tests/test_scientific_process_frozen_results.py',
    'tests/test_scientific_process_episodes.py',
    'tests/test_scientific_process_reports.py',
    'tests/test_scientific_process_return_records.py',
]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

before = {str(path.resolve()): digest(path) for folder in
    ('gene_annotation_episode', 'method_loop', 'tests')
    for path in (ROOT / folder).rglob('*.py')}
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
with (HERE / 'pytest.log').open('w') as output, redirect_stdout(output), redirect_stderr(output):
    status = pytest.main(['-q', '--tb=short', *FILES])
loaded = {}
for module in tuple(sys.modules.values()):
    name = getattr(module, '__file__', None)
    if name:
        path = Path(name).resolve()
        if str(path) in before:
            loaded[str(path.relative_to(ROOT))] = {
                'before': before[str(path)], 'after': digest(path)}
changed = [name for name, value in loaded.items() if value['before'] != value['after']]
report = {'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'pytest_arguments': ['-q', '--tb=short', *FILES], 'exit_code': int(status),
    'elapsed_seconds': time.monotonic() - clock, 'loaded_source_hashes': loaded,
    'changed_loaded_sources': changed,
    'qualification': 'Scripted decisions and credit fixtures; real shared Workflow, Store, typed admission, original-request reconstruction and redelivery. No model science, live API, HPC, or actual detached subprocess claimed.',
    'specific_pending_NCBI_job_verification_included': False}
(HERE / 'VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'exit_code': int(status), 'changed_loaded_sources': changed,
    'log': str(HERE / 'pytest.log')}))
raise SystemExit(int(status) or bool(changed))
