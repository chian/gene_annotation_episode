"""Advertise the existing native return custody requirement before selection."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.component_axis_native_hpc import FACT_SOURCE, EXECUTION_SOURCE
from gene_annotation_episode.component_axis_reports import validate_native_return_channels
from gene_annotation_episode.component_axis_workflow import INSTRUCTIONS, task_context, TASKS
from gene_annotation_episode.domain import ContractError


FIXTURE = Path(__file__).parent / 'fixtures/communication/a11039-native-return-contract.json'
NATIVE_OPERATIONS = (
    ('A107', 'partner.request_expression_hpc'), ('A107', 'partner.request_detection_hpc'),
    ('A110', 'chemistry.request_accounting_hpc'), ('A110', 'chemistry.request_flux_balance_hpc'),
)


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_axis_instructions_expose_the_existing_required_pair_before_rejection(axis):
    required = 'must include both ' + FACT_SOURCE + ' and ' + EXECUTION_SOURCE
    assert required in INSTRUCTIONS[axis]
    assert 'child_tool_info' in INSTRUCTIONS[axis]
    assert 'episode.return_contract' in INSTRUCTIONS[axis]
    assert 'empty component arrays' in INSTRUCTIONS[axis]
    assert required in task_context(axis, TASKS[axis][0])['scientific_question']


@pytest.mark.parametrize('axis,operation', NATIVE_OPERATIONS)
def test_advertised_operations_match_existing_native_custody_condition(axis, operation):
    assert operation in INSTRUCTIONS[axis]
    selection = {'evidence_axis': {'option_id': axis},
        'child_tool_info': [{'name': operation, 'resources': 'local'}]}
    with pytest.raises(ContractError, match='component_native_return_channels_required'):
        validate_native_return_channels(selection, {'properties': {}})
    schema = {'properties': {'chosen_components': {'x-source': FACT_SOURCE},
        'chosen_execution': {'x-source': EXECUTION_SOURCE}}}
    validate_native_return_channels(selection, schema)


def test_original_rejected_contract_and_actual_admitted_repair_keep_their_meanings():
    trace = json.loads(FIXTURE.read_text())
    original = trace['rejected_selection']
    assignment = json.loads(original['assignment'])
    selection = assignment['selection']
    rejected_form = json.loads(original['schema_json'])
    native_types = {field['x-source']: field for field in trace['admitted_return_form']['properties'].values()
        if field.get('x-source') in {FACT_SOURCE, EXECUTION_SOURCE}}
    for name, field in list(rejected_form['properties'].items()):
        reference = field.get('$ref', '')
        if reference.startswith('episode-fact:') and reference[13:] in native_types:
            rejected_form['properties'][name] = deepcopy(native_types[reference[13:]])
    with pytest.raises(ContractError) as failure:
        validate_native_return_channels(selection, rejected_form)
    assert str(failure.value) == trace['feedback']['detail']
    assert failure.value.detail['missing_fact_sources'] == trace['feedback']['required_fact_sources']
    validate_native_return_channels(selection, trace['admitted_return_form'])


def test_source_only_child_has_no_native_channel_requirement():
    selection = {'evidence_axis': {'option_id': 'A110'},
        'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
    validate_native_return_channels(selection, {'properties': {}})
