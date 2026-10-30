"""Actual HIC producer and retained calculation through the existing lifecycle.

Run through packet457. Native data are the synthetic454 files decoded by an
independent native program. This verifies producer/worker binding, not model
decisions or authenticated episode communication (the separate Workflow suite).
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_file_capture import capture_native_file
from gene_annotation_episode.state import Store
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    ATTEMPT_DIRECTORY_NAME, POLICY, RUN_PLAN_FILENAME, _dependency_roots,
    chromatin_output_files, digest, requested_job_from_chromatin,
    validate_chromatin_run_plan, validate_chromatin_software,
)
from gene_annotation_episode.native_chromatin_interaction_driver import _immutable, _read_control
from gene_annotation_episode.native_chromatin_interaction_preparation import (
    freeze_chromatin_software_binding, prepare_chromatin_result_worker,
)
from gene_annotation_episode.native_chromatin_interaction_tool_info import chromatin_interaction_tool_contracts

REPO = Path(os.environ['C3_ORIGINAL_REPO'])
ATTEMPT = Path(os.environ['C3_ATTEMPT'])
FIXTURES = REPO / 'verification/tool_graders_chromatin_hic_native_2026-10-27_454'
_spec = importlib.util.spec_from_file_location('chromatin457_c3_helpers', REPO / 'tests/test_chromatin_native_execution_c3.py')
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)


@pytest.fixture(scope='session')
def hic_software():
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    binding = freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(ATTEMPT / 'selected_hic_software'), python_executable=sys.executable,
        supported_formats=['hic_binary_v9'])
    (ATTEMPT / 'HIC_SOFTWARE.json').write_text(json.dumps(binding, indent=2) + '\n')
    return binding


@pytest.fixture(scope='session')
def cooler_software():
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    # Deliberately omit supported_formats: existing callers retain Cooler only.
    return freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(ATTEMPT / 'selected_default_cooler_software'), python_executable=sys.executable)


def make_hic_plan(directory, software, *, case='raw'):
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'supplied'
    source.mkdir()
    filenames = {'raw': 'native004/four.hic', 'weighted': 'native009/valid/output.hic',
        'empty': 'native010/present_zero_block/output.hic',
        'insulation': 'native005/six_insulation/output.hic'}
    shutil.copyfile(FIXTURES / filenames[case], source / 'contact.hic')
    request = deepcopy(helpers.WORKED[('insulation' if case == 'insulation' else 'raw') + '.request'])
    request['contact'].update(format='hic_binary_v9', group_path=None)
    # The older symbolic Cooler example's assembly label is not the454 HIC
    # writer's genomeId. Retain the actually supplied contig dimensions; make
    # no invented assembly-label assertion to force reference agreement.
    references = [request['supplied_metadata']['reference']]
    if request['elements'] is not None:
        references.append(request['elements']['reference'])
    for reference in references:
        if reference is not None:
            reference['assembly_label'] = None
    if case == 'weighted':
        request['normalization'] = {'kind': 'precomputed_weighted',
            'weight_column': 'SYNTHETIC_DIVISIVE', 'convention': 'divisive'}
    bindings = []
    with Store(directory / 'store') as store:
        identity = capture_native_file(store, directory=str(source), relative_path='contact.hic', format='hic_binary_v9')
        request['contact']['file'] = identity
        bindings.append({'input_key': request['contact']['input_key'], 'file': identity, 'path': str(source / 'contact.hic')})
        if request['elements'] is not None:
            (source / 'elements.bed').write_bytes(b'chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n')
            identity = capture_native_file(store, directory=str(source), relative_path='elements.bed', format='bed_outer_span_v1')
            request['elements']['file'] = identity
            bindings.append({'input_key': request['elements']['input_key'], 'file': identity, 'path': str(source / 'elements.bed')})
    request['output_prefix'] = 'selected-output'
    environment = {'PYTHONPATH': os.pathsep.join([software['module_root'], *_dependency_roots(software)]),
        'PYTHONHOME': sys.base_prefix, 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'TMPDIR': str(directory / 'tmp'), 'TMP': str(directory / 'tmp'), 'TEMP': str(directory / 'tmp'),
        'XDG_CACHE_HOME': str(directory / 'cache'), 'PIP_CACHE_DIR': str(directory / 'cache/pip'),
        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    requested = requested_job_from_chromatin({'request': request, 'software': software, 'input_bindings': bindings}, environment=environment)
    run, episode, operation = 'hic457-component-fixture', 'local-child', 'selected-start'
    root = directory / '.episode-operations' / digest({'run': run, 'episode': episode}) / digest(operation)
    plan = validate_chromatin_run_plan({'version': 'chromatin_interaction_run_plan_v1', 'identity': {
        'run_id': run, 'episode_id': episode, 'resource_id': 'selected-local', 'execution_id': str(root / 'native.json'),
        'operation_key': operation, 'attempt_id': digest(operation), 'requested_job_sha256': digest(requested),
        'assignment_sha256': digest({'fixture': 'component test, no episode authority'})},
        'requested_job': requested, 'attempt_directory': str(root / ATTEMPT_DIRECTORY_NAME),
        'policy': POLICY, 'outputs': chromatin_output_files(request)})
    root.mkdir(parents=True)
    _immutable(root / RUN_PLAN_FILENAME, plan)
    return plan


def selector_for(plan):
    request = plan['requested_job']['native_chromatin_interactions']['request']
    key = 'insulation' if request['analysis_modes'] == ['cross_window_insulation_heuristic'] else 'raw'
    selector = deepcopy(helpers.WORKED[key + '.selector'])
    selector['parameters']['normalization'] = deepcopy(request['normalization'])
    return selector


@pytest.mark.parametrize('case', ['raw', 'weighted', 'empty', 'insulation'])
def test_actual_hic_producer_and_retained_worker(tmp_path, hic_software, case):
    plan = make_hic_plan(tmp_path, hic_software, case=case)
    bundle = helpers.complete(plan)
    assert bundle['extraction']['format'] == 'hic_binary_v9'
    assert bundle['extraction']['populations'][0]['extent'] == 'complete'
    assert not any(f['stage'] in ('execution', 'input') for f in bundle['failures'])
    worker = helpers.capture_plan(tmp_path, plan, selector_for(plan))
    with Store(tmp_path / 'capture-store') as store:
        captured = prepare_chromatin_result_worker(store, plan=worker, policy=LocalJobPolicy(**POLICY))
    assert captured['result']['state'] == 'produced', captured['result']
    components = _read_control(Path(worker['directory']) / 'components.json')
    projection = _read_control(Path(worker['directory']) / 'projection.json')
    (ATTEMPT / (case + '-components.json')).write_text(json.dumps(components, indent=2) + '\n')
    (ATTEMPT / (case + '-projection.json')).write_text(json.dumps(projection, indent=2) + '\n')
    if case == 'insulation':
        expected = helpers.WORKED['insulation.projection']['rows']
        assert len(projection['rows']) == len(expected)
        for actual, wanted in zip(projection['rows'], expected):
            for key, measurement in actual['fields'].items():
                assert measurement['value'] == pytest.approx(wanted['fields'][key]['value'])
    else:
        first, second = projection['rows']
        assert first['fields']['raw_contact']['value'] == (0 if case == 'empty' else 6)
        assert first['fields']['expected_contact']['value'] == pytest.approx({'raw': 4, 'weighted': 3.25, 'empty': 0}[case])
        fold = first['fields']['fold_enrichment']
        if case == 'empty':
            assert fold['value'] is None and fold['reason'] == 'zero_denominator'
        else:
            assert fold['value'] == pytest.approx(1.5 if case == 'raw' else 24 / 13)
        assert second['fields']['raw_contact']['value'] == 0
        assert second['fields']['fold_enrichment']['value'] is None
        assert second['fields']['fold_enrichment']['reason'] == 'zero_denominator'
    # Reusing the completed retained worker observes its original execution.
    with Store(tmp_path / 'capture-store') as store:
        assert prepare_chromatin_result_worker(store, plan=worker, policy=LocalJobPolicy(**POLICY)) == captured


def test_saved_recalculation_after_hic_and_native_attempt_removed(tmp_path, hic_software):
    plan = make_hic_plan(tmp_path, hic_software, case='weighted')
    helpers.complete(plan)
    worker = helpers.capture_plan(tmp_path, plan, selector_for(plan))
    with Store(tmp_path / 'capture-store') as store:
        original = prepare_chromatin_result_worker(store, plan=worker, policy=LocalJobPolicy(**POLICY))
    assert original['result']['state'] == 'produced'
    original_sheet = (Path(worker['directory']) / 'sheet.json').read_bytes()
    original_components = (Path(worker['directory']) / 'components.json').read_bytes()
    saved = helpers.saved_plan(tmp_path, worker, fold=1)
    shutil.rmtree(tmp_path / 'supplied')
    shutil.rmtree(plan['attempt_directory'])
    with Store(tmp_path / 'saved-store') as store:
        recalculated = prepare_chromatin_result_worker(store, plan=saved, policy=LocalJobPolicy(**POLICY))
    assert recalculated['result']['state'] == 'produced', recalculated['result']
    assert (Path(saved['directory']) / 'sheet.json').read_bytes() == original_sheet
    assert (Path(worker['directory']) / 'components.json').read_bytes() == original_components
    before = _read_control(Path(worker['directory']) / 'projection.json')['rows'][0]['fields']
    after = _read_control(Path(saved['directory']) / 'projection.json')['rows'][0]['fields']
    assert before['above_fold_threshold']['value'] is False
    assert after['above_fold_threshold']['value'] is True
    assert after['fold_enrichment']['value'] == pytest.approx(24 / 13)
    intent = _read_control(Path(saved['directory']) / 'intent.json')
    assert 'h5py' not in {row['distribution'] for row in intent['dependencies']}
    assert set(saved) == {'version', 'mode', 'directory', 'sheet_bundle', 'selector'}


def test_hic_binding_has_actual_runtime_and_no_hdf5_requirement(tmp_path, hic_software):
    from jsonschema import Draft202012Validator
    assert 'h5py' not in {row['distribution'] for row in hic_software['dependencies']}
    runtime = hic_software['native_runtime']
    assert runtime['files'] and runtime['zlib_compile_version'] and runtime['zlib_runtime_version']
    paths = {row['path'] for row in runtime['files']}
    for name in ('struct', '_struct', 'zlib', 'mmap'):
        module = __import__(name)
        filename = getattr(module, '__file__', None)
        if filename is not None:
            assert str(Path(filename).resolve()) in paths
        else:
            # This interpreter builds zlib/_struct in; their implementation is
            # covered by the actual interpreter pin, not an invented .so path.
            assert module.__spec__.origin == 'built-in'
    assert validate_chromatin_software(hic_software, supported_formats=['hic_binary_v9']) == hic_software
    with pytest.raises(ValueError, match='native_dependency_unavailable'):
        validate_chromatin_software(hic_software)
    bindings = [{'operation': 'analyze_chromatin_interactions', 'resource_kind': 'local', 'software': hic_software,
        'supported_formats': ['hic_binary_v9'], 'analysis_modes': ['cis_anchor_contact_enrichment']}]
    entry, = chromatin_interaction_tool_contracts(bindings, resource_kind='local', resource_id='selected-local')
    assert 'For HIC binary version 9' in entry['instructions']
    assert 'For Cooler HDF5' not in entry['instructions']
    plan = make_hic_plan(tmp_path, hic_software)
    Draft202012Validator(entry['input_schema']).validate(plan['requested_job'])
    for key in ('native_runtime',):
        wrong = deepcopy(hic_software)
        wrong.pop(key)
        with pytest.raises(ValueError, match='native_dependency_unavailable'):
            validate_chromatin_software(wrong, supported_formats=['hic_binary_v9'])


@pytest.mark.parametrize('corrupt', ['runtime_digest', 'zlib_version'])
def test_original_selected_runtime_mismatch_does_not_read_hic(tmp_path, hic_software, corrupt):
    software = deepcopy(hic_software)
    if corrupt == 'runtime_digest':
        software['native_runtime']['files'][0]['sha256'] = '0' * 64
    else:
        software['native_runtime']['zlib_runtime_version'] += '.wrong'
    plan = make_hic_plan(tmp_path, software)
    handle = helpers.launch(plan)
    outcome = native.wait_job(handle)
    assert outcome.returncode == 1
    assert native.status(handle)['terminal'] and native.status(handle)['quiescent']
    bundle = _read_control(Path(plan['attempt_directory']) / plan['outputs'][-1]['relative_path'])
    assert any(f['code'] == 'native_dependency_unavailable' for f in bundle['failures'])
    assert bundle['extraction']['populations'][0]['extent'] == 'unavailable'
    assert all(row['declaration']['state'] == 'absent' for row in bundle['outputs'][:5])


def test_existing_default_cooler_binding_and_actual_dispatch(tmp_path, cooler_software):
    assert 'h5py' in {row['distribution'] for row in cooler_software['dependencies']}
    assert 'native_runtime' not in cooler_software
    bindings = [{'operation': 'analyze_chromatin_interactions', 'resource_kind': 'local', 'software': cooler_software,
        'supported_formats': ['cooler_hdf5_v3'], 'analysis_modes': ['cis_anchor_contact_enrichment']}]
    entry, = chromatin_interaction_tool_contracts(bindings, resource_kind='local', resource_id='selected-local')
    assert 'For Cooler HDF5' in entry['instructions'] and 'For HIC binary' not in entry['instructions']
    plan = helpers.make_plan(tmp_path, cooler_software)
    bundle = helpers.complete(plan)
    assert bundle['extraction']['format'] == 'cooler_hdf5_v3'
    assert bundle['extraction']['populations'][0]['extent'] == 'complete'
