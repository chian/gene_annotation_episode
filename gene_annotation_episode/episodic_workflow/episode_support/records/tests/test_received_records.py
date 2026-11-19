"""Store reference and scope functions, and outcome paging, over a real Store."""
from __future__ import annotations

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.own_outcomes import outcome_page
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import (
    read_record_in_scope, record_selection, reference_in_scope, references_in)
from gene_annotation_episode.state import Store

FORMATS = ('reference', 'identifier', 'accession')


@pytest.fixture
def two_subjects(tmp_path):
    fasta = tmp_path / 'two.fna'
    fasta.write_text('>first\nATGAAACCCGGGTTTAAATAG\n>second\nATGCCCAAAGGGTTTCCCTAA\n')
    with Store(tmp_path / 'state') as store:
        first, second = store.create_problem(fasta, molecule='dna')['subject_refs']
        yield store, first, second


def feature(store, subject):
    return store.put('feature', {'subject_ref': subject, 'kind': 'sequence_region',
                                 'segments': [{'start': 0, 'end': 9}], 'strand': '+', 'context_refs': []},
                     origin='caller')['id']


def test_references_in_keeps_only_existing_handles_visible_under_scope(two_subjects):
    store, first, second = two_subjects
    inside, outside = feature(store, first), feature(store, second)
    scope = {'subject_refs': [first]}
    value = {'working_state': {'last_ref': inside, 'other_refs': [outside, 'not_a_record', inside],
                               'note': 'feature text ' + inside},
             'records': [{'id': first, 'record_type': 'input'}]}
    assert references_in(value, store, scope, reference_formats=FORMATS) == [inside, first]
    both = {'subject_refs': [first, second]}
    assert references_in(value, store, both, reference_formats=FORMATS) == [inside, outside, first]


def test_references_in_reads_typed_form_fields_by_their_schema_format(two_subjects):
    store, first, _ = two_subjects
    region = feature(store, first)
    form = {'chosen': region, 'label': region, 'many': [first]}
    schema = {'type': 'object', 'properties': {
        'chosen': {'type': 'string', 'format': 'reference'}, 'label': {'type': 'string'},
        'many': {'type': 'array', 'items': {'type': 'string', 'format': 'identifier'}}}}
    scope = {'subject_refs': [first]}
    assert references_in({}, store, scope, reference_formats=FORMATS, forms=[(form, schema)]) == [region, first]
    assert references_in({}, store, scope, reference_formats=('accession',), forms=[(form, schema)]) == []


def test_projection_with_a_different_record_type_is_not_a_handle(two_subjects):
    store, first, _ = two_subjects
    region = feature(store, first)
    value = {'item': {'id': region, 'record_type': 'assessment'}}
    assert references_in(value, store, {'subject_refs': [first]}, reference_formats=FORMATS) == []


def test_reference_in_scope_checks_visibility_and_namespace(two_subjects):
    store, first, second = two_subjects
    region = feature(store, first)
    scope = {'subject_refs': [first]}
    assert reference_in_scope(store, region, scope)
    assert reference_in_scope(store, region, scope, 'feature')
    assert reference_in_scope(store, region, scope, 'subject')
    assert not reference_in_scope(store, region, scope, 'source')
    assert not reference_in_scope(store, second, scope)
    assert not reference_in_scope(store, 'missing', scope)
    assert read_record_in_scope(store, region, scope, 'feature')['id'] == region
    with pytest.raises(ContractError, match='reference_not_in_scope'):
        read_record_in_scope(store, second, scope)


def test_record_selection_pages_only_held_records(two_subjects):
    store, first, _ = two_subjects
    held, other = feature(store, first), feature(store, first)
    scope = {'subject_refs': [first]}
    assert {row['id'] for row in store.query_records('feature', scope)['records']} == {held, other}
    page = store.query_records('feature', scope, record_selection=record_selection([held]))
    assert [row['id'] for row in page['records']] == [held] and page['total'] == 1


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
