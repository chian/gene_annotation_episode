"""Controlled selected/affected checks with actual import and read-input closure."""
from pathlib import Path
import contextlib
import hashlib
import importlib.metadata
import json
import os
import shutil
import sys
import time

import pytest

H = Path(__file__).resolve().parent
R = H.parents[2]
PIN = H/'pin_011'
assert not PIN.exists()
tests = [
    'tests/test_literature_kinetic_summary_precision_binding_251.py',
    'tests/test_literature_kinetic_summary_precision_components_248.py',
    'tests/test_literature_endpoint_signal_binding_244.py',
    'tests/test_literature_kinetic_inputs.py',
    'tests/test_literature_kinetic_count_inputs.py',
    'tests/test_literature_kinetic_calculations.py',
    'tests/test_literature_kinetic_storage.py',
    'tests/test_literature_kinetic_integration.py',
    'tests/test_literature_kinetic_count_integration.py',
    'tests/test_literature_kinetic_dependency_binding_196.py',
    'tests/test_literature_kinetic_witness_publication.py',
    'tests/test_literature_kinetic_model_inputs.py',
    'tests/test_literature_kinetic_model_storage.py',
    'tests/test_literature_kinetic_model_integration.py',
    'tests/test_literature_rate_episode_integration.py',
    'tests/test_literature_cell_possession_integration.py',
    'tests/test_literature_experimental_prompt.py',
    'tests/test_literature_experimental_prompt_delivery.py',
    'tests/test_literature_reference_parent_prompt.py',
    'tests/test_literature_reference_parent_delivery.py',
    'tests/test_communication.py',
    'tests/test_episode_contract_information.py',
    'tests/test_contract_information_custody_059.py',
    'tests/test_contract_information_runtime_059.py',
    'tests/test_episode_composition.py',
]
owned = ['gene_annotation_episode/'+name for name in (
    'literature_episodes.py', 'communication.py', 'literature_numerical_contracts.py',
    'literature_numerical_return_presentation.py', 'literature_experimental_prompt.py',
    'literature_reference_parent_prompt.py', 'episode_contract_information.py',
    'literature_kinetic_summary_precision_storage.py', 'literature_kinetic_summary_precision_render.py')]
owned += ['tests/test_literature_kinetic_summary_precision_binding_251.py']
pure = ['gene_annotation_episode/literature_kinetic_summary_precision_'+suffix+'.py'
        for suffix in ('inputs', 'calculations', 'prompt')]

def digest(p):
    raw = Path(p).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def save(name, value):
    (H/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')

before = {p: digest(R/p) for p in owned+pure}
reads = set()
capturing = True
def audit(event, args):
    if not capturing:
        return
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        try:
            path = Path(os.fsdecode(args[0])).resolve()
            mode = args[1]
            flags = args[2]
            reading = isinstance(mode, str) and 'r' in mode or mode is None and isinstance(flags, int) and flags & os.O_ACCMODE == os.O_RDONLY
            relative = path.relative_to(R)
        except (ValueError, TypeError, OSError):
            return
        if path.name == 'GOAL.md':
            raise AssertionError('GOAL.md is not task authority and must not be opened')
        if reading and '.venv' not in relative.parts and path.is_file():
            # Test outputs/state produced under our basetemp are preserved
            # separately; pin original repository/fixture inputs only.
            if not str(path).startswith(str(H/'attempt_')) and not str(path).startswith(str(PIN)):
                reads.add(path)
    elif event == 'sqlite3.connect' and args and isinstance(args[0], str):
        candidate = args[0].removeprefix('file:').split('?', 1)[0]
        path = Path(candidate).resolve()
        try:
            path.relative_to(R)
        except ValueError:
            return
        if path.is_file() and not str(path).startswith(str(H/'attempt_')):
            reads.add(path)

sys.addaudithook(audit)
started = time.monotonic()
with (H/'pytest_011.stdout.txt').open('w') as out, (H/'pytest_011.stderr.txt').open('w') as err:
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = int(pytest.main(['-q', '--basetemp='+str(H/'attempt_011'),
            '--junitxml='+str(H/'pytest_011.junit.xml'), *tests]))
capturing = False
elapsed = time.monotonic()-started
assert before == {p: digest(R/p) for p in owned+pure}, 'Code changed during final verification'
repo = {R/p for p in owned+pure+tests}
imports = []
for name, module in sorted(sys.modules.items()):
    filename = getattr(module, '__file__', None)
    if not filename:
        continue
    p = Path(filename).resolve()
    if not p.is_file():
        continue
    row = {'module': name, 'path': str(p), **digest(p)}
    try:
        relative = p.relative_to(R)
    except ValueError:
        row['scope'] = 'installed_dependency'
    else:
        if '.venv' in relative.parts:
            row['scope'] = 'installed_dependency'
        else:
            row['scope'] = 'repository_import'; repo.add(p)
    imports.append(row)
repo.update(reads)
repo.add(Path(__file__).resolve())
PIN.mkdir()
entries = []
for p in sorted(repo):
    if not p.is_file() or p.name == 'GOAL.md':
        continue
    relative = p.relative_to(R)
    target = PIN/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, target)
    entries.append({'path': str(relative), 'pin_path': str(target.relative_to(H)), **digest(p)})
save('ACTUAL_IMPORTS_011.json', {'imports': imports, 'actual_import_count': len(imports),
    'installed_versions': {n: importlib.metadata.version(n) for n in ('scipy', 'jsonschema', 'pytest', 'Pillow')}})
save('PIN_MANIFEST_011.json', {'files': entries, 'original_input_read_paths': [str(p.relative_to(R)) for p in sorted(reads)],
    'actual_imports': 'ACTUAL_IMPORTS_011.json', 'code_unchanged_during_checks': True})
save('VERIFICATION_RECEIPT_011.json', {'pytest_exit_code': status, 'elapsed_seconds': elapsed,
    'test_files': tests, 'owned_before_after': before, 'code_unchanged_during_checks': True,
    'actual_import_count': len(imports), 'pinned_files': len(entries),
    'classification': 'controlled_scientific_choices_and_existing_engineering_regressions',
    'selected_original_source_example': 'reuses exact converted242 selection and pinned public bytes; no new interpretation',
    'actual_model_execution': False, 'new_source_acquisition': False, 'private_provider_data_read': False,
    'A105_complete': False, 'full_goal_complete': False})
print(json.dumps({'exit_code': status, 'elapsed_seconds': elapsed, 'pinned_files': len(entries), 'actual_import_count': len(imports)}))
sys.exit(status)
