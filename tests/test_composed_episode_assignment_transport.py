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


PACKET = Path(__file__).resolve().parents[1] / 'verification/tool_graders_composed_assignment_transport_2026-10-27_458'
ORIGINAL_REPO = Path(os.environ.get('TRANSPORT458_ORIGINAL_REPO', Path(__file__).resolve().parents[1]))
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


def test_pinned_old_generation_and_decoder_are_exact_finite_compatibility(connected, historical):
    schema = connected.schema
    assert runtime._action_generation_schema(schema, _legacy_episode_assignments=True) == historical.generate(schema)
    response = {'selection': deepcopy(connected.selection), 'report_update': {}}
    response['selection']['assignment']['launch_instructions'] = None
    old = historical.decode(response, schema)
    assert 'launch_instructions' not in old['selection']['assignment']
    assert runtime._decode_action_response(response, schema, _legacy_episode_assignments=True) == old
    assert runtime._decode_action_response(response, schema)['selection']['assignment']['launch_instructions'] is None
    assert runtime._decode_recorded_action_response(response, schema, recorded_selection=old['selection']) == old
    wrong = {**old['selection'], 'purpose': 'A different requested purpose'}
    with pytest.raises(ValueError, match='original_action_response_selection_mismatch'):
        runtime._decode_recorded_action_response(response, schema, recorded_selection=wrong)


@pytest.mark.parametrize('profile', [False, True])
def test_old_recorded_pending_exchange_and_completed_selection_replay_are_unchanged(connected, historical, monkeypatch, profile):
    case = connected
    # Freeze a historical frame through the actual exchange writer, then decode
    # it through today's boundary. No retained production record is modified.
    if profile:
        monkeypatch.setattr(case.workflow, 'contract_information_profile', lambda _: CONTRACT_INFORMATION_PROFILE)
    response = {'selection': deepcopy(case.selection), 'report_update': {}}
    response['selection']['assignment']['launch_instructions'] = None
    with monkeypatch.context() as patch:
        patch.setattr(runtime, '_action_generation_schema', historical.generate)
        returned, index, context, schema = choose(case, response)
    original_rows = deepcopy(case.workflow.decision_exchanges.rows(case.source.episode_id, index))
    saved = json.loads(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index)['request'])
    if profile:
        case.source.validate_contract_exchange_history(saved, index)
    exchange_schema = saved.get('contract_information', {}).get('exchange_schema')
    # Reopen the pending decision from its serialized host record before any
    # action exists. This exposes property-order loss in markerless histories.
    case.source.calls = 0
    returned, index, context, schema = asyncio.run(case.source.call({}, obj({})))
    if profile:
        assert runtime._json(original_rows[0]['request']['output_schema']) == runtime._json(
            runtime._action_generation_schema(exchange_schema, _legacy_episode_assignments=True))
    else:
        selected_schema = obj({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})
        selected_schema['required'] = ['response_type', *schema['required']]
        recorded = original_rows[0]['request']['output_schema']['properties']['response']['anyOf'][1]
        regenerated = runtime._action_generation_schema(selected_schema, _legacy_episode_assignments=True)
        assert recorded != regenerated
        assert runtime._same_action_schema_required_members(recorded, regenerated)
    assert runtime._decode_recorded_action_response(returned, schema, exchanges=original_rows,
        exchange_schema=exchange_schema) == historical.decode(response, schema)
    unit = case.source.apply_response(returned, index, context, schema)
    assert unit is not None, case.source.feedback
    selected = case.workflow.journal.row('runtime_actions', case.source.episode_id, index)
    assert json.loads(selected['action']) == historical.decode(response, schema)['selection']
    no_observations(case)
    # An explicit synthetic completed outcome exercises replay custody; it does
    # not claim that the native /bin/true job was run or create a measurement.
    case.workflow.journal.save('runtime_actions', {'episode_id': case.source.episode_id, 'decision_index': index,
        'action': selected['action'], 'result': json.dumps({'status': 'completed', 'fixture': True}), 'credit': 0})
    before_action = dict(case.workflow.journal.row('runtime_actions', case.source.episode_id, index))
    before_call = dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index))
    case.source.calls = 0
    replayed, same_index, same_context, old_schema = asyncio.run(case.source.call({}, obj({})))
    assert (replayed, same_index, same_context, old_schema) == (returned, index, context, schema)
    assert case.source.apply_response(replayed, same_index, same_context, old_schema) is not None
    assert dict(case.workflow.journal.row('runtime_actions', case.source.episode_id, index)) == before_action
    assert dict(case.workflow.journal.row('runtime_model_calls', case.source.episode_id, index)) == before_call
    assert case.workflow.decision_exchanges.rows(case.source.episode_id, index) == original_rows
    assert len(case.provider.schemas) == 1
    no_observations(case)
    if profile:
        changed = deepcopy(original_rows[0]['request'])
        changed['output_schema']['description'] = 'unrecorded alteration'
        with pytest.raises(runtime.WorkflowError, match='original_contract_exchange_request_mismatch'):
            case.source.validate_contract_exchange_request(changed, saved, index,
                changed['restoration']['snapshot'], changed['restoration']['pending_public_exchanges'])


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


def test_actual_retained_cooler_selection_omits_runtime_and_roundtrips_read_only(historical):
    root = ORIGINAL_REPO / 'verification/tool_graders_chromatin_workflow_2026-10-27_451'
    selection = json.loads((root / 'probe001/selected-branches.json').read_bytes())[0]['candidate']
    database = root / 'check002/temporary/pytest/chromatin4510/state/state.sqlite3'
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        saved = json.loads(connection.execute('SELECT request FROM runtime_model_calls ORDER BY rowid DESC LIMIT 1').fetchone()[0])
    schema = saved['schema']
    direct = {'selection': selection, 'report_update': {}}
    Draft202012Validator(schema).validate(direct)
    assert 'native_runtime' not in selection['assignment']['requested_job']['native_chromatin_interactions']['software']
    assert not Draft202012Validator(historical.generate(schema)).is_valid(direct)
    encoded = {'selection': {**selection, 'assignment': json.dumps(selection['assignment']),
        'scope': {**selection['scope'], 'read_selection_refs': None, 'segments': None}}, 'report_update': {}}
    Draft202012Validator(runtime._action_generation_schema(schema)).validate(encoded)
    assert runtime._decode_action_response(encoded, schema) == direct
    assert runtime._decode_action_response(direct, schema) == direct


def test_actual_completed_451_actions_replay_against_original_saved_selections_read_only(historical):
    database = ORIGINAL_REPO / ('verification/tool_graders_chromatin_workflow_2026-10-27_451/'
        'check001/temporary/pytest/chromatin4510/state/state.sqlite3')
    before_bytes = hashlib.sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        before = connection.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        rows = connection.execute('SELECT calls.request,calls.response,actions.action,actions.result '
            'FROM runtime_actions AS actions JOIN runtime_model_calls AS calls '
            'ON calls.run_id=actions.run_id AND calls.episode_id=actions.episode_id '
            'AND calls.call_index=actions.decision_index '
            'WHERE json_extract(actions.action,\'$.kind\')=\'episode_child\' '
            'AND actions.result IS NOT NULL').fetchall()
        assert rows
        changed_transports = 0
        for sent, raw, action, result in rows:
            schema = json.loads(sent)['schema']
            response, selected = json.loads(raw), json.loads(action)
            old = historical.decode(response, schema)
            assert runtime._json(old['selection']) == runtime._json(selected)
            decoded = runtime._decode_recorded_action_response(response, schema, recorded_selection=selected)
            assert runtime._json(decoded['selection']) == runtime._json(selected)
            Draft202012Validator(schema['properties']['selection']).validate(decoded['selection'])
            changed_transports += runtime._json(runtime._decode_action_response(response, schema)['selection']) != runtime._json(selected)
        assert changed_transports > 0  # Real provider-added nulls need the compatibility branch.
        assert connection.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == before
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_bytes


def test_retained_nonnull_hic_runtime_and_absent_cooler_runtime_use_same_atomic_transport():
    from gene_annotation_episode.chromatin_interaction_contracts import chromatin_record_schema
    from gene_annotation_episode.native_chromatin_interaction_contracts import validate_chromatin_software
    hic = json.loads((ORIGINAL_REPO / 'verification/tool_graders_chromatin_hic_binding_2026-10-27_457/check002/HIC_SOFTWARE.json').read_bytes())
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


@pytest.mark.parametrize('transport', ['old_direct', 'current_direct', 'old_exchange',
    'current_exchange'])
def test_unsaved_custody_requires_actual_writer_transport_proof(tmp_path, monkeypatch, historical, transport):
    from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
    from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
    from test_api_bvbrc_appservice import CONFIG
    from test_bvbrc_appservice_custody import request
    from test_execution_wiring import child, form
    from test_public_search import Client

    def forbidden(*args, **kwargs):
        raise AssertionError('Custody verification cannot use live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)

    class Authenticated(Exception):
        pass

    with Store(tmp_path / 'state') as store:
        provider = Provider()
        factory = ExecutionServiceFactory({'selected-api': CONFIG}, {}, 2, 3, .5)
        workflow = runtime.Workflow(store, ToolRegistry(store, clients=Client()), provider,
            tmp_path / 'run', 'custody458',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1),
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'results'), episode_record_receipts=True,
            initial_known_record_refs=[], decision_protocol=None)
        scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        api = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': request(), 'endpoint': 'usable_handoff', 'constraints': {}}
        # Explicit preparation operands make both provider representations valid.
        # Empty native parameters do not claim submission readiness; no prepare,
        # submission, HTTP operation or scientific computation is performed.
        api['request']['parameters'] = {}
        api['request']['start_parameters'] = {name: '' for name in (
            'parent_id', 'workspace', 'base_url', 'container_id', 'user_metadata',
            'reservation', 'data_container_id', 'user_override', 'constraint')}
        api['request']['start_parameters'].update(disable_preflight=0, preflight_data={})
        launch = launch_assignment({'selected-api': api})
        root = workflow.build('annotation', 'root', 'Inspect exact original custody', scope)
        response = child('launch', launch, deepcopy(scope), form('execution_handoff_refs'))
        response['selection']['assignment'] = json.dumps(launch)
        response['selection']['scope'].update(read_selection_refs=None, segments=None)
        provider.responses.append(response)
        returned, index, context, schema = asyncio.run(root.source.call(
            {'visible_record_refs': [], 'scope': scope}, workflow.action_schema(root.source)))
        unit = root.source.apply_response(returned, index, context, schema)
        assert unit is not None, root.source.feedback
        source = unit.child.source
        schema = workflow.action_schema(source)
        context_request = {'visible_record_refs': [], 'scope': scope,
            'tools': workflow.catalog(scope, source=source)}
        raw = child('launch_api', {**api, 'launch_instructions': None}, deepcopy(scope), form('execution_handoff_refs'))
        raw['selection']['scope'].update(read_selection_refs=None, segments=None)
        if transport.startswith('current'):
            raw['selection']['assignment'] = json.dumps(raw['selection']['assignment'])
        if transport.endswith('direct'):
            provider.responses.append(raw)
            call = historical.call if transport == 'old_direct' else runtime.DecisionSource.call
            returned, index, context, schema = asyncio.run(call(source, context_request, schema))
        else:
            workflow.decision_protocol = 'decision_exchange_v1'
            workflow.decision_exchanges = runtime.DecisionExchanges(workflow.journal)
            provider.responses.append({'response': {'response_type': 'select_action', **raw}})
            with monkeypatch.context() as patch:
                if transport == 'old_exchange':
                    patch.setattr(runtime, '_action_generation_schema', historical.generate)
                returned, index, context, schema = asyncio.run(source.call(context_request, schema))
        before = dict(workflow.journal.row('runtime_model_calls', source.episode_id, index))
        exchanges = (() if workflow.decision_exchanges is None else
            deepcopy(workflow.decision_exchanges.rows(source.episode_id, index)))
        sent = json.loads(before['request'])
        current, prior = runtime._decode_action_response(returned, schema), historical.decode(returned, schema)
        Draft202012Validator(schema).validate(current)
        assert workflow.journal.row('runtime_actions', source.episode_id, index) is None
        source.calls = 0
        replayed, same_index, same_context, same_schema = asyncio.run(source.call({}, obj({})))
        if transport == 'old_direct':
            assert 'assignment_transport' not in sent
            assert current['selection'] != prior['selection']
            assert source.apply_response(replayed, same_index, same_context, same_schema) is None
            assert source.feedback['detail'] == 'original_assignment_transport_unavailable'
        captured = []
        authenticate = AppServiceCustody.authenticate
        def inspect(self, context, *, allow_unsaved=False):
            result = authenticate(self, context, allow_unsaved=allow_unsaved)
            if context.role == 'launch_api' and context.path[-1][1] == 'child_0':
                captured.append(runtime._plain(context.assignment))
                raise Authenticated()
            return result
        monkeypatch.setattr(AppServiceCustody, 'authenticate', inspect)
        selection = (prior if transport == 'old_exchange' else current)['selection']
        # Inspect custody separately through actual selected/build construction.
        # Stop immediately at authentication, before child/action persistence.
        if transport == 'old_direct':
            with pytest.raises(AppServiceCustodyError, match='parent_selection_invalid'):
                workflow.selected(source, selection, index)
            assert captured == []
        else:
            with pytest.raises(Authenticated):
                workflow.selected(source, selection, index)
            assert len(captured) == 1
            assert ('launch_instructions' in captured[0]) is (transport != 'old_exchange')
        assert dict(workflow.journal.row('runtime_model_calls', source.episode_id, index)) == before
        if workflow.decision_exchanges is not None:
            assert workflow.decision_exchanges.rows(source.episode_id, index) == exchanges
        assert workflow.journal.row('runtime_actions', source.episode_id, index) is None
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
