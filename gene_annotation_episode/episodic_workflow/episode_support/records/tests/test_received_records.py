"""Record handles and scope visibility among the held records, run in tool units through the real runner; outcome
paging over a list of unit outcomes."""
from __future__ import annotations

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page

from .library_world import bare_world, run, tool  # noqa: F401 - ``bare_world`` is the fixture

FORMATS = ['reference', 'identifier', 'accession']


@pytest.fixture
def two_subjects(bare_world, tmp_path):
    world = bare_world
    store = world['store']
    fasta = tmp_path / 'two.fna'
    fasta.write_text('>first\nATGAAACCCGGGTTTAAATAG\n>second\nATGCCCAAAGGGTTTCCCTAA\n')
    first, second = store.create_problem(fasta, molecule='dna')['subject_refs']

    def feature(subject):
        return store.put('feature', {'subject_ref': subject, 'kind': 'sequence_region',
                                     'segments': [{'start': 0, 'end': 9}], 'strand': '+', 'context_refs': []},
                         origin='caller')['id']
    return world, first, second, feature(first), feature(second)


def test_references_in_keeps_only_held_handles_visible_under_scope(two_subjects):
    world, first, second, inside, outside = two_subjects
    value = {'working_state': {'last_ref': inside, 'other_refs': [outside, 'not_a_record', inside],
                               'note': 'feature text ' + inside},
             'records': [{'id': first, 'record_type': 'input'}]}
    _, units = run(world, 'handles', [
        tool('references_in', value=value, scope={'subject_refs': [first]}, formats=FORMATS),
        tool('references_in', value=value, scope={'subject_refs': [first, second]}, formats=FORMATS)],
        subjects=[first, second], held=[inside, outside])
    assert units[0]['outcome']['references'] == [first, inside]
    assert units[1]['outcome']['references'] == [first, inside, outside]     # plan arguments are journaled with sorted keys


def test_references_in_reads_typed_form_fields_by_their_schema_format(two_subjects):
    world, first, _, region, _ = two_subjects
    form = {'chosen': region, 'label': region, 'many': [first]}
    schema = {'type': 'object', 'properties': {
        'chosen': {'type': 'string', 'format': 'reference'}, 'label': {'type': 'string'},
        'many': {'type': 'array', 'items': {'type': 'string', 'format': 'identifier'}}}}
    scope = {'subject_refs': [first]}
    _, units = run(world, 'forms', [
        tool('references_in', value={}, scope=scope, formats=FORMATS, forms=[{'payload': form, 'schema': schema}]),
        tool('references_in', value={}, scope=scope, formats=['accession'],
             forms=[{'payload': form, 'schema': schema}])], subjects=[first], held=[region])
    assert units[0]['outcome']['references'] == [region, first]
    assert units[1]['outcome']['references'] == []


def test_projection_with_a_different_record_type_is_not_a_handle(two_subjects):
    world, first, _, region, _ = two_subjects
    value = {'item': {'id': region, 'record_type': 'assessment'}}
    _, units = run(world, 'projection', [tool('references_in', value=value, scope={'subject_refs': [first]},
                                              formats=FORMATS)], subjects=[first], held=[region])
    assert units[0]['outcome']['references'] == []


def test_reference_in_scope_checks_held_visibility_and_namespace(two_subjects):
    world, first, second, region, _ = two_subjects
    scope = {'subject_refs': [first]}
    _, units = run(world, 'visibility', [
        tool('scope_checks', scope=scope, asks=[[region, None], [region, 'feature'], [region, 'subject'],
                                                [region, 'source'], [second, None], ['missing', None]]),
        tool('read_in_scope', scope=scope, ref=region, namespace='feature'),
        tool('read_in_scope', scope=scope, ref=second)], subjects=[first, second], held=[region])
    assert units[0]['outcome']['visible'] == [True, True, True, False, False, False]
    assert units[1]['outcome'] == {'id': region}
    assert units[2]['outcome'] == {'refused': 'reference_not_in_scope'}


def test_outcome_page_shape_and_tool_filter():
    rows = [{'tool': 'a', 'n': 0}, {'tool': 'b', 'n': 1}, {'tool': 'a', 'n': 2}]
    first = outcome_page(rows, offset=0, limit=2)
    assert [row['n'] for row in first['records']] == [0, 1] and first['next_offset'] == 2 and first['total'] == 3
    assert outcome_page(rows, offset=2, limit=2)['next_offset'] is None
    only = outcome_page(rows, offset=0, limit=5, tools={'a'}, tool_of=lambda row: row['tool'])
    assert [row['n'] for row in only['records']] == [0, 2] and only['total'] == 2
    with pytest.raises(ContractError, match='outcome_page_tool_filter_requires_tool_of'):
        outcome_page(rows, offset=0, limit=1, tools={'a'})
    with pytest.raises(ContractError, match='invalid_page'):
        outcome_page(rows, offset=0, limit=0)
