"""Closed records and form references."""
import pytest

from method_loop import ClosedRecord

from gene_annotation_episode.episodic_workflow.episode_support.records.closed_json import closed_record
from gene_annotation_episode.episodic_workflow.episode_support.records.received_references import form_references


def test_closed_record_is_closed_json_with_audit_identifiers():
    record = closed_record({'b': [1, 2.5], 'a': 'x'}, audit_identifiers=('episode_1',))
    assert isinstance(record, ClosedRecord)
    assert record.as_record() == {'a': 'x', 'b': [1, 2.5]}
    assert record.audit_identifiers() == ('episode_1',)
    with pytest.raises(ValueError, match='closed_json'):
        closed_record({'x': float('nan')})


def test_form_references_follow_the_schema_branches_and_local_refs():
    schema = {'$defs': {'ref': {'type': 'string', 'format': 'reference'}},
              'type': 'object', 'properties': {
                  'hits': {'type': 'array', 'items': {'$ref': '#/$defs/ref'}},
                  'best': {'anyOf': [{'type': 'null'}, {'$ref': '#/$defs/ref'}]},
                  'label': {'type': 'string'},
                  'pair': {'type': 'array', 'prefixItems': [{'type': 'string'}, {'type': 'string', 'format': 'reference'}]}}}
    value = {'hits': ['feature:1', 'feature:2', 'feature:1'], 'best': 'feature:3', 'label': 'feature:9',
             'pair': ['note', 'product:4']}
    assert form_references(value, schema) == ['feature:1', 'feature:2', 'feature:3', 'product:4']
    assert form_references({'best': None}, schema) == []
