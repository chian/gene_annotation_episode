"""Source-only A106 cells: controlled Workflow plus authoritative saved replay."""
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
from gene_annotation_episode.literature_perturbation_inputs import LITERAL_FIELDS, PRIMITIVE_ORDER
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository, perturbation_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE / 'primary_cas2/PMC4075942.xml'
COMPONENTS = ['symmetric_effect', 'restoration_fraction_raw', 'reference_restoration_index', 'reference_index_lower']
FORM = obj({'measurements': perturbation_cells_schema()})


def source(store, data, *, parents=()):
    artifact = store.artifact(data, 'application/octet-stream')
    return store.put('source', {'provider': 'source_perturbation_example', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def witness(ref, raw, quote):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': 'original', 'start': start,
            'end': start+len(token), 'quote': quote}


def setup_case(path, *, primary=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw = PRIMARY.read_bytes() if primary else (
        b'SyntheticProtein in recipient cells: reference, perturbed and restored arms measure '
        b'the same calibrated endpoint. Restored protein amount is a nuisance comparison; '
        b'supplied controls bound alternative endpoint contributions.')
    root = source(store, raw)
    ref = root['id']
    def w(quote):
        return witness(ref, raw, quote)
    literals = dict.fromkeys(LITERAL_FIELDS)
    if primary:
        literals.update(molecule=w('Cas2'), recipient=w('BL21-AI'), donor=w('MG1655'),
            partner=w('Cas1'), endpoint=w('PCR'),
            normalization=w('OD<sub>600</sub> measurements'))
        interpretation = [w('lack all <italic toggle="yes">cas</italic> genes'), w('PCR')]
    else:
        literals.update(molecule=w('SyntheticProtein'), recipient=w('recipient cells'),
            reference_arm=w('reference'), perturbed_arm=w('perturbed'), restored_arm=w('restored'),
            endpoint=w('calibrated endpoint'))
        interpretation = [w(raw.decode('utf-8'))]
    data_ref = None
    refs = [ref]
    if not primary:
        values = dict(zip(PRIMITIVE_ORDER, [100., 20., 90., 100., 90., 8., 7.]))
        data = {'version': 'a106_source_measurements_v1', 'endpoint_unit': 'events_per_100000_cells',
            'exposure_unit': 'molecules_per_cell', 'origin': 'synthetic', 'uncertainty_basis': 'unreported',
            'measurements': {role: {'value': values[role], 'measurement_id': role+'-observed'} for role in PRIMITIVE_ORDER}}
        data_source = source(store, canonical(data), parents=[ref])
        data_ref = data_source['id']
        refs.append(data_ref)
    args = {'source_ref': ref, 'data_source_ref': data_ref,
        'source_kind': 'primary_source' if primary else 'synthetic_fixture', 'literals': literals,
        'design': 'cas_free_reconstitution' if primary else 'selective_perturbation_restoration',
        'measurement_status': 'qualitative_only' if primary else 'validated_ratio_scale',
        'same_endpoint_scope': 'unknown' if primary else 'yes', 'amount_role': 'unknown' if primary else 'nuisance',
        'orientation': None if primary else 1, 'interpretation_witnesses': interpretation}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
                  'source_refs': refs, 'requested_perturbation_components': COMPONENTS}
    context = BindingContext('perturbation-fixture-run', 'perturbation-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize('primary', [False, True])
def test_saved_source_values_exact_typed_subset_and_no_source_reread(tmp_path, monkeypatch, primary):
    store, context, args = setup_case(tmp_path, primary=primary)
    try:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.perturbation.populate', args, 'source'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        ref = outcome['result']['sheet_ref']
        facts = binding.facts(current, {'committed_record_refs': [ref]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        rows = form['measurements']
        assert [row['component'] for row in rows] == COMPONENTS
        if primary:
            assert all(row['value'] is None for row in rows)
            assert rows[0]['measurement_status'] == 'qualitative_only'
            assert rows[0]['design'] == 'cas_free_reconstitution'
            assert rows[0]['endpoint_unit'] == rows[0]['exposure_unit'] == 'unreported'
            assert store.get(rows[0]['recipient_ref'])['label'] == 'BL21-AI'
        else:
            assert [row['value'] for row in rows[:3]] == pytest.approx([2/3, .875, .4725])
        assert rows[-1]['value'] is None and rows[-1]['unavailable_reason'] == 'joint_uncertainty_unreported'
        assert all(row['uncertainty_basis'] == 'unreported' for row in rows)
        repo = LiteraturePerturbationRepository(store, context.run_id)
        bad = deepcopy(rows)
        bad[0]['value'] = 123.
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(bad, permitted_record_refs=current.received_record_refs)
        bad = deepcopy(rows)
        bad[0]['design'] = 'native_deletion_restoration'
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(bad, permitted_record_refs=current.received_record_refs)
        parent = replace(current, episode_id='parent', role='annotation', assignment={}, path=(('annotation', 'root'),))
        binding.received_form_references(parent, form, FORM, 'delivery')
        saved = store.get(ref)
        allowed = {saved['artifact_ref'], saved['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'no original source or retained measurement read on replay'
            return get_artifact(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved replay must not parse or calculate')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.populate_source_restoration', forbidden)
        store.db.execute('pragma query_only=ON')
        assert repo.populate(context, args, 'source') == outcome
        assert repo.received_cells(parent) == rows
        assert repo.project_cells([ref], permitted_record_refs=current.received_record_refs, components=COMPONENTS) == rows
    finally:
        store.close()


def test_perturbation_task_and_source_qualifications_repeat_at_provider_boundary(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_perturbation_prompt import PERTURBATION_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Evaluate what Cas2 reconstitution establishes about spacer acquisition.'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_perturbation_components'] = COMPONENTS
    first['available_report_facts']['literature_perturbation_cells'] = {'meaning':
        'Source intervention effects and proposed restoration components, with measured limitations.'}
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {
        'cells': {'reference_restoration_index': {'value': None, 'unit': 'dimensionless',
            'status': 'unavailable', 'origin': 'proposed', 'unavailable_reason': 'ratio_scale_not_validated',
            'conditional_on': ['source_restoration_convention']}},
        'design': 'cas_free_reconstitution', 'measurement_status': 'qualitative_only',
        'same_endpoint_scope': 'unknown', 'amount_role': 'unknown', 'orientation': None,
        'data_origin': None, 'endpoint_unit': 'unreported', 'exposure_unit': 'unreported',
        'uncertainty_basis': 'unreported', 'index_kind': 'proposed_source_restoration_index',
        'evaluated_scope': 'interpreted_reference_perturbation',
        'measurement_keys': {'W': 'HOST_MEASUREMENT_HASH'},
        'assay_interpretation': {'recipient': {'value': 'BL21-AI', 'witness': {'quote': 'BL21-AI'}}}}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'decision_index': 2,
        'exchange_index': 1, 'result': {'status': 'completed', 'text': 'The source recipient lacks cas genes.'}}
    wire = LiteratureWire(tmp_path / 'wire')
    reopened = LiteratureWire(tmp_path / 'reopened')
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(reopened, state_frame(second))
    asyncio.run(exercise())
    tasks = []
    for transport in (wire, reopened):
        for turn in transport.turns_sent():
            text = turn['input'][0]['text']
            task, steering = text.split('\n\nSTEERING\n', 1)
            tasks.append(task)
            assert PERTURBATION_TASK in task and first['goal']['objective'] in task
            assert 'HOST_MEASUREMENT_HASH' not in text
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ('cas_free_reconstitution', 'qualitative_only', 'unreported',
                        'proposed_source_restoration_index', 'ratio_scale_not_validated', 'BL21-AI'):
            assert meaning in steering


@pytest.mark.parametrize('denied_part', ['root', 'data'])
def test_each_direct_source_needs_receipt_and_scope_for_work_and_replay(tmp_path, monkeypatch, denied_part):
    store, context, args = setup_case(tmp_path)
    with store:
        repo = LiteraturePerturbationRepository(store, context.run_id)
        repo.populate(context, args, 'selected')
        denied = args['source_ref' if denied_part == 'root' else 'data_source_ref']
        missing = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != denied))
        for key in ('new', 'selected'):
            with pytest.raises(ContractError, match='not_received'):
                repo.populate(missing, args, key)
        subset = store.reference_subset
        monkeypatch.setattr(store, 'reference_subset', lambda refs, scope:
            [] if denied in refs else subset(refs, scope))
        for key in ('new', 'selected'):
            with pytest.raises(ContractError, match='outside_scope'):
                repo.populate(context, args, key)
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0] == 1


def test_page_assignment_rejects_unrelated_received_measurement_source(tmp_path):
    store, context, args = setup_case(tmp_path)
    with store:
        old = store.get(args['data_source_ref'])
        unrelated = source(store, store.get_artifact(old['artifact_ref']))
        context = replace(context, assignment={**context.assignment, 'page': {'source_ref': args['source_ref']}},
            received_record_refs=(*context.received_record_refs, unrelated['id']))
        repo = LiteraturePerturbationRepository(store, context.run_id)
        before = store.list('source'), store.list('reference')
        with pytest.raises(ContractError, match='outside_assigned_source'):
            repo.populate(context, {**args, 'data_source_ref': unrelated['id']}, 'invalid')
        assert (store.list('source'), store.list('reference')) == before
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0] == 0


def test_partial_publication_is_atomic_and_copied_source_is_not_a_selected_result(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_perturbation_storage import PROVIDER
    store, context, args = setup_case(tmp_path)
    with store:
        repo = LiteraturePerturbationRepository(store, context.run_id)
        before = tuple(store.list(kind) for kind in ('source', 'reference', 'term', 'context'))
        put = store.put
        def interrupted(kind, record, **kwargs):
            if kind == 'source' and record['provider'] == PROVIDER:
                raise RuntimeError('synthetic publication interruption')
            return put(kind, record, **kwargs)
        monkeypatch.setattr(store, 'put', interrupted)
        with pytest.raises(RuntimeError, match='publication interruption'):
            repo.populate(context, args, 'selected')
        assert tuple(store.list(kind) for kind in ('source', 'reference', 'term', 'context')) == before
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0] == 0
        monkeypatch.setattr(store, 'put', put)
        outcome = repo.populate(context, args, 'selected')
        actual = store.get(outcome['result']['sheet_ref'])
        copied = {key: value for key, value in actual.items() if key not in ('id', 'record_type', 'origin')}
        copied['retrieved_at'] = 'synthetic-copied-output'
        forged = store.put('source', copied, origin='tool')
        with pytest.raises(ContractError, match='not_selected_output'):
            repo.read(forged['id'])
        with pytest.raises(ContractError, match='reused_for_different_work'):
            repo.populate(context, {**args, 'orientation': -1}, 'selected')


def test_saved_binding_descriptor_reconstructs_selected_perturbation_without_reading_inputs(tmp_path, monkeypatch):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, args = setup_case(tmp_path)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.perturbation.populate', args, 'source'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(context, selected))
        descriptor = binding.as_record()
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        reconstructed, = composition.bindings
        assert reconstructed.as_record() == descriptor
        saved = store.get(outcome['result']['sheet_ref'])
        allowed = {saved['artifact_ref'], saved['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'reconstructed binding must not open original input bytes'
            return get_artifact(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('reconstructed binding must copy committed values')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_storage.populate_source_restoration', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_perturbation_inputs._measurement_key', forbidden)
        store.db.execute('pragma query_only=ON')
        assert asyncio.run(reconstructed.execute(context, 'literature.perturbation.populate', args, 'source')) == outcome
        assert form_with_facts({}, FORM, reconstructed.facts(context, selected)) == form


@pytest.mark.parametrize('primary', [False, True])
def test_source_perturbation_selected_in_ordinary_child_and_received_once(tmp_path, primary):
    store, context, args = setup_case(tmp_path / 'state', primary=primary)
    received = []
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the actual source intervention and endpoint',
            'scope': plain(context.scope), 'purpose': 'Return only requested source components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.perturbation.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert len(rows) == 4 and [row['component'] for row in rows] == COMPONENTS
            assert rows[2]['value'] == (None if primary else .4725)
            assert rows[3]['value'] is None
            assert all(row['index_kind'] == 'proposed_source_restoration_index' for row in rows)
            label = 'Cas2' if primary else 'SyntheticProtein'
            source_record = store.get(args['source_ref'])
            raw = store.get_artifact(source_record['artifact_ref'])
            start = raw.index(label.encode())
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'source_subject', 'reference_type': 'assay',
                'source_ref': source_record['id'], 'label': label, 'anchor': {
                    'source_ref': source_record['id'], 'artifact_ref': source_record['artifact_ref'],
                    'start': start, 'end': start+len(label), 'quote': label}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, action, receive]), run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path)==1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(received) == 1
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_perturbation_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()
