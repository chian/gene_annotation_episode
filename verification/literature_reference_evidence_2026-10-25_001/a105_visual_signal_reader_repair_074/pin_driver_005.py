"""Fresh coherent dependency-order repair pin; imports must resolve inside it."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import runpy
import sys

ROOT = Path.cwd().resolve()
assert ROOT.name == 'pin_005', ROOT
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
import pytest
files = ['tests/test_literature_ratio_source_inputs.py', 'tests/test_literature_ratio_source_calculations.py',
    'tests/test_literature_ratio_source_validation.py', 'tests/test_literature_ratio_reader.py',
    'tests/test_literature_ratio_calculations.py']
status = pytest.main(['-q', '-p', 'no:cacheprovider', *files])
assert status == 0, status
HERE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_repair_074'
runpy.run_path(str(HERE / 'execute_repaired_004.py'), run_name='__main__')
runpy.run_path(str(ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_reader_070/execute_constructed_014.py'), run_name='__main__')
imports = []
for name, module in sorted(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.') or name.startswith('test_literature_ratio_'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(ROOT), (name, str(path))
        imports.append({'module': name, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
receipt = {'status': 'passed', 'cwd': str(ROOT), 'python': platform.python_version(), 'executable': sys.executable,
    'targeted_test_files': files, 'pytest_exit': int(status), 'local_imports': imports,
    'third_party_versions': {name: importlib.metadata.version(name) for name in ('Pillow', 'jsonschema', 'pytest')},
    'constructed_repaired_cases': 2, 'original_constructed_cases': 12, 'actual_native_views': 0,
    'model_calls': 0, 'episode_actions': 0, 'scope': 'pure fixture/canonical saved validation; no native/C1/C4/model claim'}
(HERE / 'PIN_IMPORT_AND_EXECUTION_005.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'local_imports_inside_pin': len(imports), 'constructed_cases': 14}))
