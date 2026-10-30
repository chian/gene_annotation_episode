"""Authenticate the sealed source-reader proposal without executing a new reader."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
STAGE = BASE / 'a105_controlled_response_design_056/reader_stage_007'
PURE = BASE / 'a105_controlled_response_design_056/pure_stage_003'
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator


def load(path):
    return json.loads(path.read_bytes())


def verify(directory, entries):
    for name, row in entries.items():
        path = directory / name
        assert path.stat().st_size == row['bytes'], name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], name


def main():
    delivery = load(STAGE / 'DELIVERY_007.json')
    verify(STAGE, delivery['artifacts'])
    dependencies = {}
    for name in ('BASELINE_007.json', 'BASELINE_008.json'):
        dependencies.update(load(STAGE / name)['files'])
    verify(ROOT, dependencies)
    accepted = load(PURE / 'DELIVERY_006.json')
    verify(PURE, accepted['artifacts'])
    verify(ROOT, accepted['owned_new_paths'])
    for name in ('gene_annotation_episode/literature_controlled_response_inputs.py',
                 'tests/test_literature_controlled_response_inputs.py'):
        assert not (ROOT / name).exists(), name
    generated = runpy.run_path(str(STAGE / 'build_schema_007.py'))
    # This is part of actual main(), before it emits the three artifacts.
    # Merely importing the builder does not perform this declared hydration.
    generated['finalize_result_interface']()
    for filename, key in [('SELECTION_SCHEMA_007.json', 'selection'),
                          ('COVARIANCE_SOURCE_SCHEMA_007.json', 'covariance_source'),
                          ('RESULT_INTERFACE_007.json', 'result')]:
        assert load(STAGE / filename) == generated[key], filename
    for key in ('selection', 'covariance_source'):
        Draft202012Validator.check_schema(generated[key])
    compatibility = load(STAGE / 'COMPATIBILITY_RECEIPT_007.json')
    for name in ('ordinary', 'shared_control'):
        case = compatibility[name]
        Draft202012Validator(generated['selection']).validate(case['selection'])
        Draft202012Validator(generated['covariance_source']).validate(case['source_covariance'])
    numerical = load(STAGE / 'ROUNDTRIP_PROOF_007.json')
    for row in numerical['rows']:
        exact = Fraction(row['original_source_lexeme'])
        value = float(row['original_source_lexeme'])
        rejected = not math.isfinite(value) or value == 0 and exact != 0
        equal = not rejected and exact == Fraction(str(value))
        assert row['source_exact'] == {'numerator': str(exact.numerator), 'denominator': str(exact.denominator)}
        assert row['source_equals_frozen_q_str_interpretation'] == equal
        assert row['numeric_projection_rounding'] == (not equal and not rejected)
        assert row['numeric_range_failure'] == rejected
    for name in ('FIXTURE_ALGEBRA_RECEIPT_007.json', 'CONFIDENCE_PUNCTUATION_RECEIPT_007.json'):
        assert load(Path(__file__).with_name(name))['passed']
    verify(STAGE, delivery['artifacts'])
    output = {'passed': True, 'sealed_proposal_artifacts': len(delivery['artifacts']),
              'current_readonly_dependencies': len(dependencies),
              'accepted006_artifacts_unchanged': len(accepted['artifacts']),
              'actual_generator_outputs_equal': 3, 'synthetic_forms_validated': 2,
              'independent_decimal_roundtrips': len(numerical['rows']),
              'source_reader_and_tests_absent_at_review': True,
              'scope': 'Proposal/interface compatibility and synthetic source algebra only; no new reader, graph/native integration, scientific source truth or model execution.'}
    with Path(__file__).with_name('PROPOSAL_RECEIPT_007.json').open('x') as stream:
        json.dump(output, stream, indent=2)
        stream.write('\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
