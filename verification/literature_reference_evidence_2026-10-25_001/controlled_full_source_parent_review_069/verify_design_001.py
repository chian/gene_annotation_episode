"""Root mechanical schema/builder proof; no new source reader or native work."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
DESIGN = BASE / 'a105_controlled_full_source_design_069'
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def fp(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    manifest_path = DESIGN / 'MANIFEST_001.json'
    assert fp(manifest_path)['sha256'] == '837e95f24c0dadbd26f1829d9cd5c91b732b62fb9c96078669a2d891d3a55038'
    files = json.loads(manifest_path.read_bytes())['files']
    for name, row in files.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert fp(DESIGN / name) == row, name
    assert {str(p.relative_to(DESIGN)) for p in DESIGN.rglob('*') if p.is_file()} == set(files) | {'MANIFEST_001.json', 'SHA256SUMS_001.txt'}
    lines = (DESIGN / 'SHA256SUMS_001.txt').read_text().splitlines()
    checksums = dict(line.split('  ', 1)[::-1] for line in lines)
    assert len(checksums) == len(lines)
    assert checksums == {**{name: row['sha256'] for name, row in files.items()}, 'MANIFEST_001.json': fp(manifest_path)['sha256']}
    selection_path = BASE / 'a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json'
    assert (DESIGN / 'SELECTION_SCHEMA_V2_001.json').read_bytes() == selection_path.read_bytes()
    selection = json.loads(selection_path.read_bytes())
    schema_names = ['EXTRACTION_SCHEMA_V2_001.json', 'COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json',
        'COMPANION_EXTRACTION_SCHEMA_V3_PROPOSAL_001.json', 'CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json']
    for name in schema_names:
        Draft202012Validator.check_schema(json.loads((DESIGN / name).read_bytes()))
    v3 = json.loads((DESIGN / schema_names[1]).read_bytes())
    back = deepcopy(v3)
    for name in ('companion_readings', 'joint_reading_assignments'):
        del back['properties'][name]; back['required'].remove(name)
    back['properties']['version'] = selection['properties']['version']
    assert back == selection
    from gene_annotation_episode.literature_controlled_response_owner_calculations import controlled_response_owner_arguments_schema
    assert controlled_response_owner_arguments_schema() == json.loads((BASE / 'a105_controlled_adapter_design_065/OWNER_INPUT_SCHEMA_004.json').read_bytes())
    destination = HERE / 'reconstructed_001'
    destination.mkdir(exist_ok=False)
    adjustments = []
    for filename in ('build_declarations_001.py', 'build_constructed_examples_001.py'):
        tree = ast.parse((DESIGN / filename).read_text())
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                name = statement.targets[0].id
                paths = {'HERE': destination, 'BASE': BASE, 'ROOT': ROOT}
                if name in paths:
                    statement.value = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()), args=[ast.Constant(str(paths[name]))], keywords=[])
                    adjustments.append({'builder': filename, 'assignment': name, 'path': str(paths[name])})
        ast.fix_missing_locations(tree)
        exec(compile(tree, str(DESIGN / filename), 'exec'), {'__name__': '__main__', '__file__': str(DESIGN / filename)})
    generated = sorted(p.name for p in destination.iterdir() if p.is_file())
    assert len(generated) == 13
    for name in generated:
        assert (destination / name).read_bytes() == (DESIGN / name).read_bytes(), name
    cases = json.loads((destination / 'CONSTRUCTED_SOURCE_CASES_001.json').read_bytes())
    assert len(cases) == 14 and all(case['source_reader_executed'] is False for case in cases)
    imports = []
    for name, module in sorted(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            imports.append({'module': name, 'path': str(path.relative_to(ROOT)), **fp(path)})
    receipt = {'scope': 'Exact design reconstruction plus actual068 arithmetic on HAND projections; no new source-reader/native/model proof',
        'sealed_payloads': len(files), 'sha_lines': len(lines), 'exact061_selection_copy': True,
        'meta_schemas': 4, 'exact_v3_base_recovered': True, 'actual068_schema_matches004': True,
        'generated_payloads_byte_identical': generated, 'actual_hand_projected_cases': len(cases),
        'only_reconstruction_path_assignments_changed': adjustments, 'actual_project_imports': imports,
        'new_reader_execution': False, 'scientific_reconciliation_accepted': False,
        'native_or_typed_or_sourcefree_runtime_proof': False, 'runtime_observations': 0}
    with (HERE / 'DESIGN_ROOT_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps({key: receipt[key] for key in ('sealed_payloads', 'sha_lines', 'meta_schemas',
        'actual_hand_projected_cases', 'new_reader_execution', 'scientific_reconciliation_accepted')}))


if __name__ == '__main__':
    main()
