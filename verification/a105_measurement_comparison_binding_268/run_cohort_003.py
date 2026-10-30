"""Bounded actual integration checks with before/after source and import receipts."""
import hashlib
import ast
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
sys.dont_write_bytecode = True
import pytest

paths = [*sorted((ROOT/'gene_annotation_episode').rglob('*.py')), *sorted((ROOT/'tests').rglob('*.py'))]
paths += [ROOT/p for p in (
    'research/experimental_scoring_review_2026-10-23/a110_chemical_sheet_016/sources/PMC2944534.html',
    'research/experimental_scoring_review_2026-10-23/a110_chemical_sheet_016/sources/PMC2944534.txt',
    'research/experimental_scoring_review_2026-10-23/a105_matched_assay_consistency_case_255/SOURCE_SELECTORS_001.json',
    'verification/literature_reference_evidence_2026-10-25_001/a105_matched_assay_consistency_review_257/ROOT_SCIENTIFIC_REVIEW_001.md',
    'verification/literature_reference_evidence_2026-10-25_001/a105_matched_assay_consistency_review_257/ROOT_SCIENTIFIC_CLARIFICATION_002.md',
    'verification/a105_measurement_comparison_components_258/NFN_PARENT_CONVERSION_SELECTION_ILLUSTRATION_001.json',
    'verification/a105_measurement_comparison_binding_268/first_cold_process_001.py',
)]
for p in (ROOT/'pyproject.toml', ROOT/'pytest.ini', ROOT/'conftest.py'):
    if p.is_file():
        paths.append(p)
pin = HERE/'pin_003'
pin.mkdir(exist_ok=False)
before = []
for path in dict.fromkeys(paths):
    raw = path.read_bytes()
    rel = path.relative_to(ROOT)
    target = pin/rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    before.append({'path': str(rel), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
(HERE/'PIN_MANIFEST_003.json').write_text(json.dumps({'files': before}, indent=2)+'\n')
args = ['-q', '--tb=short', '--basetemp='+str(HERE/'pytest_003'),
    str(ROOT/'tests/test_literature_measurement_comparison_binding_268.py'),
    str(ROOT/'tests/test_literature_kinetic_summary_precision_binding_251.py')+'::test_legacy_selected_kinetic_request_result_and_cold_unchanged',
    str(ROOT/'tests/test_literature_endpoint_signal_binding_244.py')+'::test_exact_schema_discovery_selected_sheet_and_requested_rows']
started = time.time()
code = pytest.main(args)
imports = []
for name, module in sorted(sys.modules.items()):
    value = getattr(module, '__file__', None)
    if not value:
        continue
    path = Path(value).resolve()
    if path.is_file() and (path.is_relative_to(ROOT/'gene_annotation_episode') or path.is_relative_to(ROOT/'tests')):
        raw = path.read_bytes()
        imports.append({'module': name, 'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()})
changed = [r['path'] for r in before if hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() != r['sha256']]
critical = {r['path'] for r in imports}
tree = ast.parse((ROOT/'gene_annotation_episode/literature_episodes.py').read_text())
binding_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LiteratureEpisodes')
descriptor = next(n for n in binding_class.body if isinstance(n, ast.FunctionDef) and n.name == 'as_record')
critical.update('gene_annotation_episode/'+n.value for n in ast.walk(descriptor)
    if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.endswith('.py'))
critical.add('verification/a105_measurement_comparison_binding_268/first_cold_process_001.py')
critical_changes = sorted(set(changed) & critical)
record = {'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'pytest_arguments': args,
    'started_unix': started, 'finished_unix': time.time(), 'exit_code': code,
    'before_after_pinned_files': len(before), 'changed_during_execution': changed,
    'changed_actual_import_or_descriptor_dependencies': critical_changes,
    'actual_local_imports': imports,
    'scope': 'Controlled selected fixtures, original-source mechanical reuse, typed returns and cold reconstruction. No configured-model execution or A105 adequacy claim.'}
(HERE/'COHORT_RECEIPT_003.json').write_text(json.dumps(record, indent=2)+'\n')
if critical_changes:
    raise AssertionError('Actual implementation dependency changed during cohort: '+repr(critical_changes))
raise SystemExit(code)
