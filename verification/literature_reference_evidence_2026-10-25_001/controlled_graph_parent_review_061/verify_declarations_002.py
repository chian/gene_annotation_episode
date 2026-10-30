"""Root declaration reconstruction; no source, pixel decoder or grader execution."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
STAGE = BASE / 'a105_controlled_graph_design_061'
OUT = HERE / 'reconstructed_declarations_002'


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load(path):
    return json.loads(path.read_bytes())


def verify_refs(schema):
    count = 0
    def visit(node):
        nonlocal count
        if isinstance(node, dict):
            if '$ref' in node:
                ref = node['$ref']
                assert ref.startswith('#/'), ref
                target = schema
                for token in ref[2:].split('/'):
                    target = target[token.replace('~1', '/').replace('~0', '~')]
                count += 1
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    return count


def main():
    manifests = {}
    expected_digests = {
        '001': 'b91d2f600b401db81e500482ede008e1bd77c1901e69f98ff89c60985ccb7606',
        '002': '44926eefdb91b3a77e1363ce0d6d9a5c5adb7c68c1cd02f37cfe6397f2f2f5cc'}
    for version, expected_digest in expected_digests.items():
        path = STAGE / ('MANIFEST_' + version + '.json')
        assert fingerprint(path)['sha256'] == expected_digest
        manifest = load(path)
        for row in manifest['files']:
            assert fingerprint(STAGE / row['path']) == {key: row[key] for key in ('bytes', 'sha256')}, row['path']
        manifests[version] = len(manifest['files'])
    OUT.mkdir()
    relative = Path('baseline/verification/literature_reference_evidence_2026-10-25_001/a105_controlled_response_design_056/reader_stage_007/SELECTION_SCHEMA_007.json')
    destination = OUT / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes((STAGE / relative).read_bytes())
    # Both reviewed declaration builders contain no reader/model calls. Give
    # them a NEW __file__ root so all outputs stay outside the sealed owner set.
    for name in ('build_declarations_001.py', 'build_declarations_002.py'):
        exec(compile((STAGE / name).read_text(), str(STAGE / name), 'exec'),
             {'__file__': str(OUT / name), '__name__': 'root_declaration_reconstruction'})
    names = ('SELECTION_SCHEMA_V2_001.json', 'GRAPH_REQUEST_SCHEMA_001.json',
             'GRAPH_RESULT_SCHEMA_001.json', 'EXACT_DELTA_001.json',
             'COUNT_RESULT_SCHEMA_002.json', 'GRAPH_RESULT_SCHEMA_002.json',
             'COUNT_INTERFACE_002.json', 'EXACT_DELTA_002.json')
    for name in names:
        assert (OUT / name).read_bytes() == (STAGE / name).read_bytes(), name
    old = load(destination)
    changed = load(OUT / 'SELECTION_SCHEMA_V2_001.json')
    restored = deepcopy(changed)
    restored['properties']['version'] = deepcopy(old['properties']['version'])
    restored['$defs'].pop('AxisScale')
    graph = restored['$defs']['GraphMeasurement']
    graph['properties'].pop('terminal_edge')
    graph['required'].remove('terminal_edge')
    graph['properties']['axis']['properties'].pop('scale')
    graph['properties']['axis']['required'].remove('scale')
    assert restored == old
    schemas = {}
    for name in names:
        if 'SCHEMA' not in name:
            continue
        schema = load(OUT / name)
        Draft202012Validator.check_schema(schema)
        schemas[name] = {'local_refs_resolved': verify_refs(schema)}
    expected_count = load(STAGE / 'COUNT_EXPECTED_SHAPE_002.json')
    Draft202012Validator(load(OUT / 'COUNT_RESULT_SCHEMA_002.json')).validate(expected_count)
    fraction = Fraction(0.1)
    assert fraction == Fraction(3602879701896397, 36028797018963968)
    assert Fraction(1, 10) < fraction < Fraction(2, 10)
    # Exact signed endpoint algebra, independently of any proposed pixel code.
    slope = (Fraction(0) - 4) / (60 - 20)
    value = lambda pixel: 4 + (pixel - 20) * slope
    nominal = value(Fraction(159, 2))
    bounds = sorted((value(Fraction(157, 2)), value(Fraction(161, 2))))
    assert nominal == Fraction(-39, 20)
    assert bounds == [Fraction(-41, 20), Fraction(-37, 20)]
    result = {'scope': 'Proposal declaration reconstruction/shape/exact algebra only; no counter/decoder/source/model execution.',
              'manifest_entries_verified': manifests, 'declarations_reconstructed_exactly': len(names),
              'selection_delta_is_only_version_edge_scale': True,
              'schemas': schemas, 'hand_constructed_count_record_schema_valid': True,
              'exact_binary_fraction_preserved': str(fraction),
              'synthetic_signed_nominal': str(nominal), 'synthetic_signed_bounds': [str(x) for x in bounds],
              'implementation_released_by_this_check': False}
    with (HERE / 'DECLARATION_ROOT_RECEIPT_002.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
