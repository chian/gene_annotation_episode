"""Pure selection and real shared registration, using authored declarations.

No fixture here is an executed native result or authenticated child report.
Run through packet445's existing bounded native lifecycle runner.
"""
from copy import deepcopy
from importlib import import_module
import builtins
import io
import json
import os
from pathlib import Path
import socket
import subprocess

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.chromatin_interaction_execution_information import (
    chromatin_result_selector_schema, describe_chromatin_result,
    validate_chromatin_result_selector,
)
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_chromatin_interaction_contracts import (
    POLICY, REQUIRED_DEPENDENCIES, REQUIRED_MODULES, requested_job_from_chromatin,
    validate_chromatin_job,
)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


WORKED = {row['example_key']: row['record'] for row in json.loads((
    Path(__file__).resolve().parents[1] /
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json'
).read_text())['records']}


def software():
    return {'python_executable': '/synthetic/python', 'python_sha256': '1' * 64,
        'python_version': 'synthetic', 'module_root': '/synthetic/source',
        'driver_module': 'gene_annotation_episode.native_chromatin_interaction_driver',
        'implementation_files': [{'module': name, 'sha256': '2' * 64}
            for name in sorted(REQUIRED_MODULES)],
        'dependencies': [{'distribution': name, 'version': 'synthetic',
            'package_root': '/synthetic/deps/' + name,
            'files': [{'path': '/synthetic/deps/' + name + '/member',
                'sha256': '3' * 64, 'size_bytes': 1}]} for name in sorted(REQUIRED_DEPENDENCIES)]}


def requested(case='raw'):
    request, selected_software = deepcopy(WORKED[case + '.request']), software()
    inputs = [request['contact']] + ([] if request['elements'] is None else [request['elements']])
    job = {'request': request, 'software': selected_software, 'input_bindings': [
        {'input_key': item['input_key'], 'file': deepcopy(item['file']),
            'path': '/synthetic/input/' + item['file']['sha256']} for item in inputs]}
    environment = {key: '/synthetic/runtime' for key in (
        'PYTHONHOME', 'TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR')}
    environment.update({key: '1' for key in ('PYTHONNOUSERSITE', 'PYTHONSAFEPATH',
        'PYTHONDONTWRITEBYTECODE', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')})
    dependencies = sorted(selected_software['dependencies'],
        key=lambda row: row['distribution'] not in {'numpy', 'h5py'})
    environment['PYTHONPATH'] = ':'.join([selected_software['module_root'],
        *[row['package_root'] for row in dependencies]])
    return requested_job_from_chromatin(job, environment=environment)


def target(case='raw'):
    job = requested(case)
    return {'version': 'execution_target_v1', 'handle': 'synthetic-handoff',
        'run_id': 'synthetic-run', 'resource_id': 'selected-local', 'resource_kind': 'local',
        'execution_id': '/synthetic/original/native.json', 'request_sha256': digest(job),
        'origin_episode_id': 'synthetic-local-child',
        'assignment': {'resource_id': 'selected-local', 'resource_kind': 'local', 'requested_job': job},
        'scope': {'subject_refs': ['synthetic-subject']}}


def selector(case='raw', *, saved=False):
    value = deepcopy(WORKED[case + '.selector'])
    if saved:
        value.update(mode='saved_sheet_recalculation',
            saved_sheet_bundle=deepcopy(WORKED['raw_saved.selector']['saved_sheet_bundle']))
    return value


def collection(value):
    return next(row for row in value['extractors'] if row['operation'] == 'execution.results.collect')


@pytest.mark.parametrize('case', ['raw', 'weighted', 'insulation'])
@pytest.mark.parametrize('saved', [False, True])
def test_preserves_explicit_result_question_without_new_analysis(case, saved):
    original, selected = target(case), selector(case, saved=saved)
    before = deepcopy((original, selected))
    value = describe_chromatin_result(original, selector=selected)
    assert value['operation'] == 'analyze_chromatin_interactions'
    assert value['result_selection'] == selected
    assert collection(value)['parameters'] == selected['parameters']
    assert collection(value)['new_native_analysis'] is False
    assert collection(value)['native_input_acquisition'] is False
    assert collection(value)['local_job_policy'] == POLICY
    assert value['status_operations'] == (['execution.results.status'] if saved else
        ['progress.observe', 'execution.results.status'])
    assert value['extractors'][0]['fresh_native_observation'] is (not saved)
    assert ('capture' in collection(value)) is (not saved)
    value['result_selection']['population_keys'].clear()
    collection(value)['parameters'].clear()
    assert (original, selected) == before


def test_parent_population_order_and_page_are_preserved():
    request = deepcopy(WORKED['raw.request'])
    request['populations'] = [{**request['populations'][0], 'population_key': key}
        for key in ('p0', 'p1', 'p2')]
    selected = selector()
    selected['population_keys'] = ['p2', 'p0']
    selected['projection']['fields'] = ['fold_enrichment']
    selected['projection']['selection']['page'] = {'offset': 7, 'limit': 3}
    assert validate_chromatin_result_selector(selected, request=request) == selected
    selected['population_keys'] = ['unknown']
    with pytest.raises(ValueError, match='chromatin_result_population_conflict'):
        validate_chromatin_result_selector(selected, request=request)


@pytest.mark.parametrize('case,other', [('raw', 'insulation'), ('insulation', 'raw')])
def test_incompatible_analysis_cannot_be_selected(case, other):
    with pytest.raises(ValueError, match='chromatin_result_analysis_mode_conflict'):
        validate_chromatin_result_selector(selector(other), request=WORKED[case + '.request'])
    changed = selector(case)
    changed['projection'] = deepcopy(selector(other)['projection'])
    with pytest.raises(ValueError, match='chromatin_result_projection_mode_conflict'):
        validate_chromatin_result_selector(changed, request=WORKED[case + '.request'])


@pytest.mark.parametrize('mutation', ['digest', 'target_resource', 'assignment_resource', 'resource_kind'])
def test_original_request_and_resource_cannot_be_replaced(mutation):
    value = target()
    if mutation == 'digest':
        value['request_sha256'] = '0' * 64
    elif mutation == 'target_resource':
        value['resource_id'] = 'different-local'
    elif mutation == 'assignment_resource':
        value['assignment']['resource_id'] = 'different-local'
    else:
        value['resource_kind'] = 'hpc'
    with pytest.raises(ValueError, match='chromatin_result_target_conflict'):
        describe_chromatin_result(value, selector=selector())


def test_every_advertised_callable_is_real():
    for saved in (False, True):
        value = describe_chromatin_result(target(), selector=selector(saved=saved))
        for row in value['extractors']:
            for key in ('implementation', 'preparation', 'result_worker', 'calculator',
                    'projection', 'saved_input_validation', 'worker_plan', 'table_parser',
                    'capture', 'sheet_population'):
                if key not in row:
                    continue
                parts = row[key].split('.')
                module = import_module('.'.join(parts[:2]))
                resolved = module
                for attribute in parts[2:]:
                    resolved = getattr(resolved, attribute)
                assert callable(resolved), row[key]


def test_description_never_reads_inputs_observes_or_executes(monkeypatch):
    from gene_annotation_episode import chromatin_interaction_calculations as calculations
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_chromatin_interaction_results as host
    original, native, saved = target(), selector(), selector(saved=True)
    def denied(*args, **kwargs):
        raise AssertionError('pure information accessed bytes or executed work')
    with monkeypatch.context() as guard:
        for owner, name in ((builtins, 'open'), (io, 'open'), (os, 'open'),
                (Path, 'read_bytes'), (Path, 'read_text'), (Path, 'stat'),
                (subprocess, 'Popen'), (socket, 'socket'), (Store, '__init__'),
                (native_lifecycle, 'status'), (native_lifecycle, 'resume_start'),
                (host, 'prepare_chromatin_result_worker'),
                (calculations, 'calculate_chromatin_components')):
            guard.setattr(owner, name, denied)
        for selected in (native, saved):
            assert describe_chromatin_result(original, selector=selected)['result_selection'] == selected


def test_selector_embeds_with_independent_schema_scope():
    embedded = {'type': 'object', 'properties': {'selector': chromatin_result_selector_schema()},
        'required': ['selector'], '$defs': {'ResultSelector': {'not': {}}}}
    validator = Draft202012Validator(embedded)
    for saved in (False, True):
        value = selector(saved=saved)
        validator.validate({'selector': value})
        value['projection']['fields'] = ['invented_confidence']
        assert not validator.is_valid({'selector': value})


def family(store, directory, resource):
    return ExecutionEpisodes(None, store=store, directory=directory, run_id='chromatin-registration',
        resources={'selected-local': resource}, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])


def resource(directory):
    return {'kind': 'local', 'workspace': str(directory), 'policy': deepcopy(POLICY),
        'native_chromatin_interactions': [{'operation': 'analyze_chromatin_interactions',
            'resource_kind': 'local', 'analysis_modes': ['cis_anchor_contact_enrichment',
                'cross_window_insulation_heuristic'], 'supported_formats': ['cooler_hdf5_v3'],
            'software': software()}]}


def assignment(directory):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'synthetic-chromatin',
        'resource_kind': 'local', 'resource_id': 'selected-local', 'workspace': str(directory),
        'endpoint': 'usable_handoff', 'requested_job': requested(),
        'progress_requirements': [{'key': 'handoff', 'credit': 1,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(directory), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def test_actual_bound_registration_and_reconstruction(tmp_path, monkeypatch):
    config, selected = resource(tmp_path), assignment(tmp_path)
    def denied(*args, **kwargs):
        raise AssertionError('registration executed or observed work')
    monkeypatch.setattr('gene_annotation_episode.native_lifecycle.status', denied)
    monkeypatch.setattr('gene_annotation_episode.native_lifecycle.resume_start', denied)
    with Store(tmp_path / 'store') as store:
        owner = family(store, tmp_path / 'run', config)
        Draft202012Validator(owner.assignment_schema('launch_local')).validate(selected)
        assert owner._validate_request(selected) == selected
        entries = [row for row in owner.resource_tool_contracts() if row['name'] == 'analyze_chromatin_interactions']
        assert len(entries) == 1
        assert entries[0]['resources'] == 'local'
        assert entries[0]['description'] and entries[0]['instructions']
        assert entries[0]['invocation_route']['routes'] == [{'entry_role': 'launch',
            'resource_id': 'selected-local', 'resource_role': 'launch_local'}]
        assert 'analyze_chromatin_interactions' not in ToolRegistry(store).catalog()
        restored = ExecutionEpisodes(None, store=store, directory=tmp_path / 'restored',
            run_id='chromatin-registration', tool_registry=ToolRegistry(store), **owner.as_record()['configuration'])
        assert restored.as_record() == owner.as_record()
        assert restored.resource_tool_contracts() == owner.resource_tool_contracts()
        changed = deepcopy(selected)
        changed['requested_job']['native_chromatin_interactions']['software']['python_sha256'] = '0' * 64
        assert not Draft202012Validator(owner.assignment_schema('launch_local')).is_valid(changed)
        with pytest.raises(ValueError, match='native_chromatin_interactions_format_modes_software_not_bound'):
            owner._validate_request(changed)


@pytest.mark.parametrize('empty', [False, True])
def test_unbound_operation_is_not_advertised(tmp_path, empty):
    config = resource(tmp_path)
    if empty:
        config['native_chromatin_interactions'] = []
    else:
        del config['native_chromatin_interactions']
    with Store(tmp_path / 'store') as store:
        owner = family(store, tmp_path / 'run', config)
        assert not any(row['name'] == 'analyze_chromatin_interactions' for row in owner.resource_tool_contracts())
        assert not Draft202012Validator(owner.assignment_schema('launch_local')).is_valid(assignment(tmp_path))


@pytest.mark.parametrize('kind', ['api', 'pbs_ssh'])
def test_unimplemented_resource_binding_is_explicit(tmp_path, kind):
    config = {**resource(tmp_path), 'kind': kind}
    with Store(tmp_path / 'store') as store:
        with pytest.raises(ValueError, match='native_chromatin_resource_execution_binding_unfinished'):
            family(store, tmp_path / 'run', config)


def test_rna_and_chromatin_selectors_are_both_validated_when_bound_together(tmp_path):
    from gene_annotation_episode.rna_structure_contracts import OPERATIONS
    config = resource(tmp_path)
    mode = next(key for key, value in OPERATIONS.items() if value == 'analyze_rna_secondary_structure_features')
    config['native_rna_structure'] = [{'operation': OPERATIONS[mode], 'mode': mode, 'software': {
        'python_executable': '/synthetic/python', 'python_sha256': '1' * 64,
        'python_version': None, 'worker_module': 'gene_annotation_episode.native_rna_structure_worker',
        'worker_source_sha256': '2' * 64, 'viennarna_distribution_version': None,
        'rna_module_sha256': None, 'rna_extension_sha256': None}}]
    rna = {'version': 'native_rna_structure_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': 'summary', 'rows': {'offset': 0, 'limit': 1}, 'metrics': ['n_nt']}}
    with Store(tmp_path / 'store') as store:
        owner = family(store, tmp_path / 'run', config)
        validator = Draft202012Validator(owner.assignment_schema('results')['properties']['selector'])
        validator.validate(selector())
        validator.validate(rna)
        for value in (selector(), rna):
            value['projection']['unrecognized_field'] = True
            assert not validator.is_valid(value)


def test_repeated_input_bytes_preserve_roles_without_claiming_format_validity():
    job = requested()['native_chromatin_interactions']
    contact = job['request']['contact']
    elements = job['request']['elements']
    elements['file'] = {**contact['file'], 'format': elements['format']}
    job['input_bindings'][1].update(file=deepcopy(elements['file']), path=job['input_bindings'][0]['path'])
    result = validate_chromatin_job(job)
    assert len(result['input_bindings']) == 2
    assert result['input_bindings'][0]['input_key'] != result['input_bindings'][1]['input_key']
    assert [row['file']['format'] for row in result['input_bindings']] == ['cooler_hdf5_v3', 'bed_outer_span_v1']
    elements['file']['size_bytes'] += 1
    job['input_bindings'][1]['file'] = deepcopy(elements['file'])
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        validate_chromatin_job(job)
