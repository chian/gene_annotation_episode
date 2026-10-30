"""Prepared values cannot masquerade as original parser output.

Inputs below are explicitly synthetic. No scaling or compensation is executed.
"""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_context_views import project_fluorescence_context
from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
from gene_annotation_episode.fluorescence_execution_common import identity
from gene_annotation_episode.fluorescence_result_contracts import (
    CONTEXT_VIEW_SCHEMA, validate_fluorescence_context,
)
from gene_annotation_episode.native_fluorescence_contracts import (
    JOB_SCHEMA, validate_fluorescence_job, validate_fluorescence_parsed_batch,
)
from test_fluorescence_event_calculations import (
    _batch, _file, _gate, _parameters, _request, _sheet,
)
from test_native_fluorescence_contracts import event_input, job, parsed_batch, plan


def prepared_job(directory):
    first = event_input(directory, index=0)
    second = event_input(directory, index=1)
    second['sample'] = deepcopy(first['sample'])
    parameter_bytes = b'{"fixture":"supplied preparation metadata"}\n'
    parameter_path = directory / 'parameters.json'
    parameter_path.write_bytes(parameter_bytes)
    file = identity(parameter_bytes, format='json')
    second['domain'].update(sample_key=first['sample']['key'],
        parent_domain_key=first['domain']['key'], scale_kind='scaled',
        correspondence=[{'source_ordinal': i, 'event_ordinal': i} for i in range(2)],
        scaling={'state': 'applied', 'method': 'declared_fixture_scaling', 'parameters_file': file})
    value = job(directory, inputs=[first, second])
    value['support_inputs'] = [{'file': file, 'path': str(parameter_path)}]
    return value


def test_supplied_scaling_metadata_requires_its_actual_support_identity(tmp_path):
    value = prepared_job(tmp_path)
    before = deepcopy(value)
    Draft202012Validator(JOB_SCHEMA).validate(value)
    assert validate_fluorescence_job(value) == before == value
    missing = deepcopy(value)
    missing['support_inputs'] = []
    with pytest.raises(ValueError, match='fluorescence_support_input_mismatch'):
        validate_fluorescence_job(missing)


def test_original_parsed_batch_cannot_claim_new_derived_values(tmp_path):
    selected = prepared_job(tmp_path)
    original = plan(tmp_path, selected_job=selected)
    batch = parsed_batch(original, index=1)
    assert validate_fluorescence_parsed_batch(batch, original_plan=original, input_index=1) == batch
    forged = deepcopy(batch)
    forged['parse']['events'][0]['values'][0]['measurement'].update(state='derived', raw=None)
    # The new common derived-event shape is valid, but the original parser
    # envelope does not authorize a preparation it never executed.
    assert core.validate_event_parse_result(forged['parse']) == forged['parse']
    with pytest.raises(ValueError, match='fluorescence_parsed_measurement_origin_mismatch'):
        validate_fluorescence_parsed_batch(forged, original_plan=original, input_index=1)


def prepared_context():
    raw = _batch([[110], [60]])
    prepared = _batch([[100], [50]], domain='s.prepared',
        correspondence=[{'source_ordinal': i, 'event_ordinal': i} for i in range(2)])
    scaling = {'state': 'applied', 'method': 'declared_fixture_scaling', 'parameters_file': _file()}
    prepared['domain'].update(scale_kind='scaled', scaling=scaling)
    for event in prepared['events']:
        event['values'][0]['measurement'].update(state='derived', raw=None)
    sheet = _sheet([raw, prepared], gates=[_gate(domain='s.prepared', lower=0, upper=None)])
    request = {'gate_key': 'g', 'domain_key': 's.prepared', 'channel_key': 's.prepared.c0'}
    components = calculate_fluorescence_sheet(sheet, parameters=_parameters(intensities=[request]))
    selected = {'requests': [_request('intensity', 'selected_intensity_mean', **request)], 'offset': 0, 'limit': 1}
    context = project_fluorescence_context(sheet, components, selection=selected, context_fields=['domains'])
    return sheet, components, context


def test_requested_context_preserves_scaling_without_inventing_old_domain_metadata():
    sheet, components, context = prepared_context()
    before = deepcopy((sheet, components, context))
    assert [cell['value'] for cell in components['cells']
        if cell['request']['metric'] == 'selected_intensity_mean'] == [75]
    assert [d['key'] for d in context['domains']] == ['s.raw', 's.prepared']
    assert 'scaling' not in context['domains'][0]
    assert context['domains'][1]['scaling'] == sheet['measurement_domains'][1]['scaling']
    assert all('correspondence' not in d for d in context['domains'])
    Draft202012Validator(CONTEXT_VIEW_SCHEMA).validate(context)
    assert validate_fluorescence_context(context) == context
    assert before == (sheet, components, context)
    context['domains'][1]['scaling']['method'] = 'changed returned copy'
    assert sheet['measurement_domains'][1]['scaling']['method'] == 'declared_fixture_scaling'


@pytest.mark.parametrize('change', ['unknown_field', 'missing_parameters'])
def test_optional_scaling_does_not_weaken_closed_context_validation(change):
    _, _, context = prepared_context()
    if change == 'unknown_field':
        context['domains'][1]['unrequested'] = 'value'
    else:
        context['domains'][1]['scaling']['parameters_file'] = None
    with pytest.raises(ValueError):
        validate_fluorescence_context(context)
