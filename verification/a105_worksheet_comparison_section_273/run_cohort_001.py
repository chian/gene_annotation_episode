"""Capture actual imported files and exact bounded pytest output in this process."""
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
sources = sorted((ROOT/'gene_annotation_episode').glob('*.py')) + sorted((ROOT/'method_loop').rglob('*.py')) + sorted((ROOT/'tests').glob('*.py'))
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
(PACKET/'SOURCE_BEFORE_001.json').write_text(json.dumps(before, indent=2)+'\n')
result = pytest.main(['-q', 'tests/test_literature_a105_worksheet.py',
    'tests/test_literature_a105_worksheet_comparison_273.py',
    '--basetemp='+str(PACKET/'pytest_001'), '--junitxml='+str(PACKET/'PYTEST_001.xml')])
imports = []
for name, module in sorted(sys.modules.items()):
    path = getattr(module, '__file__', None)
    if path:
        path = Path(path).resolve()
        if path.is_file() and path.is_relative_to(ROOT) and path.relative_to(ROOT).parts[0] in ('gene_annotation_episode', 'method_loop', 'tests'):
            relative = str(path.relative_to(ROOT)); digest = hashlib.sha256(path.read_bytes()).hexdigest()
            imports.append({'module': name, 'path': relative, 'sha256': digest,
                'bytes': path.stat().st_size, 'before_equals_after': before.get(relative) == digest})
(PACKET/'ACTUAL_LOCAL_IMPORTS_001.json').write_text(json.dumps(imports, indent=2)+'\n')
(PACKET/'COHORT_RESULT_001.json').write_text(json.dumps({'pytest_exit_code': int(result),
    'all_imports_preexisting_and_stable': all(p['before_equals_after'] for p in imports),
    'method_loop_import_count': sum(p['path'].startswith('method_loop/') for p in imports)}, indent=2)+'\n')
raise SystemExit(result)
