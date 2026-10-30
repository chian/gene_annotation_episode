"""Synthetic persisted transport identities at the actual provider boundary.

Controlled RPC supplies no scientific inference and contacts no model service.
These tests distinguish recorded host identity from external scientific strings.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_transport_prompt import TRANSPORT_TASK
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_transport_integration import COMPONENTS, FORM, setup_synthetic
from test_runtime import FixtureController, ScriptedProvider


class RenderingScriptedProvider(ScriptedProvider):
    """Send actual runtime inputs through the real text/transport implementation."""

    def __init__(self, script, directory):
        super().__init__(script)
        self.wire = LiteratureWire(directory)
        self.calls = []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.calls.append((episode_id, instructions, deepcopy(context), deepcopy(output_schema)))
        # The scripted scientific action remains the test's only decision.
        # LiteratureWire exercises complete/_presentation/turn-start over RPC.
        await self.wire.complete(episode_id, role, instructions, context, output_schema)
        return await super().complete(episode_id, role, instructions, context, output_schema)


def read_source(source_ref):
    return {'selection': {'kind': 'tool', 'tool': 'source.read', 'arguments': {
        'source_ref': source_ref, 'representation': 'original', 'offset': 0, 'limit': 12000}},
        'report_update': {}}


def record_source_subject(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source['artifact_ref'])
    label = 'FixtureTransporter'
    start = raw.index(label.encode())
    commit = {name: [] for name in store.reasoning_schema()['required']}
    commit['source_subjects'] = [{'alias': 'reported_source', 'reference_type': 'assay',
        'source_ref': source_ref, 'label': label, 'anchor': {'source_ref': source_ref,
            'artifact_ref': source['artifact_ref'], 'start': start, 'end': start + len(label),
            'quote': label}}]
    return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}


@pytest.mark.parametrize('different', [False, True])
def test_runtime_selected_transport_records_keep_provenance_through_owned_received_and_provider_views(tmp_path, different):
    store, context, quantity_args, arguments = setup_synthetic(tmp_path / 'state', different=different)
    controllers, captured = [], {}
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the source substrate response and kinetic curve',
            'scope': plain(context.scope), 'purpose': 'Return requested conditional source-response measurements',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        quantity = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate',
            'arguments': quantity_args}, 'report_update': {}}

        def transport(inputs):
            return {'selection': {'kind': 'tool', 'tool': 'literature.transport.response.populate',
                'arguments': {**arguments, 'km_sheet_ref': inputs['last_local_outcome']['result']['sheet_ref']}},
                'report_update': {}}

        def own_result(inputs):
            captured['own'] = deepcopy(inputs)
            outcome = inputs['last_local_outcome']
            assert outcome['status'] == 'completed'
            captured['outcome'] = deepcopy(outcome)
            return read_source(quantity_args['source_ref'])

        def received(inputs):
            captured['received'] = deepcopy(inputs)
            form, = inputs['child_reports']
            assert [row['component'] for row in form['measurements']] == COMPONENTS
            assert form['measurements'][0]['value'] == 12.
            assert form['measurements'][1]['value'] == (None if different else .55)
            assert form['measurements'][3]['unavailable_reason'] == (
                'different_kinetic_curves' if different else 'primitive_covariance_unreported')
            return record_source_subject(store, quantity_args['source_ref'])

        def controller(path, initial):
            # Root takes commission/receive; the child takes quantity/transport/
            # one ordinary source read so its owned result reaches a call.
            item = FixtureController(str(path), initial, 2 if not controllers else 3)
            controllers.append(item)
            return item

        provider = RenderingScriptedProvider([commission, quantity, transport, own_result, received], tmp_path / 'wire')
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=list(context.received_record_refs)),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert [item.scores for item in controllers] == [[0, 0], [0, 0, 0]]
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 5
        assert store.db.execute('select count(*) from literature_transport_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_transport_received').fetchone()[0] == 1

        sheet_ref = captured['outcome']['result']['sheet_ref']
        payload = json.loads(store.get_artifact(store.get(sheet_ref)['artifact_ref']))
        curves = {payload['experimental_bindings'][name] for name in
            ('test_curve_ref', 'reference_curve_ref', 'km_curve_ref')}
        assert len(curves) == (2 if different else 1)
        for inputs in (captured['own'], captured['received']):
            working = {row['id']: row for row in inputs['working_state']['references']}
            admitted = inputs['literature_received_fact_display']['records']
            for reference in curves:
                record = store.get(reference)
                assert record['origin'] == 'tool'
                assert record['accession'].startswith('transport_curve_')
                assert len(record['accession']) == len('transport_curve_') + 64
                assert working[reference] == admitted[reference] == record

        turns = provider.wire.turns_sent()
        assert len(turns) == 5
        for index in (3, 4):
            text = turns[index]['input'][0]['text']
            task, steering = text.split('\n\nSTEERING\n', 1)
            if index == 3:
                assert TRANSPORT_TASK in task
            else:
                assert 'Evaluate what the assigned experimental sources establish' in task
            assert 'kinetic curve A' in steering
            assert 'interpreted_source_kinetic_response' in steering
            assert 'synthetic_fixture' in steering and 'unreported' in steering
            assert '12.0' in steering
            assert ('different_kinetic_curves' if different else 'same_kinetic_curve') in steering
            assert ('kinetic curve B' in steering) is different
            for reference in curves:
                assert reference not in steering
                assert store.get(reference)['accession'] not in text
            assert turns[index]['outputSchema'] == provider.calls[index][3]

        episode, instructions, inputs, schema = provider.calls[-1]
        reopened = LiteratureWire(tmp_path / 'reopened')
        asyncio.run(reopened.complete(episode, 'REASONING', instructions, state_frame(inputs), schema))
        assert reopened.turns_sent()[0]['input'] == turns[-1]['input']
        # Rendering/reconstruction added no action, delivery or observation.
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 5
    finally:
        store.close()


@pytest.mark.parametrize('received_map', [False, True])
def test_persisted_accessions_and_saved_reconstruction_preserve_external_identifiers_and_numbers(tmp_path, monkeypatch, received_map):
    store, context, quantity_args, arguments = setup_synthetic(tmp_path / 'state')
    try:
        journal = Journal(store, context.run_id)
        host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        first = asyncio.run(binding.execute(context, 'literature.quantity.populate', quantity_args, 'native'))
        context = replace(context, received_record_refs=(*context.received_record_refs, *first['record_refs']))
        arguments = {**arguments, 'km_sheet_ref': first['result']['sheet_ref']}
        outcome = asyncio.run(binding.execute(context, 'literature.transport.response.populate', arguments, 'response'))
        assert outcome['status'] == 'completed'
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        sheet_ref = outcome['result']['sheet_ref']
        public = []
        for accession in ('P12345', 'RHEA:12345', 'transport_curve_' + 'c' * 64,
                          'native_rate_subject_' + 'd' * 24):
            public.append(store.put('reference', {'reference_type': 'assay',
                'source_ref': quantity_args['source_ref'], 'accession': accession,
                'label': 'external identifier; pH 7.5; 50 mM buffer; endpoint <0.2 U/mg',
                'sequence_ref': None, 'molecule': None, 'length': None,
                'term_refs': [], 'context_refs': []}, origin='external', scope=plain(context.scope)))
        context = replace(context, received_record_refs=(*context.received_record_refs, *(row['id'] for row in public)))
        facts = binding.facts(context, {'committed_record_refs': [sheet_ref]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(context, form, FORM)
        before = {row['id']: store.get(row['id']) for row in public}
        payload = json.loads(store.get_artifact(store.get(sheet_ref)['artifact_ref']))
        generated = store.get(payload['experimental_bindings']['km_curve_ref'])

        def state_for(adapter):
            state = snapshot()
            state.update(adapter.decision_context(context, None))
            state.update(scope=plain(context.scope), requested_form=FORM,
                available_report_facts=adapter.fact_sources('literature'),
                working_state=store.reasoning_view(plain(context.scope)),
                last_local_outcome=outcome, child_reports=[form],
                current_report_basis_refs=[row['id'] for row in public])
            if not received_map:
                state.pop('literature_received_fact_display')
            return state

        state = state_for(binding)
        assert generated['origin'] == 'tool'
        actual = {row['id']: row for row in state['working_state']['references']}
        assert actual[generated['id']] == generated
        if received_map:
            assert state['literature_received_fact_display']['records'][generated['id']] == generated
        wire = LiteratureWire(tmp_path / 'wire')
        asyncio.run(complete(wire, state_frame(state)))
        text = wire.turns_sent()[0]['input'][0]['text']
        for row in public:
            assert row['accession'] in text
        assert 'pH 7.5; 50 mM buffer; endpoint <0.2 U/mg' in text
        assert generated['accession'] not in text
        assert 'kinetic curve A' in text and '0.55' in text and '12.0' in text

        descriptor = binding.as_record()
        source = store.get(sheet_ref)
        km_source = store.get(arguments['km_sheet_ref'])
        allowed = {source['artifact_ref'], source['request_ref'], km_source['artifact_ref'], km_source['request_ref']}
        original_get = store.get_artifact

        def saved_only(reference):
            assert reference in allowed, 'saved reconstruction must not reacquire source bytes'
            return original_get(reference)

        def forbidden(*_args, **_kwargs):
            raise AssertionError('saved reconstruction must not parse or recalculate')

        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_transport_storage.read_transport_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_transport_storage.populate_transport_response', forbidden)
        store.db.execute('pragma query_only=ON')
        composition = compose_episode_bindings(binding.services, store=store, journal=journal,
            execution_backend=None, descriptors=[descriptor], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
        reconstructed, = composition.bindings
        assert asyncio.run(reconstructed.execute(context, 'literature.transport.response.populate', arguments, 'response')) == outcome
        restored = form_with_facts({}, FORM, reconstructed.facts(context, {'committed_record_refs': [sheet_ref]}))
        assert restored == form
        assert state_for(reconstructed) == state
        reopened = LiteratureWire(tmp_path / 'reopened')
        asyncio.run(complete(reopened, state_frame(state_for(reconstructed))))
        assert reopened.turns_sent()[0]['input'] == wire.turns_sent()[0]['input']
        assert {row['id']: store.get(row['id']) for row in public} == before
        assert store.get(generated['id']) == generated
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 0
    finally:
        store.close()
