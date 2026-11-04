"""Repeated construction must retain full validation without repeated checks."""
from copy import deepcopy

from jsonschema import Draft202012Validator, SchemaError, ValidationError
import pytest

from gene_annotation_episode import tool_schema_validation as validation
from gene_annotation_episode.resource_tool_information import _contract
from gene_annotation_episode.scientific_tool_library import _catalog, _profiles


@pytest.fixture
def checked(monkeypatch):
    validation._check_serialized_schema.cache_clear()
    original = Draft202012Validator.check_schema
    calls = []

    def check(schema):
        calls.append(deepcopy(schema))
        return original(schema)

    monkeypatch.setattr(Draft202012Validator, 'check_schema', check)
    yield calls
    validation._check_serialized_schema.cache_clear()


def entry():
    return {'name': 'fixture.alignment', 'description': 'Fixture operation',
            'resources': 'api', 'instructions': 'Fixture instruction',
            'input_schema': {'type': 'object', 'properties': {
                'sequence': {'type': 'string', 'minLength': 1}},
                'required': ['sequence'], 'additionalProperties': False}}


def test_identical_schemas_share_one_check_across_real_consumers(checked):
    supplied = entry()
    for _ in range(3):
        assert _catalog([deepcopy(supplied)])[supplied['name']] == supplied
        assert _profiles([deepcopy(supplied)])[supplied['name'], 'api'] == supplied
        assert _contract(deepcopy(supplied)) == supplied
    assert checked == [supplied['input_schema']]


@pytest.mark.parametrize('consumer', [lambda row: _catalog([row]),
                                      lambda row: _profiles([row]), _contract])
def test_nested_mutation_is_rechecked_and_invalid_schema_remains_invalid(checked, consumer):
    supplied = entry()
    consumer(supplied)
    supplied['input_schema']['properties']['sequence']['minLength'] = 4
    consumer(supplied)
    supplied['input_schema']['properties']['sequence']['minLength'] = -1
    for _ in range(2):
        with pytest.raises(SchemaError):
            consumer(supplied)
    assert len(checked) == 4
    assert validation._check_serialized_schema.cache_info().currsize == 2


def test_cached_schema_does_not_cache_or_skip_argument_validation(checked):
    schema = entry()['input_schema']
    validation.check_tool_schema(schema)
    validation.check_tool_schema(deepcopy(schema))
    validator = Draft202012Validator(schema)
    validator.validate({'sequence': 'ACGT'})
    for invalid in ({'sequence': ''}, {}, {'sequence': 12}, {'sequence': 'A', 'extra': 1}):
        with pytest.raises(ValidationError):
            validator.validate(invalid)
    assert len(checked) == 1


def test_resource_and_instruction_checks_still_run_on_cache_hit(checked):
    supplied = entry()
    _profiles([supplied])
    with pytest.raises(ValueError, match='scientific_tool_resource_conflict'):
        _profiles([supplied], 'hpc')
    supplied['instructions'] = ''
    with pytest.raises(ValueError, match='scientific_tool_instructions_required'):
        _profiles([supplied])
    assert len(checked) == 1
