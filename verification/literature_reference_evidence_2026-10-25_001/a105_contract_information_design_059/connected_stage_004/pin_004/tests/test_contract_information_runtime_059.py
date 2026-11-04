"""Actual opt-in pending exchanges and host transport; choices are fixtures."""
import asyncio
from copy import deepcopy
from functools import partial
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import (CONTRACT_INFORMATION_PROFILE as PROFILE,
    CONTRACT_ARGUMENT_TRANSPORT as TRANSPORT, metadata_catalog)
from gene_annotation_episode.episode_contract_information import ContractInformationError
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import (Workflow, WorkflowError, _action_generation_schema,
    _decode_action_response, _embedded_tool_schema, TypedReportContract)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.tools import ToolRegistry
from test_literature_kinetic_storage import setup
from test_runtime import FixtureController
from test_runtime_decision_exchanges import ConversationProvider, lookup, select


def information(name, **arguments):
    return {'response': {'response_type': 'request_context', 'lookup': {
        'view': 'composition_information', 'operation': name, 'arguments': arguments}}}


class PresentedProvider(ConversationProvider):
    def __init__(self, script, **options):
        super().__init__(script, **options)
        self.rendered = []
        self.connection = _SessionConnection.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.rendered.append(self.connection._presentation(episode_id, role, instructions, context)[0])
        return await super().complete(episode_id, role, instructions, context, output_schema)


def workflow(path, provider, *, profile=PROFILE, protocol='decision_exchange_v1'):
    store, seed, args = setup(path / 'state')
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    value = Workflow(store, ToolRegistry(store), provider, path / 'run', 'info-run',
        lambda path, initial: FixtureController(str(path), initial, 1), scorer,
        initial_known_record_refs=list(seed.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            contract_information_profile=profile, reference_parent_sources=[args['source_ref']]),), decision_protocol=protocol)
    try:
        root = value.build('annotation', 'root', 'Evaluate supplied synthetic reference evidence', plain(seed.scope))
        episode = value.build('literature', 'case', 'Evaluate the synthetic reference experiment', plain(seed.scope),
            parent=root.request.goal, parent_path=root.source.path,
            contract=TypedReportContract('Fixture source investigation', obj({'saved_parameters': kinetic_cells_schema()}), lambda *_: True), initial={},
            episode_assignment=plain(seed.assignment))
    except BaseException:
        store.close()
        raise
    return store, value, episode, args


def run_child(episode, value):
    async def run():
        scope = value.context.enter(value.grains['annotation'], 'root')
        try:
            return await episode.run_async(value.context)
        finally:
            value.context.leave(scope)
    return asyncio.run(run())


def populate(args):
    return select({'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
        'arguments': json.dumps(args)}, 'report_update': {}})


def test_two_contracts_and_history_stay_in_one_pending_decision_and_one_actual_observation(tmp_path):
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    provider.script = iter([information('episode.operation_contract', operation='literature.kinetic.populate'),
        information('episode.operation_contract', operation='literature.binding.interaction.populate'), lookup(), populate(args)])
    try:
        record = run_child(episode, value)
        assert record.units_consumed == 1
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == 1
        rows = value.decision_exchanges.rows(episode.source.episode_id, 0)
        assert len(rows) == 4
        assert len(provider.contexts[-1]['pending_contract_information']) == 2
        for text in provider.rendered[2:]:
            task, steering = text.split('\n\nSTEERING\n', 1)
            assert 'Requested operation/return information: literature.kinetic.populate' in task
            assert 'Requested operation/return information: literature.binding.interaction.populate' in task
            assert 'Schema information' in task and 'Complete requested contract' not in steering
            for reply in provider.contexts[-1]['pending_contract_information']:
                assert reply['result']['schema_sha256'] not in text
        assert rows[0]['request']['context'] == provider.contexts[0]
        original = json.loads(value.journal.row('runtime_model_calls', episode.source.episode_id, 0)['request'])
        assert original['contract_information']['version'] == PROFILE
        assert len([row for row in original['context']['tools'] if row['name'].startswith('literature.')]) == 19
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()


@pytest.mark.parametrize('profile', [None, PROFILE])
def test_direct_invocation_needs_no_information_lookup_and_preserves_actual_capabilities(tmp_path, profile):
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider, profile=profile)
    provider.script = iter([populate(args)])
    try:
        actual = value.catalog(episode.source.scope, source=episode.source)
        old = _population_catalog()
        selected = [row for row in actual if row['name'].startswith('literature.')]
        assert [{key: row[key] for key in ('name', 'description', 'input_schema')} for row in selected] == old
        assert not {'episode.operation_contract', 'episode.return_contract'} & {row['name'] for row in actual}
        run_child(episode, value)
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        generated = provider.schemas[0]['properties']['response']['anyOf'][1]['properties']['selection']['anyOf']
        for branch in generated:
            name = branch.get('properties', {}).get('tool', {}).get('enum', [None])[0]
            if name and name.startswith('literature.') and profile is not None:
                assert branch['properties']['arguments']['type'] == 'string'
        assert 'x-argument-transport' not in json.dumps(provider.schemas)
        assert 'x-argument-transport' not in provider.rendered[0]
        if profile is None:
            assert 'contract_information_profile' not in value.episode_bindings.as_record()[0]['configuration']
            assert 'Operands for literature.kinetic.populate' in provider.rendered[0]
        else:
            assert value.episode_bindings.as_record()[0]['configuration']['contract_information_profile'] == PROFILE
            assert 'Operands for literature.kinetic.populate' not in provider.rendered[0]
    finally:
        store.close()


def test_explicit_profile_rejects_incompatible_protocol_before_any_model_call(tmp_path):
    provider = PresentedProvider([])
    with pytest.raises(ContractInformationError, match='requires_pending_decision_protocol'):
        store, value, episode, args = workflow(tmp_path, provider, protocol=None)
    assert not provider.contexts


def test_simple_marked_transport_decodes_outer_json_once_preserving_omission_null_and_literals():
    arguments = {'type': 'object', 'additionalProperties': False,
        'properties': {'literal': {'type': 'string'}, 'optional': {'type': ['string', 'null']},
                       'required': {'type': ['number', 'null']}}, 'required': ['literal', 'required']}
    branch = {'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
        'properties': {'kind': {'const': 'tool'}, 'tool': {'const': 'literature.simple'}, 'arguments': arguments},
        'x-argument-transport': TRANSPORT}
    generated = _action_generation_schema(branch)
    assert generated['properties']['arguments']['type'] == 'string'
    assert 'x-argument-transport' not in generated
    for supplied in ({'literal': '{"inner":1}', 'required': None},
                     {'literal': 'null', 'required': None, 'optional': None}):
        decoded = _decode_action_response({'kind': 'tool', 'tool': 'literature.simple', 'arguments': json.dumps(supplied)}, branch)
        assert decoded['arguments'] == supplied
        Draft202012Validator(branch).validate(decoded)


@pytest.mark.parametrize('encoded', ['{"literal":"x","literal":"y","required":null}',
    '{"literal":"x","required":NaN}', '[]', 'not JSON'])
def test_marked_transport_retains_strict_original_json_object_boundary(encoded):
    schema = {'type': 'object', 'required': ['kind', 'tool', 'arguments'], 'additionalProperties': False,
        'properties': {'kind': {'const': 'tool'}, 'tool': {'const': 'literature.simple'},
            'arguments': {'type': 'object'}}, 'x-argument-transport': TRANSPORT}
    with pytest.raises(ValueError):
        _decode_action_response({'kind': 'tool', 'tool': 'literature.simple', 'arguments': encoded}, schema)


def test_original_standalone_reference_scope_and_host_catalog_agreement_are_checked(tmp_path):
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    provider.script = iter([populate(args)])
    try:
        run_child(episode, value)
        saved = json.loads(value.journal.row('runtime_model_calls', episode.source.episode_id, 0)['request'])
        value.validate_contract_information(saved)
        changed = deepcopy(saved)
        entry = next(row for row in changed['context']['tools'] if row['name'] == 'literature.kinetic.populate')
        entry['input_schema']['description'] = 'Wrong independent declaration'
        from gene_annotation_episode.runtime import _digest
        changed['contract_information']['catalog_sha256'] = _digest(changed['context']['tools'])
        with pytest.raises(WorkflowError, match='original_operation_contract_mismatch'):
            value.validate_contract_information(changed)
        standalone = {'type': 'object', '$defs': {'one': {'type': 'integer'}}, 'properties': {'x': {'$ref': '#/$defs/one'}}}
        isolated = _embedded_tool_schema(standalone)
        assert '$id' in isolated and '$id' not in standalone
        assert {key: val for key, val in isolated.items() if key != '$id'} == standalone
    finally:
        store.close()


def rebuild(value, episode, provider):
    """New Workflow, source and provider objects over the original saved run."""
    request = episode.request.as_record()
    source_ref = request['message']['episode_assignment']['source_refs'][0]
    fresh = Workflow(value.store, ToolRegistry(value.store), provider, value.directory, value.run_id,
        lambda path, initial: FixtureController(str(path), initial, 1),
        ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=value.initial_known_record_refs,
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            contract_information_profile=PROFILE, reference_parent_sources=[source_ref]),),
        decision_protocol='decision_exchange_v1')
    root = fresh.build('annotation', 'root', 'Evaluate supplied synthetic reference evidence', episode.source.scope)
    child = fresh.build('literature', 'case', request['goal']['objective'], episode.source.scope,
        parent=root.request.goal, parent_path=root.source.path,
        contract=TypedReportContract(request['report_contract']['decision'],
            request['report_contract']['measurements']['schema'], lambda *_: True),
        initial={}, episode_assignment=request['message']['episode_assignment'])
    return fresh, child


def test_interrupted_pending_decision_reconstructs_original_contracts_without_current_factories(tmp_path, monkeypatch):
    provider = PresentedProvider([], compact_after=(1,))
    store, value, episode, args = workflow(tmp_path, provider)
    provider.script = iter([information('episode.operation_contract', operation='literature.kinetic.populate'),
        information('episode.operation_contract', operation='literature.binding.interaction.populate'), lookup(),
        OSError('fixture provider lost after answered requests')])
    try:
        with pytest.raises(OSError, match='fixture provider lost'):
            run_child(episode, value)
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        before = deepcopy(value.decision_exchanges.rows(episode.source.episode_id, 0))
        original_call = dict(value.journal.row('runtime_model_calls', episode.source.episode_id, 0))
        fresh_provider = PresentedProvider([populate(args)])
        fresh, child = rebuild(value, episode, fresh_provider)
        def forbidden(*_a, **_kw):
            raise AssertionError('Saved pending decision must not reconstruct current declarations')
        with monkeypatch.context() as patch:
            for name in ('catalog', 'report_sources', 'action_schema'):
                patch.setattr(Workflow, name, forbidden)
            result = run_child(child, fresh)
        assert result.units_consumed == 1
        assert len(fresh_provider.contexts) == 1
        context = fresh_provider.contexts[0]
        assert context['kind'] == 'decision_bootstrap'
        assert len(context['restored_public_exchanges']) == 3
        assert 'literature.kinetic.populate' in fresh_provider.rendered[0]
        assert 'Requested operation/return information: literature.binding.interaction.populate' in fresh_provider.rendered[0]
        rows = fresh.decision_exchanges.rows(child.source.episode_id, 0)
        assert rows[:4] == before
        assert rows[-1]['request']['retry_of_exchange_index'] == 3
        assert fresh.journal.row('runtime_model_calls', child.source.episode_id, 0)['request'] == original_call['request']
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        saved = json.loads(original_call['request'])
        child.source.validate_contract_exchange_history(saved, 0)
        # Exercise the actual provider complete/RPC-generation/presentation path.
        from test_literature_experimental_prompt_delivery import LiteratureWire
        wire = LiteratureWire(tmp_path / 'wire')
        async def deliver():
            for row in rows:
                request = row['request']
                await wire.complete(child.source.episode_id, 'REASONING', request['instructions'],
                                    request['context'], request['output_schema'])
        asyncio.run(deliver())
        sent = wire.turns_sent()
        assert len(sent) == len(rows)
        for turn, row in zip(sent, rows):
            assert turn['outputSchema'] == row['request']['output_schema']
            assert 'x-argument-transport' not in json.dumps(turn)
        assert 'Requested operation/return information: literature.binding.interaction.populate' in sent[-1]['input'][0]['text']
        # Original query/result/frame/schema are immutable journal data. Each
        # isolated tamper is rejected; restoring it restores read validation.
        for key in ('context', 'output_schema', 'instructions', 'restoration'):
            changed = deepcopy(rows[-1]['request'])
            changed[key] = {} if key != 'instructions' else 'substituted instructions'
            with pytest.raises(WorkflowError, match='original_contract_exchange'):
                child.source.validate_contract_exchange_request(changed, saved, 0,
                    rows[-1]['request']['restoration']['snapshot'],
                    rows[-1]['request']['restoration']['pending_public_exchanges'])
    finally:
        store.close()


def test_unknown_wrong_role_and_malformed_information_requests_are_feedback_not_actions(tmp_path):
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    provider.script = iter([information('episode.operation_contract', operation='absent.operation'),
        information('episode.return_contract', role='annotation', source='literature_kinetic_cells'),
        information('episode.return_contract', role='literature_strategy', source='absent_fact'),
        information('episode.operation_contract', operation='literature.kinetic.populate', extra='rejected'),
        populate(args)])
    try:
        run_child(episode, value)
        rows = value.decision_exchanges.rows(episode.source.episode_id, 0)
        assert all(row['lookup_result']['status'] == 'invalid' for row in rows[:-1])
        assert all(not row['lookup_result'].get('record_refs') for row in rows[:-1])
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        saved = json.loads(value.journal.row('runtime_model_calls', episode.source.episode_id, 0)['request'])
        episode.source.validate_contract_exchange_history(saved, 0)
    finally:
        store.close()


def test_childless_permitted_leaf_has_valid_metadata_schema_and_no_return_sources(tmp_path):
    from gene_annotation_episode.runtime import DecisionSource
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    try:
        leaf = DecisionSource(value, (*episode.source.path[:-1], ('literature_table', 'leaf')),
                              episode.request, episode.source.scope)
        value.receipts.bind(leaf.episode_id, episode.source.episode_id)
        assert value.available_child_roles(leaf) == ()
        schema = leaf.exchange_schema(value.action_schema(leaf))
        Draft202012Validator.check_schema(schema)
        lookup_schema = schema['properties']['response']['anyOf'][0]['properties']['lookup']
        request = information('episode.return_contract', role='literature', source='literature_kinetic_cells')['response']['lookup']
        Draft202012Validator(lookup_schema).validate(request)
        context = {'tools': value.catalog(leaf.scope, source=leaf), 'contract_information_profile': PROFILE}
        original = {'context': context, 'schema': value.action_schema(leaf)}
        original['contract_information'] = value.freeze_contract_information(leaf, context, original['schema'])
        frozen = value.validate_contract_information(original)
        assert frozen['fact_sources_by_role'] == {}
        result = value.contract_information_reply(original, frozen, 'episode.return_contract', request['arguments'])
        assert result['status'] == 'invalid' and result['record_refs'] == []
    finally:
        store.close()


def test_saved_opt_in_descriptor_reopens_through_actual_composition_and_requires_rate_population(tmp_path):
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    try:
        descriptors = value.episode_bindings.as_record()
        restored = Workflow(store, ToolRegistry(store), PresentedProvider([]), value.directory, value.run_id,
            lambda path, initial: FixtureController(str(path), initial, 1),
            ScientificFindingProgress(FindingProgressPolicy(1)),
            initial_known_record_refs=value.initial_known_record_refs,
            episode_binding_descriptors=descriptors, decision_protocol='decision_exchange_v1')
        assert restored.episode_bindings.as_record() == descriptors
        root = restored.build('annotation', 'root', 'Evaluate supplied synthetic reference evidence', episode.source.scope)
        assert restored.contract_information_profile(root.source) == PROFILE
        with pytest.raises(ValueError, match='unsupported_literature_contract_information_profile'):
            LiteratureEpisodes(value.services, rate_population=False, contract_information_profile=PROFILE)
        with pytest.raises(ValueError, match='unsupported_literature_contract_information_profile'):
            LiteratureEpisodes(value.services, rate_population=True, contract_information_profile='future-unknown')
        assert not provider.contexts
    finally:
        store.close()


def test_all_nineteen_original_host_contracts_validate_decoded_objects_without_capability_loss(tmp_path):
    from jsonschema import ValidationError
    provider = PresentedProvider([])
    store, value, episode, args = workflow(tmp_path, provider)
    try:
        branches = value.action_schema(episode.source)['properties']['selection']['anyOf']
        populations = [row for row in branches if row.get('properties', {}).get('tool', {}).get('const', '').startswith('literature.')]
        assert len(populations) == 19
        for branch in populations:
            name = branch['properties']['tool']['const']
            generated = _action_generation_schema(branch)
            assert generated['properties']['arguments']['type'] == 'string'
            assert 'x-argument-transport' not in json.dumps(generated)
            supplied = {'kind': 'tool', 'tool': name, 'arguments': '{"unexpected_literal":"{\\"keep\\":null}"}'}
            decoded = _decode_action_response(supplied, branch)
            assert decoded['arguments'] == {'unexpected_literal': '{"keep":null}'}
            with pytest.raises(ValidationError):
                Draft202012Validator(branch).validate(decoded)
    finally:
        store.close()
