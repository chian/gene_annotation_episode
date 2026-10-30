"""Validate proposal syntax/grammar/examples only; no workflow or reader run."""
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.communication import validate_closed_schema


def main():
    documents = {}
    for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN'):
        schema = json.loads((HERE / (family + '_SCHEMA_006.json')).read_text())
        Draft202012Validator.check_schema(schema)
        documents[family] = Draft202012Validator(schema)
    form = {'type': 'object', 'properties': {'measurements': documents['RETURN'].schema},
        'required': ['measurements'], 'additionalProperties': False}
    assert validate_closed_schema(form) == form
    examples = json.loads((HERE / 'EXAMPLES_004.json').read_text())
    for row in examples:
        documents['REQUEST'].validate(row['selection'])
        documents['SHEET'].validate(row['expected_sheet'])
        assert row['expected_sheet']['independent_preparation_count'] is None
        assert row['expected_sheet']['annotation_credit'] is None
        assert all(row['expected_sheet']['cells'][name]['value'] is None for name in (
            'calibrated_amount_ratio', 'amount_adjusted_effect', 'source_profile_log_ratio', 'source_signed_index'))
    for family in ('REQUEST',):
        assert (HERE / (family + '_SCHEMA_006.json')).read_bytes() == (HERE / (family + '_SCHEMA_005.json')).read_bytes()
    imports = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(ROOT)
            imports.append({'module': name, 'path': str(path.relative_to(ROOT)),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt = {'status': 'passed', 'normative_declaration_generation': '006',
        'draft202012_schemas_meta_validated': 4, 'actual_existing_closed_parent_grammar_validated': True,
        'constructed_requests_shape_validated': len(examples), 'expected_sheets_shape_validated': len(examples),
        'request_schema_same_as005': True,
        'actual_application_imports_for_pure_schema_grammar_only': imports,
        'production_reader_calculator_calls': 0, 'workflow_or_Store_constructed': False,
        'model_calls': 0, 'source_acquisitions': 0, 'native_image_view_receipts_created': 0,
        'runtime_actions_or_controller_observations': 0,
        'limits': 'These are design declarations, expected arithmetic and structural grammar checks. Semantic validation, actual image custody, parsing/calculation, registration, persistence, C1/C4 and readonly reconstruction are unimplemented/unrun.'}
    with (HERE / 'DESIGN_CHECK_006.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: receipt[key] for key in ('status', 'draft202012_schemas_meta_validated',
        'actual_existing_closed_parent_grammar_validated', 'constructed_requests_shape_validated', 'expected_sheets_shape_validated',
        'production_reader_calculator_calls', 'runtime_actions_or_controller_observations')}))


if __name__ == '__main__':
    main()
