"""Replay retained complete provider examples against actual installed modules."""
from contextlib import ExitStack
from pathlib import Path
import builtins
import gzip
import hashlib
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
from gene_annotation_episode import bvbrc_phylogeny_common_inputs as common_inputs
from gene_annotation_episode import bvbrc_phylogeny_common_contracts as common_contracts
from gene_annotation_episode import bvbrc_phylogeny_common_grader as common_grader
from gene_annotation_episode import bvbrc_gene_tree_inputs as gene_inputs
from gene_annotation_episode import bvbrc_gene_tree_grader as gene_grader
from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_calculators as calculators
from gene_annotation_episode import phylogeny_raxml_inputs as raxml
from gene_annotation_episode import bvbrc_codon_tree_native as codon_native


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def main():
    installation_path = HERE / 'PRODUCTION_PROVIDER_INSTALLATION_001.json'
    installation = json.loads(installation_path.read_text())
    for row in installation['files']:
        assert digest(Path(row['target']).read_bytes()) == row['target_sha256']
    modules = (common_inputs, common_contracts, common_grader, gene_inputs,
               gene_grader, formats, calculators, raxml, codon_native)
    assert all(Path(module.__file__).resolve().parent == ROOT / 'gene_annotation_episode' for module in modules)
    sources, cases = [], []
    manifest = json.loads((HERE / 'provider-common-verification/EXAMPLES_MANIFEST.json').read_text())
    for record in manifest['examples']:
        path = Path(record['path']); data = path.read_bytes()
        assert digest(data) == record['sha256'] and len(data) == record['compressed_bytes']
        case = json.loads(gzip.decompress(data))
        cases.append(('common', record['name'], case))
        sources.append({'path': str(path), 'sha256': digest(data)})
    directory = HERE / 'gene-provider-verification/examples_002'
    metrics = json.loads((directory / 'METRICS.json').read_text())
    for record in metrics:
        path = directory / (record['name'] + '.json'); data = path.read_bytes()
        cases.append(('gene', record['name'], json.loads(data)))
        sources.append({'path': str(path), 'sha256': digest(data)})
    before = fingerprint(cases)
    attempts, checked = [], []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Saved provider calculation attempted I/O, native parsing, or execution')

    targets = [(builtins, 'open'), (io, 'open'), (os, 'open'), (os, 'system'),
               (socket, 'socket'), (socket, 'create_connection'),
               (subprocess, 'run'), (subprocess, 'Popen'), (urllib.request, 'urlopen')]
    targets += [(module, name) for module in (formats, raxml, codon_native)
                for name in dir(module) if name.startswith('parse_')]
    with ExitStack() as guards:
        for module, name in targets:
            guards.enter_context(patch.object(module, name, denied))
        for kind, name, case in cases:
            if kind == 'common':
                arguments = case['extraction_inputs']
                assert common_inputs.extract_common_fields(**arguments) == case['extraction_result']
                common_contracts.validate_shared_fields(case['sheet'], provider=arguments['provider'])
                actual = common_grader.calculate_common_components(case['sheet'], provider=arguments['provider'], parameters=case['parameters'])
            else:
                assert gene_inputs.extract_gene_tree_sheet(**case['input']) == case['extraction']
                sheet = case['extraction']['value']
                assert gene_inputs.validate_gene_tree_sheet(sheet) == sheet
                actual = gene_grader.calculate_gene_tree(sheet, case['calculation_parameters'])
            assert actual == case['components'], (kind, name)
            checked.append({'provider': kind, 'example': name, 'equal': True})
    assert before == fingerprint(cases) and not attempts
    suite_path = HERE / 'production-common-gene-tests-001.xml'
    suite = ET.parse(suite_path).getroot().find('testsuite')
    counts = {key: int(suite.attrib[key]) for key in ('tests', 'errors', 'failures', 'skipped')}
    assert counts == {'tests': 102, 'errors': 0, 'failures': 0, 'skipped': 0}
    report = {'scope': 'Installed shared/GeneTree extraction, saved validation and pure calculation',
              'tests': counts, 'examples': checked, 'forbidden_access_attempts': len(attempts),
              'inputs_unchanged': True, 'example_sources': sources,
              'modules': [{'path': str(Path(module.__file__).resolve()),
                           'sha256': digest(Path(module.__file__).read_bytes())} for module in modules],
              'test_receipt': {'path': str(suite_path), 'sha256': digest(suite_path.read_bytes())},
              'production_provider_installation_sha256': digest(installation_path.read_bytes()),
              'selected_tool_to_episode_return_verified': False, 'live_execution_verified': False}
    with (HERE / 'PRODUCTION_PROVIDER_VERIFICATION_001.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'tests': counts, 'replayed_examples': len(checked),
                      'forbidden_access_attempts': len(attempts), 'inputs_unchanged': True}))


if __name__ == '__main__':
    main()
