"""One selected sklearn NMF fit with complete native artifact retention.

No retry, resource substitution, hidden investigation or continuation rule is
implemented here. Numerical max_iter belongs to the selected sklearn solver.
"""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import warnings

from .expression_nmf_common import (FACTOR_SCHEMA, MODE, NATIVE_SCHEMA, axis, digest, fit_parameters,
    identity, issue, matrix_valid, require, validate_parameters)
from .expression_nmf_inputs import parse_expression_matrix, prepare_expression_matrix
from .native_expression_nmf_contracts import (ARTIFACT_NAMES, ARTIFACT_FORMATS, OWNER_FILENAME,
    STARTED_FILENAME, expression_nmf_environment, validate_expression_nmf_run_plan, validate_expression_nmf_software)
from .native_expression_nmf_storage import (confined_file, directory, file_pin, immutable_bytes,
    immutable_json, read_json, regular)


def _now():
    return datetime.now(timezone.utc).isoformat()


def run_expression_nmf(prepared: dict, *, parameters: dict) -> dict:
    """Fit one explicit model, or retain an explicit input/dependency failure."""
    parameters = validate_parameters(parameters)
    require(type(prepared) is dict and prepared.get('schema') == 'expression_nmf_prepared_v1', 'nmf_prepared_input_required')
    require(parameters['normalization'] == prepared.get('normalization'), 'nmf_preprocessing_parameter_conflict')
    components = axis([f'component_{k}' for k in range(parameters['rank'])], 'component')
    result = {'schema': NATIVE_SCHEMA, 'mode': MODE, 'input_identity': deepcopy(prepared['input_identity']),
        'prepared_data_sha256': digest(prepared), 'parameters': parameters, 'estimator_parameters': fit_parameters(parameters),
        'components': components, 'axes': {'genes': [r['key'] for r in prepared['genes']],
            'samples': [r['key'] for r in prepared['samples']], 'components': [r['key'] for r in components]},
        'W': None, 'H': None, 'source': {'kind': 'sklearn_fit', 'estimator': 'sklearn.decomposition.NMF', 'versions': {}},
        'diagnostics': {'reconstruction_err_': None, 'n_iter_': None, 'fit_call_count': 0,
            'iteration_limit_reached': None, 'convergence_warning': None},
        'warnings': [], 'failures': deepcopy(prepared.get('failures', [])), 'outcome': 'rejected_input'}
    for g, row in enumerate(prepared.get('raw_matrix') or []):
        for s, value in enumerate(row):
            if type(value) in (int, float) and value < 0:
                result['failures'].append(issue('negative_expression_input', 'fit_validation', gene_position=g, sample_position=s))
    if prepared.get('status') != 'valid' or not matrix_valid(prepared.get('fit_matrix'), *prepared['shape'], nonnegative=True):
        if not result['failures']:
            result['failures'].append(issue('invalid_fit_matrix', 'fit_validation'))
    if result['failures']:
        return result
    observed = []
    try:
        import numpy as np
        from sklearn.decomposition import NMF
        from sklearn.exceptions import ConvergenceWarning
        result['source']['versions'] = {name: importlib.metadata.version(name)
            for name in ('scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl')}
        result['source']['versions']['python'] = sys.version
        model = NMF(**result['estimator_parameters'])
        X = np.asarray(prepared['fit_matrix'], dtype=np.float64, order='C')
        print(json.dumps({'stage': 'nmf_fit_started', 'shape': list(X.shape), 'rank': parameters['rank']}), flush=True)
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always')
            result['diagnostics']['fit_call_count'] = 1
            W = model.fit_transform(X)
        result['W'], result['H'] = W.tolist(), model.components_.tolist()
        result['diagnostics'].update(reconstruction_err_=float(model.reconstruction_err_), n_iter_=int(model.n_iter_),
            iteration_limit_reached=int(model.n_iter_) == parameters['max_iter'])
        result['outcome'] = 'complete'
    except Exception as error:
        result['outcome'] = 'failed'
        result['failures'].append(issue('native_fit_failed', 'fit', field=type(error).__module__ + '.' + type(error).__name__))
        result['native_exception'] = {'class': type(error).__module__ + '.' + type(error).__name__, 'message': str(error)}
    finally:
        result['warnings'] = [{'category': row.category.__module__ + '.' + row.category.__name__,
            'code': 'iteration_limit_warning' if row.category.__name__ == 'ConvergenceWarning' else 'native_warning',
            'message': str(row.message)} for row in observed]
    result['diagnostics']['convergence_warning'] = any(row['code'] == 'iteration_limit_warning' for row in result['warnings'])
    if result['outcome'] == 'complete' and result['warnings']:
        result['outcome'] = 'qualified'
    print(json.dumps({'stage': 'nmf_fit_finished', 'outcome': result['outcome'], 'n_iter_': result['diagnostics']['n_iter_']}), flush=True)
    return result


def retain_expression_nmf_artifacts(raw: bytes, *, delimiter: str, metadata: dict | None,
        parameters: dict, output_directory, execution: dict | None = None) -> dict:
    """Selected native producer; retains valid inputs before attempting a fit."""
    root = directory(Path(output_directory).absolute())
    root.mkdir(parents=True, exist_ok=True)
    require(not any(root.iterdir()), 'nmf_output_directory_not_empty')
    immutable_bytes(root / ARTIFACT_NAMES['original_input'], raw)
    parsed = parse_expression_matrix(raw, delimiter=delimiter, metadata=metadata)
    immutable_json(root / ARTIFACT_NAMES['input_data'], parsed)
    prepared = prepare_expression_matrix(parsed, normalization=parameters['normalization'])
    immutable_json(root / ARTIFACT_NAMES['prepared_data'], prepared)
    print(json.dumps({'stage': 'nmf_input_retained', 'shape': parsed['shape'], 'normalization': prepared['normalization']}), flush=True)
    result = run_expression_nmf(prepared, parameters=parameters)
    factors = {'schema': FACTOR_SCHEMA, 'input_identity': deepcopy(parsed['input_identity']),
        'prepared_data_sha256': digest(prepared), 'axes': deepcopy(result['axes']),
        'W': result['W'], 'H': result['H']}
    if result['W'] is not None or result['H'] is not None:
        immutable_json(root / ARTIFACT_NAMES['factors'], factors)
    G, S, K = *parsed['shape'], parameters['rank']
    declarations = []
    for role in ('original_input', 'input_data', 'prepared_data', 'factors'):
        path = confined_file(root, ARTIFACT_NAMES[role])
        present = path.is_file()
        pin = file_pin(path) if present else {'sha256': None, 'size_bytes': None}
        declarations.append({'role': role, 'relative_path': path.name, 'format': ARTIFACT_FORMATS[role],
            'state': 'present' if present else 'absent', 'sha256': pin['sha256'], 'size_bytes': pin['size_bytes'],
            'shape': {'W': [G, K], 'H': [K, S]} if role == 'factors' else [G, S]})
    manifest = {'schema': 'expression_nmf_native_manifest_v1', 'mode': MODE, 'input_identity': identity(raw),
        'prepared_data_sha256': digest(prepared), 'shape': [G, S], 'axes': deepcopy(result['axes']),
        'files': declarations, 'result': {k: v for k, v in result.items() if k not in ('W', 'H')},
        'execution': deepcopy(execution), 'sealed': True, 'finished_at': _now()}
    immutable_json(root / ARTIFACT_NAMES['manifest'], manifest)
    return manifest


def verify_expression_nmf_software(software):
    """Validate selected file closure in the bounded native process."""
    software = validate_expression_nmf_software(software)
    require(str(Path(sys.executable).resolve()) == str(Path(software['python']['path']).resolve())
        and sys.version == software['python_version'], 'nmf_interpreter_mismatch')
    for expected in [software['python'], *software['implementation_files'], *software['runtime_files']]:
        require(file_pin(expected['path']) == expected, 'nmf_software_file_changed')
    for row in software['distributions']:
        require(importlib.metadata.version(row['name']) == row['version'], 'nmf_distribution_version_changed')
    allowed = [Path(software['module_root']), Path(software['python_home']), *map(Path, software['dependency_roots'])]
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).is_file():
            require(any(Path(filename).resolve().is_relative_to(root) for root in allowed), 'nmf_unbound_import')


def execute_expression_nmf_plan(plan):
    plan = validate_expression_nmf_run_plan(plan)
    job = plan['requested_job']['native_expression_nmf']
    attempt = directory(plan['attempt_directory'])
    attempt.mkdir(parents=True, exist_ok=True)
    owner = confined_file(attempt, OWNER_FILENAME)
    started = confined_file(attempt, STARTED_FILENAME)
    require(not started.exists(), 'nmf_original_attempt_already_started')
    immutable_json(owner, plan)
    immutable_json(started, {'plan': plan, 'started_at': _now()})
    expected_environment = expression_nmf_environment(job['software'], attempt_directory=str(attempt))
    # Existing lifecycle enforcement owns these three temporary paths and sets
    # them to its monitored cwd before launching the selected driver.
    expected_environment.update({key: str(Path(plan['identity']['execution_id']).parent)
        for key in ('TMPDIR', 'TMP', 'TEMP')})
    require(all(os.environ.get(k) == v for k, v in expected_environment.items()), 'nmf_runtime_environment_mismatch')
    for name in ('tmp', 'cache'):
        directory(attempt / name).mkdir(exist_ok=True)
    verify_expression_nmf_software(job['software'])
    supplied = job['input']
    require(supplied['size_bytes'] <= plan['policy']['scratch_bytes'], 'nmf_input_exceeds_scratch_limit')
    with regular(supplied['path']) as stream:
        raw = stream.read()
    require(identity(raw) == {k: supplied[k] for k in ('sha256', 'size_bytes')}, 'nmf_original_input_identity_mismatch')
    output = attempt / job['output_prefix']
    manifest = retain_expression_nmf_artifacts(raw, delimiter=supplied['delimiter'], metadata=supplied['metadata'],
        parameters=job['parameters'], output_directory=output,
        execution={'identity': plan['identity'], 'software_sha256': digest(job['software']),
            'requested_job_sha256': digest(plan['requested_job']), 'realized_environment': expected_environment})
    verify_expression_nmf_software(job['software'])
    return 0 if manifest['result']['outcome'] in ('complete', 'qualified') else 2


def main():
    require(len(sys.argv) == 2, 'one_nmf_run_plan_required')
    try:
        return execute_expression_nmf_plan(read_json(Path(sys.argv[1]).absolute()))
    except (ValueError, OSError, MemoryError) as error:
        print(json.dumps({'stage': 'nmf_driver_failed', 'exception_class': type(error).__name__,
            'code': str(error)}), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
