"""Original incoming saved-file and model formats, without running native producers."""
from copy import deepcopy
from importlib import import_module

import pytest
from jsonschema import Draft202012Validator

AXES = ('a101', 'a105', 'a106', 'a108')


def reader(axis, module):
    return import_module('gene_annotation_episode.episodic_workflow.root.' + axis + '.library.retained_input_authority.' + module)


def file_record(format):
    digest = 'a' * 64
    return {'artifact_ref': 'artifact_' + digest, 'sha256': digest, 'size_bytes': 17, 'format': format}


@pytest.mark.parametrize('axis', AXES)
def test_original_schema_constraints_and_generic_file_remain_distinct(axis):
    nmf = reader(axis, 'expression_nmf_result_contracts')
    fba = reader(axis, 'flux_balance_result_contracts')
    model = reader(axis, 'flux_balance_model_tools')
    assert nmf.SAVED_FILE_SCHEMA['properties']['format'] == {'const': 'expression_nmf_sheet_v1'}
    assert fba.fba_result_schema('FBASavedSheetReference')['properties']['format'] == {'const': 'flux_balance_sheet_v1'}
    assert fba.fba_result_schema('FBASavedSheetReference')['properties']['artifact_ref'] == {
        'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}
    assert model.flux_balance_model_schema('Request')['oneOf'][0]['properties']['model_file']['properties']['format'] == {'enum': ['sbml', 'cobra_json']}
    assert Draft202012Validator(reader(axis, 'flux_balance_contracts').flux_balance_schema('File')).is_valid(file_record('other_file'))
    assert nmf.validate_file(file_record('other_file')) == file_record('other_file')
    malformed = file_record('flux_balance_sheet_v1'); malformed['artifact_ref'] = 'source_' + 'a' * 64
    assert not Draft202012Validator(fba.fba_result_schema('FBASavedSheetReference')).is_valid(malformed)


@pytest.mark.parametrize('axis', AXES)
def test_nmf_actual_saved_file_positive_and_identity_check(axis):
    module = reader(axis, 'expression_nmf_result_contracts')
    value = file_record('expression_nmf_sheet_v1')
    assert module.validate_file(value, saved=True) == value
    assert module.validate_file(value, saved=True) is not value
    invalid = deepcopy(value); invalid['sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='expression_nmf_file_identity_mismatch'):
        module.validate_file(invalid, saved=True)


@pytest.mark.parametrize('axis', AXES)
def test_nmf_saved_file_rejects_other_valid_generic_format(axis):
    module = reader(axis, 'expression_nmf_result_contracts')
    value = file_record('flux_balance_sheet_v1')
    assert module.validate_file(value) == value
    with pytest.raises(ValueError, match='invalid_expression_nmf_file'):
        module.validate_file(value, saved=True)


@pytest.mark.parametrize('axis', AXES)
def test_fba_actual_saved_reference_positive_and_identity_check(axis):
    module = reader(axis, 'flux_balance_result_contracts')
    value = file_record('flux_balance_sheet_v1')
    assert module.validate_fba_saved_sheet_reference(value) == value
    invalid = deepcopy(value); invalid['sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='fba_projection_selection_mismatch'):
        module.validate_fba_saved_sheet_reference(invalid)


@pytest.mark.parametrize('axis', AXES)
def test_fba_saved_reference_rejects_other_valid_generic_format(axis):
    module = reader(axis, 'flux_balance_result_contracts')
    with pytest.raises(ValueError, match='fba_projection_shape_invalid'):
        module.validate_fba_saved_sheet_reference(file_record('expression_nmf_sheet_v1'))


@pytest.mark.parametrize('axis', AXES)
@pytest.mark.parametrize('format', ('sbml', 'cobra_json'))
def test_original_model_request_accepts_declared_formats(axis, format):
    module = reader(axis, 'flux_balance_model_tools')
    value = {'version': 'flux_balance_model_request_v1', 'mode': 'inspect',
        'model_file': file_record(format), 'edits': None}
    assert module._checked(value, module.flux_balance_model_schema('Request'), 'fba_model_request_invalid') == value


@pytest.mark.parametrize('axis', AXES)
def test_original_model_request_rejects_nonmodel_saved_sheet(axis):
    module = reader(axis, 'flux_balance_model_tools')
    value = {'version': 'flux_balance_model_request_v1', 'mode': 'inspect',
        'model_file': file_record('flux_balance_sheet_v1'), 'edits': None}
    with pytest.raises(ValueError, match='fba_model_request_invalid'):
        module._checked(value, module.flux_balance_model_schema('Request'), 'fba_model_request_invalid')
