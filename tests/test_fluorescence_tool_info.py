"""Configured capabilities cannot be mixed into an unbound alternative."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.native_fluorescence_contracts import (
    OPERATIONS, fluorescence_environment, requested_job_from_fluorescence,
)
from gene_annotation_episode.native_fluorescence_tool_info import (
    fluorescence_tool_contracts, fluorescence_tool_information,
)
from test_native_fluorescence_contracts import event_input, job


def request(selected, tmp_path):
    return requested_job_from_fluorescence(selected, environment=fluorescence_environment(
        selected['software'], attempt_directory=str(tmp_path / 'attempt')))


def binding(selected, parsers):
    return {**{key: deepcopy(selected[key]) for key in ('operation', 'mode', 'software')},
        'parsers': list(parsers)}


def test_software_and_parser_alternatives_do_not_form_an_unbound_combination(tmp_path):
    first = job(tmp_path / 'first')
    second = job(tmp_path / 'second', inputs=[event_input(tmp_path / 'second', parser='table_snapshot')])
    # These fixtures declare different configured software alternatives. Input
    # directories alone do not change the software returned by job().
    second['software']['python_version'] = 'second declared fixture interpreter'
    rows = [binding(first, ['csv']), binding(second, ['table_snapshot'])]
    before = deepcopy(rows)
    entry, = fluorescence_tool_contracts(rows, resource_kind='local', resource_id='selected-local')
    validator = Draft202012Validator(entry['input_schema'])
    assert validator.is_valid(request(first, tmp_path))
    assert validator.is_valid(request(second, tmp_path))
    mixed = deepcopy(second)
    mixed['software'] = deepcopy(first['software'])
    assert not validator.is_valid(request(mixed, tmp_path))
    both = deepcopy(first)
    both['inputs'].append(deepcopy(second['inputs'][0]))
    # Test the advertised schema directly: two independently configured parsers
    # are not combined into a new installed capability for one software closure.
    body = request(first, tmp_path)
    body['native_fluorescence']['inputs'] = both['inputs']
    assert not validator.is_valid(body)
    assert rows == before
    assert entry['invocation_route']['routes'] == [{
        'entry_role': 'launch', 'resource_id': 'selected-local', 'resource_role': 'launch_local'}]


def test_only_configured_names_are_exposed_and_information_is_detached(tmp_path):
    selected = job(tmp_path)
    rows = [binding(selected, ['csv'])]
    entries = fluorescence_tool_information(rows, resource_kind='local', resource_id='here')
    assert [row['name'] for row in entries] == [OPERATIONS[0]]
    assert set(entries[0]) == {'name', 'description', 'resources', 'instructions'}
    assert entries[0]['description'] and entries[0]['instructions']
    assert entries[0]['resources'] == 'local'
    altered = deepcopy(selected)
    altered['operation'] = OPERATIONS[1]
    schema = fluorescence_tool_contracts(rows, resource_kind='local', resource_id='here')[0]['input_schema']
    assert not Draft202012Validator(schema).is_valid(request(altered, tmp_path))
    entries[0]['instructions'] = 'changed returned copy'
    assert fluorescence_tool_information(rows, resource_kind='local', resource_id='here')[0]['instructions'] != entries[0]['instructions']
    assert fluorescence_tool_contracts([], resource_kind='local', resource_id='here') == []


@pytest.mark.parametrize('kind,resource', [('api', 'here'), ('hpc', 'here'), ('local', ''), ('local', None)])
def test_tool_information_requires_actual_local_resource_identity(kind, resource):
    with pytest.raises(ValueError, match='fluorescence_local_resource_required'):
        fluorescence_tool_contracts([], resource_kind=kind, resource_id=resource)
