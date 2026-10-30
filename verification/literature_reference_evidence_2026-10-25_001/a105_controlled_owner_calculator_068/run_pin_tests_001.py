"""Actual targeted execution from the coherent068 pin; no scientific sources."""
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_001'
sys.path.insert(0, str(PIN))
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def verify():
    manifest = json.loads((HERE / 'PIN_MANIFEST_001.json').read_text())
    assert {str(p.relative_to(PIN)) for p in PIN.rglob('*') if p.is_file()} == set(manifest)
    for name, row in manifest.items():
        path = PIN / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name


def main():
    import pytest
    verify()
    result = pytest.main(['-q', '-c', '/dev/null', '-p', 'no:cacheprovider',
        str(PIN / 'tests/test_literature_controlled_response_owner_calculations.py')])
    assert result == 0
    from gene_annotation_episode.literature_controlled_response_owner_calculations import populate_controlled_response_owner
    from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
    design = PIN / 'verification/literature_reference_evidence_2026-10-25_001/a105_controlled_adapter_design_065'
    cases = json.loads((design / 'OWNER_SHAPE_EXAMPLES_004.json').read_text())['examples']
    extra = json.loads((design / 'ACTIVE_UNKNOWN_OWNER_CASE_006.json').read_text())['inputs']
    cases['unknown_active_owner_despite_known_id_coverage'] = extra
    exact = deepcopy(cases['active_owner_covariance_only'])
    exact['arms']['empty_condition0']['digitization_interval'] = {'lower': 3.95, 'upper': 4.15}
    cases['exact_decimal_mixed_shared'] = exact
    normal = deepcopy(exact)
    normal['model_kind'] = 'known_joint_normal_source_means'
    cases['constructed_active_normal_model'] = normal
    actual = {}
    for name, inputs in cases.items():
        try:
            actual[name] = {'status': 'populated', 'result': populate_controlled_response_owner(inputs)}
        except ExperimentalContractError as error:
            assert name == 'invalid_FULL_covariance_despite_canceled_B'
            actual[name] = {'status': 'invalid', 'code': error.code, 'field': error.field}
    save('ACTUAL_EXECUTED_EXAMPLES_001.json', {'scope': 'Actually executed new pure calculator on constructed inputs; no paper/image/native/model work', 'examples': actual})
    imports = []
    for name, module in sorted(sys.modules.items()):
        if name.startswith('gene_annotation_episode') and getattr(module, '__file__', None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN), (name, str(path))
            imports.append({'module': name, 'path': str(path.relative_to(PIN)), 'sha256': sha(path)})
    verify()
    save('PIN_EXECUTION_RECEIPT_001.json', {'actual_test_exit_code': int(result), 'actual_project_imports': imports,
        'python_version': sys.version, 'pytest_version': pytest.__version__,
        'jsonschema_version': importlib.metadata.version('jsonschema'), 'pin_pre_post_identity_matches': True,
        'actual_executed_new_calculator_examples': len(actual), 'scientific_inputs_or_model_calls': 0,
        'runtime_observations': 0, 'scope': 'coherent pure module/tests/helpers/declarations; native source/typed consumers unimplemented'})
    print(json.dumps({'test_exit_code': int(result), 'actual_pin_project_imports': len(imports),
        'executed_constructed_examples': len(actual), 'new_owner_calculator_actually_run': True,
        'scientific_model_execution': False}))


if __name__ == '__main__':
    main()
