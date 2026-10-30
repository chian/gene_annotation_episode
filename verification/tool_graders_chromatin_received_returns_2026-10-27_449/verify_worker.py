"""Focused synthetic authority checks within the selected native reservation."""
from pathlib import Path
import json
import sys

import pytest

attempt, snapshot = map(Path, sys.argv[1:3])
status = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(attempt / 'temporary/pytest'),
    '--rootdir', str(snapshot), '--junitxml', str(attempt / 'pytest.xml'),
    str(snapshot / 'tests/test_chromatin_interaction_returns.py'), *sys.argv[3:]])
(attempt / 'examples.json').write_text(json.dumps([str(path.relative_to(attempt)) for path in
    (attempt / 'temporary/pytest').rglob('ACTUAL_TYPED_RETURN.json')], indent=2) + '\n')
raise SystemExit(status)
