"""Verify installed FastqUtils numerics, recalculation and non-recomputing returns."""
from copy import deepcopy
import base64
import importlib
import json
from pathlib import Path
import socket
import sys
import urllib.request

sys.dont_write_bytecode = True
installed, specimen = map(lambda value: Path(value).resolve(), sys.argv[1:])
sys.path.insert(0, str(installed))
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_fastqutils_calculators as calculators
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, BVBRCFastqUtilsReturns, parent_form_schema, project_fastqutils_return_facts,
    encode_return_value, decode_return_value,
)
from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_contracts import canonical


def read(name):
    return json.loads((specimen / name).read_text())


def forbidden(*args, **kwargs):
    raise AssertionError('Unexpected acquisition, native parsing or scientific replay')


socket.socket.connect = forbidden
urllib.request.OpenerDirector.open = forbidden
inputs, expected = read('provider_input.json'), read('provider_result.json')
artifact_bytes = {key: base64.b64decode(value, validate=True) for key, value in inputs.pop('artifact_bytes_base64').items()}
input_snapshot = canonical(inputs)
actual = adapter.consume_bundle(artifact_bytes=artifact_bytes, **inputs)
assert actual == expected, 'Installed result differs from the frozen source result'
assert canonical(inputs) == input_snapshot
assert adapter.implementation_sha256() == 'e25e6accdeb551f989701d50b2bfed8a6f9393da31848cbc62a0fb2f5856e135'
numbers = {name: actual['facts'][name]['records'][0]['payload']['value']
    for name in ('read_count', 'gc', 'errors', 'retained')}
assert numbers == {'read_count': 2, 'gc': 5 / 9, 'errors': .001, 'retained': .75}
assert actual['facts']['association']['records'][0]['payload']['state'] == 'unresolved'
assert all(stage['state'] == 'unknown' for stage in actual['sheet']['stages'])

# Recalculation reads the saved sheet with native parsing and networking disabled.
# The original stored result must remain unchanged when parameters change.
for module_name, names in {
    'bvbrc_fastqutils_bundle_adapter': ('consume_bundle', 'parse_fastqutils_artifact', 'populate_fastqutils_sheet'),
    'bvbrc_fastqutils_native': ('parse_fastqutils_artifact',),
    'bvbrc_fastqutils_sheet': ('populate_fastqutils_sheet',),
}.items():
    module = importlib.import_module('gene_annotation_episode.' + module_name)
    for name in names:
        setattr(module, name, forbidden)
original_snapshot = canonical(actual)
sheet = actual['sheet']
parameters = actual['components']['calculations']['parameters']
assert calculators.calculate_fastqutils(sheet, parameters=parameters) == actual['components']['calculations']
changed = deepcopy(parameters)
quality, = [job for job in changed['calculations'] if job['method'] == 'quality_phred_v1']
quality['quality_thresholds'] = [40, 41]
recalculated = calculators.calculate_fastqutils(sheet, parameters=changed)
fractions = {row['threshold']: row['value'] for row in recalculated['components']
    if row['metric'] == 'q_ge_threshold_fraction'}
assert fractions == {40: 1, 41: 0}
assert canonical(actual) == original_snapshot
assert recalculated['sheet_sha256'] == actual['components']['calculations']['sheet_sha256']
assert {row['parameter_sha256'] for row in recalculated['components']}.isdisjoint(
    {row['parameter_sha256'] for row in actual['components']['calculations']['components']})

# Saved communication must work after all scientific calculators are unavailable.
calculators.calculate_fastqutils = forbidden
adapter.calculate_fastqutils = forbidden
for module_name, function in (
    ('composition', 'calculate_composition'), ('quality', 'calculate_quality'),
    ('mapping', 'calculate_mapping'), ('retention', 'calculate_retention'),
    ('consistency', 'calculate_report_consistency')):
    setattr(importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + module_name), function, forbidden)
body = read('saved_publication.json')
facts = project_fastqutils_return_facts(body, requested_sources=FACT_SOURCES,
    sheet=sheet, components=actual['components'])
assert facts == read('communication.json') and len(facts) == 7 and all(facts.values())
form = parent_form_schema(validate_requested_form(inputs['requested_form']))
returned = {name: facts[node['x-source']] for name, node in form['properties'].items()}
validate_form(returned, form,
    lambda reference, namespace=None: BVBRCFastqUtilsReturns._has_reference(facts, reference, namespace))
for field in actual['facts'].values():
    kind = field['selection']['target']['kind']
    assert decode_return_value(kind, encode_return_value(kind, field)) == field
assert canonical(actual) == original_snapshot
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(installed / name.split('.')[0]), (name, path)
        origins[name] = str(path)
print(json.dumps({'provider_pin': adapter.implementation_sha256(), 'numbers': numbers,
    'changed_threshold_fractions': fractions, 'same_parameters_reproduce_original': True,
    'changed_parameters_preserve_original': True, 'saved_communication_without_science': True,
    'fact_family_count': len(facts), 'field_count': len(actual['facts']),
    'matches_frozen_source_result': True, 'installed_origins': origins,
    'host_custody_verified': False, 'live_service_execution_verified': False}))
