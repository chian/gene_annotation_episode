"""Joined constructed meaning/uncertainty checks, with actual import provenance."""
from pathlib import Path
import hashlib
import json
import sys

import pytest
import gene_annotation_episode.literature_episodes as binding

BASE = Path(__file__).resolve().parent
PIN = BASE / 'pin_001'
assert Path.cwd().resolve() == PIN
assert Path(binding.__file__).resolve().is_relative_to(PIN)
SELECTION = [
    'tests/test_literature_partner_operand_bindings.py::test_actual_typed_subset_next_decisions_and_first_readonly_reconstruction',
    'tests/test_literature_context_meanings_integration.py',
    'tests/test_literature_perturbation_interpretation_basis.py',
    'tests/test_literature_perturbation_missing_amount_unit.py::test_selected_typed_unknown_unit_and_exact_saved_replay_without_sources',
    'tests/test_literature_perturbation_summary_integration.py::test_summary_operation_in_ordinary_child_admits_exact_form_once_without_extra_observation',
    'tests/test_literature_partner_operand_information.py::test_metadata_module_bytes_participate_in_actual_binding_identity',
]
args = ['-q', '-x', '--junitxml=' + str(BASE / 'TESTS_001.xml'), *SELECTION]
with (BASE / 'COMMAND_001.json').open('x') as stream:
    json.dump({'cwd': str(PIN), 'python': sys.executable, 'pytest_arguments': args,
               'scope': 'Constructed sources and portable historical engineering rows; no paper acquisition or model calls.'}, stream, indent=2)
result = pytest.main(args)
imports = {}
for name, module in tuple(sys.modules.items()):
    file = getattr(module, '__file__', None)
    if not file or not name.startswith(('gene_annotation_episode', 'method_loop', 'test_literature')):
        continue
    path = Path(file).resolve()
    if path.suffix != '.py':
        continue
    assert path.is_relative_to(PIN), (name, str(path))
    imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
with (BASE / 'ACTUAL_PARENT_IMPORTS_001.json').open('x') as stream:
    json.dump(imports, stream, indent=2)
manifest = json.loads((BASE / 'PIN_MANIFEST_001.json').read_text())
changed = [name for name, digest in manifest['files'].items()
           if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
with (BASE / 'RESULT_001.json').open('x') as stream:
    json.dump({'pytest_exit': int(result), 'snapshot_files_checked': len(manifest['files']),
               'changed_snapshot_files': changed, 'actual_imports_checked': len(imports),
               'limits': 'Ordinary scripted workflows and typed/read-only reconstruction; no independent-worker or live-model scientific claim.'}, stream, indent=2)
assert not changed, changed
raise SystemExit(int(result))
