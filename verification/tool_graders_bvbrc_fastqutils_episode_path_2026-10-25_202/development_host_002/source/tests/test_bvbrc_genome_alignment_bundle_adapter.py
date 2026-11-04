"""Public facade purity and exact source/schema dependency pin."""
import ast
import builtins
import hashlib
import inspect
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as facade
from gene_annotation_episode import bvbrc_genome_alignment_bundle_resolution as resolution
from test_bvbrc_genome_alignment_bundle_resolution import arguments


BASE = Path(facade.__file__).parent


def actual_local_closure():
    """Audit real imports, including function-local imports, and local schemas.

    C's existing reader imports acquisition and execution contracts, so their
    source dependencies are included. Instantiating unrelated clients/library
    classes is not part of the facade: their runtime data directories are not
    E-loaded schema resources. The I/O barrier below checks that distinction.
    """
    pending = ['bvbrc_genome_alignment_bundle_adapter']; seen = set(); resources = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((BASE / (name + '.py')).read_text())):
            imports = []
            if isinstance(node, ast.ImportFrom):
                if node.level == 1:
                    imports = [node.module] if node.module else [a.name for a in node.names]
                elif node.module and node.module.startswith('gene_annotation_episode.'):
                    imports = [node.module.split('.')[1]]
            elif isinstance(node, ast.Import):
                imports = [a.name.split('.')[1] for a in node.names if a.name.startswith('gene_annotation_episode.')]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(('.json', '.toml')):
                if (BASE / node.value).is_file():
                    resources.add(node.value)
            pending.extend(m for m in imports if m and m not in seen and (BASE / (m + '.py')).is_file())
    return {m + '.py' for m in seen} | resources | {'__init__.py'}


def test_public_callable_protocol_and_exact_transitive_pin_closure():
    assert facade.ADAPTER_ID == 'bvbrc_genome_alignment' and facade.ADAPTER_VERSION == '1'
    for name in ('validate_parameters', 'parameters_schema', 'requested_form_schema', 'validate_requested_form',
                 'consume_bundle', 'implementation_sha256'):
        assert callable(getattr(facade, name))
    signature = inspect.signature(facade.consume_bundle)
    assert list(signature.parameters) == ['bundle', 'artifact_bytes', 'supplied_values', 'retained_records', 'requested_form', 'parameters']
    assert signature.parameters['retained_records'].default is inspect.Parameter.empty
    assert len(facade._DEPENDENCIES) == len(set(facade._DEPENDENCIES))
    assert set(facade._DEPENDENCIES) == actual_local_closure()
    assert 'bvbrc_appservice_schemas.json' in facade._DEPENDENCIES
    assert 'bvbrc_genome_alignment_retained_records.py' in facade._DEPENDENCIES
    assert 'bvbrc_genome_alignment_returns.py' not in facade._DEPENDENCIES


def test_pin_uses_actual_sorted_filenames_exact_bytes_and_decimal_length_framing():
    digest = hashlib.sha256()
    for name in sorted(actual_local_closure()):
        content = (BASE / name).read_bytes()
        digest.update(name.encode('utf-8') + b'\0' + str(len(content)).encode('ascii') + b'\0' + content)
    assert facade.implementation_sha256() == digest.hexdigest()


@pytest.mark.parametrize('changed_name', facade._DEPENDENCIES)
def test_every_source_and_schema_dependency_changes_pin_without_editing_shared_files(monkeypatch, changed_name):
    originals = {name: (BASE / name).read_bytes() for name in facade._DEPENDENCIES}
    expected = facade.implementation_sha256()
    monkeypatch.setattr(Path, 'read_bytes', lambda path: originals[path.name] + (b'\n# pin mutation' if path.name == changed_name else b''))
    assert facade.implementation_sha256() != expected


def test_unrelated_adapter_and_downstream_consumer_bytes_are_not_pinned(monkeypatch):
    expected = facade.implementation_sha256(); original = Path.read_bytes; reads = []
    unrelated = {'bvbrc_msa_bundle_adapter.py', 'bvbrc_genome_alignment_returns.py'}
    def changed(path):
        reads.append(path.name)
        return b'unrelated changed source' if path.name in unrelated else original(path)
    monkeypatch.setattr(Path, 'read_bytes', changed)
    assert facade.implementation_sha256() == expected
    assert set(reads).isdisjoint(unrelated)


def test_consume_is_pure_and_calculates_exactly_once(monkeypatch):
    args = arguments()
    expected = facade.consume_bundle(**args)
    def forbidden(*a, **k):
        raise AssertionError('I/O, native execution, acquisition or pinning during consume')
    for module, name in ((builtins, 'open'), (Path, 'open'), (socket, 'socket'), (subprocess, 'Popen'),
                         (facade, 'implementation_sha256')):
        monkeypatch.setattr(module, name, forbidden)
    calls = []; actual = resolution.calculate_genome_alignment_components
    def counted(data, *, calculation_plan):
        calls.append(calculation_plan)
        return actual(data, calculation_plan=calculation_plan)
    monkeypatch.setattr(resolution, 'calculate_genome_alignment_components', counted)
    assert facade.consume_bundle(**args) == expected
    assert calls == [args['parameters']['calculation_plan']]
