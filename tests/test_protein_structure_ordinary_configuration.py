"""Configuration and closed-dispatch controls, without installed protein software.

Software paths and hashes below are declared, uninstalled engineering metadata.
The small Workflow uses an existing literal fixture reader, not a protein worker.
It proves real closed-owner dispatch/replay behavior; archived336 migration and
native protein execution are separate evidence.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_protein_structure_contracts import (
    DRIVER_MODULE, POLICY, WORKER_MODULE,
)
from gene_annotation_episode.protein_structure_tools import (
    PROTEIN_STRUCTURE_TOOLS, normalize_protein_structure_configuration,
    protein_structure_tool_catalog,
)
from gene_annotation_episode.resource_tool_information import tool_information_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_library import independent_source
from test_scientific_process_runtime import Scenario, action


def forbidden(*args, **kwargs):
    raise AssertionError('configuration must not execute or probe native software')


def software():
    return {'python_executable': '/declared-uninstalled/protein/python',
        'python_sha256': 'a' * 64, 'python_version': 'declared-python-version',
        'driver_module': DRIVER_MODULE, 'worker_module': WORKER_MODULE,
        'implementation_files': [
            {'module': DRIVER_MODULE, 'sha256': 'b' * 64},
            {'module': WORKER_MODULE, 'sha256': 'c' * 64}],
        'numpy_version': 'declared-numpy-version',
        'biopython_version': 'declared-biopython-version',
        'implementation': 'gene_annotation_episode_corrected_protein_structure_v1',
        'algorithm': 'unweighted_proper_rigid_ca_svd_v1'}


def resources(tmp_path):
    return {'selected-local': {'kind': 'local',
        'workspace': str(tmp_path / 'uncreated-protein-workspace'),
        'policy': deepcopy(POLICY), 'native_protein_structure': [
            {'operation': operation, 'scientific_mode': mode, 'software': software()}
            for operation, mode in [('inspect', None), ('extract_sequence', None),
                ('compare', 'fit_then_evaluate_ca'),
                ('compare', 'evaluate_declared_transform_ca')]]}}


def environments(ordinals=(0, 1, 2, 3)):
    return [{'resource_id': 'selected-local', 'binding_ordinal_0based': ordinal,
        'environment': {'PYTHONPATH': '/declared-uninstalled/protein/modules',
            'PYTHONDONTWRITEBYTECODE': '1', 'PROTEIN_FIXTURE_SETTING': 'literal'}}
        for ordinal in ordinals]


def factory(configured, table=()):
    return ExecutionServiceFactory(configured, {}, 2, .25, .5,
        protein_structure_environments=table)


def registry(store):
    return ToolRegistry(store, job_limits=deepcopy(POLICY))


def assert_no_work(store, configured):
    assert not store.list('source')
    assert store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0
    assert not Path(configured['selected-local']['workspace']).exists()


@pytest.mark.parametrize('table', [None, [], ()], ids=['none', 'empty-list', 'empty-tuple'])
def test_missing_environment_exposes_no_ordinary_protein_operation(tmp_path, table):
    configured = resources(tmp_path)
    assert normalize_protein_structure_configuration(
        configured, table, LocalJobPolicy(**POLICY)) is None
    assert protein_structure_tool_catalog(None) == {}
    with Store(tmp_path / 'store') as store:
        tools = registry(store)
        tools.configure_protein_structure_resources(configured, table)
        assert not set(PROTEIN_STRUCTURE_TOOLS).intersection(tools.catalog())
        assert_no_work(store, configured)


@pytest.mark.parametrize('ordinal', [False, True, 0.0, -1, '0', 4, None])
def test_binding_ordinals_require_actual_in_range_integers(tmp_path, ordinal):
    table = environments((0,))
    table[0]['binding_ordinal_0based'] = ordinal
    with pytest.raises(ValueError, match='protein_structure_binding_selection_invalid'):
        normalize_protein_structure_configuration(
            resources(tmp_path), table, LocalJobPolicy(**POLICY))


@pytest.mark.parametrize('fault', ['duplicate', 'foreign-resource', 'nonlocal',
    'policy', 'relative-workspace', 'extra-field', 'missing-environment',
    'null-environment', 'managed-environment'])
def test_invalid_explicit_selection_fails_before_work(tmp_path, monkeypatch, fault):
    configured, table = resources(tmp_path), environments((0,))
    if fault == 'duplicate':
        table.append(deepcopy(table[0]))
    elif fault == 'foreign-resource':
        table[0]['resource_id'] = 'not-configured'
    elif fault == 'nonlocal':
        configured['selected-local']['kind'] = 'hpc'
    elif fault == 'policy':
        configured['selected-local']['policy']['memory_bytes'] += 1
    elif fault == 'relative-workspace':
        configured['selected-local']['workspace'] = 'relative-workspace'
    elif fault == 'extra-field':
        table[0]['fallback_python'] = '/invented'
    elif fault == 'missing-environment':
        del table[0]['environment']
    elif fault == 'null-environment':
        table[0]['environment'] = None
    else:
        table[0]['environment']['HOME'] = '/forbidden-managed-path'
    monkeypatch.setattr('gene_annotation_episode.protein_structure_tools.run_cancellable_native', forbidden)
    monkeypatch.setattr('gene_annotation_episode.protein_structure_tools.prepare_selected_local_protein_structure', forbidden)
    with pytest.raises(ValueError):
        normalize_protein_structure_configuration(configured, table, LocalJobPolicy(**POLICY))
    assert not (tmp_path / 'uncreated-protein-workspace').exists()


def test_selected_software_environment_and_literal_order_are_detached(tmp_path):
    configured, table = resources(tmp_path), environments((3, 0))
    before = deepcopy((configured, table))
    selected = normalize_protein_structure_configuration(configured, table, LocalJobPolicy(**POLICY))
    assert [row['binding_ordinal_0based'] for row in selected['bindings']] == [0, 3]
    for row in selected['bindings']:
        ordinal = row['binding_ordinal_0based']
        assert row['software'] == before[0]['selected-local']['native_protein_structure'][ordinal]['software']
        assert row['environment'] == before[1][1 if ordinal == 0 else 0]['environment']
        assert row['workspace'] == configured['selected-local']['workspace']
    configured['selected-local']['native_protein_structure'][0]['software']['numpy_version'] = 'changed'
    table[1]['environment']['PROTEIN_FIXTURE_SETTING'] = 'changed'
    assert selected['bindings'][0]['software']['numpy_version'] == 'declared-numpy-version'
    assert selected['bindings'][0]['environment']['PROTEIN_FIXTURE_SETTING'] == 'literal'


def test_actual_registry_factory_is_idempotent_and_rejects_configuration_conflict(tmp_path, monkeypatch):
    configured, table = resources(tmp_path), environments((0,))
    selected_factory = factory(configured, table)
    with Store(tmp_path / 'store') as store:
        tools = registry(store)
        monkeypatch.setattr('gene_annotation_episode.protein_structure_tools.run_cancellable_native', forbidden)
        monkeypatch.setattr('gene_annotation_episode.protein_structure_tools.prepare_selected_local_protein_structure', forbidden)
        selected_factory.configure_tool_registry(tools)
        frozen = canonical(tools._protein_structure_configuration)
        selected_factory.configure_tool_registry(tools)
        configured['selected-local']['native_protein_structure'][0]['software']['python_version'] = 'caller-mutated'
        table[0]['environment']['PROTEIN_FIXTURE_SETTING'] = 'caller-mutated'
        selected_factory.configure_tool_registry(tools)
        assert canonical(tools._protein_structure_configuration) == frozen
        conflicting = plain(selected_factory.protein_structure_environments)
        conflicting[0]['environment']['PROTEIN_FIXTURE_SETTING'] = 'different'
        with pytest.raises(ValueError, match='protein_structure_configuration_changed'):
            factory(plain(selected_factory.resources), conflicting).configure_tool_registry(tools)
        assert canonical(tools._protein_structure_configuration) == frozen
        assert_no_work(store, plain(selected_factory.resources))


@pytest.mark.parametrize('explicit_empty', [False, True], ids=['absent', 'explicit-empty'])
def test_old_factory_record_omits_empty_option_exactly(tmp_path, explicit_empty):
    configured = resources(tmp_path)
    selected = factory(configured, []) if explicit_empty else factory(configured)
    expected = {'version': 'execution_service_factory_v1', 'resources': configured,
        'initial_information': {}, 'handoff_unit': 2, 'acquired_record_unit': .25,
        'monitoring_information_unit': .5, 'log_window_bytes': 8192,
        'log_roles': ['stdout', 'stderr'], 'monitor_outcome_page_size': 20}
    assert canonical(selected.as_record()) == canonical(expected)
    assert canonical(ExecutionServiceFactory.from_record(expected).as_record()) == canonical(expected)


def test_explicit_environment_requires_actual_configurable_registry(tmp_path):
    with pytest.raises(ValueError, match='actual_protein_structure_tool_registry_required'):
        factory(resources(tmp_path), environments((0,))).configure_tool_registry(object())
    factory(resources(tmp_path)).configure_tool_registry(object())


@pytest.mark.parametrize('ordinals', [(0,), (1,), (2,), (0, 1, 2, 3)])
def test_configured_direct_names_have_one_owner_and_others_keep_commission(tmp_path, ordinals):
    configured = resources(tmp_path)
    with Store(tmp_path / 'store') as store:
        tools = registry(store)
        application = factory(configured, environments(ordinals))(store,
            run_id='engineering-configuration', directory=tmp_path / 'run', tool_registry=tools)
        execution = application.role_credit_bindings['launch']['project'].__self__
        direct, commissioned = tools.catalog(), execution.resource_tool_contracts()
        joined = tool_information_contracts(direct, commissioned)
        rows = {row['name']: row for row in joined if row['name'] in PROTEIN_STRUCTURE_TOOLS}
        selected_names = set(protein_structure_tool_catalog(tools._protein_structure_configuration))
        assert set(rows) == set(PROTEIN_STRUCTURE_TOOLS)
        assert len([row for row in joined if row['name'] in PROTEIN_STRUCTURE_TOOLS]) == 3
        for name, row in rows.items():
            assert row['invocation_route']['kind'] == ('direct' if name in selected_names else 'commission')
            assert (name in direct) == (name in selected_names)
            assert (name in {entry['name'] for entry in commissioned}) == (name not in selected_names)
        assert_no_work(store, configured)


def test_assembled_configuration_refreshes_actual_catalog_before_freezing(tmp_path):
    configured, table = resources(tmp_path), environments((0,))
    independent_source(tmp_path / 'source')
    with Store(tmp_path / 'store') as store:
        tools = registry(store)
        before = tools.catalog()
        assert not set(PROTEIN_STRUCTURE_TOOLS).intersection(before)
        application = bind_assembled_services(store, run_id='engineering-assembly',
            directory=tmp_path / 'run', job_episodes=None, resource_estimator=None,
            source_directory=tmp_path / 'source', tool_catalog=before, tool_registry=tools,
            tool_retrieval={'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
                'model': {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}},
            scientific_child_roles=('scientific_process', 'literature', 'launch', 'results', 'monitor'),
            handoff_unit=2, acquired_record_unit=.25, monitoring_information_unit=.5,
            literature_outcome_page_size=7, monitor_outcome_page_size=9,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'),
            execution_resources=configured, initial_execution_information={},
            protein_structure_environments=table)
        frozen = ScientificToolLibrary(tmp_path / 'run' / 'scientific-tool-library')
        selection = [{'name': 'inspect_protein_structure', 'resources': 'local'}]
        row, = frozen.resolve_invocations(selection)
        assert row['invocation_route'] == {'kind': 'direct'}
        assert row['input_schema'] == tools.catalog()['inspect_protein_structure']['input_schema']
        assert not any(entry['name'] == 'inspect_protein_structure'
            for entry in application.resource_tool_catalogs['local'])
        assert_no_work(store, configured)


@pytest.mark.parametrize('change', ['schema', 'instructions'])
def test_live_resolution_rejects_a_stale_frozen_direct_contract(tmp_path, change):
    selected = normalize_protein_structure_configuration(
        resources(tmp_path), environments((0,)), LocalJobPolicy(**POLICY))
    original = protein_structure_tool_catalog(selected)
    library = ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=original, tool_info=True)
    selection = [{'name': 'inspect_protein_structure', 'resources': 'local'}]
    assert library.resolve_invocations(selection, original)[0]['invocation_route'] == {'kind': 'direct'}
    changed = deepcopy(original)
    if change == 'schema':
        changed['inspect_protein_structure']['input_schema']['description'] = 'A changed live contract'
    else:
        changed['inspect_protein_structure']['instructions'] += ' Changed live instructions.'
    with pytest.raises(ValueError, match='scientific_tool_contract_changed:inspect_protein_structure:local'):
        library.resolve_invocations(selection, changed)


def test_actual_closed_owner_replays_recorded_result_but_cannot_dispatch_same_mechanics(tmp_path, monkeypatch):
    """A real tiny closure, not a callback claiming an invented closed owner."""
    with Store(tmp_path / 'store') as store:
        case = Scenario(tmp_path, store)
        case.factory = lambda path, initial: FixtureController(str(path), initial, 1)
        provider = ScriptedProvider([case.commission(),
            action('fixture.inspect', {'value': 2}, 'qualified')])
        workflow = case.workflow(provider)
        children, original_selected = [], workflow.selected

        def observe_selection(source, selection, index):
            unit = original_selected(source, selection, index)
            if selection.get('kind') == 'episode_child' and selection.get('role') == 'scientific_process':
                children.append(unit.child)
            return unit

        monkeypatch.setattr(workflow, 'selected', observe_selection)
        root = workflow.build('annotation', 'root', 'Resolve the literal engineering contrast', case.scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        child, = children
        context = workflow.binding_context(child.source)
        binding = workflow.scientific_process_binding
        mechanics = deepcopy(binding.as_record())
        assert plain(context.request['message']['scientific_process']['mechanics_binding']) == mechanics
        assert workflow.services.scientific_closed_request(context) == child.request.as_record()
        assert len(provider.contexts) == 2 and len(case.tools.calls) == 1
        original_catalog = case.tools.catalog()
        changed = deepcopy(original_catalog)
        changed[0]['input_schema']['properties']['value']['maximum'] = 1
        monkeypatch.setattr(case.tools, 'catalog', lambda scope=None: deepcopy(changed))
        assert binding.as_record() == mechanics
        # Ordinary live resolution rejects the changed contract, but closed
        # inspection uses the exact already-dispatched contract from its library.
        with pytest.raises(ValueError, match='scientific_tool_contract_changed'):
            binding._tool_resolution_for(plain(context.assignment['selection']), plain(context.scope))
        binding.validate_context(context)
        inspected = next(row for row in binding.catalog(context) if row['name'] == 'fixture.inspect')
        assert inspected['input_schema'] == original_catalog[0]['input_schema']
        tables = ('runtime_actions', 'runtime_model_calls', 'runtime_observations',
            'runtime_episodes', 'runtime_forms')

        def rows():
            return {name: [tuple(row) for row in store.db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
                for name in tables}

        before, calls = rows(), deepcopy(case.tools.calls)
        with pytest.raises(ValueError, match='scientific_execution_identity_mismatch'):
            binding.validate_execution_context(context)
        with pytest.raises(ValueError, match='scientific_execution_identity_mismatch'):
            asyncio.run(workflow.execute(child.source, 'fixture.inspect', {'value': 2},
                decision_index=99, operation_key='closed-new-work'))
        with pytest.raises(ValueError, match='scientific_execution_identity_mismatch'):
            asyncio.run(child.source.execute(action('fixture.inspect', {'value': 2})['selection'], 99))
        assert rows() == before and case.tools.calls == calls
        old = store.db.execute('SELECT action,result FROM runtime_actions WHERE episode_id=? AND decision_index=0',
            (child.source.episode_id,)).fetchone()
        assert json.loads(old['result'])['status'] == 'completed'
        asyncio.run(child.source.execute(json.loads(old['action']), 0))
        assert rows() == before and case.tools.calls == calls
        assert len(provider.contexts) == 2
