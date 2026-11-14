"""Reject changed science in actual captured historical controlled-source results.

Capture files are disposable execution evidence produced by the reusable
scientific_attestation_replay helper. This check never edits captured artifacts
or replaces implementation metadata and never reacquires scientific sources.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .scientific_attestation_replay import science


def check(directory):
    path = directory / 'original_results.json'
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == (directory / 'original_results.sha256').read_text().strip()
    rows = [row for row in json.loads(original) if row['kind'] == 'extraction' and row['version'] == 3]
    assert len(rows) == 2 and {row['owner'] for row in rows} == {'axis', 'pilot'}
    verified = []
    for row in rows:
        module = science(row['owner'], 'literature_controlled_response_v3_inputs')
        retained = deepcopy(row['result'])
        assert module.validate_controlled_response_v3_extraction(row['arguments'], retained) == row['result']
        changed = deepcopy(retained)
        role = module.shared.PRIMITIVE_ORDER[2]
        operand = changed['calculation_inputs']['arms'][role]
        assert type(operand['value']) in (int, float)
        operand['value'] += 1
        assert changed['implementation_dependencies'] == row['result']['implementation_dependencies']
        try:
            module.validate_controlled_response_v3_extraction(row['arguments'], changed)
        except module.shared.ExperimentalContractError as error:
            assert str(error) == 'saved_source_projection_mismatch:extraction', str(error)
        else:
            raise AssertionError('Authenticated historical release cannot authorize changed scientific operands')
        assert retained == row['result']
        verified.append({'owner': row['owner'], 'case_index': row.get('case_index', 0), 'changed_science_rejected': True})
    assert path.read_bytes() == original
    print(json.dumps({'verified': verified, 'original_results_sha256': hashlib.sha256(original).hexdigest(), 'saved_results_unchanged': True}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    assert args.directory.resolve().is_relative_to((Path.cwd() / 'runs').resolve())
    check(args.directory)


if __name__ == '__main__':
    main()
