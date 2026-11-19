"""Filling a parent's JSON-Schema report form from interpretations and recorded facts."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.report_form_values import (
    form_with_facts, interpretation_schema, reference_resolver)

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['verdict', 'hits', 'credit'],
          'properties': {'verdict': {'type': 'string', 'enum': ['supported', 'unresolved']},
                         'hits': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                                  'x-source': 'committed_record_refs'},
                         'credit': {'type': 'number', 'x-source': 'credit'}}}


def test_interpretation_schema_keeps_only_model_written_properties():
    assert interpretation_schema(SCHEMA) == {
        'type': 'object', 'additionalProperties': False, 'required': ['verdict'],
        'properties': {'verdict': {'type': 'string', 'enum': ['supported', 'unresolved']}}}


def test_form_with_facts_copies_recorded_facts_into_their_fields():
    facts = {'committed_record_refs': ['feature:1'], 'credit': 2.5, 'unused': 1}
    assert form_with_facts({'verdict': 'supported'}, SCHEMA, facts) == {
        'verdict': 'supported', 'hits': ['feature:1'], 'credit': 2.5}


@pytest.mark.parametrize('interpretations, facts, code', [
    ({'verdict': 'supported', 'credit': 9}, {'committed_record_refs': [], 'credit': 1}, 'fill_exactly:verdict'),
    ({}, {'committed_record_refs': [], 'credit': 1}, 'fill_exactly:verdict'),
    ({'verdict': 'supported'}, {'credit': 1}, 'fact_source_unavailable:hits:committed_record_refs'),
])
def test_form_with_facts_errors_are_explicit(interpretations, facts, code):
    with pytest.raises(ValueError, match=code):
        form_with_facts(interpretations, SCHEMA, facts)


def test_reference_resolver_checks_namespace_membership():
    resolve = reference_resolver({'feature': ['feature:1'], 'artifact': ['artifact:2']})
    assert resolve('feature:1', 'feature') and not resolve('feature:1', 'artifact')
    assert resolve('artifact:2') and not resolve('product:3') and not resolve('feature:1', 'product')
