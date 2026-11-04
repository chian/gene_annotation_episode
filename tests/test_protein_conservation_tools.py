"""Explicit allocation/profile controls; no alignment or numerical reruns."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.protein_conservation_tools import (
    normalize_protein_conservation_configuration,
    protein_conservation_tool_arguments_schema,
    validate_protein_conservation_configuration,
)


POLICY = dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3, wall_seconds=None)
PARAMETERS = dict(threads=1, randseed=1, perturb=0, perm='none', consiters=2, refineiters=100)
SOFTWARE = dict(path='/caller-selected/muscle', sha256='a' * 64, size_bytes=3587040)


def configuration():
    return normalize_protein_conservation_configuration(
        {'caller-local': dict(kind='local', policy=deepcopy(POLICY))},
        [dict(operation='analyze_protein_conservation', resource_id='caller-local',
            environment=dict(version='protein_conservation_execution_selection_v1',
                environment_realization='operation_scoped_tmp_and_cache_v1',
                software=deepcopy(SOFTWARE), parameters=deepcopy(PARAMETERS)))], policy=POLICY)


def arguments(mode):
    selection = dict(version='protein_conservation_selection_v1',
        native_rows=dict(row_indices=None, offset=0, limit=5),
        sites=dict(columns_0based=None, offset=0, limit=8))
    if mode == 'read_stored':
        return dict(mode=mode, result_ref='source_' + 'b' * 24, selection=selection)
    population = dict(kind='all_output_rows_and_columns', label='selected-output', completeness='unknown')
    if mode == 'calculate_saved':
        return dict(mode=mode, result_ref='source_' + 'b' * 24,
            population_request=population, selection=selection)
    return dict(mode=mode, input=dict(namespace='artifact', reference='artifact_' + 'c' * 64,
        format='fasta'), population_request=population, selection=selection)


def test_selection_preserves_exact_caller_operands_without_opening_paths(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('configuration must not inspect installation or execute software')
    monkeypatch.setattr('pathlib.Path.open', denied)
    selected = configuration()
    assert selected['resources'][0]['environment']['software'] == SOFTWARE
    assert selected['resources'][0]['environment']['parameters'] == PARAMETERS
    assert selected['policy'] == POLICY
    assert validate_protein_conservation_configuration(selected) == selected
    selected['resources'][0]['environment']['parameters']['threads'] = 2
    assert PARAMETERS['threads'] == 1


@pytest.mark.parametrize('change', ['missing', 'remote', 'allocation', 'duplicate', 'operation'])
def test_no_implicit_resource_or_allocation_substitution(change):
    selected = configuration()
    row = selected['resources'][0]
    resources = {row['resource_id']: row['resource']}
    environments = [dict(operation='analyze_protein_conservation', resource_id=row['resource_id'],
        environment=row['environment'])]
    if change == 'missing':
        resources.clear()
    elif change == 'remote':
        row['resource']['kind'] = 'hpc'
    elif change == 'allocation':
        row['resource']['policy']['memory_bytes'] -= 1
    elif change == 'duplicate':
        environments.append(deepcopy(environments[0]))
    else:
        environments[0]['operation'] = 'analyze_protein_phylogeny'
    with pytest.raises(ValueError):
        normalize_protein_conservation_configuration(resources, environments, policy=POLICY)


@pytest.mark.parametrize('native,saved', [(False, False), (True, False), (False, True), (True, True)])
def test_callable_modes_match_explicit_configuration(native, saved):
    selected = configuration() if native else normalize_protein_conservation_configuration({}, [], policy=POLICY)
    selected['saved_modes'] = saved
    schema = protein_conservation_tool_arguments_schema(selected)
    if not native and not saved:
        assert schema is None
        return
    Draft202012Validator.check_schema(schema)
    for mode in ('run_native', 'calculate_saved', 'read_stored'):
        allowed = native if mode == 'run_native' else saved
        if allowed:
            validate_schema(arguments(mode), schema)
        else:
            with pytest.raises(ValueError):
                validate_schema(arguments(mode), schema)


@pytest.mark.parametrize('field,value', [('threads', True), ('randseed', 0), ('perturb', 0.5),
    ('perm', 'all'), ('consiters', -1), ('refineiters', False)])
def test_native_parameter_grammar_is_the_drivers_shared_authority(field, value):
    selected = configuration()
    selected['resources'][0]['environment']['parameters'][field] = value
    with pytest.raises(ValueError):
        validate_protein_conservation_configuration(selected)


@pytest.mark.parametrize('operation,required', [
    ('protein_conservation_native', {'muscle_alignment_driver.py', 'native_flux_balance_storage.py'}),
    ('protein_conservation_result', {'protein_conservation_result_worker.py',
        'protein_conservation_result_contracts.py', 'phylogeny_formats.py',
        'phylogeny_format_contracts.py', 'phylogeny_calculation_contracts.py', 'phylogeny_calculators.py'}),
])
def test_selected_worker_preparation_covers_actual_source_and_dependency_files(operation, required):
    """Exercise preparation in the selected runtime without starting a worker."""
    from gene_annotation_episode.molecular_measurement_tools import _molecular_implementation_files
    files = _molecular_implementation_files(operation)
    assert files and len(files) == len(set(files))
    assert all(path.is_absolute() and path.is_file() for path in files)
    assert required <= {path.name for path in files}
    assert any(path.name == '__init__.py' and path.parent.name == 'jsonschema' for path in files)
    assert all('__pycache__' not in path.parts and path.suffix != '.pyc' for path in files)


def test_execution_factory_roundtrip_freezes_the_actual_registry_selection(tmp_path):
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    selected = configuration()
    row = selected['resources'][0]
    factory = ExecutionServiceFactory(resources={row['resource_id']: row['resource']},
        initial_information={}, handoff_unit=1, acquired_record_unit=1, monitoring_information_unit=1,
        protein_conservation_environments=(dict(operation='analyze_protein_conservation',
            resource_id=row['resource_id'], environment=row['environment']),),
        protein_conservation_saved_modes=True)
    record = factory.as_record()
    restored = ExecutionServiceFactory.from_record(record)
    assert restored.as_record() == record
    with Store(tmp_path / 'store') as store:
        registry = ToolRegistry(store, job_limits=POLICY)
        restored.configure_tool_registry(registry)
        assert registry._protein_conservation_configuration == dict(selected, saved_modes=True)
        restored.configure_tool_registry(registry)
        changed = deepcopy(record)
        changed['protein_conservation_environments'][0]['environment']['parameters']['threads'] = 2
        with pytest.raises(ValueError, match='protein_conservation_configuration_changed'):
            ExecutionServiceFactory.from_record(changed).configure_tool_registry(registry)
        assert registry._protein_conservation_configuration == dict(selected, saved_modes=True)
        assert restored.as_record() == record


def test_default_factory_record_and_saved_only_selection_need_no_native_profile(tmp_path):
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    factory = ExecutionServiceFactory(resources={'caller-local': dict(kind='local', policy=POLICY)},
        initial_information={}, handoff_unit=1, acquired_record_unit=1, monitoring_information_unit=1)
    record = factory.as_record()
    assert 'protein_conservation_environments' not in record
    assert 'protein_conservation_saved_modes' not in record
    record['protein_conservation_saved_modes'] = True
    with Store(tmp_path / 'store') as store:
        registry = ToolRegistry(store, job_limits=POLICY)
        ExecutionServiceFactory.from_record(record).configure_tool_registry(registry)
        selected = registry._protein_conservation_configuration
        assert selected['resources'] == [] and selected['saved_modes'] is True
        modes = protein_conservation_tool_arguments_schema(selected)['$defs']['Arguments']['oneOf']
        assert [item['properties']['mode']['const'] for item in modes] == ['calculate_saved', 'read_stored']
