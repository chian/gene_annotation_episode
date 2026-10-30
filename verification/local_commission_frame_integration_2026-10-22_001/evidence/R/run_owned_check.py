"""Retain each isolated invocation without importing application code."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path('/tmp/gene-annotation-configured-caller-20261022-007')
HERE = Path(__file__).resolve().parent
PYTHON = '/home/chia/repos/gene_annotation_episode/.venv/bin/python'


def row(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def inputs():
    files = [*sorted((ROOT/'gene_annotation_episode').rglob('*.py')),
             *sorted((ROOT/'method_loop').rglob('*.py')),
             ROOT/'tests/test_local_commission_frame_runtime.py']
    return {str(p.relative_to(ROOT)): row(p) for p in files}


name, *nodes = sys.argv[1:]
out = HERE/name
out.mkdir(exist_ok=False)
before = inputs()
(out/'INPUTS_BEFORE.json').write_text(json.dumps(before, indent=2)+'\n')
retained_inputs = []
for relative, expected in before.items():
    source = ROOT/relative
    data = source.read_bytes()
    if {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} != expected:
        raise RuntimeError('source changed during input capture: '+relative)
    target = out/'source-inputs'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    retained_inputs.append({'path':relative, 'retained':True,
        'method':'direct_before_invocation_copy_matching_before_guard', **expected})
(out/'SOURCE_RETENTION.json').write_text(json.dumps(retained_inputs, indent=2)+'\n')
command = [PYTHON, '-B', '-m', 'pytest', '-q', *nodes,
    '--basetemp='+str(out/'basetemp'), '--junitxml='+str(out/'pytest.xml'),
    '-o', 'cache_dir='+str(out/'pytest-cache')]
env = dict(os.environ, PYTHONPATH=str(ROOT/'tests')+os.pathsep+str(ROOT), PYTHONDONTWRITEBYTECODE='1')
(out/'COMMAND.json').write_text(json.dumps({'argv': command, 'cwd': str(ROOT),
    'environment_assignments': {k:env[k] for k in ['PYTHONPATH','PYTHONDONTWRITEBYTECODE']},
    'claim_scope': 'owned local fixtures; all source hashes captured, coherent final source freeze not assumed'}, indent=2)+'\n')
start = time.monotonic()
with (out/'pytest.log').open('wb') as log:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
elapsed = time.monotonic()-start
after = inputs()
(out/'INPUTS_AFTER.json').write_text(json.dumps(after, indent=2)+'\n')
changes = [p for p in sorted(set(before)|set(after)) if before.get(p) != after.get(p)]
original = out/'basetemp'
copied = out/'retained-fixtures'
preservation = []
if original.exists():
    shutil.copytree(original, copied, symlinks=True)
    for p in sorted(original.rglob('*')):
        relative = p.relative_to(original)
        target = copied/relative
        if p.is_symlink():
            if os.readlink(p) != os.readlink(target):
                raise RuntimeError('alias differs')
            preservation.append({'path': str(relative), 'kind': 'symlink', 'target': os.readlink(p)})
        elif p.is_file():
            if row(p) != row(target):
                raise RuntimeError('fixture copy differs')
            source_stat, target_stat = p.stat(), target.stat()
            if (stat.S_IMODE(source_stat.st_mode),source_stat.st_mtime_ns) != (
                    stat.S_IMODE(target_stat.st_mode),target_stat.st_mtime_ns):
                raise RuntimeError('fixture metadata differs')
            preservation.append({'path': str(relative), 'kind': 'file', **row(p),
                'mode':oct(stat.S_IMODE(source_stat.st_mode)), 'mtime_ns':source_stat.st_mtime_ns})
(out/'PRESERVATION.json').write_text(json.dumps(preservation, indent=2)+'\n')
report = {'exit_code': result.returncode, 'wall_seconds': elapsed,
    'input_changes': changes, 'source_inputs_stable': not changes,
    'fixture_regular_files': sum(p['kind']=='file' for p in preservation),
    'fixture_regular_bytes': sum(p.get('bytes',0) for p in preservation),
    'tests_run_are_synthetic_only': True}
(out/'RESULT.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'directory':str(out), **report}))
print((out/'pytest.log').read_text()[-18000:])
sys.exit(result.returncode)
