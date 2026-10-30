"""Retain the actual library split and valid assignment examples; no transport."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from jsonschema import Draft202012Validator
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_public_search import Client
from test_bvbrc_proteome_tool_info import entry, launch, results


def forbidden(*args, **kwargs):
    raise AssertionError('library information attempted transport')


directory = Path(__file__).resolve().parent
example = directory / 'example_001'
example.mkdir(exist_ok=False)
with patch('socket.create_connection', forbidden), patch('socket.socket.connect', forbidden), \
        patch('urllib.request.OpenerDirector.open', forbidden), Store(example / 'state') as store:
    store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')
    registry = ToolRegistry(store, clients=Client())
    family = ExecutionEpisodes(None, store=store, directory=example / 'run', run_id='proteome-library-example',
        resources={'selected-api': deepcopy(CONFIG)}, initial_information={}, tool_registry=registry,
        handoff_unit=2, acquired_record_unit=3, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    row = entry(family)
    library = ScientificToolLibrary.freeze(example / 'library', catalog=[], tool_info=True,
        resource_catalogs={'api': [row]})
    selection = [{'name': row['name'], 'resources': 'api'}]
    outputs = {'LIBRARY_ENTRY': row, 'PARENT_VIEW': library.parent_tool_info([row]),
        'CHILD_INFO': library.resolve_tool_info(selection, [row]),
        'INVOCATION': library.resolve_invocations(selection, [row]),
        'LAUNCH_ASSIGNMENT': launch(), 'RESULTS_ASSIGNMENT': results()}
    validator = Draft202012Validator(row['input_schema'])
    for name in ('LAUNCH_ASSIGNMENT', 'RESULTS_ASSIGNMENT'):
        validator.validate(outputs[name])
    assert family.api_execution.validate_assignment(outputs['LAUNCH_ASSIGNMENT']) == outputs['LAUNCH_ASSIGNMENT']
    assert row['name'] not in registry.catalog()
    for name, value in outputs.items():
        (example / (name + '.json')).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

suite = ET.parse(directory / 'pytest_001.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests'] == '22' and suite.attrib['failures'] == suite.attrib['errors'] == '0'
files = ['gene_annotation_episode/bvbrc_proteome_tool_info.py', 'tests/test_bvbrc_proteome_tool_info.py']
files.extend(str(path.relative_to(ROOT)) for path in example.glob('*.json'))
receipt = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'tests': dict(suite.attrib),
    'command': '.venv/bin/python -m pytest tests/test_bvbrc_proteome_tool_info.py -q --junitxml=verification/tool_graders_bvbrc_proteome_tool_info_2026-10-25/pytest_001.xml',
    'transport_blocked': True, 'actual_library_freeze_and_resolution': True,
    'actual_api_assignment_validation': True, 'production_provider_registered': False,
    'full_episode_path_verified': False, 'live_resource_verified': False,
    'parent_fields': list(outputs['PARENT_VIEW'][0]), 'child_fields': list(outputs['CHILD_INFO'][0]),
    'routes': row['invocation_route']['routes'],
    'files': [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in files]}
(directory / 'VERIFICATION_001.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ('tests', 'parent_fields', 'child_fields',
    'production_provider_registered', 'full_episode_path_verified', 'live_resource_verified')}))
