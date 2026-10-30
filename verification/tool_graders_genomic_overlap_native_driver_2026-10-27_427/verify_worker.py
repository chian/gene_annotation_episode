"""Run real native component cases and labeled synthetic failures under local_jobs."""
import json
from pathlib import Path
import sys

import pytest

attempt, snapshot = map(Path, sys.argv[1:])
status = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(attempt / 'temporary/pytest'),
    '--rootdir', str(snapshot), '--junitxml', str(attempt / 'pytest.xml'),
    str(snapshot / 'tests/test_native_genomic_overlap_local.py'),
    str(snapshot / 'tests/test_native_genomic_overlap_driver.py')])
examples = {}
for name in ('ACTUAL_NATIVE_G1.json', 'ACTUAL_LIFECYCLE.json', 'ACTUAL_NEVER_STARTED.json', 'ACTUAL_KILLED.json', 'SYNTHETIC_FAILURE.json'):
    examples[name] = [str(path.relative_to(attempt)) for path in (attempt / 'temporary/pytest').rglob(name)]
(attempt / 'examples.json').write_text(json.dumps(examples, indent=2) + '\n')
raise SystemExit(status)
