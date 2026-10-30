"""Verify all retained Codon provider examples with installed modules and no I/O."""
from contextlib import ExitStack
from pathlib import Path
import builtins
import hashlib
import importlib
import io
import json
import os
import socket
import subprocess
import sys
from unittest.mock import patch
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import bvbrc_codon_tree_inputs as provider
from gene_annotation_episode import bvbrc_codon_tree_grader as grader
from gene_annotation_episode import bvbrc_codon_tree_native as native
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_raxml_inputs as raxml


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def main():
    manifest_path = HERE / 'codon-provider-verification/examples-manifest.json'
    manifest_raw = manifest_path.read_bytes(); manifest = json.loads(manifest_raw)
    modules = []
    for original in manifest['imports']:
        module = importlib.import_module(original['module'])
        path = Path(module.__file__).resolve()
        assert path.parent == ROOT / 'gene_annotation_episode'
        assert digest(path.read_bytes()) == original['sha256'], original['module']
        modules.append({'module': original['module'], 'path': str(path), 'sha256': original['sha256']})
    cases, operands = [], []
    for example in manifest['examples']:
        values = {}
        for key, source in example['files'].items():
            raw = Path(source['path']).read_bytes()
            assert digest(raw) == source['sha256'] and len(raw) == source['bytes']
            values[key] = json.loads(raw)
        cases.append((example['name'], values))
        operands.append({'name': example['name'], 'classification': example['classification'],
                         'source_files': example['files']})
    before = fingerprint(cases)
    denied_calls = []

    def denied(*args, **kwargs):
        denied_calls.append(True)
        raise AssertionError('Saved Codon provider replay attempted I/O or native parsing')

    targets = [(builtins, 'open'), (io, 'open'), (os, 'open'), (os, 'system'),
               (socket, 'socket'), (socket, 'create_connection'), (subprocess, 'run'),
               (subprocess, 'Popen'), (urllib.request, 'urlopen')]
    targets += [(module, name) for module in (native, formats, raxml)
                for name in dir(module) if name.startswith('parse_')]
    with ExitStack() as guards:
        for module, name in targets:
            guards.enter_context(patch.object(module, name, denied))
        for name, case in cases:
            assert provider.validate_codon_tree_sheet(case['sheet']) == case['sheet'], name
            assert grader.calculate_codon_tree(case['sheet'], case['parameters']) == case['components'], name
    assert not denied_calls and before == fingerprint(cases)
    assert manifest_path.read_bytes() == manifest_raw
    suite_path = HERE / 'production-codon-provider-tests-001.xml'
    suite = ET.parse(suite_path).getroot().find('testsuite')
    counts = {key: int(suite.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')}
    assert counts == {'tests': 89, 'failures': 0, 'errors': 0, 'skipped': 0}
    report = {'scope': 'Installed Codon provider saved validation and calculation; no service or episode-path claim',
              'tests': counts, 'saved_examples_replayed': len(cases), 'all_components_exactly_equal': True,
              'forbidden_access_attempts': len(denied_calls), 'inputs_unchanged': True,
              'modules': modules, 'operands': operands,
              'manifest_sha256': digest(manifest_raw), 'test_receipt_sha256': digest(suite_path.read_bytes()),
              'selected_tool_to_episode_return_verified': False, 'live_execution_verified': False}
    with (HERE / 'PRODUCTION_CODON_PROVIDER_VERIFICATION_001.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({key: report[key] for key in ('tests', 'saved_examples_replayed',
        'all_components_exactly_equal', 'forbidden_access_attempts', 'inputs_unchanged')}))


if __name__ == '__main__':
    main()
