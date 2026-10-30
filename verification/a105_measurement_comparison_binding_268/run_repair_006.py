"""Only the repaired controlled redelivery fixture; production stays at joined005."""
import hashlib
import ast
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
sys.dont_write_bytecode = True
import pytest

base = json.loads((HERE/'PIN_MANIFEST_005.json').read_text())['files']
test = ROOT/'tests/test_literature_measurement_comparison_binding_268.py'
overlay = HERE/'test_delta_006/tests/test_literature_measurement_comparison_binding_268.py'
overlay.parent.mkdir(parents=True, exist_ok=True)
overlay.write_bytes(test.read_bytes())
all_before = {r['path']: hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() for r in base}
production_delta = [r['path'] for r in base if r['path'].startswith('gene_annotation_episode/')
    and all_before[r['path']] != r['sha256']]
previous = json.loads((HERE/'COHORT_RECEIPT_005.json').read_text())
critical = {r['path'] for r in previous['actual_local_imports']}
tree = ast.parse((ROOT/'gene_annotation_episode/literature_episodes.py').read_text())
binding = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LiteratureEpisodes')
descriptor = next(n for n in binding.body if isinstance(n, ast.FunctionDef) and n.name == 'as_record')
critical.update('gene_annotation_episode/'+n.value for n in ast.walk(descriptor)
    if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.endswith('.py'))
critical_production_delta = sorted(set(production_delta) & critical)
assert not critical_production_delta, critical_production_delta
external = previous['external_shared_method_loop_sources']
for row in external:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
start = time.time()
args = ['-q', '--tb=short', '--basetemp='+str(HERE/'pytest_006'),
    str(test)+'::test_original_report_repair_redelivery_without_repopulation']
code = pytest.main(args)
imports = []
for name, module in sorted(sys.modules.items()):
    file = getattr(module, '__file__', None)
    if not file:
        continue
    path = Path(file).resolve()
    if path.is_file() and (path.is_relative_to(ROOT/'gene_annotation_episode') or path.is_relative_to(ROOT/'tests')):
        imports.append({'module': name, 'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
critical_changes = [r['path'] for r in imports if r['path'] in all_before and r['sha256'] != all_before[r['path']]]
for row in external:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
record = {'pytest_arguments': args, 'exit_code': code, 'started_unix': start, 'finished_unix': time.time(),
    'base_pin': 'PIN_MANIFEST_005.json', 'base_pin_sha256': hashlib.sha256((HERE/'PIN_MANIFEST_005.json').read_bytes()).hexdigest(),
    'test_delta': {'path': str(test.relative_to(ROOT)), 'overlay': str(overlay.relative_to(ROOT)),
        'sha256': hashlib.sha256(overlay.read_bytes()).hexdigest()},
    'production_changed_since005': production_delta, 'changed_import_or_descriptor_production_since005': critical_production_delta,
    'changed_actual_imports_during_test': critical_changes,
    'actual_local_imports': imports, 'scope': 'One explicitly fault-injected fixture: actual saved report redelivery, no repopulation, exact ordinary observations. No natural source failure or configured-model claim.'}
(HERE/'COHORT_RECEIPT_006.json').write_text(json.dumps(record, indent=2)+'\n')
assert not critical_changes
raise SystemExit(code)
