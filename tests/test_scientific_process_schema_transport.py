"""Keep caller tool contracts intact across the model's JSON transport.

These use real frozen options, scientific children, action schemas and dispatch.
The provider is a fixture; no model or external scientific service is invoked.
"""
import asyncio
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.runtime import (
    _action_generation_schema, _decode_action_response,
)
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.scientific_process_records import selector_selection
from gene_annotation_episode.state import Store
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import Scenario, prepared_child


class ContractTools:
    def __init__(self, schema):
        self.schema, self.calls = deepcopy(schema), []

    def catalog(self, scope=None):
        return [{'name': 'fixture.inspect', 'resources': 'local',
            'description': 'Validate and return synthetic fixture values under the supplied contract.',
            'input_schema': deepcopy(self.schema)}]

    def execute(self, name, arguments, *, scope, operation_key):
        assert name == 'fixture.inspect'
        self.calls.append(deepcopy(arguments))
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'result': deepcopy(arguments)}


def configured_child(tmp_path, store, actual, restriction):
    from schema_fixture_helpers import _rebase
    contract = (deepcopy(actual) if restriction is None else {"allOf": [
        _rebase(actual, ("allOf", 0)), _rebase(restriction, ("allOf", 1))]})
    case = Scenario(tmp_path, store, tools=ContractTools(contract))
    workflow = case.workflow(ScriptedProvider([]))
    root, child = prepared_child(case, workflow)
    return case, workflow, root, child


def tool_branch(schema):
    return next(branch for branch in schema['properties']['selection']['anyOf']
        if branch.get('properties', {}).get('tool', {}).get('const',
            branch.get('properties', {}).get('tool', {}).get('enum', [None])[0])
        == 'fixture.inspect')


def response(arguments, *, encoded=True):
    return {'selection': {'kind': 'tool', 'tool': 'fixture.inspect',
        'arguments': json.dumps(arguments) if encoded else deepcopy(arguments)},
        'report_update': {'status': 'unresolved'}}


def dispatch(child, workflow, proposal, schema, index=0):
    unit = child.source.apply_response(proposal, index, {'visible_record_refs': []}, schema)
    if unit is not None:
        decoded = _decode_action_response(proposal, schema)
        asyncio.run(child.source.execute(decoded['selection'], index))
    return unit


@pytest.mark.parametrize('actual_reference', ['#/$defs/shared', '#shared'])
def test_local_definitions_and_anchors_survive_standalone_host_and_generated_transport(
        tmp_path, actual_reference):
    actual = {'type': 'object', 'properties': {'value': {'$ref': actual_reference}},
        'required': ['value'], 'additionalProperties': False,
        '$defs': {'shared': {'$anchor': 'shared', 'type': 'integer', 'minimum': 0, 'maximum': 10}}}
    restriction = {'properties': {'value': {'$ref': '#shared'}},
        '$defs': {'shared': {'$anchor': 'shared', 'enum': [2, 5]}}}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual, restriction)
        entry = next(row for row in workflow.catalog(child.source.scope, source=child.source)
            if row['name'] == 'fixture.inspect')
        standalone = Draft202012Validator(entry['input_schema'])
        host = workflow.action_schema(child.source)
        generated = _action_generation_schema(host)
        Draft202012Validator.check_schema(host)
        Draft202012Validator.check_schema(generated)
        assert tool_branch(generated)['properties']['arguments']['type'] == 'string'
        for value in (2, 5):
            proposal = response({'value': value})
            assert standalone.is_valid({'value': value})
            assert Draft202012Validator(generated).is_valid(proposal)
            decoded = _decode_action_response(proposal, host)
            assert Draft202012Validator(host).is_valid(decoded)
        for value in (3, '2', -1, 12):
            assert not standalone.is_valid({'value': value})
            decoded = _decode_action_response(response({'value': value}), host)
            assert not Draft202012Validator(host).is_valid(decoded)
        assert dispatch(child, workflow, response({'value': 5}), host) is not None
        assert case.tools.calls == [{'value': 5}]
        assert actual['$defs']['shared']['$anchor'] == 'shared'
        assert restriction['$defs']['shared']['$anchor'] == 'shared'


@pytest.mark.parametrize('arguments', [
    {'value': 2}, {'value': 2, 'optional': None}, {'value': 2, 'optional': 3},
])
def test_composed_transport_preserves_omission_and_explicit_nullable_values(tmp_path, arguments):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'},
        'optional': {'type': ['integer', 'null']}}, 'required': ['value'],
        'additionalProperties': False}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual,
            {'properties': {'value': {'maximum': 3}}})
        schema = workflow.action_schema(child.source)
        proposal = response(arguments)
        assert Draft202012Validator(_action_generation_schema(schema)).is_valid(proposal)
        assert _decode_action_response(proposal, schema)['selection']['arguments'] == arguments
        assert dispatch(child, workflow, proposal, schema) is not None
        assert case.tools.calls == [arguments]


def test_restriction_can_require_an_optional_actual_field_without_null_substitution(tmp_path):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'},
        'optional': {'type': ['integer', 'null']}}, 'required': ['value'],
        'additionalProperties': False}
    restriction = {'required': ['optional'], 'properties': {'optional': {'const': None}}}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual, restriction)
        schema = workflow.action_schema(child.source)
        assert dispatch(child, workflow, response({'value': 2}), schema) is None
        assert child.source.feedback['category'] == 'action_contract'
        assert case.tools.calls == []
        assert dispatch(child, workflow, response({'value': 2, 'optional': None}), schema, 1) is not None
        assert case.tools.calls == [{'value': 2, 'optional': None}]


@pytest.mark.parametrize('arguments, valid', [
    ({'value': 2, 'mode': 'single'}, True),
    ({'value': 2, 'mode': 'single', 'note': 'extra'}, False),
    ({'value': 2, 'mode': 'with_note'}, False),
    ({'value': 2, 'mode': 'with_note', 'note': 'required'}, True),
])
def test_conditional_presence_and_max_properties_are_host_constraints(tmp_path, arguments, valid):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'},
        'mode': {'enum': ['single', 'with_note']}, 'note': {'type': 'string'}},
        'required': ['value', 'mode'], 'additionalProperties': False}
    restriction = {'if': {'properties': {'mode': {'const': 'with_note'}}},
        'then': {'required': ['note']}, 'else': {'maxProperties': 2}}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual, restriction)
        schema = workflow.action_schema(child.source)
        proposal = response(arguments)
        assert Draft202012Validator(_action_generation_schema(schema)).is_valid(proposal)
        decoded = _decode_action_response(proposal, schema)
        assert Draft202012Validator(schema).is_valid(decoded) is valid
        assert (dispatch(child, workflow, proposal, schema) is not None) is valid
        assert case.tools.calls == ([arguments] if valid else [])


@pytest.mark.parametrize('restricted', [False, True])
def test_schema_shaped_literals_remain_data_in_composition_and_json_transport(tmp_path, restricted):
    literal = {'$ref': 'literal-not-a-schema-reference', '$anchor': 'literal',
        'type': 'object', 'properties': {'value': {'const': 'data'}}, 'required': ['data']}
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'},
        'literal': {'const': literal}}, 'required': ['value', 'literal'],
        'additionalProperties': False}
    restriction = {'properties': {'literal': {'const': literal}}} if restricted else None
    arguments = {'value': 2, 'literal': literal}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual, restriction)
        schema = workflow.action_schema(child.source)
        generated = _action_generation_schema(schema)
        encoded = tool_branch(generated)['properties']['arguments'].get('type') == 'string'
        proposal = response(arguments, encoded=encoded)
        assert Draft202012Validator(generated).is_valid(proposal)
        assert dispatch(child, workflow, proposal, schema) is not None
        assert case.tools.calls == [arguments]
        assert case.tools.calls[0]['literal'] == literal


def test_boolean_property_schema_is_data_contract_not_an_action_discriminator(tmp_path):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'}, 'kind': True},
        'required': ['value', 'kind'], 'additionalProperties': False}
    arguments = {'value': 2, 'kind': {'arbitrary': ['finite', None]}}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual, None)
        schema = workflow.action_schema(child.source)
        generated = _action_generation_schema(schema)
        proposal = response(arguments, encoded=False)
        assert Draft202012Validator(generated).is_valid(proposal)
        assert dispatch(child, workflow, proposal, schema) is not None
        assert case.tools.calls == [arguments]


@pytest.mark.parametrize('encoded', ['{', '[]', 'null', '{"value":2,"value":3}',
    '{"value":NaN}', '{"value":1e10000}'])
def test_invalid_json_argument_transport_returns_action_feedback_before_dispatch(tmp_path, encoded):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'}},
        'required': ['value'], 'additionalProperties': False}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual,
            {'properties': {'value': {'maximum': 3}}})
        schema = workflow.action_schema(child.source)
        proposal = response({'value': 2})
        proposal['selection']['arguments'] = encoded
        assert Draft202012Validator(_action_generation_schema(schema)).is_valid(proposal)
        assert dispatch(child, workflow, proposal, schema) is None
        assert child.source.feedback['status'] == 'invalid'
        assert child.source.feedback['category'] == 'action_contract'
        assert case.tools.calls == []
        assert store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?',
            (child.source.episode_id,)).fetchone()[0] == 0


def test_recorded_response_reuses_its_original_host_contract_without_provider_dispatch(tmp_path):
    actual = {'type': 'object', 'properties': {'value': {'type': 'integer'}},
        'required': ['value'], 'additionalProperties': False}
    with Store(tmp_path/'state') as store:
        case, workflow, _, child = configured_child(tmp_path, store, actual,
            {'properties': {'value': {'maximum': 5}}})
        original = workflow.action_schema(child.source)
        proposed = response({'value': 5})
        context = {'visible_record_refs': [], 'selected_contract': 'original'}
        saved = {'context': context, 'schema': original}
        workflow.journal.save('runtime_model_calls', {'episode_id': child.source.episode_id,
            'call_index': 0, 'purpose': 'decision', 'request': json.dumps(saved),
            'response': json.dumps(proposed)})
        changed = deepcopy(original)
        tool_branch(changed)['properties']['arguments'] = {'type': 'object',
            'properties': {'value': {'const': 2}}, 'required': ['value'],
            'additionalProperties': False}
        returned, index, actual_context, contract = asyncio.run(child.source.call(
            {'visible_record_refs': [], 'selected_contract': 'changed'}, changed))
        assert (returned, index, actual_context, contract) == (proposed, 0, context, original)
        decoded = _decode_action_response(returned, contract)
        assert Draft202012Validator(contract).is_valid(decoded)
        assert not Draft202012Validator(changed).is_valid(decoded)
        assert workflow.provider.contexts == []
        assert case.tools.calls == []
        row = workflow.journal.row('runtime_model_calls', child.source.episode_id, 0)
        assert json.loads(row['request']) == saved
        assert json.loads(row['response']) == proposed


def test_scientific_assignment_json_transport_preserves_arbitrary_finite_context(tmp_path):
    with Store(tmp_path/'state') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(ScriptedProvider([]))
        root = workflow.build('annotation', 'root', 'Resolve fixture uncertainty', case.scope)
        host = workflow.action_schema(root.source)
        generated = _action_generation_schema(host)
        proposed = case.commission()
        context = {'optional': None, 'nested': [True, 3.25, {'α': ['a', None]}],
            '$ref': 'literal-reference', 'properties': {'type': 'data'}, 'required': ['literal']}
        proposed['selection']['assignment']['context'] = context
        proposed['selection']['assignment']['constraints'] = {'enabled': False, 'count': 0}
        original = deepcopy(proposed['selection']['assignment'])
        proposed['selection']['assignment'] = json.dumps(original)
        # Ordinary optional fields still use the provider's explicit-null
        # representation. The assignment's arbitrary JSON is inside its string.
        proposed['selection']['scope'] = {**case.scope, 'read_selection_refs': None, 'segments': None}
        assert Draft202012Validator(generated).is_valid(proposed)
        decoded = _decode_action_response(proposed, host)
        assert decoded['selection']['assignment'] == original
        assert decoded['selection']['scope'] == case.scope
        assert Draft202012Validator(host).is_valid(decoded)
        unit = root.source.apply_response(proposed, 0, {'visible_record_refs': []}, host)
        assert unit is not None
        filled = unit.child.request.message.as_record()['episode_assignment']
        assert filled == {**original, 'selection': case.filled_selection()}
        assert selector_selection(filled['selection']) == original['selection']
        assert unit.child.request.message.as_record()['episode_assignment']['context'] == context
        assert case.tools.calls == []
