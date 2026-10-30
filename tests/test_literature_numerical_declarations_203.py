"""Controlled declaration/custody checks; no paper or actual model execution."""
from copy import deepcopy
from functools import partial
import asyncio
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import interpretation_schema, validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_contract_information import ContractInformationError, validate_saved_fact_form
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode import literature_numerical_contracts as contracts
from gene_annotation_episode.schema_information_text import schema_fingerprint


QUALIFICATION = {'type': 'string', 'enum': ['unknown', 'qualified']}


def all_facts():
    binding = LiteratureEpisodes(None, rate_population=True,
        channel_population=True, compiled_assay_population=True,
        ion_discrimination_population=True, completion_time_population=True,
        product_partition_population=True, active_site_population=True,
        assay_grading_population=True, parent_depletion_population=True,
        stoichiometric_balance_population=True,
        ratio_source_population=True, controlled_response_population=True, gel_population=True)
    return binding.fact_sources('literature')


def frozen(facts=None):
    facts = all_facts() if facts is None else facts
    # A second literal source tests that aliases do not change ordinary recorded
    # value-type declarations or accidentally grant a nonnumerical alias.
    facts = {**facts, 'credit': {'type': 'number', 'meaning': 'Original scalar credit.'},
        'caller_status': {'type': 'boolean', 'meaning': 'Original caller status.'}}
    action_schema = obj({'fixture': {'type': 'boolean'}})
    record = contracts.freeze_contracts(facts_by_role={'literature': facts},
        permitted_child_roles=['literature'], action_schema=action_schema)
    return {contracts.SAVED_MEMBER: record, 'schema': action_schema}


@pytest.mark.parametrize('source', contracts.registered_sources())
def test_catalog_matches_actual_bound_complete_host_type_and_preserves_interpretations(source):
    facts = all_facts()
    original = deepcopy(facts[source])
    assert contracts.registered_schema(source) == original['report_schema']
    assert contracts.is_registered_schema(original['report_schema'], source=source)
    submitted = obj({'selected': {'$ref': 'episode-fact:' + source}, 'qualification': QUALIFICATION})
    text = json.dumps(submitted, indent=1)
    saved = frozen({source: original})
    result = contracts.expand_numerical_form(text, child_role='literature', saved=saved)
    expected = obj({'selected': original['report_schema'], 'qualification': QUALIFICATION})
    assert result['expanded_schema'] == expected
    assert validate_closed_schema(expected) == expected
    assert interpretation_schema(expected) == obj({'qualification': QUALIFICATION})
    assert validate_saved_fact_form(child_role='literature', submitted_schema_json=text,
        expanded_schema=expected, declaration=result['declaration']) == expected
    assert result['declaration']['submitted_schema_json'] == text
    assert facts[source] == original


def test_snapshot_preserves_original_source_types_without_other_axis_sheets_or_aliases():
    saved = frozen()
    record = contracts.validate_frozen_contracts(saved)
    assert record['source_types_by_role']['literature']['credit'] == {'type': 'number'}
    assert record['source_types_by_role']['literature']['caller_status'] == {'type': 'boolean'}
    assert set(record['fact_sources_by_role']['literature']) == set(contracts.registered_sources())
    assert 'literature_perturbation_cells' in record['source_types_by_role']['literature']
    assert 'literature_perturbation_cells' not in record['fact_sources_by_role']['literature']
    for source in ('credit', 'caller_status', 'literature_perturbation_cells', 'absent_source'):
        with pytest.raises(ContractInformationError, match='return_contract_not_available'):
            contracts.expand_numerical_form(json.dumps(obj({'chosen': {'$ref': 'episode-fact:' + source}})),
                child_role='literature', saved=saved)


def test_explicit_fact_reference_detection_keeps_literal_native_documents_on_original_route():
    assert set(contracts.RETURN_MEANINGS) == set(contracts.registered_sources())
    for source in ('literature_gel_component_cells', 'literature_controlled_response_component_cells'):
        literal = obj({'native': contracts.registered_schema(source)})
        assert not contracts.uses_fact_references(literal)
        literal['properties']['chosen'] = {'$ref': 'episode-fact:literature_kinetic_cells'}
        assert contracts.uses_fact_references(literal)


@pytest.mark.parametrize('schema', [
    obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells', 'description': 'override'}}),
    obj({'numbers': {'type': 'array', 'items': {'$ref': 'episode-fact:literature_kinetic_cells'}}}),
    obj({'numbers': {'$ref': 'https://invalid.example/schema'}}),
    obj({'numbers': {'$dynamicRef': 'episode-fact:literature_kinetic_cells'}}),
])
def test_reference_overrides_nested_external_and_dynamic_references_are_rejected(schema):
    with pytest.raises(ContractInformationError, match='unsupported_form_reference'):
        contracts.expand_numerical_form(json.dumps(schema), child_role='literature', saved=frozen())


def test_wrong_role_cannot_use_available_source_and_modified_type_gets_no_alias():
    with pytest.raises(ContractInformationError, match='return_child_role_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {
            '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature_strategy', saved=frozen())
    facts = all_facts()
    facts['literature_kinetic_cells']['report_schema']['items']['properties']['value']['minimum'] = 0
    assert not contracts.is_registered_schema(facts['literature_kinetic_cells']['report_schema'])
    saved = frozen(facts)
    assert 'literature_kinetic_cells' not in saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature']
    with pytest.raises(ContractInformationError, match='return_contract_not_available'):
        contracts.expand_numerical_form(json.dumps(obj({'numbers': {
            '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)


def test_saved_expansion_uses_original_snapshot_with_fact_factories_blocked(monkeypatch):
    saved = frozen()
    before = deepcopy(saved)
    def forbidden(*_args, **_kwargs):
        raise AssertionError('Original frozen declarations must not reload current factories')
    monkeypatch.setattr(contracts, 'registered_schema', forbidden)
    result = contracts.expand_numerical_form(json.dumps(obj({'numbers': {
        '$ref': 'episode-fact:literature_kinetic_cells'}})), child_role='literature', saved=saved)
    assert result['expanded_schema']['properties']['numbers'] == saved[contracts.SAVED_MEMBER][
        'fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema']
    assert saved == before


@pytest.mark.parametrize('location', ['schema', 'fact_source', 'source_type', 'roles'])
def test_original_snapshot_associations_reject_tamper(location):
    saved = frozen()
    if location == 'schema':
        saved['schema']['properties']['fixture']['type'] = 'integer'
    elif location == 'fact_source':
        saved[contracts.SAVED_MEMBER]['fact_sources_by_role']['literature'][
            'literature_kinetic_cells']['report_schema']['x-source'] = 'literature_binding_cells'
    elif location == 'source_type':
        saved[contracts.SAVED_MEMBER]['source_types_by_role']['literature']['credit']['type'] = 'array'
    else:
        saved[contracts.SAVED_MEMBER]['permitted_child_roles'].append('invented_role')
    with pytest.raises(ContractInformationError, match='original_literature_numerical'):
        contracts.validate_frozen_contracts(saved)


def test_even_rehashed_wrong_source_relationship_is_rejected_without_fact_factory():
    saved = frozen()
    record = saved[contracts.SAVED_MEMBER]
    record['fact_sources_by_role']['literature']['literature_kinetic_cells']['report_schema'][
        'x-source'] = 'literature_binding_cells'
    record['fact_sources_sha256'] = schema_fingerprint(record['fact_sources_by_role'])
    with pytest.raises(ContractInformationError, match='original_literature_numerical_fact_mismatch'):
        contracts.validate_frozen_contracts(saved)


def world(path, *, execution_binding=None, protocol='decision_exchange_v1', profile=None, extra_binding=None):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_contract_information_runtime_059 import PresentedProvider
    from test_literature_kinetic_storage import setup
    from test_runtime import FixtureController, ScriptedProvider
    from gene_annotation_episode.providers import _SessionConnection

    class DirectPresentedProvider(ScriptedProvider):
        def __init__(self):
            super().__init__([])
            self.rendered = []
            self.connection = _SessionConnection.__new__(_SessionConnection)
            self.connection.scientific_prompt_states = {}

        async def complete(self, episode_id, role, instructions, context, output_schema):
            self.rendered.append(self.connection._presentation(episode_id, role, instructions, context)[0])
            return await super().complete(episode_id, role, instructions, context, output_schema)

    store, seed, args = setup(path / 'state')
    provider = DirectPresentedProvider() if protocol is None else PresentedProvider([])
    value = Workflow(store, ToolRegistry(store), provider, path / 'run', seed.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
        ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=list(seed.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args['source_ref']], contract_information_profile=profile,
            **(extra_binding or {})),),
        decision_protocol=protocol, execution_binding=execution_binding)
    root = value.build('annotation', 'root', 'Evaluate the supplied synthetic experimental evidence', plain(seed.scope))
    return store, seed, args, provider, value, root


@pytest.mark.parametrize('protocol', [None, 'decision_exchange_v1'], ids=['direct', 'pending'])
@pytest.mark.parametrize('compact', [False, True], ids=['literal_original', 'numerical_alias'])
def test_actual_selected_legacy_child_delivery_preserves_original_type_subset_and_observations(tmp_path, protocol, compact):
    from test_contract_information_custody_059 import COMPACT, LITERAL, commission
    from test_literature_kinetic_integration import reason
    from test_runtime_decision_exchanges import select

    store, seed, args, provider, value, root = world(tmp_path, protocol=protocol)
    selected = commission(seed, args, COMPACT if compact else LITERAL)
    populate = {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
        'arguments': args}, 'report_update': {'qualification': 'qualified'}}
    direct_selected = {key: val for key, val in selected['response'].items() if key != 'response_type'}
    provider.script = iter([direct_selected, populate, reason(store, args['source_ref'])]
        if protocol is None else [selected, select(populate), select(reason(store, args['source_ref']))])
    try:
        completed = asyncio.run(root.run_async(value.context))
        assert completed.units_consumed == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_received').fetchone()[0] == 1
        child = store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()
        request = json.loads(child['request'])
        assert request['report_contract']['measurements']['schema'] == LITERAL
        if compact:
            assert request['message']['report_contract_declaration']['submitted_schema_json'] == direct_selected['selection']['schema_json']
        else:
            assert 'report_contract_declaration' not in request['message']
        returned = json.loads(store.db.execute('SELECT form FROM runtime_forms').fetchone()[0])
        assert returned['qualification'] == 'qualified'
        assert [row['component'] for row in returned['numbers']] == ['parameter_ratio']
        assert returned['numbers'][0]['value'] == 4
        assert all(row[side]['uncertainty_values']['delivery_status'] == 'not_requested'
            for row in returned['numbers'] for side in ('numerator', 'denominator'))
        assert value.contract_information_profile(root.source) is None
        assert 'contract_information_profile' not in value.episode_bindings.as_record()[0]['configuration']
        for context in provider.contexts:
            assert contracts.SAVED_MEMBER not in json.dumps(context)
        for row in store.db.execute('SELECT request FROM runtime_model_calls'):
            saved = json.loads(row['request'])
            assert contracts.SAVED_MEMBER in saved
            assert 'contract_information' not in saved
            assert contracts.SAVED_MEMBER not in saved['context']
            contracts.validate_frozen_contracts(saved)
        for text in provider.rendered:
            task = text.split('\n\nSTEERING\n', 1)[0]
            from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
            from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
            assert EXPERIMENTAL_TASK in task or REFERENCE_PARENT_TASK in task
            assert 'uncertainty' in task
            assert 'count_reported_value' not in task
            assert 'return.numbers[].formula_code' not in task
            assert 'child_return.literature_kinetic_cells[].formula_code' not in task
        assert not store.list('assessment') and not store.list('observation')
    finally:
        store.close()


def test_pending_legacy_decision_uses_original_snapshot_before_current_fact_or_catalog_factories(tmp_path, monkeypatch):
    from gene_annotation_episode import runtime
    from test_contract_information_custody_059 import COMPACT, LITERAL, commission

    store, seed, args, provider, value, root = world(tmp_path)
    provider.script = iter([OSError('Controlled interruption before response')])
    try:
        with pytest.raises(OSError, match='before response'):
            asyncio.run(root.run_async(value.context))
        original = value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request']
        saved = json.loads(original)
        record = contracts.validate_frozen_contracts(saved)
        assert record['source_types_by_role']['literature']['credit'] == {'type': 'number'}
        assert record['source_types_by_role']['literature']['committed_record_refs'] == {'type': 'array'}
        def forbidden(*_a, **_kw):
            raise AssertionError('Pending original declaration must not reload current fact/catalog factories')
        monkeypatch.setattr(runtime.Workflow, 'report_sources', forbidden)
        monkeypatch.setattr(runtime, 'runtime_report_sources', forbidden)
        monkeypatch.setattr(runtime.Workflow, 'catalog', forbidden)
        monkeypatch.setattr(runtime.Workflow, 'action_schema', forbidden)
        type_declaration_factory = contracts.registered_schema
        monkeypatch.setattr(contracts, 'registered_schema', forbidden)
        selected = commission(seed, args, COMPACT)
        mixed = deepcopy(selected['response']['selection'])
        mixed_form = obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'},
            'total_credit': {'type': 'number', 'x-source': 'credit'}, 'qualification': QUALIFICATION})
        mixed['schema_json'] = json.dumps(mixed_form)
        actual, _ = value.expanded_contract_form(root.source, mixed, 0, 'literature')
        assert actual['properties']['total_credit'] == {'type': 'number', 'x-source': 'credit'}
        mixed_form['properties']['total_credit'] = {'type': 'array', 'x-source': 'credit',
            'items': {'type': 'string', 'format': 'reference'}}
        mixed['schema_json'] = json.dumps(mixed_form)
        with pytest.raises(ValueError, match='different declared value type'):
            value.expanded_contract_form(root.source, mixed, 0, 'literature')
        expanded, declaration = value.expanded_contract_form(root.source, selected['response']['selection'], 0, 'literature')
        assert expanded == LITERAL
        assert declaration['submitted_schema_json'] == selected['response']['selection']['schema_json']
        assert value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == original
        # Rendering may check an exact registered TYPE, as communication's
        # existing native validators do. It does not acquire source facts or
        # substitute a current report_sources contract for the saved choice.
        monkeypatch.setattr(contracts, 'registered_schema', type_declaration_factory)
        root.source.calls = 0
        provider.script = iter([selected])
        # The ordinary Episode next() path must use its original pending
        # context/action schema before constructing the chosen child.
        async def choose_only():
            view = type('UnusedFreshView', (), {})()
            return await root.source.next(view)
        unit = asyncio.run(choose_only())
        assert unit is not None
        child = store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()
        assert json.loads(child['request'])['report_contract']['measurements']['schema'] == LITERAL
        assert value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == original
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


def test_synthetic_saved_legacy_record_without_new_member_keeps_literal_only_behavior(tmp_path):
    from gene_annotation_episode.communication import ReportBoundaryError
    from test_contract_information_custody_059 import COMPACT, LITERAL, commission
    store, seed, args, provider, value, root = world(tmp_path)
    provider.script = iter([OSError('Controlled pre-response old-record fixture')])
    try:
        with pytest.raises(OSError, match='old-record fixture'):
            asyncio.run(root.run_async(value.context))
        row = value.journal.row('runtime_model_calls', root.source.episode_id, 0)
        old = json.loads(row['request'])
        del old[contracts.SAVED_MEMBER]
        # Explicit synthetic old-format fixture; no actual historical record
        # or configured-model request is read or rewritten by this test.
        value.journal.save('runtime_model_calls', {'episode_id': root.source.episode_id,
            'call_index': 0, 'purpose': 'decision', 'request': json.dumps(old), 'response': None})
        expected = value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request']
        literal = commission(seed, args, LITERAL)['response']['selection']
        assert value.expanded_contract_form(root.source, literal, 0, 'literature') == (LITERAL, None)
        alias = commission(seed, args, COMPACT)['response']['selection']
        with pytest.raises(ReportBoundaryError, match='unsupported schema keyword'):
            value.expanded_contract_form(root.source, alias, 0, 'literature')
        assert value.journal.row('runtime_model_calls', root.source.episode_id, 0)['request'] == expected
        assert contracts.SAVED_MEMBER not in json.loads(expected)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


def test_new_legacy_alias_uses_actual_c1_c4_original_contract_and_readonly_saved_delivery(tmp_path, monkeypatch):
    # Reuse the complete original C1/C4 fixture assertions, changing only its
    # caller to legacy None. It publishes a real selected commission, executes
    # the synthetic child's native work, rolls back failed receipt admission,
    # admits the exact typed return, then cold-reopens SQLite mode=ro before
    # binding construction with acquisition/calculation/receive blocked.
    import test_contract_information_custody_059 as custody
    captured = {}
    def original_world(*args, **kwargs):
        result = world(*args, **kwargs)
        captured['descriptors'] = result[4].episode_bindings.as_record()
        return result
    monkeypatch.setattr(custody, 'world', original_world)
    custody.test_original_c1_c4_compact_form_native_custody_rollback_and_readonly_first_reconstruction(tmp_path, monkeypatch)
    # Strengthen the existing logical SQL equality proof with a connection
    # that is read-only from its first open, before the real binding composer.
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_services import WorkflowServices
    state_path = tmp_path / 'state'
    def hashes():
        return {str(path.relative_to(state_path)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in state_path.rglob('*') if path.is_file()}
    before = hashes()
    cold = Store.__new__(Store)
    cold.path, cold._savepoint = state_path, 0
    cold.db = sqlite3.connect((state_path / 'state.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1',
        uri=True, isolation_level=None)
    cold.db.row_factory = sqlite3.Row
    cold.db.execute('PRAGMA query_only=ON')
    statements = []
    cold.db.set_trace_callback(statements.append)
    try:
        spec = json.loads(cold.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()[0])
        admission = json.loads(cold.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        parent_row = cold.db.execute('SELECT request FROM runtime_episodes WHERE episode_id=?',
            (spec['parent']['episode_id'],)).fetchone()
        parent_request = json.loads(parent_row['request'])
        original_form = admission['report']
        source_ref = original_form['numbers'][0]['evidence_source_ref']
        original_source_artifact = cold.get(source_ref)['artifact_ref']
        get_artifact = cold.get_artifact
        def saved_artifact(reference):
            if reference == original_source_artifact:
                raise AssertionError('Cold reconstruction must not reacquire original synthetic source bytes')
            return get_artifact(reference)
        monkeypatch.setattr(cold, 'get_artifact', saved_artifact)
        refs = tuple(dict.fromkeys([source_ref, *admission['received_record_refs'],
            *parent_request['message']['scope']['subject_refs']]))
        context = BindingContext(spec['run_id'], spec['parent']['episode_id'], 'annotation',
            spec['parent']['path'], parent_request['message']['scope'], {}, parent_request, refs)
        host = SimpleNamespace(store=cold, run_id=spec['run_id'], tools=None)
        services = WorkflowServices(host)
        composition = compose_episode_bindings(services, store=cold,
            journal=SimpleNamespace(store=cold, run_id=spec['run_id']),
            execution_backend=None, descriptors=captured['descriptors'], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
        bindings = EpisodeBindingRegistry(composition.bindings)
        host.episode_bindings = bindings
        binding = bindings.for_role('literature')
        assert bindings.as_record() == captured['descriptors']
        assert binding.received_report_facts(context)['literature_kinetic_cells'] == original_form['numbers']
        request = spec['child']['request']
        declaration = request['message']['report_contract_declaration']
        exact = validate_saved_fact_form(child_role='literature',
            submitted_schema_json=declaration['submitted_schema_json'],
            expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
        assert exact == custody.LITERAL
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        assert cold.db.execute('PRAGMA query_only').fetchone()[0] == 1
        assert cold.db.total_changes == 0
    finally:
        cold.close()
    assert hashes() == before
    (tmp_path / 'COLD_PROOF_203.json').write_text(json.dumps({'mode': 'ro&immutable=1; query_only=ON',
        'before_binding_composer': True, 'written_rows': 0,
        'idempotent_existing_schema_checks': sum('CREATE TABLE IF NOT EXISTS' in text.upper() for text in statements),
        'state_file_hashes': before, 'exact_form_and_type': True,
        'scientific_acquisition_calculation_receive_blocked': True}, sort_keys=True, indent=2) + '\n')


@pytest.mark.parametrize('native', ['literature_gel_component_cells', 'literature_controlled_response_component_cells'])
def test_mixed_native_literal_and_alias_expand_and_saved_validate_without_changing_either(native):
    facts = all_facts()
    submitted = obj({'native': facts[native]['report_schema'],
        'kinetic': {'$ref': 'episode-fact:literature_kinetic_cells'}, 'qualification': QUALIFICATION})
    text = json.dumps(submitted)
    result = contracts.expand_numerical_form(text, child_role='literature',
        saved=frozen({name: facts[name] for name in (native, 'literature_kinetic_cells')}))
    expected = obj({'native': facts[native]['report_schema'],
        'kinetic': facts['literature_kinetic_cells']['report_schema'], 'qualification': QUALIFICATION})
    assert result['expanded_schema'] == expected
    assert validate_saved_fact_form(child_role='literature', submitted_schema_json=text,
        expanded_schema=expected, declaration=result['declaration']) == expected
    assert result['declaration']['fact_references'][0]['field'] == 'kinetic'
    assert len(result['declaration']['fact_references']) == 1


@pytest.mark.parametrize('native', ['literature_gel_component_cells', 'literature_controlled_response_component_cells'])
@pytest.mark.parametrize('mutation', ['nested_alias', 'modified_type', 'invented_native_label', 'wrong_native_family', 'dynamic_ref'])
def test_native_literal_opacity_rejects_altered_schema_labels_and_nested_aliases(native, mutation):
    facts = all_facts()
    literal = deepcopy(facts[native]['report_schema'])
    if mutation == 'nested_alias':
        literal['$defs']['IllicitAlias'] = {'$ref': 'episode-fact:literature_kinetic_cells'}
    elif mutation == 'modified_type':
        literal['minItems'] = 0
    elif mutation == 'invented_native_label':
        literal['x-source'] = 'invented_native_document'
    elif mutation == 'wrong_native_family':
        literal['x-source'] = ('literature_controlled_response_component_cells'
            if native == 'literature_gel_component_cells' else 'literature_gel_component_cells')
    else:
        literal['$defs']['IllicitDynamic'] = {'$dynamicRef': '#/$defs/Cell'}
    submitted = obj({'native': literal, 'kinetic': {'$ref': 'episode-fact:literature_kinetic_cells'}})
    with pytest.raises(ContractInformationError):
        contracts.expand_numerical_form(json.dumps(submitted), child_role='literature',
            saved=frozen({name: facts[name] for name in (native, 'literature_kinetic_cells')}))


@pytest.mark.parametrize('native, option', [
    ('literature_gel_component_cells', 'gel_population'),
    ('literature_controlled_response_component_cells', 'controlled_response_population')])
def test_actual_mixed_native_literal_alias_commission_freezes_and_replays_original_child(tmp_path, monkeypatch, native, option):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.runtime import Workflow
    from test_contract_information_custody_059 import commission

    binding_record = {'factory_module': 'fixture', 'factory_name': 'open_commission', 'arguments': {},
        'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}
    store, seed, args, provider, value, root = world(tmp_path, execution_binding=binding_record,
        extra_binding={option: True})
    literal = contracts.registered_schema(native)
    original = obj({'native': literal, 'numbers': contracts.registered_schema('literature_kinetic_cells'),
        'qualification': QUALIFICATION})
    chosen = commission(seed, args, obj({'native': literal,
        'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'}, 'qualification': QUALIFICATION}))
    provider.script = iter([chosen])
    try:
        response, index, context, schema = asyncio.run(root.source.call({
            'goal': root.goal.as_record(), 'scope': plain(seed.scope),
            'visible_record_refs': list(seed.received_record_refs),
            'tools': value.catalog(seed.scope, source=root.source)}, value.action_schema(root.source)))
        unit = root.source.apply_response(response, index, context, schema)
        assert unit is not None
        spec, = value.commissions.recover_selected(root.source.episode_id)
        saved_request = deepcopy(spec['child']['request'])
        assert saved_request['report_contract']['measurements']['schema'] == original
        assert len(saved_request['message']['report_contract_declaration']['fact_references']) == 1
        def forbidden(*_a, **_kw):
            raise AssertionError('Saved mixed declaration must not reload a current fact source')
        monkeypatch.setattr(Workflow, 'report_sources', forbidden)
        expanded, declaration = value.expanded_contract_form(root.source, response['selection'], index, 'literature')
        assert expanded == original
        assert declaration == saved_request['message']['report_contract_declaration']
        assert value.returned_request(spec).as_record() == saved_request
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert spec['child']['request'] == saved_request
    finally:
        store.close()


@pytest.mark.parametrize('source', contracts.registered_sources())
@pytest.mark.parametrize('surface', ['legacy_request', 'profile_request', 'profile_lookup', 'legacy_parent'])
def test_actual_public_return_surfaces_keep_scientific_task_interpretations_and_usable_declaration(source, surface):
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.episode_contract_information import return_contract_information
    from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK, render_literature_experimental_prompt
    from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt

    schema = contracts.registered_schema(source)
    form = obj({'numbers': schema, 'qualification': QUALIFICATION})
    fact = {'type': 'array', 'meaning': contracts.RETURN_MEANINGS[source], 'report_schema': schema}
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
        'goal': {'objective': 'Examine the supplied synthetic experiment and retain its actual measurement meanings.',
            'result_contract': form},
        'requested_form': form, 'available_report_facts': {source: fact}}
    lookups = []
    if surface.startswith('profile'):
        state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    if surface == 'profile_lookup':
        lookups = [return_contract_information(facts_by_role={'literature': {source: fact}},
            permitted_child_roles=['literature'], role='literature', source=source)]
        state.pop('requested_form')
        state['goal'].pop('result_contract')
    if surface == 'legacy_parent':
        state['literature_experimental_work']['aspect'] = 'reference_evidence_parent'
        state['reference_evidence_parent'] = {'version': 'reference_evidence_parent_v1',
            'source_refs': ['synthetic_source_assignment']}
    original_state, original_lookups = deepcopy(state), deepcopy(lookups)
    renderer = render_reference_evidence_parent_prompt if surface == 'legacy_parent' else render_literature_experimental_prompt
    prompt = renderer(state, 'Examine the assigned synthetic experiment.', lookup_results=lookups)
    task, steering = prompt.split('\n\nSTEERING\n', 1)
    assert (REFERENCE_PARENT_TASK if surface == 'legacy_parent' else EXPERIMENTAL_TASK) in task
    assert 'uncertainty' in task
    assert 'episode-fact:' + source in task
    assert 'formula_code' not in task
    assert 'count_reported_value' not in task
    assert '"$defs"' not in task
    if surface != 'profile_lookup':
        assert 'qualification' in task and 'qualified' in task and 'unknown' in task
    else:
        assert 'Requested recorded return declaration' in task
        assert 'Complete requested contract' not in task
        assert 'formula_code' not in steering
    assert state == original_state
    assert lookups == original_lookups
    assert schema == contracts.registered_schema(source)


def test_operation_input_nomination_contract_is_not_redacted_as_a_return_sheet():
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
    from gene_annotation_episode.episode_contract_information import operation_contract_information
    from gene_annotation_episode.literature_episodes import _population_catalog
    from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
    from gene_annotation_episode.schema_information_text import render_schema_information
    operation = next(row for row in _population_catalog() if row['name'] == 'literature.kinetic.populate')
    original = deepcopy(operation)
    reply = operation_contract_information(catalog=[operation], operation=operation['name'])
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
        'contract_information_profile': CONTRACT_INFORMATION_PROFILE}
    prompt = render_literature_experimental_prompt(state, 'Identify the original source operands.', lookup_results=[reply])
    task = prompt.split('\n\nSTEERING\n', 1)[0]
    assert render_schema_information(operation['input_schema'], title='Arguments for ' + operation['name']) in task
    assert 'number_start' in task and 'number_end' in task
    assert operation == original
    assert reply['result']['input_schema'] == operation['input_schema']


def test_actual_controlled_provider_wire_sends_complete_science_and_declaration_without_sheet(tmp_path):
    from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, OUTPUT_SCHEMA
    form = obj({'numbers': contracts.registered_schema('literature_kinetic_cells'),
        'qualification': QUALIFICATION})
    context = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
        'goal': {'objective': 'Examine the supplied synthetic kinetic experiment.'},
        'requested_form': form}
    original = deepcopy(context)
    wire = LiteratureWire(tmp_path / 'wire')
    response = asyncio.run(wire.complete('synthetic_203_child', 'REASONING',
        'Examine the assigned original measurements and qualifications.', context, OUTPUT_SCHEMA))
    assert response == {'fixture': True}
    turn, = wire.turns_sent()
    assert turn['outputSchema'] == OUTPUT_SCHEMA
    payload, = turn['input']
    assert payload['type'] == 'text'
    task = payload['text'].split('\n\nSTEERING\n', 1)[0]
    assert EXPERIMENTAL_TASK in task
    assert 'episode-fact:literature_kinetic_cells' in task
    assert 'qualification' in task and 'qualified' in task
    assert 'formula_code' not in task and 'count_reported_value' not in task
    assert contracts.SAVED_MEMBER not in json.dumps(turn)
    assert context == original


def test_actual_standard_c1_worker_reopens_legacy_alias_original_request_without_model_work(tmp_path, monkeypatch):
    from gene_annotation_episode import independent_execution as worker
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.literature_episodes import _population_catalog
    from gene_annotation_episode.runtime import assemble_workflow, run_workflow
    from gene_annotation_episode.tool_configuration import build_tools
    from test_contract_information_custody_059 import COMPACT, LITERAL, commission
    from test_contract_information_runtime_059 import PresentedProvider
    from test_literature_kinetic_storage import setup
    store, seed, args = setup(tmp_path / 'state')
    directory = tmp_path / 'run'
    binding_factory = partial(LiteratureEpisodes, rate_population=True,
        reference_parent_sources=[args['source_ref']], contract_information_profile=None)
    provider = PresentedProvider([OSError('Controlled root interruption before any action')])
    try:
        with pytest.raises(OSError, match='before any action'):
            asyncio.run(run_workflow(store, build_tools(store), provider=provider, run_dir=directory,
                initial_known_record_refs=list(seed.received_record_refs),
                episode_binding_factories=(binding_factory,), decision_protocol='decision_exchange_v1'))
        settings = json.loads((directory / 'run.json').read_text())
        run_id = settings.pop('run_id')
        original_binding = worker.make_runtime_binding(store, directory)
        options = worker._standard_bindings(store, directory, settings)
        worker._check_bindings(options, settings)
        chosen = commission(seed, args, COMPACT)
        chooser = PresentedProvider([chosen])
        value = assemble_workflow(store, build_tools(store), chooser, directory, run_id, settings,
            episode_binding_descriptors=settings['episode_bindings'],
            **{key: val for key, val in options.items() if key != 'binding_definitions'})
        value.configure_execution(original_binding)
        root = value.build('annotation', 'root', settings['goal'], plain(seed.scope))
        root.source.calls = 1
        response, index, context, schema = asyncio.run(root.source.call({
            'goal': root.goal.as_record(), 'scope': plain(seed.scope),
            'visible_record_refs': list(seed.received_record_refs),
            'tools': value.catalog(seed.scope, source=root.source)}, value.action_schema(root.source)))
        unit = root.source.apply_response(response, index, context, schema)
        assert unit is not None and index == 1
        spec, = value.commissions.recover_selected(root.source.episode_id)
        value.execution_backend.commission(spec)
        original = deepcopy(spec)
        request = spec['child']['request']
        assert request['report_contract']['measurements']['schema'] == LITERAL
        assert request['message']['report_contract_declaration']['submitted_schema_json'] == chosen['response']['selection']['schema_json']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()
    connections = []
    class ForbiddenModel(PresentedProvider):
        def __init__(self, *_a, **_kw):
            super().__init__([])
            self.entered = self.exited = False
            connections.append(self)
        async def __aenter__(self):
            self.entered = True
            return self
        async def __aexit__(self, *_args):
            self.exited = True
        async def complete(self, *_a, **_kw):
            raise AssertionError('Worker reconstruction must not invoke a model')
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection', ForbiddenModel)
    async def reopen():
        async with worker.open_commission(spec) as opened:
            episode = opened['episode']
            restored = episode.source.workflow
            assert episode.request.as_record() == original['child']['request']
            assert restored.contract_information_profile(episode.source) is None
            assert restored.episode_bindings.as_record() == settings['episode_bindings']
            assert 'contract_information_profile' not in settings['episode_bindings'][0]['configuration']
            assert restored.execution_binding == original_binding
            assert restored.execution_backend.load_commission(spec['handle']) == original
            operations = [row for row in restored.catalog(episode.source.scope, source=episode.source)
                if row['name'].startswith('literature.')]
            assert operations == _population_catalog()
            assert restored.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    asyncio.run(reopen())
    assert len(connections) == 1 and connections[0].entered and connections[0].exited
    assert not connections[0].contexts and spec == original
