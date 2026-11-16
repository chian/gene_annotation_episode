"""Advertise the existing native return custody requirement before selection."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a107 import component_axis_native_hpc as native_a107
from gene_annotation_episode.episodic_workflow.root.a110 import component_axis_native_hpc as native_a110
from gene_annotation_episode.episodic_workflow.root.a107 import component_axis_reports as reports_a107
from gene_annotation_episode.episodic_workflow.root.a110 import component_axis_reports as reports_a110
from gene_annotation_episode.episodic_workflow.root.a107 import component_axis_workflow as workflow_a107
from gene_annotation_episode.episodic_workflow.root.a110 import component_axis_workflow as workflow_a110
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError as ContractErrorA107
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError as ContractErrorA110

ContractError = (ContractErrorA107, ContractErrorA110)


FIXTURE = Path(__file__).resolve().parents[1] / 'gene_annotation_episode/episodic_workflow/root/a110/tests/fixtures/communication/a11039-native-return-contract.json'
NATIVE_OPERATIONS = (
    ('A107', 'partner.request_expression_hpc'), ('A107', 'partner.request_detection_hpc'),
    ('A110', 'chemistry.request_accounting_hpc'), ('A110', 'chemistry.request_flux_balance_hpc'),
)
FACT_SOURCE = native_a107.FACT_SOURCE
EXECUTION_SOURCE = native_a107.EXECUTION_SOURCE
WORKFLOWS = {'A107': workflow_a107, 'A110': workflow_a110}
REPORTS = {'A107': reports_a107, 'A110': reports_a110}
assert (FACT_SOURCE, EXECUTION_SOURCE) == (native_a110.FACT_SOURCE, native_a110.EXECUTION_SOURCE)




@pytest.mark.parametrize('axis,operation', NATIVE_OPERATIONS)
def test_advertised_operations_match_existing_native_custody_condition(axis, operation):
    assert operation in WORKFLOWS[axis].INSTRUCTIONS[axis]
    selection = {'evidence_axis': {'option_id': axis},
        'child_tool_info': [{'name': operation, 'resources': 'local'}]}
    with pytest.raises(ContractError, match='component_native_return_channels_required'):
        REPORTS[axis].validate_native_return_channels(selection, {'properties': {}})
    schema = {'properties': {'chosen_components': {'x-source': FACT_SOURCE},
        'chosen_execution': {'x-source': EXECUTION_SOURCE}}}
    REPORTS[axis].validate_native_return_channels(selection, schema)


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
        REPORTS['A110'].validate_native_return_channels(selection, rejected_form)
    assert str(failure.value) == trace['feedback']['detail']
    assert failure.value.detail['missing_fact_sources'] == trace['feedback']['required_fact_sources']
    REPORTS['A110'].validate_native_return_channels(selection, trace['admitted_return_form'])


def test_source_only_child_has_no_native_channel_requirement():
    selection = {'evidence_axis': {'option_id': 'A110'},
        'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
    REPORTS['A110'].validate_native_return_channels(selection, {'properties': {}})
