"""Add explicit scalar types required by the existing closed parent grammar."""
from copy import deepcopy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def typed_constants(node):
    node = deepcopy(node)
    if isinstance(node, dict):
        if 'const' in node and 'type' not in node:
            assert isinstance(node['const'], str)
            node['type'] = 'string'
        for name, value in tuple(node.items()):
            node[name] = typed_constants(value)
    elif isinstance(node, list):
        node = [typed_constants(value) for value in node]
    return node


def main():
    for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN'):
        document = json.loads((HERE / (family + '_SCHEMA_004.json')).read_text())
        if family == 'RETURN':
            document = typed_constants(document)
        with (HERE / (family + '_SCHEMA_005.json')).open('x') as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
    interface = json.loads((HERE / 'INTERFACE_004.json').read_text())
    interface['normative_declaration_generation'] = '005'
    interface['schemas'] = {key: value.replace('_004.json', '_005.json') for key, value in interface['schemas'].items()}
    interface['supersedes'] = 'INTERFACE_004 plus explicit parent-form constant scalar types; no scientific meaning/version/runtime change'
    with (HERE / 'INTERFACE_005.json').open('x') as stream:
        json.dump(interface, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'final_declaration_generation': '005', 'parent_constant_types_explicit': True,
        'other_three_schema_contents_unchanged': True, 'application_imports': 0}))


if __name__ == '__main__':
    main()
