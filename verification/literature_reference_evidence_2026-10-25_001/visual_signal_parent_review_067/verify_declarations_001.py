"""Mechanical declaration reconstruction only; no scientific conversion."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / 'a105_visual_signal_design_067'


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    manifest_path = DESIGN / 'MANIFEST_007.json'
    assert fingerprint(manifest_path)['sha256'] == '7232969c2e0dc3e6b6e5bd91482214983ccd582ca75d9db9981e8ea39b68ea2c'
    manifest = json.loads(manifest_path.read_bytes())
    rows = manifest['files']
    for name, row in rows.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert fingerprint(DESIGN / name) == row, name
    assert {str(p.relative_to(DESIGN)) for p in DESIGN.rglob('*') if p.is_file()} == set(rows) | {'MANIFEST_007.json', 'SHA256SUMS_007.txt'}
    checksums = dict(line.split('  ', 1)[::-1] for line in (DESIGN / 'SHA256SUMS_007.txt').read_text().splitlines())
    assert checksums == {**{name: row['sha256'] for name, row in rows.items()}, 'MANIFEST_007.json': fingerprint(manifest_path)['sha256']}
    destination = HERE / 'reconstructed_declarations_001'
    destination.mkdir(exist_ok=False)
    for name in ('build_declarations_001.py', 'build_declarations_004.py', 'build_declarations_005.py',
                 'build_declarations_006.py', 'INTERFACE_004.json'):
        with (destination / name).open('xb') as stream:
            stream.write((DESIGN / name).read_bytes())
    execution = []
    for generation in ('004', '005', '006'):
        result = subprocess.run([sys.executable, '-P', '-B', str(destination / ('build_declarations_' + generation + '.py'))],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        execution.append({'generation': generation, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        assert result.returncode == 0, execution[-1]
    final_names = [family + '_SCHEMA_006.json' for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN')] + ['INTERFACE_006.json']
    for name in final_names:
        assert (destination / name).read_bytes() == (DESIGN / name).read_bytes(), name
    schemas = {family: json.loads((destination / (family + '_SCHEMA_006.json')).read_bytes())
               for family in ('REQUEST', 'EXTRACTION', 'SHEET', 'RETURN')}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    examples = json.loads((DESIGN / 'EXAMPLES_004.json').read_bytes())
    for example in examples:
        Draft202012Validator(schemas['REQUEST']).validate(example['selection'])
        Draft202012Validator(schemas['SHEET']).validate(example['expected_sheet'])
    result = {'scope': 'Mechanical exact declaration generation and shape checks; root post-packet reset/scientific interpretation pending',
        'sealed_payloads': len(rows), 'sealed_bytes': sum(row['bytes'] for row in rows.values()),
        'sha_lines': len(checksums), 'exact_normative_files_rebuilt': final_names,
        'draft_schema_meta_checks': 4, 'constructed_request_and_expected_sheet_shapes': len(examples),
        'actual_builder_executions': execution, 'application_imports': 0,
        'production_reader_calculator_executed': False, 'source_or_model_execution': False,
        'runtime_observations': 0, 'scientific_acceptance': False}
    with (HERE / 'DECLARATIONS_ROOT_RECEIPT_001.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({key: result[key] for key in ('sealed_payloads', 'sealed_bytes', 'sha_lines',
        'draft_schema_meta_checks', 'constructed_request_and_expected_sheet_shapes', 'scientific_acceptance')}))


if __name__ == '__main__':
    main()
