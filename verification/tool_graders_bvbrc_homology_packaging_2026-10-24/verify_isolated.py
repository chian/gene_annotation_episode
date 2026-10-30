"""Verify installed-package resources and a retained synthetic numerical example."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

installed, original, fixture = map(Path, sys.argv[1:4])
sys.path.insert(0, str(installed))

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.bvbrc_appservice_contracts import contract_schema
from gene_annotation_episode.bvbrc_homology_grader import calculate_homology_scores
from gene_annotation_episode.bvbrc_homology_returns import homology_fact_sources
from gene_annotation_episode.bvbrc_homology_tool_info import homology_tool_contracts
from gene_annotation_episode.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService

assert Path(adapter.__file__).is_relative_to(installed)
names = [*adapter._DEPENDENCIES, 'bvbrc_appservice_adapters.py', 'bvbrc_appservice_publication.py',
    'bvbrc_homology_returns.py', 'bvbrc_homology_tool_info.py', 'bvbrc_appservice_host.py',
    'bvbrc_appservice_monitor.py', 'execution_episodes.py', 'api_service_execution.py']
hashes = {}
for name in names:
    raw = (installed / 'gene_annotation_episode' / name).read_bytes()
    assert raw == (original / 'gene_annotation_episode' / name).read_bytes(), name
    hashes[name] = hashlib.sha256(raw).hexdigest()
pin = adapter.implementation_sha256()
bound = bind_adapters([{'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
    'implementation_sha256': pin}])
assert bound[(adapter.ADAPTER_ID, adapter.ADAPTER_VERSION)][0] is adapter
assert len(homology_fact_sources()) == 3
assignment = json.loads(json.dumps(API_SERVICE_ASSIGNMENT_SCHEMA))
assignment['properties']['request'] = BVBRCAppServiceService.request_schema
rows = homology_tool_contracts(resource_id='configured-fixture-api', assignment_schema=assignment)
assert len(rows) == 2
assert contract_schema('ResolvedInputs')
inputs = json.loads((fixture / 'SYNTHETIC_INPUTS.json').read_text())
raws = {artifact['raw_artifact_ref']: (fixture / 'native' / (artifact['role'] + '.bytes')).read_bytes()
    for artifact in inputs['bundle']['artifacts']}
expected = json.loads((fixture / 'SYNTHETIC_RESULT.json').read_text())

def forbidden(*args, **kwargs):
    raise AssertionError('isolated parser/calculator attempted native execution or network')

socket.create_connection = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
subprocess.run = forbidden
subprocess.Popen = forbidden
value = adapter.consume_bundle(inputs['bundle'], artifact_bytes=raws,
    supplied_values=inputs['supplied_values'], requested_form=inputs['requested_form'],
    parameters=inputs['parameters'])
assert value == expected
rescored = calculate_homology_scores(value['sheet'], database_model={'temperature_bits': 1})
kernel = rescored['queries'][0]['conditional_function_weights']
assert kernel['parameters']['temperature_bits'] == 1
print(json.dumps({'loaded_from_isolated_wheel': True,
    'verification': 'installed modules/schema and retained synthetic numerical example; not live API or full installed Workflow',
    'scientific_implementation_sha256': pin, 'module_sha256': hashes,
    'artifact_count': len(raws), 'result_status': value['status'], 'requested_facts': value['facts'],
    'saved_sheet_recalculation_temperature_bits': kernel['parameters']['temperature_bits'],
    'tool_names': [row['name'] for row in rows]}, sort_keys=True))
