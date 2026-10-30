"""Freeze the reviewed native-only subset; preserve the original proposal."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
proposal_path = HERE / 'PROPOSED_CONTRACTS_001.json'
service_path = ROOT / 'gene_annotation_episode/bvbrc_appservice_schemas.json'
proposal = json.loads(proposal_path.read_text())
service = json.loads(service_path.read_text())
definitions = deepcopy(proposal['$defs'])
definitions['ContentBinding'] = deepcopy(service['$defs']['ContentBinding'])
definitions['NativeSource'] = {
    'type': 'object', 'properties': {
        'content': {'$ref': '#/$defs/ContentBinding'},
        'body_complete': {'type': 'boolean'},
        'object_complete': {'enum': ['yes', 'no', 'unknown']}},
    'required': ['content', 'body_complete', 'object_complete'],
    'additionalProperties': False,
}
definitions['NativeProjection']['properties']['source'] = {'$ref': '#/$defs/NativeSource'}
definitions['NativeProjection']['properties']['projection_completeness']['enum'] = [
    'complete_document', 'complete_prefix_only', 'partial_or_unknown_artifact', 'invalid_document']


def referenced(value):
    if isinstance(value, dict):
        if '$ref' in value:
            assert value['$ref'].startswith('#/$defs/')
            yield value['$ref'].removeprefix('#/$defs/')
        for item in value.values():
            yield from referenced(item)
    elif isinstance(value, list):
        for item in value:
            yield from referenced(item)


selected = {}
pending = ['NativeProjectionResult', 'NativeJSONDocument', 'NativeSource']
while pending:
    name = pending.pop()
    if name in selected:
        continue
    selected[name] = definitions[name]
    pending.extend(referenced(definitions[name]))
assert 'ArtifactSource' not in selected and 'TaskIdentity' not in selected
document = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'urn:gene-annotation:proteome-native-contracts:002',
    '$defs': {name: selected[name] for name in sorted(selected)}}
Draft202012Validator.check_schema(document)
encoded = (json.dumps(document, indent=2) + '\n').encode()
receipt = {'status': 'native_data_contract_frozen_not_implemented',
    'proposal_sha256': hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
    'existing_service_contract_sha256': hashlib.sha256(service_path.read_bytes()).hexdigest(),
    'native_contract_sha256': hashlib.sha256(encoded).hexdigest(),
    'definitions': list(document['$defs']), 'scope': 'native_format_parser_only',
    'full_producer_retention_still_required': True,
    'native_output_observed': False, 'runtime_or_source_pin_changes': False}
with (HERE / 'NATIVE_CONTRACTS_002.json').open('xb') as output:
    output.write(encoded)
with (HERE / 'NATIVE_CONTRACT_RECEIPT_002.json').open('x') as output:
    json.dump(receipt, output, indent=2)
    output.write('\n')
print(json.dumps(receipt))
