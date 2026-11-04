"""Source kinetic response in the existing loop; all decisions are controlled."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain, form_with_facts
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_transport_storage import transport_response_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

COMPONENTS = ['apparent_km', 'condition_response', 'log_condition_response', 'condition_response_variance']
FORM = obj({'measurements': transport_response_cells_schema()})


def witness(source, raw, quote):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': source, 'representation': 'original', 'start': start,
            'end': start+len(token), 'quote': quote}


def concentration(source, raw, quote):
    number, unit = quote.split(' ')
    return {'witness': witness(source, raw, quote), 'number_start': 0,
        'number_end': len(number), 'unit_start': len(number)+1, 'unit_end': len(quote)}


def setup_synthetic(path, *, different=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    text = ('<article><body><sec id="s"><p id="p">FixtureTransporter apparent Km = 12 uM for S.</p>'
        '<p id="conditions">FixtureTransporter uses substrate S in whole cells and a whole-cell system; '
        'initial uptake follows kinetic curve A with Michaelis-Menten response. '
        'The test substrate is 8 uM; the reference substrate is 32 uM. '
        'A different preparation uses proteoliposomes and a vesicle system with kinetic curve B.</p>'
        '</sec></body></article>')
    raw = text.encode('utf-8')
    artifact = store.artifact(raw, 'application/xml')
    source = store.put('source', {'provider': 'synthetic_fixture', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None}, origin='caller')
    ref = source['id']
    ctx = {field: witness(ref, raw, quote) for field, quote in {
        'molecule': 'FixtureTransporter', 'analyte': 'substrate S', 'preparation': 'whole cells',
        'experimental_system': 'whole-cell system', 'endpoint': 'initial uptake', 'curve': 'kinetic curve A'}.items()}
    other = {**ctx, **{field: witness(ref, raw, quote) for field, quote in {
        'preparation': 'proteoliposomes', 'experimental_system': 'vesicle system', 'curve': 'kinetic curve B'}.items()}}
    args = {'source_ref': ref, 'source_kind': 'synthetic_fixture',
        'primitives': {'substrate_test': concentration(ref, raw, '8 uM'),
                       'substrate_reference': concentration(ref, raw, '32 uM')},
        'km_sheet_ref': None, 'curve_contexts': {'substrate_test': ctx, 'substrate_reference': other if different else ctx,
                                              'km': ctx},
        'covariance_source_ref': None, 'variance_status': 'unknown', 'observation_model': 'michaelis_menten',
        'model_witnesses': [witness(ref, raw, 'Michaelis-Menten response')]}
    quantity = {'source_ref': ref, 'source_kind': 'synthetic_fixture', 'section_id': 's', 'paragraph_id': 'p',
                'subject': 'FixtureTransporter', 'quantity': 'apparent_km', 'analyte': 'S'}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
                  'source_refs': [ref], 'requested_quantity_components': [],
                  'requested_transport_components': COMPONENTS}
    context = BindingContext('transport-fixture-run', 'transport-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, (ref,))
    return store, context, quantity, args


@pytest.mark.parametrize('different', [False, True])
def test_selected_transport_response_actual_typed_delivery_and_observation_accounting(tmp_path, different):
    store, context, quantity_args, args = setup_synthetic(tmp_path / 'state', different=different)
    received, controllers = [], []
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the source substrate response and actual kinetic curve',
            'scope': plain(context.scope), 'purpose': 'Return only requested native and conditional response cells',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        quantity = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate', 'arguments': quantity_args},
                    'report_update': {}}
        def transport(inputs):
            assert inputs['last_local_outcome']['status'] == 'completed'
            selected = {**args, 'km_sheet_ref': inputs['last_local_outcome']['result']['sheet_ref']}
            return {'selection': {'kind': 'tool', 'tool': 'literature.transport.response.populate', 'arguments': selected},
                    'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert [row['component'] for row in rows] == COMPONENTS
            assert rows[0]['value'] == 12.
            assert rows[1]['value'] == (None if different else .55)
            if different:
                assert rows[1]['unavailable_reason'] == 'different_kinetic_curves'
                assert rows[1]['test_curve_ref'] != rows[1]['reference_curve_ref']
            else:
                assert rows[1]['test_curve_ref'] == rows[1]['reference_curve_ref'] == rows[1]['km_curve_ref']
                assert rows[1]['conditional_on'] == ['same_kinetic_curve', 'michaelis_menten_response']
            assert rows[3]['value'] is None
            assert rows[3]['unavailable_reason'] == ('different_kinetic_curves' if different else 'primitive_covariance_unreported')
            assert all(row['reported_km_uncertainty_kind'] == 'unreported' for row in rows)
            assert all(row['operand_source_kind'] == 'synthetic_fixture' for row in rows)
            assert all(row['evaluated_scope'] == 'interpreted_source_kinetic_response' for row in rows)
            assert all(row['covariance_source_ref'] is None for row in rows)
            source = store.get(quantity_args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            start = raw.index(b'FixtureTransporter')
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'reported_source', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': 'FixtureTransporter', 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': source['artifact_ref'], 'start': start,
                    'end': start+len('FixtureTransporter'), 'quote': 'FixtureTransporter'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, quantity, transport, receive]), run_dir=tmp_path / 'run',
            controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(received) == 1
        assert [c.scores for c in controllers] == [[0, 0], [0, 0]]
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 4
        assert store.db.execute('select count(*) from literature_quantity_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_transport_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_transport_received').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_quantity_received').fetchone()[0] == 0
    finally:
        store.close()


def test_transport_task_and_conditional_meaning_survive_actual_provider_transport(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_transport_prompt import TRANSPORT_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Evaluate the source substrate response for this fitted kinetic curve.'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_transport_components'] = COMPONENTS
    first['available_report_facts']['literature_transport_cells'] = {'meaning':
        'Conditional response for the actual source kinetic curve, not annotation reliability.'}
    second = deepcopy(first)
    second['working_state']['references'] = [{'id': 'reference_curve', 'record_type': 'reference',
        'label': 'the source whole-cell kinetic curve', 'accession': 'transport_curve_'+'a'*64,
        'source_ref': 'source_selected'}]
    second['last_local_outcome'] = {'status': 'completed', 'record_refs': ['reference_curve'], 'result': {
        'cells': {'condition_response': {'value': .55, 'unit': 'dimensionless', 'status': 'populated',
            'origin': 'derived', 'unavailable_reason': None,
            'conditional_on': ['same_kinetic_curve', 'michaelis_menten_response']}},
        'observation_model': 'michaelis_menten', 'variance_status': 'unknown',
        'operand_source_kind': 'synthetic_fixture', 'covariance_origin': None,
        'reported_km_uncertainty_kind': 'unspecified',
        'evaluated_scope': 'interpreted_source_kinetic_response',
        'curve_keys': {'km': 'HOST_CURVE_HASH'}, 'measurement_keys': {'km': 'HOST_MEASUREMENT_HASH'}}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'decision_index': 2,
        'exchange_index': 1, 'result': {'status': 'completed', 'text': 'Selected source explicitly distinguishes cell and vesicle preparations.'}}
    wire = LiteratureWire(tmp_path / 'wire')
    reopened = LiteratureWire(tmp_path / 'reopened')
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(reopened, state_frame(second))
    asyncio.run(exercise())
    tasks = []
    for transport in [wire, reopened]:
        for turn in transport.turns_sent():
            text = turn['input'][0]['text']
            task, steering = text.split('\n\nSTEERING\n', 1)
            tasks.append(task)
            assert TRANSPORT_TASK in task and first['goal']['objective'] in task
            assert 'HOST_CURVE_HASH' not in text and 'HOST_MEASUREMENT_HASH' not in text
            assert 'transport_curve_'+'a'*64 not in text
    assert all(task == tasks[0] for task in tasks)
    for turn in [*wire.turns_sent()[1:], *reopened.turns_sent()]:
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ['same_kinetic_curve', 'michaelis_menten', 'synthetic_fixture', 'unspecified']:
            assert meaning in steering


def test_saved_transport_binding_reconstructs_and_replays_without_input_reading(tmp_path, monkeypatch):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, quantity_args, args = setup_synthetic(tmp_path)
    try:
        host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        first = asyncio.run(binding.execute(context, 'literature.quantity.populate', quantity_args, 'native'))
        context = replace(context, received_record_refs=(*context.received_record_refs, *first['record_refs']))
        args = {**args, 'km_sheet_ref': first['result']['sheet_ref']}
        outcome = asyncio.run(binding.execute(context, 'literature.transport.response.populate', args, 'response'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        sheet_ref = outcome['result']['sheet_ref']
        facts = binding.facts(context, {'committed_record_refs': [sheet_ref]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(context, form, FORM)
        descriptor = binding.as_record()
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        reconstructed, = composition.bindings
        assert reconstructed.as_record() == descriptor
        source = store.get(sheet_ref)
        km_source = store.get(args['km_sheet_ref'])
        allowed = {source['artifact_ref'], source['request_ref'], km_source['artifact_ref'], km_source['request_ref']}
        original_get = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'reconstruction must not read original source/covariance bytes'
            return original_get(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('reconstruction must not parse or recalculate')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_transport_storage.read_transport_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_transport_storage.populate_transport_response', forbidden)
        store.db.execute('pragma query_only=ON')
        assert asyncio.run(reconstructed.execute(context, 'literature.transport.response.populate', args, 'response')) == outcome
        restored_facts = reconstructed.facts(context, {'committed_record_refs': [sheet_ref]})
        assert form_with_facts({}, FORM, restored_facts) == form
    finally:
        store.close()
