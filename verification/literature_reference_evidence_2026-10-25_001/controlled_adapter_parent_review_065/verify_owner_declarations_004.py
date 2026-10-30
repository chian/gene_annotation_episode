"""Reconstruct every owner declaration from completely reviewed builders.

No new calculator is implemented or run. All numerical examples are explicitly
constructed fixtures/expected shapes, not paper or runtime evidence.
"""
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
DESIGN = BASE / 'a105_controlled_adapter_design_065'
PIN = BASE / 'a105_controlled_response_design_056/implementation_stage_008/execution_pin_008'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refs(value):
    if isinstance(value, dict):
        if '$ref' in value:
            yield value['$ref']
        for item in value.values():
            yield from refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from refs(item)


def main():
    output = HERE / 'reconstructed_owner_declarations_004'
    output.mkdir()
    old = "O=B/'a105_controlled_adapter_design_065'"
    modified = 'O=Path(' + repr(str(output)) + ')'
    builder_rows = []
    for name in ('build_owner_declarations_003.py', 'build_owner_correction_004.py'):
        path = DESIGN / name
        source = path.read_text()
        assert source.count(old) == 1
        adjusted = source.replace(old, modified)
        assert adjusted.replace(modified, old) == source
        exec(compile(adjusted, str(path), 'exec'), {'__name__': 'root_declaration_reconstruction'})
        builder_rows.append({'path': str(path), 'sha256': sha(path), 'only_change': 'output directory assignment'})
    generated = []
    for path in sorted(output.iterdir()):
        assert path.is_file() and path.read_bytes() == (DESIGN / path.name).read_bytes(), path.name
        generated.append({'name': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size})
    assert len(generated) == 11
    for name in ('OWNER_INPUT_SCHEMA_003.json', 'OWNER_OUTPUT_SCHEMA_003.json',
                 'OWNER_INPUT_SCHEMA_004.json', 'OWNER_OUTPUT_SCHEMA_004.json'):
        schema = json.loads((output / name).read_bytes())
        Draft202012Validator.check_schema(schema)
        for reference in refs(schema):
            assert reference.startswith('#/$defs/') and reference.split('/')[-1] in schema['$defs']
    schema = json.loads((output / 'OWNER_INPUT_SCHEMA_004.json').read_bytes())
    examples = json.loads((output / 'OWNER_SHAPE_EXAMPLES_004.json').read_bytes())
    for example in examples['examples'].values():
        Draft202012Validator(schema).validate(example)
    expected = json.loads((output / 'OWNER_EXPECTED_SHEET_004.json').read_bytes())
    Draft202012Validator(json.loads((output / 'OWNER_OUTPUT_SCHEMA_004.json').read_bytes())).validate(expected)
    imports = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN.resolve()), (name, str(path))
            imports.append({'module': name, 'path': str(path), 'sha256': sha(path)})
    result = {'scope': 'Root exact declaration-builder review/reconstruction; no new semantic calculator implementation',
        'complete_builders_reviewed': builder_rows, 'generated_files_byte_identical': generated,
        'schemas_meta_valid_and_all_local_refs_resolve': 4, 'shape_examples_validated': len(examples['examples']),
        'hand_constructed_expected_sheet_shape_valid': True, 'new_owner_calculator_executed': False,
        'actual_project_imports': imports, 'paper_reads': 0, 'model_calls': 0, 'runtime_observations': 0,
        'still_required': 'Implement semantic owner algebra/guards and verify them, then source/native/typed/model paths.'}
    with (HERE / 'OWNER_DECLARATIONS_ROOT_RECEIPT_004.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'generated_identical': len(generated), 'schemas': 4, 'shape_cases': len(examples['examples']),
        'hand_constructed_expected_only': True, 'new_owner_calculator_run': False}))


if __name__ == '__main__':
    main()
