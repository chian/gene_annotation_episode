"""A107 pure declared-request/saved-control boundaries; never execute native code."""
from copy import deepcopy
import hashlib
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.episodic_workflow.root.a107 import lumpy_request_binding, macs2_peak_request_binding
from gene_annotation_episode.episodic_workflow.root.a107.library import atac_execution_contracts as atac
from gene_annotation_episode.episodic_workflow.root.a107.library import lumpy_request_contracts as lumpy
from gene_annotation_episode.episodic_workflow.root.a107.library import macs2_request_contracts as macs
from gene_annotation_episode.episodic_workflow.root.a107.library.atac_control_json import decode_json


def environment():
    return dict(PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONHOME='/declared/python',
        TMP='/declared/tmp', TEMP='/declared/tmp', TMPDIR='/declared/tmp',
        XDG_CACHE_HOME='/declared/cache', PIP_CACHE_DIR='/declared/cache/pip')


def original_environment():
    # Independent source audit pins this exact original function body. The
    # selected helpers are original AST-identical definitions, not mocks.
    raw = Path(__file__).with_name('fixtures').joinpath('a107_original_native_environment.py').read_bytes()
    namespace = dict(atac.__dict__)
    exec(compile(raw, 'authenticated_original_native_environment', 'exec'), namespace)
    return namespace['_environment']






@pytest.mark.parametrize('owner', [lumpy_request_binding, macs2_peak_request_binding])
def test_actual_compact_request_caller_uses_selected_owner_and_empty_bindings(owner):
    schema = owner.scientific_request_schema()
    Draft202012Validator.check_schema(schema)
    bound = owner.resource_assignment_schema('declared_resource', bindings=[])
    assert bound['properties']['binding_ordinal_0based']['enum'] == []
    schema['properties']['version']['const'] = 'changed'
    assert owner.scientific_request_schema()['properties']['version']['const'] != 'changed'


@pytest.mark.parametrize('raw', [b'{"same":1,"same":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff'])
def test_saved_control_json_keeps_duplicate_nonfinite_and_encoding_failures(raw):
    with pytest.raises(ValueError, match='^invalid_native_control_json$'):
        decode_json(raw)


def test_saved_control_json_preserves_nested_nulls_and_array_order():
    assert decode_json(b'{"x":[null,2,1],"y":{"z":false}}') == {'x': [None, 2, 1], 'y': {'z': False}}


def pin(path):
    return {'path': path, 'sha256': '0' * 64, 'size_bytes': 0}


def declared_macs_plan():
    """Typed metadata operands only. No files or actual execution are asserted."""
    dependencies = [{'distribution': name, 'version': 'declared',
        'package_root': '/declared/deps/' + name, 'files': [pin('/declared/deps/' + name + '/module.py')]}
        for name in sorted(atac.REQUIRED_DEPENDENCIES)]
    driver = {'python_executable': '/declared/python/bin/python', 'python_sha256': '0' * 64,
        'python_version': '3.13', 'module_root': '/declared/modules',
        'implementation_files': [{'module': name, 'sha256': '0' * 64}
            for name in sorted(atac.REQUIRED_MODULES | {macs.DRIVER_MODULE})],
        'dependencies': dependencies}
    runtime = {'python_executable': '/declared/macs/bin/python', 'python_sha256': '0' * 64,
        'python_version': '3.13', 'macs2_script': '/declared/macs/bin/macs2',
        'macs2_sha256': '0' * 64, 'macs2_version': '2.2.9.1', 'import_roots': ['/declared/macs/site'],
        'files': [pin(path) for path in ('/declared/macs/bin/macs2',
            '/declared/macs/site/MACS2/callpeak_cmd.py', '/declared/macs/site/MACS2/bdgdiff_cmd.py',
            '/declared/macs/site/MACS2/IO/Parser.declared.so', '/declared/macs/site/numpy/__init__.py')]}
    reference = {'reference_id': 'declared_reference', 'assembly_accession_version': None,
        'source_refs': [], 'contigs': [], 'aliases': []}
    inputs = []; samples = []
    for role, symbol in (('treatment', 'a'), ('control', 'b')):
        file = {'artifact_ref': 'artifact_' + symbol * 64, 'sha256': symbol * 64, 'size_bytes': 0, 'format': 'bed6'}
        inputs.append({'input_key': role, 'role': role, 'sample_id': role,
            'reference_id': reference['reference_id'], 'file': file})
        samples.append({'sample_id': role, 'input_artifact_refs': [file['artifact_ref']],
            'reference_id': reference['reference_id'], 'biospecimen_id': None, 'replicate_id': None,
            'origin': 'synthetic_engineering_fixture'})
    request = {'version': macs.REQUEST_VERSION, 'operation': macs.OPERATION, 'mode': macs.MODE,
        'run_key': 'declared_run', 'condition_id': 'declared_condition', 'reference': reference,
        'samples': samples, 'inputs': inputs, 'callpeak': {'genome_size_argument': 'hs', 'qvalue_cutoff': 0.05},
        'output_prefix': 'declared_output'}
    job = {'request': request, 'software': {'driver_runtime': driver, 'macs2_runtime': runtime},
        'input_bindings': [{'input_key': row['input_key'], 'file': row['file'],
            'path': '/declared/input/' + row['input_key']} for row in inputs]}
    env = environment(); env['PYTHONPATH'] = ':'.join([driver['module_root'], *atac._dependency_roots(driver)])
    requested = macs.requested_job_from_macs2_peak(job, environment=env)
    identity = {'run_id': 'declared_run', 'episode_id': 'declared_episode', 'resource_id': 'declared_resource',
        'execution_id': '/declared/operation/native.json', 'operation_key': 'declared_operation',
        'attempt_id': macs.digest('declared_operation'), 'requested_job_sha256': macs.digest(requested),
        'assignment_sha256': '0' * 64}
    plan = {'version': macs.PLAN_VERSION, 'identity': identity, 'requested_job': requested,
        'attempt_directory': '/declared/operation/' + macs.ATTEMPT_DIRECTORY_NAME,
        'policy': deepcopy(macs.POLICY), 'outputs': macs.macs2_peak_output_files(request)}
    return macs.validate_macs2_peak_run_plan(plan)


def failure(code):
    return {'code': code, 'stage': 'execution', 'step_key': None, 'file_key': None,
        'binding_key': None, 'artifact_ref': None, 'locator': None, 'field_path': None,
        'requirement': 'original_native_outcome', 'partial_artifact_refs': []}


@pytest.mark.parametrize('outcome', ['not_run', 'failed'])
def test_saved_seal_retains_failed_and_unexecuted_outcomes(outcome):
    plan = declared_macs_plan()
    value = {'version': macs.SEAL_VERSION, 'identity': plan['identity'],
        'producer_ref': macs._producer_ref(plan), 'argv': macs.macs2_peak_command_argv(plan),
        'environment': macs._native_environment(plan),
        'inputs': [{key: row[key] for key in ('input_key', 'role', 'file')}
            for row in plan['requested_job']['native_macs2_peak']['request']['inputs']],
        'started_at': None if outcome == 'not_run' else '2026-01-01T00:00:00+00:00',
        'finished_at': None if outcome == 'not_run' else '2026-01-01T00:00:01+00:00',
        'returncode': None if outcome == 'not_run' else 7, 'outcome': outcome,
        'outputs': [{'specification': row, 'declaration': {'relative_path': row['relative_path'],
            'format': row['format'], 'state': 'absent', 'sha256': None, 'size_bytes': None}}
            for row in plan['outputs'] if row['role'] != 'seal'],
        'failures': [failure('native_dependency_unavailable' if outcome == 'not_run' else 'native_nonzero_exit')]}
    before = deepcopy(value)
    assert macs.validate_macs2_peak_seal(value, plan=plan) == before == value
    assert value['environment']['OPENBLAS_NUM_THREADS'] == value['environment']['OMP_NUM_THREADS'] == '1'
    changed = deepcopy(value); changed['environment']['OMP_NUM_THREADS'] = '2'
    with pytest.raises(ValueError, match='^original_attempt_mismatch$'):
        macs.validate_macs2_peak_seal(changed, plan=plan)
    changed = deepcopy(value); changed['outcome'] = 'succeeded'
    with pytest.raises(ValueError):
        macs.validate_macs2_peak_seal(changed, plan=plan)


def test_original_control_bytes_authenticate_digest_and_request_without_path_reads():
    plan = declared_macs_plan()
    paths = {key: '/declared/operation/' + key for key in ('request', 'ready', 'release', 'status', 'result', 'launcher')}
    raw = macs.canonical(macs._job_request(plan, paths))
    original = {'version': macs.native.VERSION, 'stage': 'released',
        'command': macs.macs2_peak_driver_argv(plan), 'cwd': '/declared/operation',
        'metadata': {'policy': deepcopy(plan['policy'])}, 'paths': paths,
        'stdout': '/declared/operation/stdout.log', 'stderr': '/declared/operation/stderr.log',
        'request_sha256': hashlib.sha256(raw).hexdigest()}
    assert macs.validate_macs2_peak_original_controls(plan, original, raw) == plan
    with pytest.raises(ValueError, match='^original_attempt_mismatch$'):
        macs.validate_macs2_peak_original_controls(plan, original, raw + b' ')
    changed = deepcopy(original); changed['metadata']['policy']['memory_bytes'] += 1
    with pytest.raises(ValueError, match='^original_attempt_mismatch$'):
        macs.validate_macs2_peak_original_controls(plan, changed, raw)
