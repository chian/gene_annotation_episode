"""Owned synthetic probe of valid partial saved validation; no scientific source."""
import ast
from copy import deepcopy
import errno
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PIN = BASE / 'a105_contract_information_design_059/connected_stage_004/pin_010'
PRELIM = HERE / 'reader008_preliminary_001'
sys.path.insert(0, str(PIN))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    import gene_annotation_episode
    reader_path = PRELIM / 'gene_annotation_episode/literature_controlled_response_inputs.py'
    assert hashlib.sha256(reader_path.read_bytes()).hexdigest() == '8c3cfc3434edb33d8f16621ecd0e70311692fffbacc11ede1e53fbae690b23fe'
    reader = load_module('gene_annotation_episode.literature_controlled_response_inputs', reader_path)
    gene_annotation_episode.literature_controlled_response_inputs = reader
    test_path = PRELIM / 'tests/test_literature_controlled_response_inputs.py'
    fixture_module = load_module('root_preliminary_controlled_fixture', test_path)
    fixture_module.PIN = BASE / 'a105_controlled_response_design_056/reader_stage_007'
    # Reuse only the complete reviewed invented fixture setup, ending before
    # its original reader call/assertions. No production implementation changes.
    tree = ast.parse(test_path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'test_source_defined_units_are_endpoint_bound_and_converted_once')
    function.name = 'make_defined_unit_fixture'
    boundary = next(i for i, node in enumerate(function.body)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'result' for t in node.targets))
    function.body = [*function.body[:boundary], ast.Return(value=ast.Name(id='f', ctx=ast.Load()))]
    ast.fix_missing_locations(function)
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<reviewed-owned-fixture-setup>', 'exec'), fixture_module.__dict__)
    fixture = fixture_module.make_defined_unit_fixture()
    baseline = fixture.read()
    reader.validate_controlled_response_extraction(fixture.args, baseline)
    source_ref = fixture_module.identity('source', {'scope': 'invented unavailable unit witness only'})
    nomination = fixture.args['arms']['protein_condition1']['measurement']['unit']
    nomination['witness'] = {'source_ref': source_ref, 'representation': 'original',
                             'start': 0, 'end': 4, 'quote': 'U/mg'}
    def callback(reference, representation):
        if reference == source_ref:
            raise FileNotFoundError(errno.ENOENT, 'Owned invented unavailable unit witness')
        return fixture.source(reference, representation)
    result = reader.read_controlled_response_inputs(fixture.args, read_source=callback)
    unit = result['arms']['protein_condition1']['measurement']['unit']
    assert unit['status'] == 'dependency_unavailable' and unit['definition_witnesses'] is None
    assert result['arms']['empty_condition1']['calculation_operand']['value'] == 2
    before_calls = deepcopy(fixture.calls)
    error_record = None
    def forbidden(*_args, **_kwargs):
        raise AssertionError('Saved validation must not instantiate source readers')
    with patch.object(reader, '_Sources', forbidden), patch.object(reader, '_Inputs', forbidden):
        try:
            reader.validate_controlled_response_extraction(fixture.args, result)
        except reader.ExperimentalContractError as error:
            error_record = {'code': error.code, 'field': error.field}
    assert fixture.calls == before_calls
    assert error_record and error_record['code'] == 'closed_fields_required', error_record
    receipt = {'scope': 'Invented fixture, preliminary immutable reader; not scientific coverage or final implementation.',
               'reader_sha256': hashlib.sha256(reader_path.read_bytes()).hexdigest(),
               'fully_available_defined_unit_validates': True,
               'reader_preserved_valid_missing_unit_partial': True,
               'independent_control_value_preserved': 2,
               'saved_validation_rejects_its_own_valid_partial': error_record,
               'source_reader_or_decoder_called_by_saved_validation': False,
               'production_or_oldrun_modified': False}
    with (HERE / 'DEFINED_UNIT_PARTIAL_PROBE_008_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
