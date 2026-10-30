"""Constructed final-generation validation with exact imports and snapshot checks."""
from pathlib import Path
import hashlib
import json
import sys

import pytest
import gene_annotation_episode.literature_perturbation_summary_storage as summary

BASE = Path(__file__).resolve().parent
PIN = BASE / 'pin_002'
assert Path.cwd().resolve() == PIN
assert Path(summary.__file__).resolve().is_relative_to(PIN)
selection = [
    'tests/test_literature_perturbation_covariance_meanings.py',
    'tests/test_literature_perturbation_inputs.py',
    'tests/test_literature_perturbation_calculations.py',
    'tests/test_literature_perturbation_summary.py',
    'tests/test_literature_perturbation_summary_integration.py',
    'tests/test_literature_perturbation_interpretation_basis.py',
    'tests/test_literature_perturbation_missing_amount_unit.py',
    'tests/test_literature_perturbation_integration.py',
    'tests/test_communication.py',
    'tests/test_form_reference_validation.py',
    'tests/test_literature_experimental_prompt.py',
    'tests/test_literature_experimental_prompt_delivery.py',
    'tests/test_literature_parent_population_information.py',
    'tests/test_literature_gel_communication.py',
    'tests/test_literature_controlled_response_communication.py',
]
deselect = [
    'tests/test_literature_perturbation_integration.py::test_saved_source_values_exact_typed_subset_and_no_source_reread[True]',
    'tests/test_literature_perturbation_integration.py::test_source_perturbation_selected_in_ordinary_child_and_received_once[True]',
]
args = ['-q', '-x', '--junitxml=' + str(BASE / 'FINAL_TESTS_001.xml'),
        *['--deselect=' + name for name in deselect], *selection]
with (BASE / 'FINAL_COMMAND_001.json').open('x') as stream:
    json.dump({'cwd': str(PIN), 'python': sys.executable, 'pytest_arguments': args,
               'limits': 'Constructed sources and portable historical engineering records; two original-paper fixture variants deliberately excluded. No model calls or new primary interpretation.'}, stream, indent=2)
result = pytest.main(args)
imports = {}
for name, module in tuple(sys.modules.items()):
    file = getattr(module, '__file__', None)
    if not file or not name.startswith(('gene_annotation_episode', 'method_loop', 'test_')):
        continue
    path = Path(file).resolve()
    if path.suffix != '.py':
        continue
    assert path.is_relative_to(PIN), (name, str(path))
    imports[name] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
with (BASE / 'FINAL_ACTUAL_IMPORTS_001.json').open('x') as stream:
    json.dump(imports, stream, indent=2)
manifest = json.loads((BASE / 'PIN_MANIFEST_002.json').read_text())
changed = [name for name, digest in manifest['files'].items()
           if hashlib.sha256((PIN / name).read_bytes()).hexdigest() != digest]
with (BASE / 'FINAL_RESULT_001.json').open('x') as stream:
    json.dump({'pytest_exit': int(result), 'snapshot_files_checked': len(manifest['files']),
               'changed_snapshot_files': changed, 'actual_imports_checked': len(imports),
               'scope': 'Applied main generation, five metadata/presentation files; no numerical formula, observation rule, operation, namespace, goal or governing amendment change.'}, stream, indent=2)
assert not changed, changed
raise SystemExit(int(result))
