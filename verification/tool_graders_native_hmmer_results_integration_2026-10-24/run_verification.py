"""Retain exact final pytest invocation and source stability evidence."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_sources():
    return {str(path.relative_to(ROOT)): sha(path)
        for directory in ('gene_annotation_episode', 'method_loop')
        for path in (ROOT / directory).rglob('*.py')}


class Audit:
    def __init__(self):
        self.results = Counter()
        self.loaded = {}

    def pytest_runtest_logreport(self, report):
        if report.when == 'call' or report.failed:
            self.results[report.outcome] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                if path.suffix == '.py' and path.is_relative_to(ROOT) and '.venv' not in path.parts:
                    self.loaded[str(path.relative_to(ROOT))] = sha(path)


def main():
    before = production_sources()
    tests_before = {name: sha(ROOT / name) for name in (
        'tests/test_native_hmmer_acquisition.py', 'tests/test_native_hmmer_results_integration.py')}
    audit = Audit()
    arguments = ['-q', 'tests/test_native_hmmer_acquisition.py',
        'tests/test_native_hmmer_results_integration.py', '--tb=short',
        '--basetemp=' + str(EVIDENCE / 'final-pytest')]
    started = time.monotonic()
    result = pytest.main(arguments, plugins=[audit])
    after = production_sources()
    tests_after = {name: sha(ROOT / name) for name in tests_before}
    record = {'command': [sys.executable, str(Path(__file__).resolve())],
        'pytest_arguments': arguments, 'returncode': int(result),
        'elapsed_seconds': time.monotonic() - started, 'test_outcomes': dict(audit.results),
        'production_sha256_before': before, 'production_sha256_after': after,
        'loaded_repo_module_sha256': audit.loaded, 'production_unchanged': before == after,
        'test_sha256_before': tests_before, 'test_sha256_after': tests_after,
        'tests_unchanged': tests_before == tests_after,
        'local_policy': {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3,
                         'wall_seconds': None},
        'coverage_meaning': {'native': 'Fresh tiny installed HMMER through selected practical.job.start',
            'retained': 'Copied 064 producer files and B003 saved numerical comparators',
            'synthetic': 'Input sequences, scripted decisions, custody and binding faults',
            'workflow': 'Shared Workflow, production execution results credit and typed parent receipt',
            'not_claimed': ['LLM scientific decisions', 'API', 'HPC', 'pending NCBI RID', 'literature', 'W05']}}
    (EVIDENCE / 'VERIFICATION.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'returncode': int(result), 'production_unchanged': before == after,
        'loaded_repo_module_count': len(audit.loaded), 'test_outcomes': dict(audit.results)}))
    return int(result) or (0 if before == after and tests_before == tests_after else 1)


if __name__ == '__main__':
    raise SystemExit(main())
