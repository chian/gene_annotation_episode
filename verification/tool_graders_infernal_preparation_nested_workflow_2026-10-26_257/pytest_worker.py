"""Retain imported-source identities and immediate test failures."""
import hashlib
import json
from pathlib import Path
import sys

import pytest


class Evidence:
    def pytest_runtest_logreport(self, report):
        if report.failed:
            print('\nRETAINED FAILURE ' + report.nodeid + '\n' + str(report.longrepr), flush=True)

    def pytest_sessionfinish(self, session, exitstatus):
        rows = {}
        for name, module in sorted(sys.modules.items()):
            filename = getattr(module, '__file__', None)
            if filename and filename.endswith('.py') and Path(filename).is_file():
                rows[name] = {'path': str(Path(filename).resolve()),
                    'sha256_at_session_finish': hashlib.sha256(Path(filename).read_bytes()).hexdigest()}
        (Path.cwd() / 'imported_sources.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[Evidence()]))
