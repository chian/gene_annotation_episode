"""Bind existing public runtime files; never start the configured model."""
from __future__ import annotations
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_001'
OUT = HERE / 'verification_001'


def main():
    spec = importlib.util.spec_from_file_location('owned_metadata_preflight', HERE / 'verify_preparation_001.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.verify_pin(PIN)
    helper.install_pin(PIN)
    calls, blocked = helper.forbid_model()
    previously_loaded = json.loads((OUT / 'CONTRACT_SNAPSHOT_NEW_001.json').read_bytes())['actual_project_imports']
    for row in previously_loaded:
        module = importlib.import_module(row['module'])
        assert str(Path(module.__file__).resolve()) == row['path']
        assert helper.sha(row['path']) == row['sha256']
    from method_loop.durable import DurableExecutionStore
    from gene_annotation_episode import providers
    configuration = providers.load_config()  # packaged public defaults only
    executable = shutil.which(configuration['connection']['command'][0])
    assert executable is not None
    roots = [str(Path(inspect.getfile(DurableExecutionStore)).resolve().parent.parent),
             *(str(Path(entry or os.getcwd()).resolve()) for entry in sys.path)]
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join(dict.fromkeys(roots))
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    probe_code = '''import inspect,json
from gene_annotation_episode import providers
def forbidden(*a, **kw): raise AssertionError("worker import probe forbids model entry")
for cls in (providers.ModelConnection, providers._SessionConnection):
    for name in ("__init__", "__aenter__", "complete", "catalog"): setattr(cls,name,forbidden)
providers._SessionConnection._rpc=forbidden
from gene_annotation_episode.state import Store
from gene_annotation_episode.independent_execution import open_commission
from method_loop.episode import Episode
import method_loop.durable_worker as worker
print(json.dumps([inspect.getfile(x) for x in (Store,Episode,worker,inspect.unwrap(open_commission))]))
'''
    command = [sys.executable, '-P', '-B', '-c', probe_code]
    probe = subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
    paths = json.loads(probe.stdout)
    assert len(paths) == 4 and all(Path(path).resolve().is_relative_to(PIN) for path in paths)
    helper.save(OUT / 'WORKER_IMPORT_PROBE_001.json', {'exit_code': probe.returncode,
        'actual_paths': paths, 'safe_path': True, 'bytecode_disabled': True,
        'runtime_root_first': roots[0], 'configured_model_entered': False,
        'scope': 'fresh Python import probe; no worker commission or provider started'})
    from packaging.requirements import Requirement
    package_map = importlib.metadata.packages_distributions()
    loaded, project = [], []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if not path.is_file():
            continue
        row = {'module': name, **helper.fingerprint(path)}
        if name.split('.')[0] in {'gene_annotation_episode', 'method_loop'}:
            assert path.is_relative_to(PIN)
            project.append(row)
        elif path != Path(__file__).resolve() and not path.is_relative_to(HERE):
            loaded.append(row)
    names = {dist for row in loaded for dist in package_map.get(row['module'].split('.')[0], [])}
    # Include all installed runtime files declared by each actually imported
    # distribution, plus recursively required active non-extra dependencies.
    pending, selected = list(names), {}
    while pending:
        name = pending.pop()
        distribution = importlib.metadata.distribution(name)
        normalized = distribution.metadata['Name'].lower().replace('_', '-')
        if normalized in selected:
            continue
        selected[normalized] = distribution
        for literal in distribution.requires or []:
            requirement = Requirement(literal)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                pending.append(requirement.name)
    distributions = []
    for name, distribution in sorted(selected.items()):
        files, caches, missing = [], [], []
        for relative in distribution.files or []:
            path = Path(distribution.locate_file(relative)).resolve()
            if '__pycache__' in relative.parts or path.suffix in ('.pyc', '.pyo'):
                caches.append(str(relative))
            elif path.is_file():
                files.append({'distribution_relative_path': str(relative), **helper.fingerprint(path)})
            else:
                missing.append(str(relative))
        assert files and not missing, (name, missing)
        distributions.append({'name': distribution.metadata['Name'], 'version': distribution.version,
            'files': files, 'excluded_regenerable_bytecode_caches': caches,
            'RECORD_present': any(Path(row['path']).name == 'RECORD' for row in files)})
    interpreter = Path(sys.executable)
    pyvenv = interpreter.parent.parent / 'pyvenv.cfg'
    assert pyvenv.is_file()
    binding = {'scope': 'Existing public Python/runtime file identity, not a hermetic operating-system image',
        'interpreter_invocation_path': str(interpreter), 'resolved_interpreter': helper.fingerprint(interpreter),
        'python_version': sys.version, 'pyvenv_cfg': helper.fingerprint(pyvenv),
        'stdlib_path': sysconfig.get_path('stdlib'), 'extension_suffix': sysconfig.get_config_var('EXT_SUFFIX'),
        'configured_executable_invocation_path': executable, 'configured_executable': helper.fingerprint(executable),
        'configured_executable_started': False, 'installed_distributions': distributions,
        'actually_loaded_external_module_files': loaded, 'actual_project_imports': project,
        'model_entrypoints_disabled': blocked, 'attempted_model_entrypoints': calls,
        'binding_algorithm': 'actual external modules plus installed distribution files and active non-extra dependency closure; regenerable bytecode excluded explicitly',
        'excluded': ['user/provider configuration', 'credentials', 'environment dump', 'process argv', 'scientific input decoding', 'network/model execution']}
    assert not calls
    helper.save(HERE / 'RUNTIME_DEPENDENCIES_001.json', binding)
    # Recheck every authoritative file after collecting the complete binding.
    rows = [binding['resolved_interpreter'], binding['pyvenv_cfg'], binding['configured_executable'], *loaded]
    rows.extend(row for dist in distributions for row in dist['files'])
    for row in rows:
        assert helper.fingerprint(row['path']) == {k: row[k] for k in ('path', 'bytes', 'sha256')}, row['path']
    helper.verify_pin(PIN)
    helper.save(OUT / 'DEPENDENCY_AFTER_001.json', {'status': 'passed',
        'authoritative_file_rows_reverified': len(rows), 'distributions': len(distributions),
        'external_loaded_modules': len(loaded), 'project_imports': len(project),
        'binding_sha256': helper.sha(HERE / 'RUNTIME_DEPENDENCIES_001.json'),
        'pin_unchanged': True, 'model_entries': 0})
    print(json.dumps({'status': 'passed', 'worker_import_paths': len(paths),
        'distributions': len(distributions), 'external_loaded_modules': len(loaded),
        'authoritative_file_rows_reverified': len(rows), 'project_imports': len(project),
        'model_entries': 0, 'scientific_input_decoding': False}))


if __name__ == '__main__':
    main()
