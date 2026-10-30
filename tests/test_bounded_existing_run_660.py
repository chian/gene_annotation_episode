"""Bounded continuation preflight; no scientific program or Workflow is run."""
import hashlib
import json
import os
from pathlib import Path


def test_original_run_and_new_closure_share_the_declared_scratch_root():
    attempt = Path(os.environ['HMMER529_ATTEMPT'])
    request = json.loads((attempt / 'selected_request.json').read_text())
    handle = json.loads((attempt / 'handle.json').read_text())
    root = Path(request['working_root'])
    case = Path(os.environ['HMMER_NATIVE_ORACLE_CONTINUATION_CASE'])
    assert root == attempt.parent == Path.cwd()
    assert case.is_dir() and case.is_relative_to(root)
    assert Path(handle['cwd']) == root
    assert Path(request['repository_root']).is_dir()
    assert Path(request['argv'][0]).is_relative_to(root)
    for name in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR'):
        assert Path(request['environment'][name]).is_relative_to(root)
    assert request['policy'] == {
        'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3,
        'wall_seconds': None,
    }
    assert request['swap_bytes'] == 0
    original = json.loads((root / 'receipt.json').read_text())
    assert original['terminal'] and original['quiescent']
    assert original['returncode'] == 1
    assert all(original[k] for k in (
        'source_unchanged', 'dependency_unchanged', 'stdlib_unchanged', 'binary_unchanged'))


def test_selected_original_executable_paths_and_bytes_are_preserved():
    attempt = Path(os.environ['HMMER529_ATTEMPT'])
    request = json.loads((attempt / 'selected_request.json').read_text())
    selected = json.loads((attempt / 'selected_native_executables.json').read_text())
    existing = json.loads((attempt / 'selected_existing_native_executables.json').read_text())
    before = {r['path']: r for r in json.loads((attempt / 'native_library_pins_before.json').read_text())}
    assert request['native_executables'] == []
    assert request['existing_native_executables'] == existing
    assert selected == [r['path'] for r in existing]
    assert {Path(r['path']).name for r in existing} == {
        'blastdb_aliastool', 'makembindex', 'makeprofiledb',
    }
    for row in existing:
        path = Path(row['path'])
        assert path.is_relative_to(Path(request['working_root']) / 'source_snapshot')
        assert not path.is_relative_to(attempt)
        raw = path.read_bytes()
        assert row == before[str(path)]
        assert row['size_bytes'] == len(raw)
        assert row['sha256'] == hashlib.sha256(raw).hexdigest()
