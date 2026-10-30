"""Retain an explicit host-owned synthetic-fixture origin in final declarations."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN'):
        document = json.loads((HERE / (family + '_SCHEMA_005.json')).read_text())
        def visit(node):
            if isinstance(node, dict):
                for name, child in node.get('properties', {}).items():
                    if name == 'origin' and isinstance(child, dict) and 'enum' in child and 'synthetic' not in child['enum']:
                        child['enum'].append('synthetic')
                    if name == 'source_origins' and 'synthetic' not in child['items']['enum']:
                        child['items']['enum'].append('synthetic')
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        visit(document)
        if family == 'EXTRACTION':
            document['properties']['evidence_origin'] = {'type': 'string', 'enum': ['reported_source', 'synthetic_fixture']}
            document['required'].append('evidence_origin')
        with (HERE / (family + '_SCHEMA_006.json')).open('x') as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
    interface = json.loads((HERE / 'INTERFACE_005.json').read_text())
    interface['normative_declaration_generation'] = '006'
    interface['schemas'] = {key: value.replace('_005.json', '_006.json') for key, value in interface['schemas'].items()}
    interface['public_apis']['read_relative_signal_source_inputs'] = '(selection, *, read_source, read_view, evidence_origin) -> extraction; evidence_origin is explicit host-owned reported_source or synthetic_fixture, never a model-selected number or label'
    interface['evidence_origin'] = {'owner': 'actual caller/test harness', 'selection_field': False,
        'allowed': ['reported_source', 'synthetic_fixture'],
        'propagation': 'Synthetic fixture rows use synthetic origin; genuine source-image readings use visual_transcription and genuine prose readings use reported. Derived cells remain derived with exact saved input origin. Native production adapter binds reported_source; controlled fixtures must be explicitly labeled by their trusted harness, not silently passed off as primary work.',
        'not_a_scientific_weight': True}
    interface['supersedes'] = 'INTERFACE_005 plus explicit caller-owned fixture origin; existing v1/pins unchanged'
    with (HERE / 'INTERFACE_006.json').open('x') as stream:
        json.dump(interface, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'final_declaration_generation': '006', 'explicit_fixture_origin': True, 'application_imports': 0}))


if __name__ == '__main__':
    main()
