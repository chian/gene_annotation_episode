"""Factory and ToolInfo wiring controls; no FBA execution or custody claim.

The registry below records explicit engineering declarations. Real factory and
library consumers freeze those declarations without importing Cobra, reading
declared software paths, acquiring a model or starting native work.
"""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_flux_balance_contracts import POLICY, STACK
from gene_annotation_episode.resource_tool_information import tool_information_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from test_scientific_process_library import independent_source


TOOL = 'perform_flux_balance_analysis'
ENVIRONMENT = {'version': 'flux_balance_execution_selection_v1',
    'environment_realization': 'operation_scoped_tmp_and_cache_v1'}


def software():
    base = '/declared-uninstalled/fba'
    def pin(path):
        return {'path': path, 'sha256': 'a' * 64, 'size_bytes': 0}
    return {'version': 'fba_software_v1', 'python': pin(base + '/python/bin/python'),
        'python_version': 'declared-python-version', 'python_home': base + '/python',
        'module_root': base + '/modules', 'dependency_roots': [base + '/deps'],
        'implementation_files': [pin(base + '/modules/gene_annotation_episode/' + name)
            for name in ('__init__.py', 'execution_contracts.py', 'flux_balance_contracts.py',
                'native_flux_balance_contracts.py', 'native_flux_balance_storage.py',
                'native_flux_balance_cobra_glpk.py', 'native_flux_balance_driver.py')],
        'runtime_files': [pin(base + '/python/lib/os.py'), pin(base + '/deps/cobra/__init__.py')],
        'distributions': [{'name': name, 'version': version} for name, version in STACK.items()],
        'solver_interface': 'optlang.glpk_interface',
        'solver_runtime_files': [pin(base + '/solver/libglpk.so')]}


def resources(tmp_path):
    return {'selected-local': {'kind': 'local',
        'workspace': str(tmp_path / 'uncreated-fba-workspace'), 'policy': deepcopy(POLICY),
        'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
            'operation': TOOL, 'mode': 'steady_state_linear_fba', 'software': software(),
            'model_formats': ['sbml', 'cobra_json']}]}}


def environments():
    return [{'resource_id': 'selected-local', 'binding_ordinal_0based': 0,
        'environment': deepcopy(ENVIRONMENT)}]


def factory(configured, table=(), *, protein_table=()):
    return ExecutionServiceFactory(configured, {}, 2, .25, .5,
        protein_structure_environments=protein_table, flux_balance_environments=table)


class RecordingRegistry:
    """An explicit configuration port, not an FBA normalizer or executor."""
    def __init__(self, *, expose='direct', bind=True):
        self.calls, self.expose, self.bind = [], expose, bind
        self._flux_balance_configuration = None

    def configure_flux_balance_resources(self, configured, table):
        self.calls.append(('flux_balance', deepcopy(configured), deepcopy(table)))
        self._flux_balance_configuration = ({'selected': deepcopy(table)}
            if table and self.bind else None)

    def catalog(self, scope=None):
        if self.expose == 'missing' or not self.calls or not self.calls[-1][2]:
            return {}
        return {TOOL: {'description': 'Engineering FBA configuration declaration.',
            'resources': 'local', 'instructions': 'Engineering configuration fixture.',
            'input_schema': obj({'mode': {'enum': ['inspect', 'edit', 'solve',
                'read_stored', 'calculate_saved']}}),
            'invocation_route': {'kind': self.expose}}}


class BothRegistries(RecordingRegistry):
    def configure_protein_structure_resources(self, configured, table):
        self.calls.append(('protein_structure', deepcopy(configured), deepcopy(table)))


@pytest.mark.parametrize('explicit_empty', [False, True])
def test_default_factory_record_is_exactly_legacy_and_roundtrips(tmp_path, explicit_empty):
    configured = resources(tmp_path)
    selected = factory(configured, []) if explicit_empty else factory(configured)
    expected = {'version': 'execution_service_factory_v1', 'resources': configured,
        'initial_information': {}, 'handoff_unit': 2, 'acquired_record_unit': .25,
        'monitoring_information_unit': .5, 'log_window_bytes': 8192,
        'log_roles': ['stdout', 'stderr'], 'monitor_outcome_page_size': 20}
    assert canonical(selected.as_record()) == canonical(expected)
    assert canonical(ExecutionServiceFactory.from_record(expected).as_record()) == canonical(expected)


def test_fba_environment_table_and_resources_are_detached_frozen_and_reconstructible(tmp_path):
    configured, table = resources(tmp_path), environments()
    selected = factory(configured, table)
    expected = selected.as_record()
    configured['selected-local']['native_flux_balance'][0]['software']['python_version'] = 'caller-mutated'
    table[0]['environment']['environment_realization'] = 'caller-mutated'
    assert selected.as_record() == expected
    assert plain(selected.flux_balance_environments)[0]['environment'] == ENVIRONMENT
    with pytest.raises(TypeError):
        selected.flux_balance_environments[0]['environment']['version'] = 'mutated'
    restored = ExecutionServiceFactory.from_record(expected)
    assert canonical(restored.as_record()) == canonical(expected)
    expected['flux_balance_environments'][0]['environment']['version'] = 'detached-record'
    assert plain(selected.flux_balance_environments)[0]['environment'] == ENVIRONMENT
    assert plain(restored.flux_balance_environments)[0]['environment'] == ENVIRONMENT


@pytest.mark.parametrize('table', [None, {}, 'not-a-table'])
def test_non_table_configuration_is_rejected(tmp_path, table):
    with pytest.raises(ValueError, match='explicit_flux_balance_environment_table_required'):
        factory(resources(tmp_path), table)


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan')])
def test_environment_table_requires_finite_json(tmp_path, value):
    table = environments()
    table[0]['environment']['unaccepted_nonfinite_fixture'] = value
    with pytest.raises(ValueError):
        factory(resources(tmp_path), table)


def test_missing_unselected_protein_port_does_not_skip_fba_configuration(tmp_path):
    configured, table = resources(tmp_path), environments()
    registry = RecordingRegistry()
    selected = factory(configured, table)
    selected.configure_tool_registry(registry)
    assert registry.calls == [('flux_balance', configured, table)]
    registry.calls[0][1]['selected-local']['kind'] = 'caller-mutated'
    registry.calls[0][2][0]['environment']['version'] = 'caller-mutated'
    selected.configure_tool_registry(registry)
    assert registry.calls[-1] == ('flux_balance', configured, table)
    assert plain(selected.flux_balance_environments) == table


def test_both_independent_families_receive_their_own_literal_tables(tmp_path):
    configured, table = resources(tmp_path), environments()
    protein = [{'resource_id': 'protein-resource', 'binding_ordinal_0based': 3,
        'environment': {'PYTHONPATH': '/declared-protein-modules'}}]
    registry = BothRegistries()
    selected = factory(configured, table, protein_table=protein)
    selected.configure_tool_registry(registry)
    assert registry.calls == [('protein_structure', configured, protein),
        ('flux_balance', configured, table)]
    record = selected.as_record()
    assert record['protein_structure_environments'] == protein
    assert record['flux_balance_environments'] == table


def test_selected_fba_environment_requires_an_actual_configuration_port(tmp_path):
    class ProteinOnly:
        def configure_protein_structure_resources(self, configured, table):
            pass
    with pytest.raises(ValueError, match='actual_flux_balance_tool_registry_required'):
        factory(resources(tmp_path), environments()).configure_tool_registry(ProteinOnly())
    with pytest.raises(ValueError, match='actual_flux_balance_tool_registry_required'):
        factory(resources(tmp_path), environments()).configure_tool_registry(object())
    factory(resources(tmp_path)).configure_tool_registry(object())


def test_empty_tables_still_configure_both_available_ports(tmp_path):
    configured = resources(tmp_path)
    registry = BothRegistries()
    factory(configured).configure_tool_registry(registry)
    assert registry.calls == [('protein_structure', configured, []), ('flux_balance', configured, [])]
    assert registry.catalog() == {} and registry._flux_balance_configuration is None


@pytest.mark.parametrize('case', ['legacy', 'missing_entry', 'commission_entry', 'unconfigured_entry', 'direct'])
def test_real_factory_suppresses_only_the_configured_direct_fba_route(tmp_path, case):
    configured = resources(tmp_path)
    registry = RecordingRegistry(expose={'missing_entry': 'missing', 'commission_entry': 'commission'}.get(case, 'direct'),
        bind=case != 'unconfigured_entry')
    table = () if case == 'legacy' else environments()
    with Store(tmp_path / 'store') as store:
        application = factory(configured, table)(store, run_id='engineering-fba-configuration',
            directory=tmp_path / 'run', tool_registry=registry)
        execution = application.role_credit_bindings['launch']['project'].__self__
        commissioned = execution.resource_tool_contracts()
        fba = [row for row in commissioned if row['name'] == TOOL]
        assert len(fba) == (0 if case == 'direct' else 1)
        assert any(row['name'] != TOOL for row in commissioned)
        if case == 'direct':
            joined = tool_information_contracts(registry.catalog(), commissioned)
            row, = [row for row in joined if row['name'] == TOOL]
            assert row['invocation_route'] == {'kind': 'direct'}
        else:
            assert fba[0]['invocation_route']['kind'] == 'commission'
        assert not store.list('source')
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_operations'").fetchone() is None
        assert not Path(configured['selected-local']['workspace']).exists()


def test_assembled_fba_only_configuration_refreshes_catalog_before_scientific_freeze(tmp_path):
    configured, table = resources(tmp_path), environments()
    registry = RecordingRegistry()
    independent_source(tmp_path / 'source')
    assert registry.catalog() == {}
    with Store(tmp_path / 'store') as store:
        application = bind_assembled_services(store, run_id='engineering-fba-assembly',
            directory=tmp_path / 'run', job_episodes=None, resource_estimator=None,
            source_directory=tmp_path / 'source', tool_catalog={}, tool_registry=registry,
            tool_retrieval={'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
                'model': {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}},
            scientific_child_roles=('scientific_process', 'literature', 'launch', 'results', 'monitor'),
            handoff_unit=2, acquired_record_unit=.25, monitoring_information_unit=.5,
            literature_outcome_page_size=7, monitor_outcome_page_size=9,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'),
            execution_resources=configured, initial_execution_information={},
            flux_balance_environments=table)
        frozen = ScientificToolLibrary(tmp_path / 'run' / 'scientific-tool-library')
        row, = frozen.resolve_invocations([{'name': TOOL, 'resources': 'local'}])
        assert row['invocation_route'] == {'kind': 'direct'}
        assert row['input_schema'] == registry.catalog()[TOOL]['input_schema']
        assert not any(row['name'] == TOOL for row in application.resource_tool_catalogs['local'])
        assert [name for name, _, _ in registry.calls] == ['flux_balance', 'flux_balance']
        assert all(selected == table for _, _, selected in registry.calls)
        assert not store.list('source')
        assert not Path(configured['selected-local']['workspace']).exists()
