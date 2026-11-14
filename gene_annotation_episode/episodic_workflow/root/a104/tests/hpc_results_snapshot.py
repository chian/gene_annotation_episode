"""Reusable explicit own-A104 archived-source importer for Results controls.

The archive is authenticated by a test promotion. It is not a historical
execution environment. External modules remain the recorded current inputs.
No missing A104 module may fall back to canonical application code.
"""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104'
AXIS = Path(*PREFIX.split('.'))
TEST_NAMES = ('test_a104_results_preservation.py', 'test_a104_results_boundaries.py',
    'test_a104_results_native_receipts.py', 'test_a104_results_progress.py')
def digest(raw): return hashlib.sha256(raw).hexdigest()

def materialize(repository, destination):
    repository, destination = Path(repository).resolve(), Path(destination).resolve()
    assert destination.is_relative_to(repository / 'runs') and not destination.exists()
    assets = repository / AXIS / 'tests/fixtures/hpc_results_preunion'
    record = json.loads((assets / 'source_manifest.json').read_bytes())
    assert record['version'] == 'a104_preunion_results_required_source_archive_v1'
    assert record['axis'] == str(AXIS) and record['historical_prechange_execution_claimed'] is False
    expected = {}
    for name, entry in record['assets'].items():
        assert Path(name).is_relative_to(AXIS)
        source = (repository / entry['asset']).resolve(); assert source.is_relative_to(assets)
        data = source.read_bytes()
        assert digest(data) == entry['sha256'] == record['source_sha256'][name]
        target = destination / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        expected[name] = digest(data)
    for name in (*TEST_NAMES, 'hpc_results_snapshot.py'):
        relative = AXIS / 'tests' / name
        data = (repository / relative).read_bytes()
        target = destination / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        assert str(relative) not in expected; expected[str(relative)] = digest(data)
    # Preserve pytest's full package name. These three unchanged current parent
    # initializers are package-discovery inputs, not archived A104 application.
    scaffolding = ('gene_annotation_episode/__init__.py',
        'gene_annotation_episode/episodic_workflow/__init__.py',
        'gene_annotation_episode/episodic_workflow/root/__init__.py')
    assert set(record['current_package_scaffolding']) == set(scaffolding)
    for name in scaffolding:
        data = (repository / name).read_bytes()
        assert digest(data) == record['current_package_scaffolding'][name]
        target = destination / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        assert name not in expected; expected[name] = digest(data)
    actual = {str(p.relative_to(destination)): digest(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}
    assert actual == expected
    return record, expected

class ExactOwnSource(importlib.abc.MetaPathFinder):
    def __init__(self, directory): self.directory = Path(directory).resolve()
    def find_spec(self, fullname, path=None, target=None):
        if fullname != PREFIX and not fullname.startswith(PREFIX + '.'):
            return None
        directory = self.directory / Path(*fullname.split('.'))
        package_file = directory / '__init__.py'
        module_file = directory.with_suffix('.py')
        if package_file.is_file():
            return importlib.util.spec_from_file_location(fullname, package_file,
                submodule_search_locations=[str(directory)])
        if module_file.is_file(): return importlib.util.spec_from_file_location(fullname, module_file)
        raise ModuleNotFoundError('archived_own_A104_module_absent:' + fullname, name=fullname)

def install(directory):
    assert not any(name == PREFIX or name.startswith(PREFIX + '.') for name in sys.modules)
    finder = ExactOwnSource(directory); sys.meta_path.insert(0, finder); return finder

def module_custody(own_root):
    own_root = Path(own_root).resolve(); own, external = {}, {}
    for name, module in tuple(sys.modules.items()):
        raw = getattr(module, '__file__', None)
        if not raw: continue
        file = Path(raw).resolve()
        if not file.is_file(): continue
        value = {'path': str(file), 'sha256': digest(file.read_bytes())}
        if name == PREFIX or name.startswith(PREFIX + '.'):
            assert file.is_relative_to(own_root / AXIS), (name, str(file))
            own[name] = value
        else: external[name] = value
    return {'own': own, 'current_external_modules': external}
