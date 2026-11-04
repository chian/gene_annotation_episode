"""Engineering controls for finite reviewed code repairs; no scientific results.

The old-hash active request below is explicitly an engineered journal fixture.
Authentic355 checkpoint continuation is verified by the separate retained test.
These owner-context checks establish no whole-run configuration migration.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

import pytest
from method_loop import Episode, EpisodeGoal, EpisodeRequest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_composition import scientific_binding_compatible
from gene_annotation_episode.runtime import DecisionSource, Record, TypedReportContract
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.state import Store
from test_runtime import FixtureController
from test_scientific_process_runtime import Scenario


RECORDED = 'e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94'
PRIOR = 'e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8'
PRE_ORF = '4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe'
PRE_SAVED_ORF = '7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077'
PRE_RETURN_ORF = '92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e'
PRE_REFERENCE_EDIT = 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'
ACTUAL = 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'
UNKNOWN = '0' * 64
REVIEWED_PAIRS = ((RECORDED, PRIOR), (RECORDED, PRE_ORF), (PRIOR, PRE_ORF),
    (RECORDED, PRE_SAVED_ORF), (PRIOR, PRE_SAVED_ORF), (PRE_ORF, PRE_SAVED_ORF),
    (RECORDED, PRE_RETURN_ORF), (PRIOR, PRE_RETURN_ORF), (PRE_ORF, PRE_RETURN_ORF), (PRE_SAVED_ORF, PRE_RETURN_ORF),
    (RECORDED, PRE_REFERENCE_EDIT), (PRIOR, PRE_REFERENCE_EDIT), (PRE_ORF, PRE_REFERENCE_EDIT),
    (PRE_SAVED_ORF, PRE_REFERENCE_EDIT), (PRE_RETURN_ORF, PRE_REFERENCE_EDIT),
    (RECORDED, ACTUAL), (PRIOR, ACTUAL), (PRE_ORF, ACTUAL), (PRE_SAVED_ORF, ACTUAL),
    (PRE_RETURN_ORF, ACTUAL), (PRE_REFERENCE_EDIT, ACTUAL))
OBJECTIVE = 'What evidence is retained for the supplied engineering fixture?'
PURPOSE = 'Return the declared engineering status without performing science.'
SCHEMA = obj({'status': {'type': 'string', 'enum': ['unresolved']}})
INITIAL = {'status': 'unresolved'}


def _descriptor(hash_=ACTUAL):
    """Literal descriptors test the comparator; they grant no runtime authority."""
    return {'version': 'scientific_process_episodes_v8', 'binding_id': 'scientific_process',
        'implementation_sha256': hash_, 'configuration': {
            'library': {'version': 'scientific_process_library_snapshot_v2',
                'library_id': 'a' * 64, 'manifest_sha256': 'b' * 64},
            'tool_library': {'version': 'scientific_tool_library_v2', 'catalog_sha256': 'c' * 64},
            'child_roles': ['scientific_process', 'literature']}}


@pytest.mark.parametrize('actual', [RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT, ACTUAL, UNKNOWN])
@pytest.mark.parametrize('recorded', [RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT, ACTUAL, UNKNOWN])
def test_only_exact_identity_or_approved_direction_is_compatible(actual, recorded):
    current, saved = _descriptor(actual), _descriptor(recorded)
    before = deepcopy((current, saved))
    expected = actual == recorded or (recorded, actual) in REVIEWED_PAIRS
    assert scientific_binding_compatible(current, saved) is expected
    assert (current, saved) == before


def test_compatibility_roster_is_only_the_explicit_reviewed_pairs():
    from gene_annotation_episode.episode_composition import _SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY
    assert _SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY == REVIEWED_PAIRS


@pytest.mark.parametrize('value', [None, True, 1, 1.0, 'descriptor', [], {},
    {'version': 'scientific_process_episodes_v8'}])
def test_identical_non_descriptors_are_rejected_before_the_identity_shortcut(value):
    assert scientific_binding_compatible(value, deepcopy(value)) is False


@pytest.mark.parametrize('field,value', [
    ('version', []), ('version', 'scientific_process_episodes_v99'), ('binding_id', 'literature'),
    ('configuration', []), ('configuration', None), ('implementation_sha256', True),
    ('implementation_sha256', []), ('implementation_sha256', 'A' * 64),
    ('implementation_sha256', 'a' * 63),
])
def test_identical_malformed_descriptor_fields_still_reject(field, value):
    descriptor = _descriptor()
    descriptor[field] = value
    assert scientific_binding_compatible(descriptor, deepcopy(descriptor)) is False


@pytest.mark.parametrize('change', ['library', 'tool_library', 'roles', 'retrieval', 'extra_configuration',
    'extra_descriptor', 'legacy_version', 'configuration_scalar_type'])
@pytest.mark.parametrize('recorded_hash', [RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT])
def test_approved_hash_pair_does_not_permit_other_descriptor_changes(change, recorded_hash):
    current, saved = _descriptor(), _descriptor(recorded_hash)
    if change == 'library':
        saved['configuration']['library']['manifest_sha256'] = 'd' * 64
    elif change == 'tool_library':
        saved['configuration']['tool_library']['catalog_sha256'] = 'd' * 64
    elif change == 'roles':
        saved['configuration']['child_roles'].reverse()
    elif change == 'retrieval':
        saved['configuration']['tool_retrieval'] = {'mode': 'semantic_fast_v1'}
    elif change == 'extra_configuration':
        saved['configuration']['unexpected'] = None
    elif change == 'extra_descriptor':
        saved['unexpected'] = None
    elif change == 'legacy_version':
        current['version'] = saved['version'] = 'scientific_process_episodes_v7'
    else:
        current['configuration']['engineering_scalar'] = 1
        saved['configuration']['engineering_scalar'] = True
    assert scientific_binding_compatible(current, saved) is False


class UnusedProvider:
    def __init__(self):
        self.released = []

    async def complete(self, *args, **kwargs):
        raise AssertionError('compatibility control attempted a model call')

    async def release(self, *args, **kwargs):
        self.released.append(args[0])


class MetadataProvider(UnusedProvider):
    """Choose one real library-guidance read; fabricate no scientific outcome."""
    def __init__(self):
        super().__init__()
        self.contexts = []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING' and self.contexts == []
        self.contexts.append(deepcopy(context))
        return {'selection': {'kind': 'tool', 'tool': 'process.entry', 'arguments': {'option_id': 'P01'}},
            'report_update': deepcopy(INITIAL)}


def _metadata_controller(path, initial):
    """Declare one completed metadata action before Workflow construction."""
    return FixtureController(str(path), initial, 1)


def _prepare(workflow, parent, assignment, scope):
    return workflow.scientific_process_binding.prepare_invocation(
        workflow.binding_context(parent.source), 'scientific_process', assignment, scope,
        'engineering:explicit-construction', invocation={'objective': OBJECTIVE, 'purpose': PURPOSE,
            'report_schema': SCHEMA, 'initial_report': INITIAL})


def _build_child(workflow, parent, scope, prepared, *, key='engineered_old_capture'):
    contract = TypedReportContract(PURPOSE, deepcopy(SCHEMA), workflow.resolver(scope, grain='scientific_process'))
    return workflow.build('scientific_process', key, OBJECTIVE, scope, parent=parent.goal,
        parent_path=parent.source.path, contract=contract, initial=deepcopy(INITIAL),
        episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'])


def _assembled_source(workflow, parent, scope, prepared, key):
    """Assemble request operands; this helper creates no episode journal row."""
    path = (*parent.source.path, ('scientific_process', key))
    identity = Episode.identity(workflow.context, workflow.grains['scientific_process'], key,
        parent_path=parent.source.path)
    contract = TypedReportContract(PURPOSE, deepcopy(SCHEMA), workflow.resolver(scope, grain='scientific_process'))
    goal = EpisodeGoal.child(parent.goal, objective=OBJECTIVE, result_contract=contract.schema)
    message = {'scope': plain(scope), 'initial_report': deepcopy(INITIAL),
        'episode_assignment': deepcopy(prepared['assignment']),
        'scientific_process': deepcopy(prepared['scientific_process']),
        'scientific_invocation_ref': scientific_invocation_ref(workflow.run_id, path),
        'knowledge_inheritance': workflow.receipts.bind(identity.episode_id, parent.source.episode_id)}
    request = EpisodeRequest(goal, Record(message), contract)
    return DecisionSource(workflow, path, request, scope)


@pytest.fixture
def active_engineering_request(tmp_path, request):
    with Store(tmp_path / 'store') as store:
        case = Scenario(tmp_path, store)
        case.factory = _metadata_controller
        workflow = case.workflow(UnusedProvider())
        parent = workflow.build('annotation', 'root', 'Construct the explicit engineering request.', case.scope)
        assignment = case.commission()['selection']['assignment']
        prepared = _prepare(workflow, parent, assignment, case.scope)
        assert prepared['scientific_process']['mechanics_binding']['implementation_sha256'] == ACTUAL
        # Seed one explicitly ENGINEERED saved-active request through the real
        # Journal publisher, BEFORE current construction. This is its first row;
        # no existing request, result, observation or source record is rewritten.
        # The authentic355 historical prefix belongs to the separate retained test.
        current = _assembled_source(workflow, parent, case.scope, prepared, 'engineered_old_capture')
        initial_credit = workflow.source_credit_view(current)['credit']
        historical = deepcopy(prepared)
        recorded_hash = getattr(request, 'param', RECORDED)
        assert recorded_hash in (RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT)
        historical['scientific_process']['mechanics_binding']['implementation_sha256'] = recorded_hash
        saved = _assembled_source(workflow, parent, case.scope, historical, 'engineered_old_capture')
        assert workflow.journal.row('runtime_episodes', saved.episode_id) is None
        workflow.journal.save('runtime_episodes', {'episode_id': saved.episode_id,
            'path': json.dumps(saved.path), 'request': json.dumps(plain(saved.request.as_record())),
            'initial_credit': initial_credit, 'state': 'active', 'completion': None, 'archive': None})
        child = _build_child(workflow, parent, case.scope, prepared)
        yield case, workflow, parent, child, prepared


@pytest.mark.parametrize('active_engineering_request', [RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT], indirect=True)
def test_real_reopening_and_active_constructor_preserve_engineered_original_request(active_engineering_request):
    case, original, parent, child, prepared = active_engineering_request
    stored = dict(original.journal.row('runtime_episodes', child.source.episode_id))
    request = plain(child.request.as_record())
    assert stored['state'] == 'active' and stored['completion'] is stored['archive'] is None
    recorded_hash = request['message']['scientific_process']['mechanics_binding']['implementation_sha256']
    assert recorded_hash in (RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT)
    descriptors = deepcopy(case.descriptors)
    descriptors[0]['implementation_sha256'] = recorded_hash
    case.descriptors = descriptors
    # The real Workflow constructor exercises both generic composition checks.
    reopened = case.workflow(UnusedProvider())
    actual = reopened.scientific_process_binding.as_record()
    assert actual['implementation_sha256'] == ACTUAL
    assert actual != descriptors[0] and scientific_binding_compatible(actual, descriptors[0])
    restored_parent = reopened.build('annotation', 'root', 'Construct the explicit engineering request.', case.scope)
    current_prepared = _prepare(reopened, restored_parent, prepared['assignment'], case.scope)
    assert current_prepared['scientific_process']['mechanics_binding'] == actual
    rebuilt = _build_child(reopened, restored_parent, case.scope, current_prepared)
    assert plain(rebuilt.request.as_record()) == request
    assert dict(reopened.journal.row('runtime_episodes', child.source.episode_id)) == stored
    context = reopened.binding_context(rebuilt.source)
    reopened.scientific_process_binding.validate_context(context)
    reopened.scientific_process_binding.validate_execution_context(context)
    assert reopened.scientific_process_binding.as_record() == actual
    fresh = _build_child(reopened, restored_parent, case.scope, current_prepared, key='fresh_current_capture')
    assert fresh.request.message.as_record()['scientific_process']['mechanics_binding'] == actual
    fresh_context = reopened.binding_context(fresh.source)
    assert reopened.scientific_process_binding.restore_saved_process(fresh_context,
        original_request=plain(fresh.request.as_record())) == plain(fresh_context.request)['message']['scientific_process']
    for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_forms'):
        assert case.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
    assert case.tools.calls == []


@pytest.mark.parametrize('change', ['goal', 'root_task', 'request_scope', 'context_scope',
    'request_assignment', 'context_assignment', 'schema', 'selection', 'initial_report', 'mechanics'])
def test_active_projection_rejects_every_non_mechanics_change(active_engineering_request, change):
    case, workflow, parent, child, _ = active_engineering_request
    original = plain(child.request.as_record())
    candidate = deepcopy(original)
    candidate['message']['scientific_process']['mechanics_binding'] = workflow.scientific_process_binding.as_record()
    context = workflow.binding_context(child.source)
    scope, assignment = plain(context.scope), plain(context.assignment)
    if change == 'goal':
        candidate['goal']['objective'] = 'A changed question'
    elif change == 'root_task':
        candidate['goal']['task_context']['root_objective'] = 'A changed root question'
    elif change == 'request_scope':
        candidate['message']['scope']['extra'] = True
    elif change == 'context_scope':
        scope['extra'] = True
    elif change == 'request_assignment':
        candidate['message']['episode_assignment']['context']['condition'] = 'changed'
    elif change == 'context_assignment':
        assignment['context']['condition'] = 'changed'
    elif change == 'schema':
        candidate['report_contract']['measurements']['schema']['properties']['status']['enum'].append('changed')
    elif change == 'selection':
        candidate['message']['scientific_process']['selection']['child_tool_info'][0]['name'] = 'fixture.excluded'
    elif change == 'initial_report':
        candidate['message']['initial_report']['status'] = 'changed'
    else:
        candidate['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = UNKNOWN
    changed = replace(context, request=candidate, scope=scope, assignment=assignment)
    with pytest.raises(ContractError, match='scientific_saved_identity_mismatch'):
        workflow.scientific_process_binding.restore_saved_process(changed, original_request=original)
    assert plain(child.request.as_record()) == original
    assert workflow.scientific_process_binding.as_record()['implementation_sha256'] == ACTUAL


@pytest.mark.parametrize('recorded_hash', [UNKNOWN, ACTUAL])
def test_supplied_original_cannot_override_the_authenticated_saved_request(active_engineering_request, recorded_hash):
    _, workflow, _, child, _ = active_engineering_request
    context = workflow.binding_context(child.source)
    original = plain(context.request)
    original['message']['scientific_process']['mechanics_binding']['implementation_sha256'] = recorded_hash
    candidate = deepcopy(original)
    candidate['message']['scientific_process']['mechanics_binding'] = workflow.scientific_process_binding.as_record()
    with pytest.raises(ContractError, match='scientific_saved_request_mismatch'):
        workflow.scientific_process_binding.restore_saved_process(
            replace(context, request=candidate), original_request=original)


@pytest.mark.parametrize('active_engineering_request', [RECORDED, PRIOR, PRE_ORF, PRE_SAVED_ORF, PRE_RETURN_ORF, PRE_REFERENCE_EDIT], indirect=True)
@pytest.mark.parametrize('port', ['build', 'context', 'binding_dispatch', 'workflow_dispatch'])
def test_fresh_old_mechanics_have_no_saved_active_authority(active_engineering_request, port):
    case, workflow, parent, child, prepared = active_engineering_request
    historical = deepcopy(prepared)
    historical['scientific_process']['mechanics_binding'] = deepcopy(
        plain(child.request.as_record())['message']['scientific_process']['mechanics_binding'])
    source = _assembled_source(workflow, parent, case.scope, historical, 'fresh_fabricated_old_capture')
    context = workflow.binding_context(source)
    assert workflow.journal.row('runtime_episodes', source.episode_id) is None
    assert workflow.services.scientific_saved_request(context) is None
    assert workflow.scientific_process_binding.restore_saved_process(context,
        original_request=plain(context.request)) is None
    with pytest.raises(ContractError, match='scientific_.*identity_mismatch'):
        if port == 'build':
            _build_child(workflow, parent, case.scope, historical, key='fresh_fabricated_old_capture')
        elif port == 'context':
            workflow.scientific_process_binding.validate_context(context)
        elif port == 'binding_dispatch':
            workflow.scientific_process_binding.validate_execution_context(context)
        else:
            asyncio.run(workflow.execute(source, 'fixture.inspect', {'value': 1}, decision_index=0,
                operation_key=f'{workflow.run_id}:{source.episode_id}:0'))
    assert workflow.journal.row('runtime_episodes', source.episode_id) is None
    assert case.tools.calls == []
    assert case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0


@pytest.mark.parametrize('change', ['run', 'role', 'episode', 'path'])
def test_active_reader_rejects_context_identity_mismatch(active_engineering_request, change):
    _, workflow, _, child, _ = active_engineering_request
    context = workflow.binding_context(child.source)
    changed = (replace(context, run_id='unrelated-run') if change == 'run' else
        replace(context, role='annotation', path=context.path[:-1]) if change == 'role' else
        replace(context, episode_id='unrelated-episode') if change == 'episode' else
        replace(context, path=(*context.path[:-1], ('scientific_process', 'other-child'))))
    with pytest.raises(ValueError, match='scientific_saved_request_identity_mismatch'):
        workflow.services.scientific_saved_request(changed)


@pytest.mark.parametrize('state,completion,archive', [
    ('yielded', None, None), ('active', {'engineering_only': True}, None),
    ('active', None, {'engineering_only': True}),
])
def test_active_reader_rejects_nonactive_or_inconsistent_lifecycle_rows(
        active_engineering_request, state, completion, archive):
    case, workflow, parent, _, prepared = active_engineering_request
    historical = deepcopy(prepared)
    historical['scientific_process']['mechanics_binding']['implementation_sha256'] = RECORDED
    source = _assembled_source(workflow, parent, case.scope, historical, 'engineered_ineligible_lifecycle')
    assert workflow.journal.row('runtime_episodes', source.episode_id) is None
    # These deliberately ineligible first-insert records are denial fixtures,
    # not claimed episode completions, archives or scientific observations.
    workflow.journal.save('runtime_episodes', {'episode_id': source.episode_id,
        'path': json.dumps(source.path), 'request': json.dumps(plain(source.request.as_record())),
        'initial_credit': 0, 'state': state,
        'completion': None if completion is None else json.dumps(completion),
        'archive': None if archive is None else json.dumps(archive)})
    context = workflow.binding_context(source)
    assert workflow.services.scientific_saved_request(context) is None
    assert workflow.scientific_process_binding.restore_saved_process(context,
        original_request=plain(context.request)) is None
    assert case.tools.calls == []


@pytest.mark.parametrize('active_engineering_request,mechanics', [
    (RECORDED, 'recorded'), (PRIOR, 'recorded'), (PRE_ORF, 'recorded'),
    (PRE_SAVED_ORF, 'recorded'), (PRE_RETURN_ORF, 'recorded'), (PRE_REFERENCE_EDIT, 'recorded'), (RECORDED, 'current')],
    indirect=['active_engineering_request'])
def test_authenticated_metadata_action_closed_request_still_prohibits_dispatch(active_engineering_request, mechanics):
    case, workflow, parent, child, prepared = active_engineering_request
    if mechanics == 'current':
        child = _build_child(workflow, parent, case.scope, prepared, key='metadata_action_current_capture')
    provider = MetadataProvider()
    workflow.provider = provider
    context = workflow.binding_context(child.source)
    original = plain(context.request)
    original_request_text = workflow.journal.row('runtime_episodes', child.source.episode_id)['request']
    # Its declared controller yields after one actual library-metadata action.
    # The scripted response chooses guidance; it supplies no scientific result.
    # Real closure callbacks publish the archive, completion and unresolved form.
    original_context = workflow.context
    boundary = type(original_context).from_commission(tree=original_context.tree, run_id=workflow.run_id,
        parent_path=parent.source.path, parent_goal_id=parent.goal.goal_id,
        child_goal_id=child.goal.goal_id, grain=child.grain.name, key=child.key)
    workflow.context = boundary
    try:
        record = asyncio.run(child.run_async(boundary))
        assert case.store.db.execute('SELECT count(*) FROM runtime_forms').fetchone()[0] == 0
        assert workflow.services.scientific_closed_request(context) is None
        assert workflow.services.scientific_saved_request(context) is None
        assert workflow.services.scientific_saved_request(context, active_only=False) == original
        workflow.scientific_process_binding.validate_context(context)
        assert workflow.scientific_process_binding.restore_saved_process(context,
            original_request=original, active_only=False) == original['message']['scientific_process']
        with pytest.raises(ContractError, match='scientific_.*identity_mismatch'):
            workflow.scientific_process_binding.validate_execution_context(context)
        result = asyncio.run(child.build_result(record))
        assert plain(result.as_record()) == {'form': INITIAL}
        row = workflow.journal.row('runtime_episodes', child.source.episode_id)
        assert row['state'] == 'yielded' and row['completion'] is not None and row['archive'] is not None
        assert row['request'] == original_request_text
        assert workflow.services.scientific_saved_request(context) is None
        assert workflow.services.scientific_closed_request(context) == original
        assert workflow.scientific_process_binding.restore_closed_process(context) == original['message']['scientific_process']
        workflow.scientific_process_binding.validate_context(context)
        with pytest.raises(ContractError, match='scientific_execution_identity_mismatch'):
            workflow.scientific_process_binding.validate_execution_context(context)
        with pytest.raises(ContractError, match='scientific_execution_identity_mismatch'):
            asyncio.run(workflow.execute(child.source, 'fixture.inspect', {'value': 1}, decision_index=0,
                operation_key=f'{workflow.run_id}:{child.source.episode_id}:0'))
    finally:
        workflow.context = original_context
    assert case.tools.calls == []
    for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations'):
        assert case.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 1
    selected, = [json.loads(row[0]) for row in case.store.db.execute('SELECT action FROM runtime_actions')]
    assert selected == {'kind': 'tool', 'tool': 'process.entry', 'arguments': {'option_id': 'P01'}}
    actual, = [json.loads(row[0]) for row in case.store.db.execute('SELECT result FROM runtime_actions')]
    assert actual['status'] == 'completed' and len(provider.contexts) == 1


@pytest.mark.parametrize('value', [0, 1, None, 'False'])
def test_saved_reader_lifecycle_flag_requires_an_explicit_boolean(active_engineering_request, value):
    _, workflow, _, child, _ = active_engineering_request
    context = workflow.binding_context(child.source)
    with pytest.raises(ValueError, match='scientific_saved_request_active_flag_invalid'):
        workflow.services.scientific_saved_request(context, active_only=value)


def test_uncontracted_annotation_root_has_no_requested_received_sources(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = Scenario(tmp_path, store)
        workflow = case.workflow(UnusedProvider())
        parent = workflow.build('annotation', 'root', 'Read only the actual root received-fact declaration.', case.scope)
        context = workflow.binding_context(parent.source)
        assert context.role == 'annotation' and plain(context.request)['report_contract'] is None
        def unrequested(*args, **kwargs):
            raise AssertionError('uncontracted root queried an unrequested scientific fact source')
        monkeypatch.setattr(workflow.services, 'molecular_received_facts', unrequested)
        monkeypatch.setattr(workflow.services, 'protein_structure_action_received_facts', unrequested)
        assert workflow.scientific_process_binding.received_report_facts(context) == {}
        assert workflow.episode_bindings.received_report_facts(context) == {}
        assert workflow.scientific_process_binding.as_record()['implementation_sha256'] == ACTUAL
        assert case.tools.calls == []
        for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'runtime_forms'):
            assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


def test_unknown_binding_in_an_actual_saved_active_row_still_cannot_restore_or_dispatch(active_engineering_request):
    case, workflow, parent, _, prepared = active_engineering_request
    historical = deepcopy(prepared)
    historical['scientific_process']['mechanics_binding']['implementation_sha256'] = UNKNOWN
    source = _assembled_source(workflow, parent, case.scope, historical, 'engineered_unknown_active')
    assert workflow.journal.row('runtime_episodes', source.episode_id) is None
    # An explicitly engineered first-insert denial record. Its existence alone
    # must not turn an unreviewed implementation into restoration authority.
    workflow.journal.save('runtime_episodes', {'episode_id': source.episode_id,
        'path': json.dumps(source.path), 'request': json.dumps(plain(source.request.as_record())),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    context = workflow.binding_context(source)
    before = dict(workflow.journal.row('runtime_episodes', source.episode_id))
    original = workflow.services.scientific_saved_request(context)
    assert original == plain(context.request)
    assert workflow.scientific_process_binding.restore_saved_process(context, original_request=original) is None
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        workflow.scientific_process_binding.validate_context(context)
    with pytest.raises(ContractError, match='scientific_filled_identity_mismatch'):
        asyncio.run(workflow.execute(source, 'fixture.inspect', {'value': 1}, decision_index=0,
            operation_key=f'{workflow.run_id}:{source.episode_id}:0'))
    assert dict(workflow.journal.row('runtime_episodes', source.episode_id)) == before
    assert case.tools.calls == []
    for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_forms'):
        assert case.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
