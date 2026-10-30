"""Exercise the actual owned integration-test guard without running Workflow."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
import test_bvbrc_alignment_episode_flow as tested

directory = EVIDENCE / 'guard-check-028'
directory.mkdir()
used_file, late_file, outside_file = [directory / name for name in ('used.py', 'late.py', 'unimported.py')]
for path in (used_file, late_file, outside_file):
    path.write_text('value = 1\n')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

load('controlled_guard_used', used_file)
explicit = set().union(*(tested.explicit_source_paths(kind) for kind in tested.CASES))
initial = tested.loaded_source_paths()
before = tested.source_hashes(explicit | initial | {late_file, outside_file})
checks = []

def check(name, rejected, *, extra=()):
    used = explicit | initial | tested.loaded_source_paths()
    after = tested.source_hashes(used | {late_file, outside_file} | set(extra))
    guard = tested.source_guard(before, after, used)
    try:
        tested.require_source_guard(guard)
    except AssertionError as error:
        assert rejected, (name, str(error))
        outcome = {'rejected': True, 'message': str(error)}
    else:
        assert not rejected, name
        outcome = {'rejected': False}
    checks.append({'name': name, **outcome, 'guard': guard})
    return guard

check('unchanged_actual_loaded_and_explicit_sources', False)
used_file.write_text('value = 2\n')
assert str(used_file.relative_to(ROOT)) in check('changed_loaded_source', True)['used_changes']
used_file.write_text('value = 1\n')
used_file.unlink()
assert str(used_file.relative_to(ROOT)) in check('deleted_loaded_source', True)['used_changes']
used_file.write_text('value = 1\n')
outside_file.write_text('value = 2\n')
assert str(outside_file.relative_to(ROOT)) in check('changed_unimported_source_logged', False)['outside_used_changes']
added = directory / 'new_unimported.py'
added.write_text('value = 3\n')
assert str(added.relative_to(ROOT)) in check('added_unimported_source_logged', False, extra=(added,))['outside_used_additions']
late_file.write_text('value = 4\n')
load('controlled_guard_late', late_file)
assert str(late_file.relative_to(ROOT)) in check('late_imported_changed_source', True)['used_changes']
late_file.write_text('value = 1\n')
load('controlled_guard_new', added)
assert str(added.relative_to(ROOT)) in check('late_import_missing_before_hash', True)['used_without_before_hash']
del sys.modules['controlled_guard_new']
guard = check('restored_used_sources_with_unrelated_changes', False, extra=(added,))
assert not guard['used_changes'] and not guard['used_without_before_hash']
for required in ('scientific_process_prompt.py', 'bvbrc_appservice_saved_results.py'):
    assert str(Path('gene_annotation_episode') / required) in guard['used_paths']
receipt = {'status': 'all_guard_checks_passed', 'workflow_started': False,
    'test_source_sha256': hashlib.sha256(Path(tested.__file__).read_bytes()).hexdigest(),
    'before_hashes': before, 'checks': checks}
(EVIDENCE / 'source-guard-028.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'checks': len(checks),
    'used_path_count': len(guard['used_paths']), 'broad_before_path_count': len(before)}))
