"""Run only workload271's new controlled integration checks and retain facts."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
attempt = sys.argv[1] if len(sys.argv) > 1 else '001'
if not attempt.isdigit():
    raise ValueError('numeric_attempt_required')
output = HERE / ('attempt_' + attempt)
output.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = {str(p.relative_to(ROOT)): sha(p)
    for directory in ('gene_annotation_episode', 'tests')
    for p in (ROOT / directory).rglob('*.py')}
loop_spec = importlib.util.find_spec('method_loop')
loop_directory = Path(loop_spec.origin).resolve().parent
loop_before = {str(p): sha(p) for p in loop_directory.rglob('*.py')}
arguments = ['tests/test_literature_a105_worksheet_integration_271.py', '-q',
    '-p', 'no:cacheprovider', '--basetemp=' + str(output / 'pytest'),
    '--junitxml=' + str(output / 'result.xml')]
started = time.monotonic()
import pytest
with (output / 'pytest.log').open('x') as stream, redirect_stdout(stream), redirect_stderr(stream):
    exit_code = int(pytest.main(arguments))
actual = {}
actual_loop = {}
for name, module in sorted(sys.modules.items()):
    filename = getattr(module, '__file__', None)
    if not filename:
        continue
    path = Path(filename).resolve()
    if not path.is_file() or path.suffix != '.py':
        continue
    if path.is_relative_to(ROOT):
        relative = str(path.relative_to(ROOT))
        if relative in before:
            after = sha(path)
            actual[relative] = {'before_sha256': before[relative],
                'after_sha256': after, 'unchanged': after == before[relative]}
    elif name == 'method_loop' or name.startswith('method_loop.'):
        after = sha(path)
        actual_loop[str(path)] = {'before_sha256': loop_before.get(str(path)),
            'after_sha256': after, 'unchanged': loop_before.get(str(path)) == after}
report = {'method': 'actual pytest.main over the newly implemented selected worksheet path',
    'arguments': arguments, 'exit_code': exit_code,
    'elapsed_seconds': time.monotonic() - started,
    'actual_local_imports': actual,
    'actual_method_loop_imports': actual_loop,
    'all_actual_imports_unchanged': all(row['unchanged'] for row in (*actual.values(), *actual_loop.values())),
    'controlled_provider_responses': True, 'actual_model_backed_science': False,
    'scientific_source_use': 'Previously root-converted AP selectors reused by selected deterministic tools; no new biological interpretation.',
    'original_goal_changed': False}
with (output / 'receipt.json').open('x') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in report.items()
    if k not in ('actual_local_imports', 'actual_method_loop_imports')}, indent=2))
raise SystemExit(exit_code if report['all_actual_imports_unchanged'] else 1)
