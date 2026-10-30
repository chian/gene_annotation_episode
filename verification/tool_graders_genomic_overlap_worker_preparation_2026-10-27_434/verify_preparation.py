"""Execute focused 434 tests inside the actual existing local_jobs boundary."""
from pathlib import Path
import json
import sys
import pytest

attempt, snapshot = map(Path, sys.argv[1:3])
status = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(attempt / 'temporary/pytest'),
    '--rootdir', str(snapshot), '--junitxml', str(attempt / 'pytest.xml'),
    str(snapshot / 'tests/test_native_genomic_overlap_preparation.py'), *sys.argv[3:]])
examples = {name: [str(p.relative_to(attempt)) for p in (attempt / 'temporary/pytest').rglob(name)]
    for name in ('ACTUAL_WORKER_EXECUTION.json', 'SAVED_RECALCULATION.json', 'RECOVERY.json',
                 'ACTUAL_NONZERO_WORKER.json', 'INJECTED_TERMINAL_FAILURE.json')}
(attempt / 'examples.json').write_text(json.dumps(examples, indent=2) + '\n')
raise SystemExit(status)
