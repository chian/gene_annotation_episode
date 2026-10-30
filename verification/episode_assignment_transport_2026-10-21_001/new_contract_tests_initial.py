"""Exercise assignment transport through the real assembled decision boundary.

All work uses isolated temporary cases and explicit provider fixtures. Saved
commissions are never dispatched; no model, native search or scientific result
is claimed. Invented A/P entries exist only in the construction fixture.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import independent_execution
from gene_annotation_episode.case_execution import prepared_case_bindings
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import _action_generation_schema, _decode_action_response
from gene_annotation_episode.schema_support import _schema_nodes
from gene_annotation_episode.state import Store
from method_loop.durable import DurableExecutionStore, canonical
from test_assembled_case_reconstruction import initialize_case, reopen
from test_assembled_service_setup import ROOT_ROLES
from test_homology_episode_runtime import Provider


FINITE_CONTEXT = {
    'explicit_null': None,
    'nested': [True, False, 0, -2, 3.25, 'α', {'empty': {}}],
    '$ref': 'literal-reference-not-a-schema',
    'properties': {'type': 'literal-data'},
    'required': ['literal-data'],
}


def forbidden(*args, **kwargs):
    raise AssertionError('Assignment transport cannot launch a model or native work')


@pytest.fixture
def assembled(tmp_path, monkeypatch, request):
    invented = getattr(request, 'param', True)
    fixture = initialize_case(tmp_path, monkeypatch, invented=invented)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    monkeypatch.setattr(HomologyJobs, 'order', forbidden)
    monkeypatch.setattr(HomologyJobs, 'submit', forbidden)
    monkeypatch.setattr(DurableExecutionStore, 'start', forbidden)
    with Store(fixture['workspace']) as store, prepared_case_bindings(
            store, fixture['directory']) as (_, options):
        provider = Provider([])
        workflow = reopen(fixture, store, options, provider)
        workflow.configure_execution(independent_execution.make_runtime_binding(
            store, fixture['directory'], kind='fixed_case'))
        scope = {'subject_refs': [fixture['manifest']['target_ref']]}
        root = workflow.build('annotation', 'root', fixture['settings']['goal'], scope)
        yield SimpleNamespace(fixture=fixture, store=store, workflow=workflow,
            root=root, provider=provider, scope=scope,
            host=workflow.action_schema(root.source))
        assert not fixture['turns'].exists()
        assert options['job_episodes'].jobs.db.execute(
            'SELECT count(*) FROM orders').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def branch(schema, role):
    return next(node for node in schema['properties']['selection']['anyOf']
        if node['properties']['kind'].get('const',
            node['properties']['kind'].get('enum', [None])[0]) == 'episode_child'
        and node['properties']['role'].get('const',
            node['properties']['role'].get('enum', [None])[0]) == role)


def requested_form():
    return {'type': 'object', 'properties': {
        'finding_state': {'type': 'string', 'enum': ['unknown', 'measured']},
        'records': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
            'x-source': 'committed_record_refs'}},
        'required': ['finding_state', 'records'], 'additionalProperties': False}


def assignment(case, role):
    target = case.fixture['manifest']['target_ref']
    if role == 'scientific_process':
        library = case.workflow.scientific_process_binding.library
        return {'selection': {'version': 'scientific_process_selection_v2',
            'annotation_ref': library.reference('A01'),
            'thought_ref': library.reference('P01'), 'tools': ['sequence.inspect']},
            'evidence_refs': [target], 'constraints': deepcopy(FINITE_CONTEXT),
            'context': {'inherited': deepcopy(FINITE_CONTEXT)}}
    if role == 'literature':
        return {'version': 'literature_assignment_v1',
            'question_context_refs': [target],
            'source_refs': [case.fixture['manifest']['context_source_ref']]}
    if role == 'monitor':
        return {'version': 'monitor_assignment_v1', 'target_handle': 'execution_' + 'a' * 64,
            'requested_fields': ['execution_status'], 'known_progress_refs': [],
            'permitted_committed_record_types': ['assessment']}
    adapter = next(iter(case.workflow.episode_bindings.for_role('launch').adapters.values()))
    selection = adapter._selection(1)
    if role == 'launch':
        return {'version': 'resource_launch_assignment_v1',
            'job_request': {'adapter_extension': deepcopy(FINITE_CONTEXT)},
            'immutable_input_versions': [{'reference': target, 'version': None,
                'content_sha256': None}],
            'constraints': {'allowed_kinds': ['local'], 'cpu': 1, 'wall_seconds': None,
                'caller_context': deepcopy(FINITE_CONTEXT)},
            'resource_selection': selection,
            'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    assert role == 'results'
    # Pure transport operands only: this synthetic handoff is never accepted
    # as a real physical execution or used to retrieve native results.
    handle = 'job_transport_fixture'
    handoff = {'version': 'execution_handoff_v1', 'execution_handle': handle,
        'resource_selection': selection, 'submitted_input_versions': [],
        'monitoring': {'provider_id': adapter.resource_id, 'target_handle': handle,
            'contract_ref': 'homology.status.v1'},
        'results': {'provider_id': adapter.resource_id, 'target_handle': handle,
            'contract_ref': 'homology.results.v1'},
        'checked_at': '2026-10-21T00:00:00+00:00', 'check_record_refs': [],
        'state': 'usable', 'failure': None}
    return {'version': 'resource_results_assignment_v1', 'handoff': handoff,
        'requested_data_selector': {'offset': 0, 'limit': None,
            'adapter_extension': deepcopy(FINITE_CONTEXT)}}


def proposal(case, role, value=None, *, encoded=True):
    value = assignment(case, role) if value is None else deepcopy(value)
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Inspect the isolated transport fixture within its assigned scope.',
        'scope': deepcopy(case.scope), 'purpose': 'Return the original typed fixture form.',
        'schema_json': canonical(requested_form()),
        'initial_report_json': '{"finding_state":"unknown"}',
        'assignment': json.dumps(value, ensure_ascii=False) if encoded else value},
        'report_update': {}}


def select(case, value):
    """Save a real fixture decision response before ordinary validation/C1."""
    case.provider.script = iter([deepcopy(value)])

    async def choose():
        response, index, context, schema = await case.root.source.call(
            {'visible_record_refs': [], 'scope': case.scope}, case.host)
        unit = case.root.source.apply_response(response, index, context, schema)
        return unit, index

    return asyncio.run(choose())


def assert_no_commission(case):
    for table in ('runtime_actions', 'runtime_commission_intents', 'runtime_completion_slots',
                  'runtime_observations'):
        assert case.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
    # Admissions are installed only on first use; an absent table is not an
    # SQL error and must not be reported as an existing zero-row ledger.
    installed = case.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='runtime_return_admissions'").fetchone()
    if installed:
        assert case.store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 0


@pytest.mark.parametrize('assembled', [False, True], indirect=True)
def test_full_actual_assembled_root_transport_has_strict_shapes_and_all_five_edges(assembled):
    case = assembled
    original = deepcopy(case.host)
    generated = _action_generation_schema(case.host)
    Draft202012Validator.check_schema(generated)
    objects = []
    for path, node in _schema_nodes(generated):
        if not isinstance(node, dict):
            continue
        declared = node.get('type')
        if declared == 'object' or isinstance(declared, list) and 'object' in declared:
            objects.append(path)
            assert node.get('additionalProperties') is False, path
            assert isinstance(node.get('properties'), dict), path
            assert set(node.get('required', [])) == set(node['properties']), path
    assert objects
    roles = [node['properties']['role']['enum'][0]
        for node in generated['properties']['selection']['anyOf']
        if node['properties']['kind'].get('enum') == ['episode_child']]
    assert roles == list(ROOT_ROLES)
    assert tuple(grain.name for grain in case.workflow.tree.allowed_children('annotation')) == ROOT_ROLES
    for role in ROOT_ROLES:
        encoded = branch(generated, role)['properties']['assignment']
        original_assignment = branch(case.host, role)['properties']['assignment']
        assert encoded['type'] == 'string'
        description = encoded['description']
        assert json.loads(description[description.index('{'):]) == original_assignment
        assert original_assignment['type'] == 'object'
    assert branch(case.host, 'launch')['properties']['assignment']['properties']['job_request'] == {'type': 'object'}
    assert branch(case.host, 'launch')['properties']['assignment']['properties']['constraints'] == {'type': 'object'}
    assert branch(case.host, 'results')['properties']['assignment']['properties']['requested_data_selector'] == {'type': 'object'}
    assert case.host == original
    assert_no_commission(case)


def test_all_five_assignments_roundtrip_without_normalizing_nested_nulls_or_literals(assembled):
    case = assembled
    original_schema = deepcopy(case.host)
    generated = _action_generation_schema(case.host)
    for role in ROOT_ROLES:
        value = assignment(case, role)
        encoded = proposal(case, role, value)
        encoded['selection']['scope'].update(read_selection_refs=None, segments=None)
        assert Draft202012Validator(generated).is_valid(encoded), role
        decoded = _decode_action_response(encoded, case.host)
        assert decoded['selection']['assignment'] == value
        assert decoded['selection']['scope'] == case.scope
        assert Draft202012Validator(case.host).is_valid(decoded), role
        # Existing scripted providers may still return an authoritative object.
        direct = proposal(case, role, value, encoded=False)
        assert _decode_action_response(direct, case.host) == direct
        assert Draft202012Validator(case.host).is_valid(direct), role
    assert case.host == original_schema
    assert_no_commission(case)


@pytest.mark.parametrize('encoded', [
    '{', '[]', 'null', '{"duplicate":1,"duplicate":2}',
    '{"value":NaN}', '{"value":1e10000}',
])
def test_assignment_strings_reject_malformed_duplicate_nonobject_and_nonfinite_json(assembled, encoded):
    case = assembled
    generated = _action_generation_schema(case.host)
    for role in ROOT_ROLES:
        value = proposal(case, role)
        value['selection']['assignment'] = encoded
        assert Draft202012Validator(generated).is_valid(value), role
        with pytest.raises(ValueError):
            _decode_action_response(value, case.host)
    assert_no_commission(case)


@pytest.mark.parametrize('role', ROOT_ROLES)
def test_strict_assignment_parse_failure_uses_existing_feedback_without_an_observation(assembled, role):
    value = proposal(assembled, role)
    value['selection']['assignment'] = '{"duplicate":1,"duplicate":2}'
    unit, _ = select(assembled, value)
    assert unit is None
    assert assembled.root.source.feedback['category'] == 'action_contract'
    assert 'Duplicate JSON object key' in assembled.root.source.feedback['detail']
    assert_no_commission(assembled)


@pytest.mark.parametrize('role', ['scientific_process', 'literature', 'launch'])
def test_decoded_assignment_original_typed_form_and_saved_commission_remain_exact(assembled, role):
    case = assembled
    value = assignment(case, role)
    selected = proposal(case, role, value)
    unit, index = select(case, selected)
    assert unit is not None
    spec, = case.workflow.commissions.recover_selected(case.root.source.episode_id)
    assert spec['child']['role'] == role
    request = spec['child']['request']
    assert request['message']['episode_assignment'] == value
    assert request['message']['initial_report'] == {'finding_state': 'unknown'}
    assert request['report_contract']['measurements']['schema'] == requested_form()
    assert request['report_contract']['decision'] == selected['selection']['purpose']
    assert spec['parent']['episode_id'] == case.root.source.episode_id
    action = case.workflow.journal.row('runtime_actions', case.root.source.episode_id, index)
    assert json.loads(action['action']) == _decode_action_response(selected, case.host)['selection']
    assert json.loads(action['result'])['pending_handle'] == spec['handle']
    assert action['credit'] is None
    call = case.workflow.journal.row('runtime_model_calls', case.root.source.episode_id, index)
    assert json.loads(call['response']) == selected
    assert json.loads(call['request'])['schema'] == case.host
    # Publish the immutable C1 identity only, never start its worker.
    case.workflow.execution_backend.commission(spec)
    assert case.workflow.execution_backend.load_commission(spec['handle']) == spec
    assert case.store.db.execute('SELECT count(*) FROM runtime_completion_slots').fetchone()[0] == 0
    assert case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('invalid', ['launch_host_shape', 'results_adapter_selector',
    'literature_reference', 'scientific_library_reference'])
def test_decoding_preserves_existing_host_and_semantic_rejections(assembled, invalid):
    case = assembled
    role = {'launch_host_shape': 'launch', 'results_adapter_selector': 'results',
        'literature_reference': 'literature',
        'scientific_library_reference': 'scientific_process'}[invalid]
    value = assignment(case, role)
    if invalid == 'launch_host_shape':
        value['resource_selection']['allocation']['cpu'] = 0
    elif invalid == 'results_adapter_selector':
        value['requested_data_selector'] = {'offset': -1}
    elif invalid == 'literature_reference':
        value['source_refs'] = ['source_' + '0' * 24]
    else:
        value['selection']['annotation_ref']['option_id'] = 'A999'
    selected = proposal(case, role, value)
    decoded = _decode_action_response(selected, case.host)
    assert decoded['selection']['assignment'] == value
    if invalid == 'launch_host_shape':
        assert not Draft202012Validator(case.host).is_valid(decoded)
    else:
        assert Draft202012Validator(case.host).is_valid(decoded)
    unit, _ = select(case, selected)
    assert unit is None
    assert case.root.source.feedback['category'] == 'action_contract'
    if invalid == 'results_adapter_selector':
        assert case.root.source.feedback['detail'] == 'invalid_resource_selector'
    assert_no_commission(case)


def test_assignment_encoding_does_not_relax_parent_return_form_validation(assembled):
    case = assembled
    selected = proposal(case, 'literature')
    selected['selection']['schema_json'] = canonical({'type': 'object',
        'properties': {'finding': {'type': 'string'}}, 'required': ['finding'],
        'additionalProperties': False})
    selected['selection']['initial_report_json'] = '{"finding":"unrestricted prose"}'
    assert Draft202012Validator(_action_generation_schema(case.host)).is_valid(selected)
    unit, _ = select(case, selected)
    assert unit is None
    assert case.root.source.feedback['category'] == 'action_contract'
    assert 'strings need a declared semantic type' in case.root.source.feedback['detail']
    assert_no_commission(case)
