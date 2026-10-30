"""Read-only, fresh-process registry, source and package-origin verification."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import resource
import socket
import sys

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
TARGET = Path(sys.argv[1]).resolve()
OUT = OWN / sys.argv[2]
assert OUT.parent == OWN and not OUT.exists()
sys.dont_write_bytecode = True
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
sys.path.insert(0, str(TARGET))


def forbidden(*args, **kwargs):
    raise AssertionError('Pure source/registry check attempted network access')


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = forbidden


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest_path = OWN / ('APPLICATION_AFTER_001.json' if TARGET == ROOT else 'COMPOSITION_SOURCE_BEFORE_001.json')
expected = json.loads(manifest_path.read_text())
before = {name: sha(TARGET / name) for name in expected}
assert before == expected
registry = importlib.import_module('gene_annotation_episode.bvbrc_appservice_adapters')
modules = ['bvbrc_homology_bundle_adapter', 'bvbrc_gene_tree_bundle_adapter',
    'bvbrc_codon_tree_bundle_adapter', 'bvbrc_msa_bundle_adapter', 'bvbrc_metacats_bundle_adapter',
    'bvbrc_genome_alignment_bundle_adapter', 'bvbrc_proteome_bundle_adapter',
    'bvbrc_proteome_bundle_adapter_v2', 'bvbrc_comparative_systems_bundle_adapter']
config, pins = [], {}
for name in modules:
    module = importlib.import_module('gene_annotation_episode.' + name)
    path = Path(module.__file__).resolve()
    assert path == TARGET / 'gene_annotation_episode' / (name + '.py')
    pin = module.implementation_sha256()
    row = {'adapter_id': module.ADAPTER_ID, 'adapter_version': module.ADAPTER_VERSION,
           'implementation_sha256': pin}
    config.append(row)
    pin_owner = importlib.import_module(module.implementation_sha256.__module__)
    pin_path = Path(pin_owner.__file__).resolve()
    assert pin_path.is_relative_to(TARGET)
    dependencies = {dep: sha(pin_path.with_name(dep)) for dep in pin_owner._DEPENDENCIES}
    assert all(expected['gene_annotation_episode/' + dep] == value for dep, value in dependencies.items())
    pins[name] = {**row, 'path': str(path), 'pin_implementation_module': pin_owner.__name__, 'dependencies': dependencies}
bound = registry.bind_adapters(config)
assert len(bound) == len(modules) == 9
for row in config:
    module, pin = bound[row['adapter_id'], row['adapter_version']]
    assert pin == row['implementation_sha256'] == module.implementation_sha256()
for name in ('communication', 'episode_return_records', 'bvbrc_proteome_returns',
             'bvbrc_genome_alignment_sheet', 'runtime'):
    importlib.import_module('gene_annotation_episode.' + name)
origins = {}
for name, module in tuple(sys.modules.items()):
    if name.split('.')[0] not in {'gene_annotation_episode', 'method_loop'}:
        continue
    filename = getattr(module, '__file__', None)
    if not filename:
        continue
    path = Path(filename).resolve()
    assert path.is_relative_to(TARGET), (name, path)
    relative = str(path.relative_to(TARGET))
    assert relative in expected and sha(path) == expected[relative], (name, path)
    origins[name] = {'path': str(path), 'sha256': sha(path)}
after = {name: sha(TARGET / name) for name in expected}
assert after == before
receipt = {'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
    'executable': sys.executable, 'cwd': str(Path.cwd()), 'exit_code': 0,
    'target': str(TARGET), 'manifest': str(manifest_path), 'manifest_sha256': sha(manifest_path),
    'verified_source_paths': len(expected), 'source_before_after_equal': True,
    'registry_bound_adapters': len(bound), 'pins': pins, 'package_origins': origins,
    'network': 'forbidden', 'no_science_or_acquisition_executed': True, 'wall_time_limit': None}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
    stream.write('\n')
OUT.chmod(0o444)
print(json.dumps({'target': str(TARGET), 'pins': {name: row['implementation_sha256'] for name, row in pins.items()},
    'verified_source_paths': len(expected), 'package_modules': len(origins), 'exit_code': 0}, sort_keys=True))
