"""Opt-in factory wiring using explicit engineering policy/configuration values."""
from copy import deepcopy
from dataclasses import fields
from pathlib import Path

import pytest

from gene_annotation_episode import assembled_case_policy
from gene_annotation_episode.assembled_case_policy import create_policy
from gene_annotation_episode.case_execution import PolicyBindings, _load_policy
from gene_annotation_episode.episode_application_services import service_binding
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.investigation_policy import create_policy as investigation_policy
from gene_annotation_episode.investigation_progress import ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_timing_information import NativeTimingInformation
from gene_annotation_episode.resource_episodes import ResourceEpisodes
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES


SPECIALIST_ROLES = (*ScientificProcessEpisodes.roles, *LiteratureEpisodes.roles,
    *ResourceEpisodes.roles, *MonitorEpisodes.roles)
REPLACED_FIELDS = {'episode_service_factory', 'episode_service_binding',
    'episode_service_inputs', 'annotation_child_roles', 'episode_record_receipts',
    'execution_planning_roles'}


def test_annotation_root_uses_explicit_axis_cutoffs_without_repricing_child_tasks():
    from gene_annotation_episode.numerical import AnnotationAxisYieldController
    from gene_annotation_episode.root_axis_scalars import AXES, VERSION
    supplied = parameters()['policy']
    supplied['annotation_support'] = {'version': VERSION}
    cutoffs = {axis: (index + 1) / 1000 for index, axis in enumerate(AXES)}
    supplied['root_task'] = {'kind': 'annotation_axis_credit', 'cutoffs': cutoffs}
    policy = investigation_policy(supplied, episode_roles=SPECIALIST_ROLES)
    assert policy.project_task_credit.task_credit
    assert policy.project_scientific_child_credit is None
    assert not policy.project_annotation_score.task_credit
    controller = policy.controller_factory((('annotation', 'root'),),
        {'mode': 'annotation_axis_credit', 'arms': []})
    assert type(controller) is AnnotationAxisYieldController
    assert controller.cutoffs == cutoffs
    assert controller.cutoffs['A105'] != controller.cutoffs['A106']
    original = dict(cutoffs)
    cutoffs['A105'] = 99
    assert controller.cutoffs == original
    with pytest.raises(ValueError, match='scientific_child_yield_requires_original_task_credit'):
        policy.controller_factory((('annotation', 'root'), ('literature', 'child')), 3)


def parameters():
    # These units, costs and lists exercise interfaces; none adopts a real profile.
    return {'policy': {'scientific_progress': {'finding_unit': 7,
            'initial_known_record_refs': [], 'loss_preview_size': 5},
        'operational': {'registry_ref': 'engineering-registry',
            'handoff_unit': 3.25, 'acquired_record_unit': .125},
        'monitoring': {'information_unit': .5, 'include_handoff_checks': True},
        'controller': {'cost': .003, 'window_size': 8, 'subsample_size': 4,
            'uncertainty_alpha': .05,
            'cost_by_role': {**{role: (index+1)/100 for index, role in enumerate(SPECIALIST_ROLES)},
                'improvement': .11, 'job_launch': .12, 'job_monitor': .13,
                'job_results': .14}}},
        'services': {'version': 'assembled_case_services_v1',
            'source_directory': str(PUBLICATION), 'tool_retrieval': deepcopy(RETRIEVAL),
            'scientific_child_roles': list(ROOT_ROLES),
            'annotation_child_roles': list(ROOT_ROLES),
            'execution_planning_roles': ['annotation', 'scientific_process'],
            'handoff_unit': 2.75, 'acquired_record_unit': .125,
            'monitoring_information_unit': .375, 'literature_outcome_page_size': 7,
            'monitor_outcome_page_size': 13, 'log_window_bytes': 123,
            'log_roles': ['native_stderr', 'native_text']}}


def test_factory_replaces_only_explicit_setup_ports_and_keeps_original_policy_objects(monkeypatch):
    supplied, calls = parameters(), []

    def original_policy(value, *, episode_roles):
        assert value is supplied['policy']
        assert episode_roles == SPECIALIST_ROLES
        base = investigation_policy(value, episode_roles=episode_roles)
        calls.append(base)
        return base

    monkeypatch.setattr(assembled_case_policy, 'investigation_policy', original_policy)
    policy = create_policy(supplied)
    base, = calls
    assert type(policy) is PolicyBindings
    for field in fields(PolicyBindings):
        if field.name not in REPLACED_FIELDS:
            assert getattr(policy, field.name) is getattr(base, field.name)
    assert type(policy.project_task_credit) is ScientificFindingProgress
    assert policy.project_scientific_child_credit is None
    assert policy.project_annotation_score is None
    assert type(policy.native_timing_information) is NativeTimingInformation
    assert policy.native_timing_information.information_unit == .5
    assert policy.initial_known_record_refs is supplied['policy']['scientific_progress']['initial_known_record_refs']
    assert policy.episode_service_binding == supplied['services']
    assert policy.episode_service_binding is not supplied['services']
    assert policy.episode_service_inputs == 'actual_tool_catalog_v1'
    assert policy.annotation_child_roles == ROOT_ROLES
    assert policy.execution_planning_roles == ('annotation', 'scientific_process')
    assert policy.episode_record_receipts is True
    assert policy.task_credit_definition['policy']['finding_unit'] == 7
    assert policy.annotation_score_definition is None
    assert policy.controller_definition == base.controller_definition
    for role in ('annotation', 'job_launch', *SPECIALIST_ROLES):
        actual = policy.controller_factory(((role, 'engineering'),), 11)
        original = base.controller_factory(((role, 'engineering'),), 11)
        assert actual.cost == original.cost == supplied['policy']['controller']['cost_by_role'].get(role, .003)
        assert actual.initial_credit == original.initial_credit == 11
        assert actual.settings.as_record() == original.settings.as_record()


def test_setup_closure_passes_same_actual_resources_and_catalog_and_copied_original_operands(monkeypatch):
    supplied = parameters()
    expected = deepcopy(supplied['services'])
    policy = create_policy(supplied)
    supplied['services']['handoff_unit'] = 99
    supplied['services']['tool_retrieval']['model']['model'] = 'changed-original'
    policy.episode_service_binding['acquired_record_unit'] = 98
    policy.episode_service_binding['log_roles'].clear()
    store, jobs, estimator, catalog, sentinel = (object() for _ in range(5))
    captured = []

    def setup(actual_store, **kwargs):
        captured.append((actual_store, kwargs))
        return sentinel

    monkeypatch.setattr(assembled_case_policy, 'bind_assembled_services', setup)
    assert policy.episode_service_factory(store, run_id='engineering-run', directory=Path('run'),
        job_episodes=jobs, resource_estimator=estimator, tool_catalog=catalog) is sentinel
    actual_store, operands = captured[0]
    assert actual_store is store
    assert operands['job_episodes'] is jobs and operands['resource_estimator'] is estimator
    assert operands['tool_catalog'] is catalog
    assert operands == {'run_id': 'engineering-run', 'directory': Path('run'),
        'job_episodes': jobs, 'resource_estimator': estimator, 'tool_catalog': catalog,
        'source_directory': Path(expected['source_directory']),
        'tool_retrieval': expected['tool_retrieval'],
        'scientific_child_roles': tuple(expected['scientific_child_roles']),
        **{key: expected[key] for key in ('handoff_unit', 'acquired_record_unit',
            'monitoring_information_unit', 'literature_outcome_page_size',
            'monitor_outcome_page_size', 'log_window_bytes')},
        'log_roles': tuple(expected['log_roles'])}
    with pytest.raises(TypeError, match='tool_catalog'):
        policy.episode_service_factory(store, run_id='engineering-run', directory=Path('run'),
            job_episodes=jobs, resource_estimator=estimator)


def test_wired_setup_keeps_scientific_policy_and_passes_original_registry(monkeypatch, tmp_path):
    supplied = parameters()
    supplied['services'].update(version='assembled_case_services_v2',
        execution_resources={'here': {'kind': 'local', 'workspace': str(tmp_path),
            'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}, 'ebi': {'kind': 'hmmer_api'}},
        initial_execution_information={})
    original = deepcopy(supplied)
    policy = create_policy(supplied)
    assert policy.episode_service_inputs == 'actual_tool_registry_v1'
    assert policy.task_credit_definition == investigation_policy(
        original['policy'], episode_roles=SPECIALIST_ROLES).task_credit_definition
    captured = []
    monkeypatch.setattr(assembled_case_policy, 'bind_assembled_services',
        lambda store, **kwargs: captured.append((store, kwargs)))
    store, registry, catalog = object(), object(), object()
    policy.episode_service_factory(store, run_id='fixture', directory=tmp_path,
        job_episodes=None, resource_estimator=None, tool_catalog=catalog, tool_registry=registry)
    actual_store, operands = captured[0]
    assert actual_store is store and operands['tool_registry'] is registry
    assert operands['tool_catalog'] is catalog
    assert operands['execution_resources'] == original['services']['execution_resources']
    assert operands['initial_execution_information'] == {}
    assert service_binding(policy.episode_service_factory, policy.episode_service_binding,
        inputs=policy.episode_service_inputs)['inputs'] == 'actual_tool_registry_v1'


def test_contract_discovery_profile_survives_policy_capture_and_rejects_unknown_profile(monkeypatch, tmp_path):
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
    supplied = parameters()
    supplied['services']['scientific_contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    policy = create_policy(supplied)
    supplied['services']['scientific_contract_information_profile'] = 'changed'
    captured = []
    monkeypatch.setattr(assembled_case_policy, 'bind_assembled_services',
        lambda store, **kwargs: captured.append(kwargs))
    policy.episode_service_factory(object(), run_id='profile-fixture', directory=tmp_path,
        job_episodes=object(), resource_estimator=object(), tool_catalog={})
    assert captured[0]['scientific_contract_information_profile'] == CONTRACT_INFORMATION_PROFILE
    with pytest.raises(ValueError, match='contract_information_profile'):
        create_policy(supplied)


def test_snapshot_loader_preserves_exact_opt_in_definition_and_original_policy_values(tmp_path):
    supplied = parameters()
    policy, recorded = _load_policy(tmp_path, Path(assembled_case_policy.__file__), supplied, resume=False)
    expected = service_binding(policy.episode_service_factory, policy.episode_service_binding,
        inputs='actual_tool_catalog_v1')
    assert recorded['parameters'] == supplied
    assert expected == {'version': 'episode_application_services_v2',
        'factory': 'fixed_gene_policy_'+recorded['source_sha256']+'.create_policy.<locals>.setup',
        'definition': supplied['services'], 'inputs': 'actual_tool_catalog_v1'}
    assert recorded['episode_application_services'] == expected
    assert recorded['annotation_child_roles'] == list(ROOT_ROLES)
    assert recorded['execution_planning_roles'] == ['annotation', 'scientific_process']
    assert recorded['initial_known_record_refs'] == supplied['policy']['scientific_progress']['initial_known_record_refs']
    restored, replay = _load_policy(tmp_path, None, None, resume=True)
    assert replay == recorded
    assert restored.controller_definition == policy.controller_definition
    assert restored.task_credit_definition == policy.task_credit_definition
    assert restored.annotation_score_definition == policy.annotation_score_definition
    assert restored.native_timing_information.as_record() == policy.native_timing_information.as_record()


@pytest.mark.parametrize('mode', ['received_findings', 'annotation_accounts', None])
def test_factory_rejects_role_wide_scientific_credit(mode):
    supplied = parameters()
    supplied['policy']['scientific_child'] = mode
    before = deepcopy(supplied)
    with pytest.raises(ValueError, match='role_wide_scientific_child_credit_policy_retired'):
        create_policy(supplied)
    assert supplied == before


@pytest.mark.parametrize('missing', ['finding_unit', 'initial_known_record_refs', 'loss_preview_size'])
def test_available_finding_calculation_configuration_stays_explicit(missing):
    supplied = parameters()
    del supplied['policy']['scientific_progress'][missing]
    with pytest.raises(ValueError, match='explicit_scientific_progress_configuration_required'):
        create_policy(supplied)


@pytest.mark.parametrize('missing', tuple(parameters()['services']))
def test_all_assembled_service_configuration_fields_are_required(missing):
    supplied = parameters()
    del supplied['services'][missing]
    with pytest.raises(ValueError, match='explicit_assembled_services_configuration_required'):
        create_policy(supplied)


@pytest.mark.parametrize(('field', 'value', 'message'), [
    ('annotation_child_roles', ['scientific_process', 'literature', 'launch', 'monitor', 'results', 'job_launch'],
        'assembled_scientific_and_root_entry_roles_must_match'),
    ('scientific_child_roles', ['scientific_process', 'literature'],
        'assembled_scientific_and_root_entry_roles_must_match'),
    ('annotation_child_roles', [], 'explicit_unique_assembled_episode_roles_required'),
    ('execution_planning_roles', ['annotation'], 'assembled_scientific_planning_roles_required'),
    ('execution_planning_roles', ['annotation', 'annotation'], 'explicit_unique_assembled_episode_roles_required'),
    ('source_directory', '', 'explicit_scientific_publication_directory_required'),
    ('tool_retrieval', None, 'explicit_scientific_tool_retrieval_configuration_required'),
    ('tool_retrieval', {'mode': 'semantic_fast_v1'}, 'scientific_tool_retrieval_configuration_invalid'),
    ('log_roles', 'native_text', 'explicit_assembled_log_roles_required'),
])
def test_factory_validates_explicit_shape_without_inventing_replacement_values(field, value, message):
    supplied = parameters()
    supplied['services'][field] = value
    with pytest.raises((ValueError, TypeError), match=message):
        create_policy(supplied)


def test_nonfinite_service_definition_is_rejected():
    supplied = parameters()
    supplied['services']['monitoring_information_unit'] = float('nan')
    with pytest.raises(ValueError):
        create_policy(supplied)


def test_optional_existing_policy_role_port_changes_only_allowed_cost_keys():
    supplied = parameters()['policy']
    with pytest.raises(ValueError, match='controller_cost_by_role_requires_known_episode_roles'):
        investigation_policy(supplied)
    policy = investigation_policy(supplied, episode_roles=SPECIALIST_ROLES)
    assert policy.controller_definition['cost_by_role'] == supplied['controller']['cost_by_role']
    supplied['controller']['cost_by_role']['unbound_role'] = .2
    with pytest.raises(ValueError, match='controller_cost_by_role_requires_known_episode_roles'):
        investigation_policy(supplied, episode_roles=SPECIALIST_ROLES)


@pytest.mark.parametrize('roles', [None, [], ['literature'], ('literature', 'literature'), ('',), (1,)])
def test_optional_role_port_requires_explicit_tuple_with_unique_nonempty_names(roles):
    with pytest.raises(ValueError, match='explicit_unique_episode_roles_required'):
        investigation_policy(parameters()['policy'], episode_roles=roles)


def test_original_policy_call_and_empty_optional_roster_keep_identical_definitions_and_costs():
    supplied = parameters()['policy']
    supplied['controller']['cost_by_role'] = {'job_launch': .12}
    original = investigation_policy(supplied)
    explicit_empty = investigation_policy(supplied, episode_roles=())
    for name in ('task_credit_definition', 'scientific_child_credit_definition',
                 'job_credit_definition', 'monitoring_credit_definition',
                 'controller_definition', 'annotation_score_definition'):
        assert getattr(original, name) == getattr(explicit_empty, name)
    assert original.controller_factory((('annotation', 'engineering'),), 3).cost == .003
    assert explicit_empty.controller_factory((('job_launch', 'engineering'),), 3).cost == .12
    assert original.episode_service_factory is original.episode_service_binding is None
    assert original.episode_service_inputs is original.annotation_child_roles is None
    assert original.execution_planning_roles is None and original.episode_record_receipts is False
