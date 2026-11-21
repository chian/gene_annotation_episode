"""The offline check of the model endpoint's schema rules (``provider_schema_rules``) on the shapes the endpoint
refused in recorded runs and on a strict schema it takes."""
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange import strict_output
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

OPTIONS = {'open_records_as_text': False, 'argument_transport_error': 'tool_argument_transport_unsupported'}


def action(child):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'], 'properties': {
        'selection': {'anyOf': [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot'],
                                 'properties': {'kind': {'const': 'episode_child'}, 'slot': {'const': 'reader'},
                                                **child}}]}}}


def test_the_refused_shapes_are_named_with_their_schema_path():
    # the A101 head's first real request (19 November 2026): the selection of a child that declares nothing selectable
    refused = strict_output.strict_output_schema(action({'selection': {'type': 'array', 'maxItems': 0}}), **OPTIONS)
    assert violations(refused) == [('/properties/selection/anyOf/0/properties/selection/anyOf/0',
                                    'array_without_items')]
    embedded = strict_output.strict_output_schema(action({'grading': {'allOf': [{'type': 'string'}]}}), **OPTIONS)
    assert ('/properties/selection/anyOf/0/properties/grading/anyOf/0', 'keyword_not_taken:allOf') in violations(
        embedded)
    valued = strict_output.strict_output_schema(action({'update': {'enum': [{'report': 1}]}}), **OPTIONS)
    assert ('/properties/selection/anyOf/0/properties/update/anyOf/0', 'enum_value_not_scalar') in violations(valued)


def test_an_open_record_is_taken_only_as_text():
    schema = action({'scope': {'type': 'object'}, 'fields': {'type': 'array', 'items': {'enum': ['a', 'b']}}})
    assert violations(strict_output.strict_output_schema(schema, **OPTIONS)) == [
        ('/properties/selection/anyOf/0/properties/scope/anyOf/0', 'object_not_closed')]
    assert violations(strict_output.strict_output_schema(schema, **{**OPTIONS, 'open_records_as_text': True})) == []
