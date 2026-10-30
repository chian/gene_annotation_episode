"""Run B's final suite and retain exact commands, exit status and source digests."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[1]
CANDIDATE = BASE / 'candidate'
EVIDENCE = BASE / 'evidence_b'
PYTHON = '/home/chia/repos/gene_annotation_episode/.venv/bin/python'
OWNED_MODULES = [
    'fastqc_reader', 'trim_reader', 'pair_report_reader', 'hostile_reader',
    'retention', 'consistency',
]


def record(path):
    return {'path': str(path.relative_to(REPO)), 'exists': path.exists(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
            'bytes': path.stat().st_size if path.exists() else None}


def dependencies():
    paths = [CANDIDATE / 'gene_annotation_episode' / f'bvbrc_fastqutils_{name}.py'
             for name in OWNED_MODULES + ['contracts', 'identity', 'metric_specs']]
    paths += [CANDIDATE / 'gene_annotation_episode/bvbrc_fastqutils_schemas.json']
    paths += [CANDIDATE / 'tests/test_bvbrc_fastqutils_report_formats.py',
              CANDIDATE / 'tests/test_bvbrc_fastqutils_report_calculators.py']
    paths += sorted((CANDIDATE / 'tests/fixtures/bvbrc_fastqutils/reports').iterdir())
    # Include the frozen registries read by the shared specifications module.
    paths += sorted((REPO / 'verification/tool_graders_bvbrc_fastqutils_interface_2026-10-25_195').glob('*SPECS_002.json'))
    paths += [REPO / 'verification/tool_graders_bvbrc_fastqutils_interface_2026-10-25_195/NUMERICAL_CORRECTIONS_003.json']
    return [record(path) for path in paths if path.is_file()]


def main():
    before = dependencies()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    command = [PYTHON, '-m', 'pytest', '-q',
               'tests/test_bvbrc_fastqutils_report_formats.py',
               'tests/test_bvbrc_fastqutils_report_calculators.py',
               '--junitxml=../evidence_b/junit_final.xml']
    start = datetime.now(timezone.utc).isoformat()
    clock_start = time.monotonic()
    with (EVIDENCE / 'pytest_final.txt').open('wb') as log:
        result = subprocess.run(command, cwd=CANDIDATE, env=env, stdout=log, stderr=subprocess.STDOUT)
    seconds = time.monotonic() - clock_start
    end = datetime.now(timezone.utc).isoformat()
    after = dependencies()
    suite = ET.parse(EVIDENCE / 'junit_final.xml').getroot().find('testsuite')
    receipt = {
        'command_argv': command, 'cwd': str(CANDIDATE),
        'environment_overrides': {'PYTHONDONTWRITEBYTECODE': '1'},
        'started_utc': start, 'finished_utc': end, 'elapsed_seconds': seconds,
        'exit_code': result.returncode, 'junit_summary': dict(suite.attrib),
        'maximum_child_rss_kib_linux': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'dependencies_unchanged_during_run': before == after,
        'dependency_hashes_before': before, 'dependency_hashes_after': after,
        'stdout': record(EVIDENCE / 'pytest_final.txt'),
        'junit': record(EVIDENCE / 'junit_final.xml'),
    }
    (EVIDENCE / 'TERMINAL_RECEIPT_FINAL.json').write_text(json.dumps(receipt, indent=2) + '\n')
    initial = json.loads((EVIDENCE / 'SOURCE_BEFORE.json').read_text())
    current = [record(REPO / entry['path']) for entry in initial]
    source_receipt = {
        'original_sources_unchanged': all(a == b for a, b in zip(initial, current) if a['exists']),
        'before': initial, 'after': current,
        'scope': 'All producer source files recorded before B implementation; the six B production modules were absent.',
    }
    (EVIDENCE / 'SOURCE_AFTER.json').write_text(json.dumps(source_receipt, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ['exit_code', 'junit_summary', 'elapsed_seconds',
          'maximum_child_rss_kib_linux', 'dependencies_unchanged_during_run']}, indent=2))
    if result.returncode:
        print((EVIDENCE / 'pytest_final.txt').read_text())
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
