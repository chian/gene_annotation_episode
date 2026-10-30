"""Actual new caller with isolated operands; no model, public HTTP or native work."""
from copy import deepcopy
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionError

from gene_annotation_episode import api_planning_case_policy as caller, assembled_case_policy
from gene_annotation_episode.api_execution_planning import ApiExecutionPlanner
from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
from gene_annotation_episode.api_timing_records import ApiTimingBinding, ApiTimingLedger
from gene_annotation_episode.case_execution import PolicyBindings, _load_policy
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.public_search_operations import ProviderJobOperations, PublicSearchPorts
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.tools import ToolRegistry
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES
from test_hmmer_api_operations import FixtureClient, registry
from test_resource_service_setup import forbidden, resources


# Original adopted numeric operands, with only isolated native identity and
# an empty fixture baseline replacing the two caller-output bindings.
_POLICY = json.loads(r'''{"controller": {"cost": 0.001, "cost_by_role": {"job_launch": 0.1, "job_monitor": 0.1}, "subsample_size": 4, "uncertainty_alpha": 0.05, "window_size": 8}, "monitoring": {"include_handoff_checks": true, "information_unit": 1}, "operational": {"acquired_record_unit": 1, "handoff_unit": 1, "registry_ref": "execution_registry_fixture"}, "scientific": {"applicability_weights": {"contextual": 0.35, "direct": 1.0, "incomparable": 0.0, "scope_limited": 0.2, "transfer": 0.6}, "axis_weights": {"biological_context": 1.0, "comparative": 1.0, "discrimination": 1.0, "empirical": 1.0, "mechanistic": 1.0}, "epsilon": 0.25, "observation_axes": [["assay_report", "empirical"], ["biochemical_assay", "empirical"], ["genetic_phenotype", "empirical"], ["growth_assay", "empirical"], ["read_support", "empirical"], ["alignment", "comparative"], ["profile_match", "comparative"], ["comparison", "comparative"], ["gene_prediction", "comparative"], ["structure_match", "mechanistic"], ["mechanism", "mechanistic"], ["reaction_context", "mechanistic"], ["context_measurement", "biological_context"], ["context", "biological_context"], ["taxonomy_assignment", "biological_context"], ["sequence_composition", "biological_context"]], "relation_weights": {"does_not_discriminate": 0.0, "mixed": 0.5, "strengthens": 1.0, "weakens": 1.0}, "scale": 100.0, "target_weights": {}, "unresolved_factor": 0.5}, "scientific_child": "received_findings", "scientific_progress": {"finding_unit": 1, "initial_known_record_refs": [], "loss_preview_size": 24}}''')
MARKER = {'version': 'hmmer_api_execution_planning_v1',
    'callable': 'execution.estimate', 'target': 'public.hmmer.search'}


def parameters(tmp_path, *, client=None):
    owner = (registry(client) if client is not None else {
        'version': 'public_search_registry_v1', 'registry_ref': 'execution_registry_fixture',
        'resource_id': 'fixture_hmmer_resource', 'provider': 'hmmer',
        'client_binding_sha256': 'a'*64})
    timing = ApiTimingBinding(ledger_path=tmp_path/'timing.sqlite',
        history_path=tmp_path/'history.sqlite', resource_id=owner['resource_id'],
        monitoring_information_unit=1)
    return {'policy': deepcopy(_POLICY), 'services': {
        'version': caller.VERSION, 'source_directory': str(PUBLICATION),
        'tool_retrieval': deepcopy(RETRIEVAL), 'scientific_child_roles': list(ROOT_ROLES),
        'annotation_child_roles': list(ROOT_ROLES),
        'execution_planning_roles': ['annotation', 'scientific_process'],
        'handoff_unit': 1, 'acquired_record_unit': 1, 'monitoring_information_unit': 1,
        'literature_outcome_page_size': 8, 'monitor_outcome_page_size': 32,
        'log_window_bytes': 16384, 'log_roles': ['native_stderr', 'native_text'],
        'public_search_registry': owner, 'api_timing': timing.as_record(),
        'api_execution_planning': deepcopy(MARKER)}}


def test_original_operands_and_full_definition_are_preserved(tmp_path, monkeypatch):
    supplied = parameters(tmp_path)
    before = deepcopy(supplied)
    bases, base_inputs = [], []
    original = assembled_case_policy.create_policy
    def actual_base(value):
        base_inputs.append(deepcopy(value))
        base = original(value)
        bases.append(base)
        return base
    monkeypatch.setattr(assembled_case_policy, 'create_policy', actual_base)
    policy = caller.create_policy(supplied)
    base, = bases
    assert type(policy) is PolicyBindings
    for field in fields(PolicyBindings):
        if field.name not in {'resource_estimator', 'episode_service_factory',
                'episode_service_binding', 'episode_service_inputs'}:
            assert getattr(policy, field.name) is getattr(base, field.name)
    static = deepcopy(supplied['policy'])
    static['scientific_progress'].pop('initial_known_record_refs')
    static['operational'].pop('registry_ref')
    assert hashlib.sha256(canonical(static).encode()).hexdigest() == (
        'dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1')
    assert policy.episode_service_binding == before['services']
    assert policy.episode_service_inputs == 'actual_tool_registry_v1'
    assert policy.episode_record_receipts is True
    assert policy.annotation_child_roles == ROOT_ROLES
    assert policy.execution_planning_roles == ('annotation', 'scientific_process')
    assert policy.initial_known_record_refs == before['policy']['scientific_progress']['initial_known_record_refs']
    assert policy.initial_known_record_refs is not supplied['policy']['scientific_progress']['initial_known_record_refs']
    assert type(policy.resource_estimator) is ResourceToolEstimator
    assert policy.resource_estimator.as_record() == ResourceToolEstimator.with_reported_results().as_record()
    projected, = base_inputs
    assert projected['policy'] == before['policy']
    assert projected['services']['version'] == assembled_case_policy.API_VERSION
    assert projected['services']['public_search_registry'] == before['services']['public_search_registry']
    assert not {'api_timing', 'api_execution_planning'} & set(projected['services'])
    supplied['policy']['scientific_progress']['initial_known_record_refs'].clear()
    supplied['policy']['controller']['cost_by_role']['job_launch'] = 99
    supplied['services']['public_search_registry']['resource_id'] = 'changed'
    assert policy.initial_known_record_refs == before['policy']['scientific_progress']['initial_known_record_refs']
    assert policy.controller_factory((('job_launch', 'fixture'),), 0).cost == .1
    assert policy.episode_service_binding == before['services']
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('invalid', [None, [], {'policy': {}}, {'policy': {}, 'services': {}, 'extra': 1}])
def test_outer_sections_are_closed(tmp_path, invalid, monkeypatch):
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    with pytest.raises(ValueError, match='^explicit_api_prechoice_policy_sections_required$'):
        caller.create_policy(invalid)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -float('inf'), (1,), {1: 2}, object()])
def test_non_json_values_reject_before_canonicalization_or_base(tmp_path, invalid, monkeypatch):
    supplied = parameters(tmp_path)
    supplied['policy']['scientific']['target_weights'] = invalid
    monkeypatch.setattr(caller, 'canonical', forbidden)
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    with pytest.raises(ValueError, match='^finite_json_api_prechoice_parameters_required$'):
        caller.create_policy(supplied)
    assert not list(tmp_path.iterdir())


def test_cycles_reject_but_shared_finite_values_copy_independently(tmp_path, monkeypatch):
    supplied = parameters(tmp_path)
    supplied['policy']['cycle'] = supplied
    with monkeypatch.context() as patch:
        patch.setattr(caller, 'canonical', forbidden)
        patch.setattr(assembled_case_policy, 'create_policy', forbidden)
        with pytest.raises(ValueError, match='^finite_json_api_prechoice_parameters_required$'):
            caller.create_policy(supplied)
    value = {'same': []}
    copied = caller._json_copy([value, value])
    assert copied == [value, value] and copied[0] is not copied[1]


@pytest.mark.parametrize('change', ['missing', 'extra', 'old_version', 'nonobject',
    'marker_extra', 'marker_missing', 'marker_target', 'marker_version'])
def test_closed_services_and_marker_reject_before_base(tmp_path, change, monkeypatch):
    supplied = parameters(tmp_path)
    if change == 'missing':
        del supplied['services']['api_timing']
    elif change == 'extra':
        supplied['services']['extra'] = 1
    elif change == 'old_version':
        supplied['services']['version'] = assembled_case_policy.API_VERSION
    elif change == 'nonobject':
        supplied['services'] = []
    elif change == 'marker_extra':
        supplied['services']['api_execution_planning']['extra'] = True
    elif change == 'marker_missing':
        del supplied['services']['api_execution_planning']['callable']
    elif change == 'marker_target':
        supplied['services']['api_execution_planning']['target'] = 'sequence.align'
    else:
        supplied['services']['api_execution_planning']['version'] = 'unknown'
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    message = ('unsupported_api_execution_planning_binding' if change.startswith('marker_')
               else 'explicit_api_prechoice_services_configuration_required')
    with pytest.raises(ValueError, match='^'+message+'$'):
        caller.create_policy(supplied)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('name', ['handoff_unit', 'acquired_record_unit', 'monitoring_information_unit'])
@pytest.mark.parametrize('invalid', [True, False, 0, -1, '1', 10**1000],
    ids=['boolean_true', 'boolean_false', 'zero', 'negative', 'string', 'overflow'])
def test_closed_configuration_rejects_before_setup(tmp_path, name, invalid, monkeypatch):
    supplied = parameters(tmp_path)
    # timing and policy remain valid integer1: True==1 must not escape.
    supplied['services'][name] = invalid
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    monkeypatch.setattr(caller, 'bind_assembled_services_with_public_search_timing_planning', forbidden)
    with pytest.raises(ValueError, match='^explicit_positive_api_prechoice_service_units_required$'):
        caller.create_policy(supplied)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('change', ['extra', 'version', 'path', 'same_path', 'bool_unit'])
def test_closed_timing_uses_actual_value_validation_before_base(tmp_path, change, monkeypatch):
    supplied = parameters(tmp_path)
    timing = supplied['services']['api_timing']
    if change == 'extra': timing['extra'] = 1
    elif change == 'version': timing['version'] = 'unknown'
    elif change == 'path': timing['history_path'] = 'relative.sqlite'
    elif change == 'same_path': timing['history_path'] = timing['ledger_path']
    else: timing['monitoring_information_unit'] = True
    monkeypatch.setattr(assembled_case_policy, 'create_policy', forbidden)
    with pytest.raises(ValueError, match='^unsupported_api_timing_binding$'):
        caller.create_policy(supplied)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('change', ['resource', 'service_unit', 'policy_unit', 'bad_registry', 'bad_policy'])
def test_actual_base_validation_and_cross_identity_errors(tmp_path, change):
    supplied = parameters(tmp_path)
    if change == 'resource':
        supplied['services']['public_search_registry']['resource_id'] = 'different'
        message = 'api_prechoice_resource_identity_mismatch'
    elif change == 'service_unit':
        supplied['services']['monitoring_information_unit'] = 2
        message = 'api_timing_information_unit_mismatch'
    elif change == 'policy_unit':
        supplied['policy']['monitoring']['information_unit'] = 2
        message = 'api_timing_information_unit_mismatch'
    elif change == 'bad_registry':
        del supplied['services']['public_search_registry']['resource_id']
        message = 'explicit_public_search_registry_required'
    else:
        supplied['policy']['monitoring']['information_unit'] = True
        message = 'explicit_positive_monitoring_information_unit_required'
    with pytest.raises(ValueError, match='^'+message+'$'):
        caller.create_policy(supplied)
    assert not list(tmp_path.iterdir())


@pytest.fixture
def bound(resources, tmp_path, monkeypatch):
    r = resources
    # Actual capability reports unavailable for this nonexecutable fixture file;
    # it cannot probe systemctl or launch a process during actual composition.
    Path(r.jobs.config['executable']['path']).chmod(0o600)
    monkeypatch.setattr('subprocess.run', forbidden)
    problem = r.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = FixtureClient()
    supplied = parameters(tmp_path, client=client)
    supplied['policy']['operational']['registry_ref'] = r.jobs.config['registry_ref']
    supplied['policy']['scientific_progress']['initial_known_record_refs'] = list(problem['subject_refs'])
    RunHistory(supplied['services']['api_timing']['history_path']).close()
    policy = caller.create_policy(supplied)
    ordinary = OrdinaryExecutionStatistics(tmp_path/'ordinary-history.sqlite',
        'fixture-native', tmp_path/'native-receipts')
    tools = ToolRegistry(r.store, clients=client, native_statistics=ordinary)
    baseline_records = r.store.db.execute('SELECT count(*) FROM records').fetchone()[0]
    yield SimpleNamespace(r=r, supplied=supplied, policy=policy, tools=tools,
        client=client, scope=r.store.validate_scope({'subject_refs':problem['subject_refs']}),
        target=problem['subject_refs'][0], baseline_records=baseline_records)


def setup(h, **changes):
    r = h.r
    return h.policy.episode_service_factory(r.store, **{
        'run_id':r.run_id, 'directory':r.directory, 'job_episodes':r.homology,
        'resource_estimator':h.policy.resource_estimator,
        'tool_catalog':h.tools.catalog(), 'tool_registry':h.tools, **changes})


def no_work(h):
    r = h.r
    assert h.client.calls == []
    assert r.store.db.execute('SELECT count(*) FROM records').fetchone()[0] == h.baseline_records
    for table in ('orders', 'handoffs', 'samples'):
        assert r.jobs.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    for table in ('provider_jobs', 'public_search_orders', 'public_search_operations',
            'public_search_publications', 'runtime_runs', 'runtime_episodes', 'runtime_actions',
            'runtime_model_calls', 'runtime_observations'):
        assert r.store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
    assert r.store.count('observation') == r.store.count('assessment') == r.store.count('native_execution') == 0
    binding = ApiTimingBinding.from_record(h.supplied['services']['api_timing'])
    with sqlite3.connect(binding.ledger_path) as db:
        for table in ('api_timing_orders', 'api_timing_submission_intents',
                'api_timing_measurements', 'api_timing_export_dispositions'):
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


def test_actual_setup_binds_shared_owners_and_freezes_actual_api_map(bound):
    h, r = bound, bound.r
    original_catalog = deepcopy(h.tools.catalog())
    original_resources = deepcopy(h.tools.resource_binding())
    application = setup(h)
    first = h.tools.api_execution_planner
    assert type(first) is ApiExecutionPlanner
    assert type(first.ports) is PublicSearchPorts
    assert type(first.ports.operations) is ProviderJobOperations
    assert type(first.ports.result_publisher) is PublicSearchResultPublisher
    assert type(first.timing) is ApiTimingLedger
    assert type(first.timing.statistics) is ApiReportedStatistics
    assert first.store is first.ports.operations.store is first.ports.result_publisher.store is r.store
    assert first.run_id == first.timing.run_id == r.run_id
    assert first.ports.operations.remote_searches is h.tools.remote_searches
    assert first.ports.result_publisher.tools is h.tools
    assert first.resource_estimator is h.policy.resource_estimator
    assert application.job_progress_provider.ports is first.ports
    catalog = h.tools.catalog()
    branches = catalog['execution.estimate']['input_schema']['anyOf']
    assert branches[:-1] == original_catalog['execution.estimate']['input_schema']['anyOf']
    assert branches[-1]['properties']['arguments'] == catalog['public.hmmer.search']['input_schema']
    assert branches[-1]['properties']['resource_selection'] == {'const':first._selection()}
    assert branches[-1]['required'] == ['tool','arguments','resource_selection','constraints','immutable_input_versions']
    assert h.tools.resource_binding() == original_resources
    frozen = ScientificToolLibrary(r.directory/'scientific-tool-library')
    assert frozen.catalog() == sorted([{'name':name,**value} for name,value in catalog.items()],key=lambda row:row['name'])
    workflow = SimpleNamespace(store=r.store, tools=h.tools, run_id=r.run_id)
    composition = compose_episode_bindings(WorkflowServices(workflow), store=r.store,
        journal=Journal(r.store,r.run_id), execution_backend=None,
        descriptors=[d for d in application.episode_binding_descriptors if d['binding_id']!='monitor'],
        job_episodes=r.homology, resource_estimator=h.policy.resource_estimator,
        role_credit_bindings=application.role_credit_bindings, directory=r.directory)
    adapter = next(a for b in composition.bindings if b.as_record()['binding_id']=='resource_episodes'
        for a in b.adapters.values() if a.resource_id==h.supplied['services']['public_search_registry']['resource_id'])
    final = h.tools.api_execution_planner
    assert final is adapter.api_execution_planning
    assert final.ports is adapter.ports is composition.api_timing_reader.ports
    assert final.timing is adapter.timing is composition.api_timing_reader.ledger
    assert final.resource_estimator is adapter.resource_estimator is h.policy.resource_estimator
    assert final.as_record() == first.as_record()
    assert h.tools.resource_binding() == original_resources
    assert frozen.resolve(['execution.estimate'],available_catalog=h.tools.catalog())
    assert len([d for d in composition.resource_capabilities if d['kind']=='api']) == 1
    assert next(d for d in composition.resource_capabilities if d['kind']=='api')['availability']=='unknown'
    no_work(h)


def test_input_and_exposed_definition_mutation_cannot_change_setup(bound):
    h = bound
    original = deepcopy(h.supplied['services'])
    inherited = list(h.supplied['policy']['scientific_progress']['initial_known_record_refs'])
    assert inherited == [h.target]  # Actual registered isolated protein input.
    h.supplied['policy']['scientific_progress']['initial_known_record_refs'].clear()
    h.supplied['services']['public_search_registry']['resource_id'] = 'changed-input'
    h.supplied['services']['monitoring_information_unit'] = 99
    h.supplied['services']['tool_retrieval']['model']['model'] = 'changed-input'
    h.policy.episode_service_binding['api_timing']['resource_id'] = 'changed-definition'
    h.policy.episode_service_binding['scientific_child_roles'].clear()
    application = setup(h)
    planner = h.tools.api_execution_planner
    assert h.policy.initial_known_record_refs == inherited
    assert planner.ports.registry == original['public_search_registry']
    assert planner.timing.binding.as_record() == original['api_timing']
    scientific = application.episode_binding_descriptors[0]
    assert scientific['configuration']['child_roles'] == original['scientific_child_roles']
    assert scientific['configuration']['tool_retrieval'] == original['tool_retrieval']
    # no_work uses original valid binding, not the deliberately mutated caller input.
    h.supplied['services'] = original
    no_work(h)


@pytest.mark.parametrize('change', ['stale_map', 'client_pin', 'estimator', 'foreign_store'])
def test_actual_setup_rejects_wrong_map_client_estimator_and_owner(bound, tmp_path, change):
    h = bound
    changes = {}
    if change == 'stale_map':
        changes['tool_catalog'] = deepcopy(h.tools.catalog())
        del changes['tool_catalog']['state.query']
    elif change == 'client_pin':
        supplied = deepcopy(h.supplied)
        supplied['services']['public_search_registry']['client_binding_sha256'] = '0'*64
        h.policy = caller.create_policy(supplied)
    elif change == 'estimator':
        changes['resource_estimator'] = ResourceToolEstimator()
    else:
        from gene_annotation_episode.state import Store
        with Store(tmp_path/'foreign-workspace') as other:
            changes['tool_registry'] = ToolRegistry(other,clients=h.client)
            changes['tool_catalog'] = changes['tool_registry'].catalog()
            with pytest.raises((DurableExecutionError,ValueError)):
                setup(h,**changes)
        assert h.tools.api_execution_planner is None and h.client.calls == []
        return
    with pytest.raises((DurableExecutionError,ValueError)):
        setup(h,**changes)
    assert h.tools.api_execution_planner is None and h.client.calls == []
    assert not h.r.directory.exists()
    assert h.r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


@pytest.mark.parametrize('history_present', [True,False])
def test_actual_prechoice_estimate_is_no_work_and_unknown_with_new_history(bound, monkeypatch, history_present):
    h = bound
    setup(h)
    planner = h.tools.api_execution_planner
    if not history_present:
        planner.timing.binding.history_path.unlink()
    selected = {'tool':'public.hmmer.search','arguments':{'subject_ref':h.target,
        'algorithm':'phmmer','database':'swissprot'},'resource_selection':planner._selection(),
        'constraints':{},'immutable_input_versions':[]}
    original = deepcopy(selected)
    result = h.tools.execute('execution.estimate',selected,scope=h.scope,operation_key='caller-estimate')
    assert result['status']=='completed' and result['record_refs']==[]
    forecast, = result['result']['api_reported_execution_forecasts']
    assert forecast['expected_total_seconds'] is None
    assert forecast['reported_result_support'] == ({'reported_result_count':0} if history_present else None)
    assert forecast['status'] == ('no_matching_history' if history_present else 'history_unavailable')
    assert result['result']['arguments'] == original['arguments']
    saved = h.r.store.db.execute('SELECT arguments,result FROM tool_operations WHERE operation_key=?',('caller-estimate',)).fetchone()
    assert canonical(json.loads(saved['arguments']))==canonical(original)
    assert json.loads(saved['result'])==result and selected==original
    monkeypatch.setattr(planner.timing.statistics,'capture',forbidden)
    assert h.tools.execute('execution.estimate',selected,scope=h.scope,operation_key='caller-estimate')==result
    no_work(h)


def test_snapshot_loader_records_exact_new_factory_and_complete_parameters(tmp_path):
    supplied = parameters(tmp_path)
    run = tmp_path/'policy-snapshot';run.mkdir()
    policy, recorded = _load_policy(run,Path(caller.__file__),supplied,resume=False)
    assert recorded['parameters']==supplied
    assert recorded['episode_application_services']=={
        'version':'episode_application_services_v3',
        'factory':'fixed_gene_policy_'+recorded['source_sha256']+'.create_policy.<locals>.setup',
        'inputs':'actual_tool_registry_v1','definition':supplied['services']}
    assert recorded['definitions']['resource_estimator']==policy.resource_estimator.as_record()
    restored, replay = _load_policy(run,None,None,resume=True)
    assert replay==recorded
    assert restored.controller_definition==policy.controller_definition
    assert restored.initial_known_record_refs==policy.initial_known_record_refs
    assert restored.native_timing_information.as_record()==policy.native_timing_information.as_record()
    assert not list(tmp_path.glob('*.sqlite'))
