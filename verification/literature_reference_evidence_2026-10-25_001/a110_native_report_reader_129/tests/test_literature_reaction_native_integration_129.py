"""Synthetic engineering consumers of the isolated129 native A110 candidate."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_reaction_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository, reaction_semantic_cells_schema
from gene_annotation_episode.literature_reaction_native_storage import native_observations_schema, NAMESPACE, POSITIONS_FIELD
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_native_inputs_129 import recipe, number, witness
from test_runtime import FixtureController, ScriptedProvider


def source(store, raw, parents=()):
    artifact = store.artifact(raw, 'application/octet-stream')
    return store.put('source', {'provider': 'synthetic_native_reaction129', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def setup_case(path, *, requested=True):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw = b'SyntheticProtein; ProductA; ProductB; matched reaction; ratio = 0.8; SD = 0.2; n = 4 technical injections.'
    paper = source(store, raw)
    selected = recipe(raw)
    selected['ratio']['summary']['uncertainty'].update(kind='sample_sd', number=number(raw, raw.decode(), '0.2'))
    selected['ratio']['summary']['count'].update(basis='technical_repeat', number=number(raw, raw.decode(), '4'),
        basis_witnesses=[witness(raw, 'technical injections')])
    def rebind(value):
        if isinstance(value, dict):
            if 'source_ref' in value:
                value['source_ref'] = paper['id']
            for child in value.values():
                rebind(child)
        elif isinstance(value, list):
            for child in value:
                rebind(child)
    rebind(selected)
    dataset = source(store, canonical(selected), [paper['id']])
    literals = dict.fromkeys(LITERAL_FIELDS)
    for field, label in [('molecule', 'SyntheticProtein'), ('numerator', 'ProductA'), ('denominator', 'ProductB'),
            ('experiment', 'matched reaction')]:
        literals[field] = witness(raw, label, paper['id'])
    args = {'source_ref': paper['id'], 'data_source_ref': dataset['id'], 'source_kind': 'synthetic_fixture',
        'literals': literals, 'interpretation_witnesses': []}
    refs = (paper['id'], dataset['id'])
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': list(refs),
        'requested_reaction_components': ['claim_mean_squared_error']}
    if requested:
        assignment[POSITIONS_FIELD] = [0]
    context = BindingContext('native129-run', 'native129-child', 'literature', (('literature', 'fixture'),),
        store.validate_scope(), assignment, {}, refs)
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize('requested', [False, True])
def test_selected_existing_operation_saved_views_and_first_read_only_reconstruction(tmp_path, monkeypatch, requested):
    store, context, args = setup_case(tmp_path / 'state', requested=requested)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome
        current = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *outcome['record_refs']))))
        properties = {'score': reaction_semantic_cells_schema()}
        if requested:
            properties['native'] = native_observations_schema()
        form_schema = obj(properties)
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, form_schema, binding.facts(current, selected))
        binding.validate_report(current, form, form_schema)
        assert form['score'][0]['value'] is None
        assert form['score'][0]['independent_n'] is None
        if requested:
            native, = form['native']
            assert native['reported_count'] == 4 and native['independent_n'] is None
            assert native['count_basis'] == 'technical_repeat'
            assert native['uncertainty_kind'] == 'sample_sd' and native['uncertainty_value'] == .2
            assert native['ratio_form'] == 'reported_point'
            assert 'component' not in native
        else:
            assert all('reported_count' not in row for row in form['score'])
        ref = outcome['result']['sheet_ref']
        saved = store.get(ref)
        descriptor = binding.as_record()
        allowed = {saved['artifact_ref'], saved['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'read-only reconstruction may not read scientific source bytes'
            return get_artifact(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved reconstruction must not rerun parsing/calculation')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.read_reaction_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints', forbidden)
        store.db.execute('PRAGMA query_only=ON')
        # Reconstruct only after entering read-only mode, before any new receipt exists.
        restored = binding_for(store, context)
        assert restored.as_record() == descriptor
        assert asyncio.run(restored.execute(context, 'literature.reaction.populate', args, 'selected')) == outcome
        assert form_with_facts({}, form_schema, restored.facts(current, selected)) == form


@pytest.mark.parametrize('requested', [False, True])
@pytest.mark.parametrize('position_mode', ['explicit', 'omitted', 'empty'])
def test_ordinary_original_child_return_exact_receipt_and_normal_observation_accounting(tmp_path, monkeypatch, requested, position_mode):
    store, context, args = setup_case(tmp_path / 'state', requested=requested)
    captures = []
    with store:
        props = {'score': reaction_semantic_cells_schema()}
        if requested:
            props['native'] = native_observations_schema()
        form = obj(props)
        assignment = plain(context.assignment)
        if position_mode == 'omitted':
            assignment.pop(POSITIONS_FIELD, None)
        elif position_mode == 'empty':
            assignment[POSITIONS_FIELD] = []
        expected_native = requested and position_mode != 'empty'
        def parent(inputs):
            captures.append(deepcopy(inputs))
            report, = inputs['child_reports']
            assert report['score'][0]['value'] is None
            assert ('native' in report) == requested
            text = render_literature_experimental_prompt(inputs, 'Evaluate synthetic reaction evidence')
            steering = text.split('\n\nSTEERING\n', 1)[1]
            assert ('Requested native reaction observations' in steering) == expected_native
            if expected_native:
                assert report['native'][0]['reported_count'] == 4
                assert 'technical_repeat' in steering
            else:
                if requested:
                    assert report['native'] == []
                assert 'reported_count' not in steering and 'technical injections' not in steering
            empty = {name: [] for name in store.reasoning_schema()['required']}
            paper = store.get(args['source_ref'])
            empty['source_subjects'] = [{'alias': 'synthetic_subject', 'reference_type': 'assay',
                'source_ref': paper['id'], 'label': 'SyntheticProtein', 'anchor': {
                    'source_ref': paper['id'], 'artifact_ref': paper['artifact_ref'],
                    'start': 0, 'end': len('SyntheticProtein'), 'quote': 'SyntheticProtein'}}]
            return {'selection': {'kind': 'reason', 'commit': empty}, 'report_update': {}}
        provider = ScriptedProvider([
            {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
                'goal': 'Extract synthetic reference ratio evidence', 'scope': plain(context.scope),
                'purpose': 'Return selected components and requested source operands',
                'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}},
            {'selection': {'kind': 'tool', 'tool': 'literature.reaction.populate', 'arguments': args}, 'report_update': {}}, parent])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(captures) == 1
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_reaction_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_reaction_semantic_received').fetchone()[0] == 1
        table = store.db.execute("select 1 from sqlite_master where type='table' and name='literature_reaction_native_observations_received'").fetchone()
        assert bool(table) == expected_native
        assert not store.list('observation') and not store.list('assessment')
        if expected_native:
            row = store.db.execute('select cells from literature_reaction_native_observations_received').fetchone()
            assert json.loads(row['cells']) == captures[0]['child_reports'][0]['native']
        parent_row = store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchone()
        request = json.loads(parent_row['request'])
        parent_context = BindingContext(result['run_id'], parent_row['episode_id'], 'annotation',
            tuple(tuple(piece) for piece in json.loads(parent_row['path'])), plain(context.scope), {}, request,
            tuple(captures[0]['literature_received_fact_display']['received_refs']))
        operation = store.db.execute('select outcome from literature_reaction_operations').fetchone()
        sheet_ref = json.loads(operation['outcome'])['result']['sheet_ref']
        saved_source = store.get(sheet_ref)
        allowed = {saved_source['artifact_ref'], saved_source['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'admitted-source replay must not read paper/recipe bytes'
            return get_artifact(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('admitted-source replay must not parse/recalculate')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.read_reaction_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_reaction_native_inputs.read_native_reaction_selection', forbidden)
        store.db.execute('PRAGMA query_only=ON')
        repository = LiteratureReactionRepository(store, result['run_id']).native_observations_projection()
        received = repository.received_rows(parent_context)
        assert received == (captures[0]['child_reports'][0]['native'] if expected_native else [])
        if expected_native:
            assert repository.fact_rows(parent_context, [sheet_ref], positions=['all']) == received
            forged = deepcopy(received)
            forged[0]['independent_n'] = forged[0]['reported_count']
            with pytest.raises(ContractError):
                repository.validate_returned_values(forged, permitted_record_refs=parent_context.received_record_refs)



def test_unreceived_new_selector_source_rejected_before_bytes(tmp_path, monkeypatch):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        forbidden = source(store, b'Hidden ratio = 0.8.')
        dataset = store.get(args['data_source_ref'])
        selected = json.loads(store.get_artifact(dataset['artifact_ref']))
        selected['ratio']['summary']['value'] = {'kind': 'point', 'number': number(
            b'Hidden ratio = 0.8.', 'Hidden ratio = 0.8.', '0.8', forbidden['id'])}
        replacement = source(store, canonical(selected), [args['source_ref']])
        args['data_source_ref'] = replacement['id']
        context = replace(context, received_record_refs=(*context.received_record_refs, replacement['id']))
        old = store.get_artifact
        def guarded(ref):
            assert ref != forbidden['artifact_ref'], 'unauthorized bytes were touched'
            return old(ref)
        monkeypatch.setattr(store, 'get_artifact', guarded)
        outcome = asyncio.run(binding_for(store, context).execute(context, 'literature.reaction.populate', args, 'denied'))
        assert outcome['status'] == 'invalid'
        assert 'not_received' in str(outcome)
        assert store.db.execute('select count(*) from literature_reaction_operations').fetchone()[0] == 0


def test_native_position_subset_does_not_expand_from_globally_known_sheet(tmp_path):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        recipe_source = store.get(args['data_source_ref'])
        selected = json.loads(store.get_artifact(recipe_source['artifact_ref']))
        extra_raw = b'Independent second synthetic preparation ratio = 0.9.'
        extra = source(store, extra_raw, [args['source_ref']])
        selected['ratio']['mode'] = 'independent_units'
        selected['ratio']['observations'] = [
            {'measurement_key': 'first', 'value': selected['ratio']['summary']['value'], 'basis_witnesses': []},
            {'measurement_key': 'second', 'value': {'kind': 'point', 'number': number(extra_raw,
                extra_raw.decode(), '0.9', extra['id'])}, 'basis_witnesses': []}]
        selected['ratio']['summary'] = None
        dataset = source(store, canonical(selected), [args['source_ref'], extra['id']])
        args['data_source_ref'] = dataset['id']
        context = replace(context, received_record_refs=(*context.received_record_refs, extra['id'], dataset['id']))
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'two-units'))
        assert outcome['status'] == 'completed', outcome
        owner = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *outcome['record_refs']))))
        adapter = binding.services.literature_reaction_repository().native_observations_projection()
        sheet = outcome['result']['sheet_ref']
        all_rows = adapter.fact_rows(owner, [sheet], positions=['all'])
        assert [row['value'] for row in all_rows] == [.8, .9]
        assert all(row['origin'] == 'synthetic' for row in all_rows)
        receiver = replace(owner, episode_id='manual-trusted-receiver', assignment={})
        adapter.receive_rows(receiver, all_rows[:1], 'trusted-fixture-delivery')
        assert adapter.fact_rows(receiver, [sheet], positions=['all']) == all_rows[:1]
        assert adapter.fact_rows(receiver, [sheet], positions=[1]) == []
        with pytest.raises(ContractError):
            adapter.validate_fact_rows(receiver, all_rows)
        # A genuine global sheet and matching source bytes do not manufacture
        # an unadmitted position. Exact duplicate and altered rows also fail.
        with pytest.raises(ContractError):
            adapter.validate_returned_values([all_rows[0], all_rows[0]], permitted_record_refs=owner.received_record_refs)
        changed = deepcopy(all_rows[:1])
        changed[0]['reported_count'] = 9
        with pytest.raises(ContractError):
            adapter.validate_returned_values(changed, permitted_record_refs=owner.received_record_refs)


def test_mixed_old_prepared_and_native_sheets_preserve_aggregate_and_skip_missing_native_view(tmp_path):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        binding = binding_for(store, context)
        native = asyncio.run(binding.execute(context, 'literature.reaction.populate', args, 'native'))
        assert native['status'] == 'completed', native
        normalized = binding.services.literature_reaction_repository().read(native['result']['sheet_ref'])['extraction']['observations']
        # Both historical v1 and v2 prepared routes remain available alongside
        # a newly selected native-source recipe in this exact same episode.
        prepared = []
        for version in ('a110_source_reaction_measurements_v1', 'a110_source_reaction_measurements_v2'):
            data = deepcopy(normalized)
            data['version'] = version
            if version.endswith('_v1'):
                data.pop('meanings')
            dataset = source(store, canonical(data), [args['source_ref']])
            context = replace(context, received_record_refs=(*context.received_record_refs, dataset['id']))
            selected_args = {**args, 'data_source_ref': dataset['id']}
            outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', selected_args, version))
            assert outcome['status'] == 'completed', outcome
            prepared.append(outcome)
        all_refs = tuple(dict.fromkeys((*context.received_record_refs, *native['record_refs'],
            *(ref for outcome in prepared for ref in outcome['record_refs']))))
        current = replace(context, received_record_refs=all_refs)
        sheets = [outcome['result']['sheet_ref'] for outcome in [*prepared, native]]
        facts = binding.facts(current, {'committed_record_refs': sheets})
        assert len(facts['literature_reaction_cells']) == 1
        assert len(facts['literature_reaction_semantic_cells']) == 2
        assert len(facts[NAMESPACE]) == 1
        assert facts[NAMESPACE][0]['sheet_ref'] == native['result']['sheet_ref']
