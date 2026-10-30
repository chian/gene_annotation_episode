"""Finite authority checks; native outputs are separately labeled fixtures."""
from pathlib import Path
import json
import os
import sys
import pytest
attempt, snapshot = map(Path, sys.argv[1:3])
os.environ['ATAC471_REPO'] = str(snapshot)
os.environ['ATAC471_ATTEMPT'] = str(attempt)
selected = sys.argv[3:] or ['tests/test_atac_differential_returns.py']
status = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(attempt/'temporary/pytest'),
    '--rootdir', str(snapshot), '--junitxml', str(attempt/'pytest.xml'),
    *[str(snapshot/path) for path in selected]])
raise SystemExit(status)
