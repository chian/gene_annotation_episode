"""One explicit isolated selected pytest invocation with retained raw fixtures."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path('/tmp/gene-annotation-configured-caller-20261022-008')

def witness(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def guard():
    files = {str(path.relative_to(ROOT)): witness(path)
        for package in ('gene_annotation_episode', 'method_loop')
        for path in sorted((ROOT / package).rglob('*.py'))}
    files['tests/test_direct_hmmer_timing_tools.py'] = witness(ROOT / 'tests/test_direct_hmmer_timing_tools.py')
    return files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--node', action='append', required=True)
    args = parser.parse_args()
    if '/' in args.label or not args.label.startswith('invocation-'):
        raise ValueError('new_invocation_label_required')
    out = EVIDENCE / args.label
    out.mkdir(mode=0o700)
    def save(name, value):
        raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        with (out / name).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    before = guard()
    for name in ('gene_annotation_episode/direct_hmmer_timing.py', 'gene_annotation_episode/tools.py',
            'tests/test_direct_hmmer_timing_tools.py'):
        with (out / ('source-' + Path(name).name)).open('xb') as stream:
            stream.write((ROOT / name).read_bytes())
    argv = ['/home/chia/repos/gene_annotation_episode/.venv/bin/python', '-B', '-m', 'pytest', '-q',
        *args.node, '--basetemp', str(out / 'fixtures'), '--junitxml', str(out / 'pytest.xml')]
    env = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT)}
    started = datetime.now(timezone.utc).isoformat()
    save('INPUTS.json', {'argv': argv, 'cwd': str(ROOT), 'explicit_environment': env,
        'started_at_utc': started, 'files': before,
        'scope': 'bounded evolving component only; no full implementation worker claim'})
    with (out / 'stdout.log').open('xb') as stdout, (out / 'stderr.log').open('xb') as stderr:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, **env}, stdout=stdout, stderr=stderr)
    after = guard()
    save('AFTER.json', after)
    cases = []
    if (out / 'pytest.xml').is_file():
        for case in ET.parse(out / 'pytest.xml').iter('testcase'):
            cases.append({'classname': case.get('classname'), 'name': case.get('name'),
                'failure': case.find('failure') is not None, 'error': case.find('error') is not None,
                'skipped': case.find('skipped') is not None})
    save('RESULTS.json', {'exit_code': result.returncode, 'started_at_utc': started,
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'changed_inputs': [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)],
        'stdout': witness(out / 'stdout.log'), 'stderr': witness(out / 'stderr.log'),
        'raw_fixtures_retained': str(out / 'fixtures'), 'cases': cases})
    print((out / 'stdout.log').read_text())
    print((out / 'stderr.log').read_text())
    print('EXIT', result.returncode)
    return result.returncode

if __name__ == '__main__':
    raise SystemExit(main())
