"""Run retained-value return tests under the selected bounded reservation."""
from pathlib import Path
import json
import sys
import pytest
attempt, snapshot = map(Path, sys.argv[1:3])
status = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(attempt / 'temporary/pytest'),
    '--rootdir', str(snapshot), '--junitxml', str(attempt / 'pytest.xml'),
    str(snapshot / 'tests/test_genomic_overlap_returns.py'), *sys.argv[3:]])
examples = [str(path.relative_to(attempt)) for path in
    (attempt / 'temporary/pytest').rglob('ACTUAL_TYPED_RETURN.json')]
(attempt / 'examples.json').write_text(json.dumps(examples, indent=2) + '\n')
raise SystemExit(status)
