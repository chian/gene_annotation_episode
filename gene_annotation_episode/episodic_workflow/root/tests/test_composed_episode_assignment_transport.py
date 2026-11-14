"""Composed assignment transport through real schemas, admission and history.

All provider choices are engineering fixtures. The retained Cooler/HIC records
are read-only operands; these checks do not invoke native scientific work.
"""
import ast
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import runtime
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import native_assignment, launch_assignment
from test_runtime import FixtureController


PACKET = Path(__file__).parent / 'fixtures/composed_transport'
ORIGINAL_REPO = Path(os.environ.get('TRANSPORT458_ORIGINAL_REPO', Path(__file__).resolve().parents[4]))
OLD_RUNTIME_SHA = '57f3fff849bc6703fe14f9a2382ea958b0f1f6697394cef9a8dfdff3a10b15ba'


@pytest.fixture(scope='module')
def historical():
    """Execute only the pinned pre-change pure functions, inside the quota run."""
    path = PACKET / 'baseline/runtime.py'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OLD_RUNTIME_SHA
    names = {'_action_generation_schema', '_json_episode_assignment', '_decode_action_response'}
    tree = ast.parse(raw)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(functions) == len(names)
    namespace = dict(vars(runtime))
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DecisionSource')
    call = next(node for node in klass.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'call')
    exec(compile(ast.Module(body=[call], type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(generate=namespace['_action_generation_schema'],
        decode=namespace['_decode_action_response'], call=namespace['call'])


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
        'additionalProperties': False}


LITERAL = {'$ref': 'this-is-data', 'type': 'object', 'properties': {'required': None},
    'const': {'nested': [None, False, 0, 'α']}, 'anyOf': [{'format': 'data'}]}
PAYLOAD_SCHEMA = obj({'version': {'const': 'transport_fixture_v1'}, 'value': {'type': 'integer', 'minimum': 1},
    'optional': {'type': ['integer', 'null']}, 'literal': {'const': LITERAL}}, ['version', 'value', 'literal'])


def assignment_schema(form):
    base = deepcopy(PAYLOAD_SCHEMA)
    if form == 'anyOf':
        return {'anyOf': [base]}
    if form == 'allOf':
        return {'allOf': [base, {'properties': {'value': {'maximum': 3}}}]}
    if form == 'oneOf':
        return {'oneOf': [base]}
    if form in ('reference', 'anchor'):
        return {'$id': 'urn:transport458:' + form, '$ref': '#/$defs/job' if form == 'reference' else '#job',
            '$defs': {'job': {**base, '$anchor': 'job'}}}
    raise AssertionError(form)


def host_schema(assignment):
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'episode_child'},
        'role': {'const': 'launch_local'}, 'assignment': assignment})]}, 'report_update': obj({})})


def proposed(assignment, *, encoded=True):
    return {'selection': {'kind': 'episode_child', 'role': 'launch_local',
        'assignment': json.dumps(assignment, allow_nan=False) if encoded else deepcopy(assignment)}, 'report_update': {}}


@pytest.mark.parametrize('form', ['anyOf', 'allOf', 'oneOf', 'reference', 'anchor'])
@pytest.mark.parametrize('optional', ['absent', None, 0])
def test_composed_objects_preserve_omission_null_and_schema_looking_literals(form, optional):
    payload = {'version': 'transport_fixture_v1', 'value': 2, 'literal': deepcopy(LITERAL)}
    if optional != 'absent':
        payload['optional'] = optional
    schema = host_schema(assignment_schema(form))
    original = deepcopy(schema)
    generated = runtime._action_generation_schema(schema)
    transported = generated['properties']['selection']['anyOf'][0]['properties']['assignment']
    assert transported['type'] == 'string'
    assert json.loads(transported['description'][transported['description'].index('{'):]) == assignment_schema(form)
    for encoded in (True, False):
        response = proposed(payload, encoded=encoded)
        if encoded:
            Draft202012Validator(generated).validate(response)
        decoded = runtime._decode_action_response(response, schema)
        assert decoded['selection']['assignment'] == payload
        Draft202012Validator(schema).validate(decoded)
    assert schema == original


@pytest.mark.parametrize('value', [0, 4, '2', None])
def test_original_composed_domain_rejections_are_not_weakened(value):
    schema = host_schema(assignment_schema('allOf'))
    payload = {'version': 'transport_fixture_v1', 'value': value, 'optional': None, 'literal': deepcopy(LITERAL)}
    for encoded in (True, False):
        decoded = runtime._decode_action_response(proposed(payload, encoded=encoded), schema)
        assert decoded['selection']['assignment'] == payload
        assert not Draft202012Validator(schema).is_valid(decoded)


@pytest.mark.parametrize('encoded', ['{', '[]', 'null', '{"a":1,"a":2}', '{"a":NaN}',
    '{"a":Infinity}', '{"a":1e10000}'])
def test_strict_parser_rejects_ambiguous_nonobject_nonfinite_assignments(encoded):
    schema = host_schema(assignment_schema('anyOf'))
    value = proposed({})
    value['selection']['assignment'] = encoded
    Draft202012Validator(runtime._action_generation_schema(schema)).validate(value)
    with pytest.raises(ValueError):
        runtime._decode_action_response(value, schema)


@pytest.mark.parametrize('change', ['missing', 'extra', 'duplicate', 'nonstring',
    'const', 'enum', 'default', 'examples', 'alternative_order', 'constraint'])
def test_markerless_schema_comparison_only_accepts_required_member_permutations(change):
    literal = {'required': ['second', 'first'], 'properties': {'x': {'required': ['b', 'a']}}}
    schema = obj({'first': {'type': 'integer', 'minimum': 0}, 'second': {'anyOf': [
        {'type': 'string'}, {'type': 'null'}]}, 'literal': {'const': literal, 'enum': [literal],
            'default': literal, 'examples': [literal]}})
    permutation = deepcopy(schema)
    permutation['required'].reverse()
    assert runtime._same_action_schema_required_members(permutation, schema)
    original = deepcopy(schema)
    wrong = deepcopy(permutation)
    if change == 'missing':
        wrong['required'].pop()
    elif change == 'extra':
        wrong['required'].append('absent')
    elif change == 'duplicate':
        wrong['required'].append(wrong['required'][0])
    elif change == 'nonstring':
        wrong['required'].append(1)
    elif change in ('const', 'default'):
        wrong['properties']['literal'][change]['required'].reverse()
    elif change in ('enum', 'examples'):
        wrong['properties']['literal'][change][0]['required'].reverse()
    elif change == 'alternative_order':
        wrong['properties']['second']['anyOf'].reverse()
    else:
        wrong['properties']['first']['minimum'] = 1
    assert not runtime._same_action_schema_required_members(wrong, schema)
    assert schema == original


class Provider:
    def __init__(self):
        self.responses, self.schemas, self.contexts = [], [], []

    async def complete(self, episode_id, role, instructions, context, schema):
        assert self.responses, 'No provider dispatch is permitted during saved replay'
        self.schemas.append(deepcopy(schema))
        self.contexts.append(deepcopy(context))
        response = self.responses.pop(0)
        Draft202012Validator(schema).validate(response)
        return deepcopy(response)

    async def release(self, _):
        pass


@pytest.fixture
def connected(tmp_path):
    workspace = tmp_path / 'project'
    workspace.mkdir()
    with Store(tmp_path / 'state') as store:
        scope = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        scope = {'subject_refs': scope['subject_refs']}
        provider = Provider()
        family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id='transport458',
            resources={'here': {'kind': 'local', 'workspace': str(workspace), 'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}}},
            initial_information={}, tool_registry=ToolRegistry(store), handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=4, log_roles=['stdout', 'stderr'])
        workflow = runtime.Workflow(store, ToolRegistry(store), provider, tmp_path / 'run', 'transport458',
            lambda path, initial: FixtureController(str(path), initial, 1), lambda *_: 0,
            episode_binding_descriptors=[family.as_record()], root_role='launch', decision_protocol='decision_exchange_v1',
            role_credit_bindings={role: {'definition': {'version': 'transport_fixture_no_work_v1'},
                'project': lambda *_: 0} for role in family.roles})
        assignment = native_assignment(workspace)
        root = workflow.build('launch', 'root', 'Prepare exactly the selected fixture job', scope,
            episode_assignment=launch_assignment({'here': assignment}))
        selection = {'kind': 'episode_child', 'role': 'launch_local', 'goal': 'Prepare the exact fixture request',
            'scope': {**scope, 'read_selection_refs': None, 'segments': None}, 'purpose': 'Return preparation status',
            'schema_json': json.dumps(obj({'status': {'type': 'string', 'enum': ['unknown', 'ready']}})),
            'initial_report_json': '{"status":"unknown"}', 'assignment': deepcopy(assignment)}
        yield SimpleNamespace(store=store, workflow=workflow, source=root.source, provider=provider,
            schema=workflow.action_schema(root.source), selection=selection, assignment=assignment, scope=scope)


def choose(case, response):
    case.provider.responses.append({'response': {'response_type': 'select_action', **deepcopy(response)}})
    return asyncio.run(case.source.call({'visible_record_refs': [], 'scope': case.scope,
        'tools': case.workflow.catalog(case.scope, source=case.source)}, case.schema))


def no_observations(case):
    assert case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_new_production_local_assignment_dispatch_and_semantic_parent_constraints(connected):
    case = connected
    response = {'selection': {**case.selection, 'assignment': json.dumps(case.assignment)}, 'report_update': {}}
    returned, index, context, schema = choose(case, response)
    unit = case.source.apply_response(returned, index, context, schema)
    assert unit is not None, case.source.feedback
    assert unit.child.request.message.as_record()['episode_assignment'] == case.assignment
    assert json.loads(case.workflow.journal.row('runtime_actions', case.source.episode_id, index)['action'])['assignment'] == case.assignment
    no_observations(case)
    changed = deepcopy(response)
    changed_job = deepcopy(case.assignment)
    changed_job['requested_job']['argv'] = ['/bin/false']
    changed['selection']['assignment'] = json.dumps(changed_job)
    returned, index, context, schema = choose(case, changed)
    assert case.source.apply_response(returned, index, context, schema) is None
    assert 'execution_original_request_conflict' in case.source.feedback['detail']
    assert case.workflow.journal.row('runtime_actions', case.source.episode_id, index) is None
    no_observations(case)


@pytest.mark.parametrize('encoded', ['{', '[]', 'null', '{"a":1,"a":2}', '{"a":NaN}', '{"a":1e10000}'])
def test_malformed_composed_assignment_is_feedback_without_action_or_observation(connected, encoded):
    case = connected
    returned, index, context, schema = choose(case, {'selection': {**case.selection, 'assignment': encoded}, 'report_update': {}})
    assert case.source.apply_response(returned, index, context, schema) is None
    assert case.source.feedback['category'] == 'action_contract'
    assert case.workflow.journal.row('runtime_actions', case.source.episode_id, index) is None
    no_observations(case)






def test_expanded_valid_explicit_null_without_historical_proof_is_preserved(connected):
    case = connected
    response = {'selection': deepcopy(case.selection), 'report_update': {}}
    response['selection']['assignment']['launch_instructions'] = None
    unit = case.source.apply_response(response, 0, {'visible_record_refs': []}, case.schema)
    assert unit is not None, case.source.feedback
    assert unit.child.request.message.as_record()['episode_assignment']['launch_instructions'] is None
    recorded = json.loads(case.workflow.journal.row('runtime_actions', case.source.episode_id, 0)['action'])
    assert recorded['assignment']['launch_instructions'] is None
    no_observations(case)


@pytest.mark.parametrize('optional_null', [False, True])
def test_unmarked_direct_provider_pending_replay_requires_identical_decoded_selection(connected, optional_null):
    case = connected
    case.workflow.decision_protocol = None
    case.workflow.decision_exchanges = None
    response = {'selection': deepcopy(case.selection), 'report_update': {}}
    if optional_null:
        response['selection']['assignment']['launch_instructions'] = None
    original = {'context': {'visible_record_refs': []}, 'schema': case.schema}
    case.workflow.journal.save('runtime_model_calls', {'episode_id': case.source.episode_id,
        'call_index': 0, 'purpose': 'decision', 'request': runtime._json(original),
        'response': runtime._json(response)})
    before = dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, 0))
    returned, index, context, schema = asyncio.run(case.source.call({}, obj({})))
    assert returned == response
    unit = case.source.apply_response(returned, index, context, schema)
    if optional_null:
        assert unit is None
        assert case.source.feedback == {'status': 'invalid', 'category': 'action_contract',
            'detail': 'original_assignment_transport_unavailable'}
        assert case.workflow.journal.row('runtime_actions', case.source.episode_id, index) is None
    else:
        assert unit is not None, case.source.feedback
        assert unit.child.request.message.as_record()['episode_assignment'] == case.assignment
    assert dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, 0)) == before
    assert not case.provider.schemas
    no_observations(case)


def test_new_direct_provider_transport_marker_is_private_and_replays_exact_values(connected):
    case = connected
    case.workflow.decision_protocol = None
    case.workflow.decision_exchanges = None
    assignment = {**case.assignment, 'launch_instructions': None}
    response = {'selection': {**case.selection, 'assignment': json.dumps(assignment)}, 'report_update': {}}
    case.provider.responses.append(response)
    returned, index, context, schema = asyncio.run(case.source.call({'visible_record_refs': [], 'scope': case.scope}, case.schema))
    before = dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index))
    saved = json.loads(before['request'])
    assert saved['assignment_transport'] == {'version': runtime._ASSIGNMENT_TRANSPORT,
        'action_schema_sha256': runtime._digest(schema)}
    assert 'assignment_transport' not in saved['context']
    assert all('assignment_transport' not in context for context in case.provider.contexts)
    case.source.calls = 0
    replayed, same_index, same_context, same_schema = asyncio.run(case.source.call({}, obj({})))
    assert (replayed, same_index, same_context, same_schema) == (returned, index, context, schema)
    unit = case.source.apply_response(replayed, same_index, same_context, same_schema)
    assert unit is not None, case.source.feedback
    assert unit.child.request.message.as_record()['episode_assignment'] == assignment
    assert dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index)) == before
    assert len(case.provider.schemas) == 1
    no_observations(case)


@pytest.mark.parametrize('marker', [
    {'version': 'unknown', 'action_schema_sha256': '0' * 64},
    {'version': runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': '0' * 64},
])
def test_direct_provider_transport_marker_is_bound_to_actual_generator_and_schema(connected, marker):
    case = connected
    case.workflow.decision_protocol = None
    case.workflow.decision_exchanges = None
    saved = {'context': {'visible_record_refs': []}, 'schema': case.schema, 'assignment_transport': marker}
    response = {'selection': deepcopy(case.selection), 'report_update': {}}
    case.workflow.journal.save('runtime_model_calls', {'episode_id': case.source.episode_id,
        'call_index': 0, 'purpose': 'decision', 'request': runtime._json(saved), 'response': runtime._json(response)})
    with pytest.raises(runtime.WorkflowError, match='original_assignment_transport_mismatch'):
        asyncio.run(case.source.call({}, obj({})))
    assert case.workflow.journal.row('runtime_actions', case.source.episode_id, 0) is None
    assert not case.provider.schemas
    no_observations(case)






def test_retained_nonnull_hic_runtime_and_absent_cooler_runtime_use_same_atomic_transport():
    from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_schema
    from gene_annotation_episode.native_chromatin_interaction_contracts import validate_chromatin_software
    hic = json.loads((Path(__file__).parent / 'fixtures/composed_transport/chromatin_hic/HIC_SOFTWARE.json').read_bytes())
    assert hic['native_runtime']['files']
    validate_chromatin_software(hic, supported_formats=['hic_binary_v9'])
    software_schema = chromatin_record_schema('SoftwareBinding')
    # This is the same real software schema/literal conjunction that made the
    # old provider representation contradictory for a Cooler binding.
    assignment = {'anyOf': [{'allOf': [software_schema, {'const': hic}]}]}
    schema = host_schema(assignment)
    encoded = proposed(hic)
    Draft202012Validator(runtime._action_generation_schema(schema)).validate(encoded)
    decoded = runtime._decode_action_response(encoded, schema)
    Draft202012Validator(schema).validate(decoded)
    assert decoded['selection']['assignment'] == hic


def test_bvbrc_custody_uses_original_complete_selection_for_legacy_transport(tmp_path):
    from test_bvbrc_appservice_custody import SavedRecords, launch_assignment as app_launch
    with Store(tmp_path / 'state') as store:
        records = SavedRecords(store)
        child = records.child(records.root, 'launch', app_launch(), 0, model=False)
        action = json.loads(records.journal.row('runtime_actions', records.root.episode_id, 0)['action'])
        properties = {key: {} for key in action}
        properties['kind'] = {'const': 'episode_child'}
        properties['assignment'] = {'anyOf': [{**obj({key: {} for key in child.assignment}),
            'properties': {**{key: {} for key in child.assignment}, 'launch_instructions': {'type': 'object'}}}]}
        schema = obj({'selection': obj(properties), 'report_update': obj({})})
        raw = {'selection': deepcopy(action), 'report_update': {}}
        raw['selection']['assignment']['launch_instructions'] = None
        records.journal.save('runtime_model_calls', {'episode_id': records.root.episode_id, 'call_index': 0,
            'purpose': 'decision', 'request': json.dumps({'context': {}, 'schema': schema}), 'response': json.dumps(raw)})
        before = dict(records.journal.row('runtime_model_calls', records.root.episode_id, 0))
        records.custody.authenticate(child)
        assert dict(records.journal.row('runtime_model_calls', records.root.episode_id, 0)) == before
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0




def test_current_recorded_full_profile_proves_exact_decoding_before_admission(connected, monkeypatch):
    case = connected
    monkeypatch.setattr(case.workflow, 'contract_information_profile', lambda _: CONTRACT_INFORMATION_PROFILE)
    assignment = {**case.assignment, 'launch_instructions': None}
    response = {'selection': {**case.selection, 'assignment': json.dumps(assignment)}, 'report_update': {}}
    returned, index, context, schema = choose(case, response)
    before = dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index))
    sent = json.loads(before['request'])
    exchanges = deepcopy(case.workflow.decision_exchanges.rows(case.source.episode_id, index))
    case.source.calls = 0
    replayed, same_index, same_context, same_schema = asyncio.run(case.source.call({}, obj({})))
    decoded = runtime._decode_recorded_action_response(replayed, same_schema, exchanges=exchanges,
        exchange_schema=sent['contract_information']['exchange_schema'], unproven_replay=True)
    assert decoded == runtime._decode_action_response(response, case.schema)
    assert decoded['selection']['assignment'] == assignment
    unit = case.source.apply_response(replayed, same_index, same_context, same_schema)
    assert unit is not None, case.source.feedback
    assert unit.child.request.message.as_record()['episode_assignment'] == assignment
    assert dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index)) == before
    assert case.workflow.decision_exchanges.rows(case.source.episode_id, index) == exchanges
    no_observations(case)


@pytest.mark.parametrize('marker', [
    {'version': 'unknown', 'action_schema_sha256': '0' * 64},
    {'version': runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': '0' * 64},
])
def test_unsaved_custody_reuses_runtime_marker_validation(tmp_path, marker):
    from test_bvbrc_appservice_custody import SavedRecords, launch_assignment as app_launch
    from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
    with Store(tmp_path / 'state') as store:
        records = SavedRecords(store)
        child = records.child(records.root, 'launch', app_launch(), 0, save=False, action=False)
        row = dict(records.journal.row('runtime_model_calls', records.root.episode_id, 0))
        sent = json.loads(row['request'])
        sent['assignment_transport'] = marker
        records.journal.save('runtime_model_calls', {**row, 'request': runtime._json(sent)})
        with pytest.raises(AppServiceCustodyError, match='parent_selection_invalid'):
            records.custody.authenticate(child, allow_unsaved=True)
        assert records.journal.row('runtime_actions', records.root.episode_id, 0) is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
