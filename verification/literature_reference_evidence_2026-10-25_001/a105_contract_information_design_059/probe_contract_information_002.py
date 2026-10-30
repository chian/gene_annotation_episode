"""Additive proof that the actual named-definition TEXT retains each contract.

001 proved graph reconstruction.002 makes scalar/reference types explicit and
parses the rendered tables back to the original contract, including edge text.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from probe_contract_information_001 import NamedDefinitions, OUT, canonical, save
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.scientific_process_prompt import _schema


def literal(value):
    # Scalar JSON spelling disambiguates strings, numbers, booleans and null;
    # this is a table cell, never a serialized schema/context envelope.
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace('|', '\\u007c')


def render(graph, title):
    lines = [title, '', 'Root: ' + graph.root['definition'], '',
        'Definition names are local grammar labels. A reference reuses the entire named structure. '
        'Literal scalar cells use quoted string spelling and explicit null/boolean/number spelling; '
        'escaped newlines and Unicode escapes preserve source text exactly. All constraints are supplied.']
    for row in graph.definitions:
        lines.extend(['', row['name'] + ' — ' + row['kind'], '',
            '| Field or position | Entry kind | Declared value or structure |', '| --- | --- | --- |'])
        if not row['fields']:
            lines.append('| (none) | empty | ' + row['kind'] + ' |')
        for key, value in row['fields']:
            kind = 'reference' if 'definition' in value else 'literal'
            shown = value['definition'] if kind == 'reference' else literal(value['literal'])
            lines.append('| ' + literal(key) + ' | ' + kind + ' | ' + shown + ' |')
    return '\n'.join(lines) + '\n'


def parse_rendered(text):
    root = None
    rows = []
    current = None
    for line in text.splitlines():
        if line.startswith('Root: '):
            root = {'definition': line[len('Root: '):]}
        heading = re.fullmatch(r'(Definition[0-9]+) — (object|array)', line)
        if heading:
            current = {'name': heading[1], 'kind': heading[2], 'fields': []}
            rows.append(current)
        elif line.startswith('| ') and current is not None:
            fields = line[2:-2].split(' | ')
            if len(fields) != 3 or fields[1] in ('Entry kind', '---', 'empty'):
                continue
            key, kind, value = fields
            assert kind in ('reference', 'literal')
            current['fields'].append((json.loads(key), {'definition': value} if kind == 'reference' else {'literal': json.loads(value)}))
    assert root and rows
    graph = NamedDefinitions({})
    graph.root, graph.definitions = root, rows
    return graph.reconstruct()


def main():
    operations = _population_catalog()
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    measurements = []
    for kind, entries in [('operation', {row['name']: row['input_schema'] for row in operations}),
                          ('fact', {name: row['report_schema'] for name, row in facts.items()})]:
        for name, schema in entries.items():
            graph = NamedDefinitions(schema)
            text = render(graph, name + ' complete declared contract')
            assert parse_rendered(text) == schema, name
            measurements.append({'kind': kind, 'name': name, 'text_bytes': len(text.encode()),
                'old_expanded_table_bytes': len(_schema(schema, 'arguments' if kind == 'operation' else 'return').encode()),
                'unique_definitions': len(graph.definitions), 'rendered_text_roundtrip_exact': True})
            if name in ('literature.binding.interaction.populate', 'literature.kinetic.populate',
                        'literature_binding_interaction_cells', 'literature_kinetic_cells'):
                save(name.replace('.', '_') + '_NAMED_CONTRACT_002.txt', text)
    edge = {'description': 'literal Definition1, a|b, quotes " and newline\n; escaped \\n; <br> and μ',
        'const': {'looks_like_schema': {'type': 'string'}}, 'enum': [None, False, 0, 'null', 'false', '0'],
        'items': {}, 'properties': {'same': {}, 'same_again': {}}, 'required': [],
        'arbitrary_extension': ['Definition1', ['two', 2, 2.0, True], ['two', 2, 2.0, True]]}
    edge_text = render(NamedDefinitions(edge), 'Synthetic scalar/type/escaping edge case')
    assert parse_rendered(edge_text) == edge
    # Equality alone can conflate booleans/integers. Canonical spelling is exact.
    assert canonical(parse_rendered(edge_text)) == canonical(edge)
    save('SYNTHETIC_EDGE_TEXT_002.txt', edge_text)
    receipt = {'scope': 'Proposal-only, all actual19 operation and18 fact contracts; no runtime or sources',
        'rendered_text_roundtrip_contracts': len(measurements), 'synthetic_edge_case_roundtrip_exact': True,
        'supersedes_presentation_only': '001 graph roundtrip remains true;002 disambiguates reference/literal scalar spelling in text',
        'all_constraints_descriptions_enums_structure_retained': True, 'measurements': measurements,
        'model_calls': 0, 'completed_actions': 0, 'controller_observations': 0,
        'production_or_test_edits': False}
    save('PROBE_RECEIPT_002.json', receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'measurements'}))


if __name__ == '__main__':
    main()
