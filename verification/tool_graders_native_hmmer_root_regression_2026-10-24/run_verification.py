"""Run affected existing execution regressions with loaded-source evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {str(path.relative_to(ROOT)): digest(path)
        for folder in ('gene_annotation_episode', 'method_loop')
        for path in (ROOT / folder).rglob('*.py')}


class Audit:
    def __init__(self):
        self.outcomes = Counter()
        self.loaded = {}

    def pytest_runtest_logreport(self, report):
        if report.when == 'call' or report.failed:
            self.outcomes[report.outcome] += 1

    def pytest_sessionfinish(self, session, exitstatus):
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                if path.suffix == '.py' and path.is_relative_to(ROOT) and '.venv' not in path.parts:
                    self.loaded[str(path.relative_to(ROOT))] = digest(path)


def main():
    before, audit, started = sources(), Audit(), time.monotonic()
    arguments = ['-q', 'tests/test_execution_episodes_family.py',
        'tests/test_execution_progress.py', 'tests/test_execution_tool_contract_declarations.py',
        '--tb=short', '--basetemp=' + str(HERE / 'pytest-tmp')]
    result = pytest.main(arguments, plugins=[audit])
    after = sources()
    record = {'command': [sys.executable, str(Path(__file__).resolve())],
        'pytest_arguments': arguments, 'returncode': int(result),
        'elapsed_seconds': time.monotonic() - started,
        'test_outcomes': dict(audit.outcomes),
        'production_sha256_before': before, 'production_sha256_after': after,
        'loaded_repo_module_sha256': audit.loaded, 'production_unchanged': before == after,
        'coverage': 'Existing generic execution/progress and configured tool declaration regressions; '
            'native numerical Workflow verification belongs to the separate integration suite.',
        'specific_pending_NCBI_job_verification_included': False}
    (HERE / 'VERIFICATION.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'returncode': int(result), 'production_unchanged': before == after,
        'test_outcomes': dict(audit.outcomes), 'loaded_repo_module_count': len(audit.loaded)}))
    return int(result) or (0 if before == after else 1)


if __name__ == '__main__':
    raise SystemExit(main())
