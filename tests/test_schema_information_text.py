"""Complete contract text, including actual C7 schemas, without a runtime."""
from copy import deepcopy
from types import MappingProxyType
import json

import pytest

from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.schema_information_text import (
    SchemaInformationError, parse_schema_information, render_schema_information, schema_fingerprint)


OPERATIONS = [(row['name'], row['input_schema']) for row in _population_catalog()]
FACTS = [(name, row['report_schema']) for name, row in LiteratureEpisodes(None, rate_population=True)._rate_fact_sources().items()]


def exact(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


@pytest.mark.parametrize('name,schema', OPERATIONS + FACTS, ids=[name for name, _ in OPERATIONS + FACTS])
def test_every_actual_operation_and_fact_contract_roundtrips_from_rendered_text(name, schema):
    original = deepcopy(schema)
    text = render_schema_information(schema, title=name)
    recovered = parse_schema_information(text)
    assert exact(recovered) == exact(original)
    assert exact(schema) == exact(original)
    assert schema_fingerprint(recovered) == schema_fingerprint(original)
    assert text == render_schema_information(recovered, title=name)
    assert not text.startswith('{')


@pytest.mark.parametrize('value', [None, True, False, 0, 0.0, -0.0, 2, 2.0, 'Definition1', {}, [],
    {'unknown_keyword': {'const': {'type': 'literal', '$ref': 'https://example.invalid/not-resolved'}},
     'enum': [True, 1, 1.0, False, 0, 0.0, None, 'null'], 'array': [{}, [], {}, []]}])
def test_scalar_types_unknown_keywords_literal_schema_data_and_empty_values_are_exact(value):
    text = render_schema_information(value, title='Literal edge')
    assert exact(parse_schema_information(text)) == exact(value)


def test_unicode_line_separators_pipes_escapes_and_titles_cannot_inject_structure():
    text_value = 'μ|"quoted"\nDefinition1 — object\r\t\u0085\u2028\u2029 literal \\u007c; <br>; \ud800'
    schema = {'description': text_value, text_value: 'Definition1', 'nested': [text_value]}
    text = render_schema_information(schema, title=text_value)
    text.encode('utf-8')
    assert exact(parse_schema_information(text)) == exact(schema)
    assert 'μ' in text
    assert '\\u2028' in text and '\\u007c' in text and '\\ud800' in text


def test_identical_substructures_are_named_once_without_conflating_scalars():
    item = {'type': 'array', 'items': {'type': 'string', 'enum': ['same', 'other']}, 'minItems': 1}
    schema = {'properties': {'a': item, 'b': deepcopy(item)}, 'numbers': [True, 1, 1.0]}
    text = render_schema_information(schema, title='Shared definitions')
    assert text.count('| "minItems" | literal | 1 |') == 1
    assert exact(parse_schema_information(text)) == exact(schema)
    assert len({schema_fingerprint(value) for value in (True, 1, 1.0, '1', None, 'null', 0.0, -0.0)}) == 8


def test_immutable_host_mappings_and_tuples_normalize_to_detached_json_equivalents():
    value = MappingProxyType({'type': 'string', 'enum': ('one', 'two'), 'nullable': None})
    recovered = parse_schema_information(render_schema_information(value, title='Frozen host contract'))
    assert recovered == {'type': 'string', 'enum': ['one', 'two'], 'nullable': None}
    recovered['enum'].append('three')
    assert value['enum'] == ('one', 'two')


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan'), {1: 'nonstring key'}, object(), {1, 2}])
def test_non_json_or_nonfinite_values_are_rejected(value):
    with pytest.raises(SchemaInformationError):
        render_schema_information(value, title='Invalid')
    with pytest.raises(SchemaInformationError):
        schema_fingerprint(value)


def test_cycles_are_rejected_while_shared_acyclic_objects_are_allowed():
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(SchemaInformationError, match='cyclic_json_value'):
        render_schema_information(cyclic, title='Invalid cycle')
    common = {'type': 'string'}
    assert parse_schema_information(render_schema_information([common, common], title='Shared')) == [common, common]


@pytest.mark.parametrize('title', ['', None, 1, False])
def test_title_must_be_explicit_nonempty_text(title):
    with pytest.raises(SchemaInformationError):
        render_schema_information({}, title=title)


def test_unknown_reference_and_cycles_in_information_text_are_rejected():
    text = render_schema_information({'item': {'type': 'number'}}, title='Links')
    with pytest.raises(SchemaInformationError):
        parse_schema_information(text.replace('Root: reference Definition1', 'Root: reference Definition999'))
    with pytest.raises(SchemaInformationError):
        parse_schema_information(text.replace('| "item" | reference | Definition2 |', '| "item" | reference | Definition1 |'))


@pytest.mark.parametrize('change', [
    lambda text: text.removesuffix('\n'),
    lambda text: text.replace('End schema information', ''),
    lambda text: text + 'unrecorded text\n',
    lambda text: text.replace('Definition1 — object', 'Definition01 — object'),
    lambda text: text.replace('| "type" | literal | "string" |', '| "type" | literal | "string" |\n| "type" | literal | "string" |'),
    lambda text: text.replace('| "type" | literal | "string" |', '| "type" | literal | {"invented":"object"} |'),
    lambda text: text.replace('| "type" | literal | "string" |', '| "type" | literal | NaN |'),
    lambda text: text.replace('| "type" | literal | "string" |', '| "type" | literal | "str\\u0069ng" |'),
])
def test_malformed_duplicate_noncanonical_and_trailing_information_is_rejected(change):
    text = render_schema_information({'type': 'string'}, title='Strict document')
    assert change(text) != text
    with pytest.raises(SchemaInformationError):
        parse_schema_information(change(text))


def test_unreachable_and_duplicate_definition_blocks_are_rejected():
    text = render_schema_information({'type': 'string'}, title='Strict definitions')
    block = '\nDefinition2 — object\n\n| Field or position | Entry kind | Declared value or structure |\n| --- | --- | --- |\n| (none) | empty | object |\n'
    with pytest.raises(SchemaInformationError):
        parse_schema_information(text.replace('\nEnd schema information', block + '\nEnd schema information'))
    with pytest.raises(SchemaInformationError):
        parse_schema_information(text.replace('\nEnd schema information', block.replace('Definition2', 'Definition1') + '\nEnd schema information'))


@pytest.mark.parametrize('position', ['true', '1', '0.0', '"0"'])
def test_array_positions_are_exact_contiguous_integers(position):
    text = render_schema_information(['item'], title='Array positions')
    with pytest.raises(SchemaInformationError):
        parse_schema_information(text.replace('| 0 | literal', '| ' + position + ' | literal'))


def test_literal_definition_name_never_becomes_a_reference():
    value = {'field': 'Definition1', 'other': {'field': 'Definition1'}}
    text = render_schema_information(value, title='Literal versus reference')
    assert '| "field" | literal | "Definition1" |' in text
    assert parse_schema_information(text) == value
