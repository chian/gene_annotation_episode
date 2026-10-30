"""Add the missing truthful generic-text locator; preserve all earlier schemas."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / 'a105_visual_signal_design_067'
DESTINATION = HERE / 'text_locator_declarations_008'


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')


def main():
    from jsonschema import Draft202012Validator
    DESTINATION.mkdir(exist_ok=False)
    reference = {'type': 'string', 'format': 'reference'}
    text_span = obj({'kind': {'const': 'text_span'}, 'source_ref': deepcopy(reference),
        'artifact_ref': deepcopy(reference), 'representation': {'type': 'string', 'enum': ['original', 'text']},
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1},
        'quote': {'type': 'string', 'minLength': 1}})
    old = json.loads((DESIGN / 'EXTRACTION_SCHEMA_006.json').read_bytes())
    extraction = deepcopy(old)
    extraction['properties']['version']['const'] = 'relative_signal_source_extraction_v3'
    changed = []
    def visit(node, path=''):
        if isinstance(node, dict):
            if set(node.get('properties', {})) == {'selection', 'locator', 'authentication', 'attribution', 'diagnostics'}:
                union = node['properties']['locator']['anyOf'][0]['oneOf']
                assert [item['properties']['kind']['const'] for item in union] == ['jats', 'image']
                union.append(deepcopy(text_span)); changed.append(path + '.properties.locator')
            for name, value in node.items():
                visit(value, path + '.' + name)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, path + '[' + str(index) + ']')
    visit(extraction)
    assert changed
    reverted = deepcopy(extraction)
    reverted['properties']['version']['const'] = old['properties']['version']['const']
    def reverse(node):
        if isinstance(node, dict):
            if set(node.get('properties', {})) == {'selection', 'locator', 'authentication', 'attribution', 'diagnostics'}:
                actual = node['properties']['locator']['anyOf'][0]['oneOf'].pop()
                assert actual == text_span
            for child in node.values():
                reverse(child)
        elif isinstance(node, list):
            for child in node:
                reverse(child)
    reverse(reverted)
    assert reverted == old
    for family in ('REQUEST', 'SHEET', 'RETURN'):
        original = (DESIGN / (family + '_SCHEMA_006.json')).read_bytes()
        with (DESTINATION / (family + '_SCHEMA_008.json')).open('xb') as stream:
            stream.write(original)
    save(DESTINATION / 'EXTRACTION_SCHEMA_008.json', extraction)
    interface = json.loads((DESIGN / 'INTERFACE_006.json').read_bytes())
    interface['normative_declaration_generation'] = '008'
    interface['schemas'] = {key: value.replace('_006.json', '_008.json') for key, value in interface['schemas'].items()}
    interface['native_storage']['version'] = 'literature_relative_signal_source_record_v3'
    interface['supersedes'] = '006 plus exact generic text_span locators; extraction/native payload advance to v3; request/sheet/typed return unchanged'
    interface['text_locator_correction'] = {'extraction_version': 'relative_signal_source_extraction_v3',
        'native_record_version': 'literature_relative_signal_source_record_v3',
        'text_span_locator': text_span,
        'meaning': 'An authenticated generic text witness retains its actual artifact, representation, UTF8 byte offsets and exact quote. No JATS section/paragraph is invented.',
        'unchanged': ['request selection v2', 'numerical sheet v2', 'typed return schema', 'all numerical component meanings',
            'actual JATS percentage locators', 'visual image locators', 'source/host fixture origin', 'old v1 and frozen pins']}
    save(DESTINATION / 'INTERFACE_008.json', interface)
    documents = [DESTINATION / (family + '_SCHEMA_008.json') for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN')]
    for path in documents:
        Draft202012Validator.check_schema(json.loads(path.read_bytes()))
    receipt = {'status': 'passed', 'scope': 'Additive exact declaration correction only; no reader, Store, model or numerical action',
        'authenticated_witness_locator_nodes_corrected': len(changed), 'changed_paths': changed,
        'reverse_to006_exact': True, 'request_sheet_return_byte_identical_to006': True,
        'draft_schema_meta_checks': 4, 'files': {p.name: {'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(DESTINATION.iterdir()) if p.is_file()}}
    save(HERE / 'TEXT_LOCATOR_DECLARATION_RECEIPT_008.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('status', 'authenticated_witness_locator_nodes_corrected',
        'reverse_to006_exact', 'request_sheet_return_byte_identical_to006', 'draft_schema_meta_checks')}))


if __name__ == '__main__':
    main()
