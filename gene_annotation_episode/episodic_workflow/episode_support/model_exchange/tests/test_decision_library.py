"""The model-exchange library: rejection feedback, strict output and context presentation."""
import pytest
from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange import (
    presentation, rejection_feedback, strict_output)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence import (
    action_transport as open_record_transport)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence import (
    action_transport as closed_record_transport)


def test_rejection_feedback_names_the_failed_constraint():
    schema = {'type': 'object', 'required': ['tool'], 'properties': {'tool': {'enum': ['blast', 'hmmer']}}}
    with pytest.raises(ValidationError) as caught:
        Draft202012Validator(schema).validate({'tool': 'psiblast'})
    feedback = rejection_feedback.rejection_feedback(caught.value, category='action_contract')
    assert feedback['status'] == 'invalid' and feedback['category'] == 'action_contract'
    assert feedback['detail']['code'] == 'schema_validation'


ACTION = {'type': 'object', 'additionalProperties': False, 'required': ['selection'], 'properties': {
    'note': {'type': 'string'},
    'payload': {'type': 'object'},
    'selection': {'anyOf': [
        {'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'], 'properties': {
            'kind': {'const': 'tool'}, 'tool': {'const': 'search'},
            'arguments': {'type': 'object', 'anyOf': [{'required': ['query']}, {'required': ['ref']}],
                          'properties': {'query': {'type': 'string'}, 'ref': {'type': 'string'}}}}},
        {'type': 'object', 'additionalProperties': False, 'required': ['kind'],
         'properties': {'kind': {'const': 'reason'}}}]}}}


@pytest.mark.parametrize('open_records, carried', [(False, closed_record_transport), (True, open_record_transport)])
def test_strict_output_matches_the_carried_axis_transports(open_records, carried):
    options = {'open_records_as_text': open_records, 'argument_transport_error': 'tool_argument_transport_unsupported'}
    strict = strict_output.strict_output_schema(ACTION, **options)
    assert strict == carried.generation_schema(ACTION)
    sent = {'note': None, 'payload': '{"a": 1}' if open_records else {'a': 1},
            'selection': {'kind': 'tool', 'tool': 'search', 'arguments': '{"query": "x"}'}}
    decoded = strict_output.decode_strict_output(sent, ACTION, **options)
    assert decoded == carried.decode_response(sent, ACTION)
    assert decoded == {'payload': {'a': 1}, 'selection': {'kind': 'tool', 'tool': 'search',
                                                          'arguments': {'query': 'x'}}}
    Draft202012Validator(ACTION).validate(decoded)


def test_strict_output_refuses_argument_transport():
    schema = {'type': 'object', 'x-argument-transport': {}, 'properties': {
        'kind': {'const': 'tool'}, 'arguments': {'type': 'object'}}}
    with pytest.raises(ValueError, match='^a102_tool_argument_transport_unsupported$'):
        strict_output.strict_output_schema(schema, open_records_as_text=False,
                                           argument_transport_error='a102_tool_argument_transport_unsupported')


def test_extend_context_adds_present_inputs_and_refuses_a_clash():
    context = presentation.extend_context({'goal': 'g'}, {'resource_context': {'cpu': 1}, 'shared': None},
                                          conflict='initial_binding_context_field_conflict')
    assert context == {'goal': 'g', 'resource_context': {'cpu': 1}}
    with pytest.raises(ValueError, match='^initial_binding_context_field_conflict:goal$'):
        presentation.extend_context(context, {'goal': 'other'}, conflict='initial_binding_context_field_conflict')


def test_present_context_uses_the_first_applicable_presentation():
    presentations = (
        (lambda state: 'monitor' in state, lambda state, instructions, lookup_results: 'MONITOR ' + state['monitor'],
         lambda instructions: instructions + ' Read the TASK text.'),
        (lambda state: 'task' in state,
         lambda state, instructions, lookup_results: 'TASK ' + state['task'] + ' ' + str(len(lookup_results)),
         lambda instructions: instructions))
    assert presentation.present_context({'task': 't'}, 'Do.', presentations, lookup_results=[{'r': 1}],
                                        text_field='task_text') == ('Do.', {'task_text': 'TASK t 1'})
    assert presentation.present_context({'monitor': 'm', 'task': 't'}, 'Do.', presentations, lookup_results=(),
                                        text_field='task_text') == ('Do. Read the TASK text.',
                                                                    {'task_text': 'MONITOR m'})
    with pytest.raises(LookupError):
        presentation.present_context({}, 'Do.', presentations, lookup_results=(), text_field='task_text')
