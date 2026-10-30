"""Run the scoped final suite and record immutable source/test identities."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

EVIDENCE = Path(__file__).resolve().parent
CANDIDATE = EVIDENCE.parent / 'candidate'
TESTS = [
    'tests/test_bvbrc_proteome_directional_sheet.py',
    'tests/test_bvbrc_proteome_directional_numerical_contracts.py',
    'tests/test_bvbrc_proteome_directional_geometry.py',
    'tests/test_bvbrc_proteome_directional_calculators.py',
    'tests/test_bvbrc_proteome_directional.py',
    'tests/test_bvbrc_proteome_directional_contracts.py',
    'tests/test_blast_pairwise_grader.py',
    'tests/test_blast_database_grader.py',
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    path = EVIDENCE / name
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def digest(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def manifest():
    paths = set()
    for directory in ('gene_annotation_episode', 'tests'):
        for path in (CANDIDATE / directory).rglob('*'):
            if (path.is_file() and '__pycache__' not in path.parts
                    and (path.suffix in ('.py', '.json') or 'fixtures' in path.parts)):
                paths.add(path)
    return {str(path.relative_to(CANDIDATE)): digest(path) for path in sorted(paths)}


def main():
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               '--junitxml=' + str(EVIDENCE / 'final_tests_001.xml'), *TESTS]
    before = manifest()
    save('source_manifest_before_001.json', before)
    start = utc()
    monotonic = time.monotonic()
    with (EVIDENCE / 'final_tests_001.log').open('x', encoding='utf-8') as stream:
        process = subprocess.run(command, cwd=CANDIDATE, stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - monotonic
    after = manifest()
    save('source_manifest_after_001.json', after)
    differences = [p for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)]
    xml = EVIDENCE / 'final_tests_001.xml'
    suites = []
    if xml.exists():
        suites = [dict(s.attrib) for s in ET.parse(xml).getroot().iter('testsuite')]
    receipt = {
        'scope': 'Local candidate unit/regression verification; no live tool execution or episode witness',
        'started_utc': start, 'finished_utc': utc(), 'elapsed_seconds': elapsed,
        'cwd': str(CANDIDATE), 'command': command, 'returncode': process.returncode,
        'source_test_manifest_unchanged': not differences, 'changed_paths': differences,
        'manifest_entries': len(before), 'testsuites': suites,
        'harness': digest(Path(__file__)), 'log': digest(EVIDENCE / 'final_tests_001.log'),
        'xml': digest(xml) if xml.exists() else None,
        'prior_unrecorded_development_run': 'Not claimed; completion output unavailable',
    }
    save('final_test_receipt_001.json', receipt)
    print(json.dumps(receipt, indent=2))
    return process.returncode if process.returncode else bool(differences)


if __name__ == '__main__':
    raise SystemExit(main())
