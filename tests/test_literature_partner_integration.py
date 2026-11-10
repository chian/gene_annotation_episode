"""Condition-specific partner components through the ordinary typed episode path."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_partner_calculations import COMPONENTS
from gene_annotation_episode.literature_partner_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_integration import source, witness
from test_runtime import FixtureController, ScriptedProvider

BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE / 'primary_pdx_partner_015'
CASES = ('primary_crossed', 'matched', 'censored', 'baseline_reused')
FORM = obj({'measurements': partner_cells_schema()})


def setup_case(path, *, case='primary_crossed', components=None, target_sequence=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT' if target_sequence is None else target_sequence,
        molecule='dna' if target_sequence is None else 'protein')
    if case == 'primary_crossed':
        manifest = json.loads((PRIMARY/'PAPER_SOURCE_RECORD_001.json').read_text())
        original_args = json.loads((PRIMARY/'PAPER_ARGUMENTS_001.json').read_text())
        sources, refs = {}, []
        for row in manifest['sources'][:2]:
            raw = (PRIMARY/row['file']).read_bytes()
            saved = source(store, raw, parents=refs[:1])
            sources[row['source_ref']] = saved['id']
            refs.append(saved['id'])
        recipe = json.loads((PRIMARY/'PAPER_SELECTION_001.json').read_text())
        args = deepcopy(original_args)
        args['source_ref'] = sources[args['source_ref']]
        for selected in (*args['literals'].values(), *args['interpretation_witnesses']):
            if selected:
                selected['source_ref'] = sources[selected['source_ref']]
    else:
        raw = (b'Synthetic subject; Synthetic partner; PLP assay; product formation; '
               b'reference glutamine; omitted glutamine; addback glutamine; per mg subject. '
               b'All other declared conditions are matched.')
        paper = source(store, raw)
        refs = [paper['id']]
        w = lambda q: witness(paper['id'], raw, q)
        literal_quotes = ('Synthetic subject', 'Synthetic partner', 'PLP assay', 'product formation',
                          'per mg subject', 'reference glutamine', 'omitted glutamine',
                          'addback glutamine', 'PLP assay')
        args = {'source_ref': paper['id'], 'source_kind': 'synthetic_fixture',
            'literals': {name: w(quote) for name, quote in zip(LITERAL_FIELDS, literal_quotes)},
            'interpretation_witnesses': [w('All other declared conditions are matched.')]}
        arms = {}
        for role, value in (('reference', 100), ('omitted', 20), ('addback', 90)):
            arms[role] = {'subject_ref': 'synthetic_subject', 'partner_ref': 'synthetic_partner',
                'partner_state': 'absent' if role == 'omitted' else 'present',
                'endpoint_ref': 'synthetic_PLP', 'normalization_ref': 'synthetic_subject_mass',
                'unit': 'pmol/min/mg', 'conditions': {'coverage': 'complete', 'factors': [
                    {'factor': 'nitrogen_source', 'level': 'glutamine', 'unit': 'identity'},
                    {'factor': 'temperature', 'level': 37, 'unit': 'degC'}]},
                'measurement': {'measurement_id': 'synthetic_' + role, 'status': 'observed',
                    'value': value, 'origin': 'synthetic',
                    'spread': {'kind': 'unreported', 'magnitude': None}}}
        if case == 'censored':
            arms['omitted']['measurement'].update(status='upper_bound', value=5)
        elif case == 'baseline_reused':
            arms['addback']['measurement'].update(measurement_id='synthetic_reference', value=100)
        recipe = {'version': 'literature_partner_selection_v1',
            'inputs': {'version': 'literature_partner_inputs_v1', 'arms': arms}}
    dataset = source(store, json.dumps(recipe), parents=refs)
    refs.append(dataset['id'])
    args['data_source_ref'] = dataset['id']
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_partner_components': list(COMPONENTS if components is None else components)}
    context = BindingContext('partner-fixture-run', 'partner-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, case):
    assert [r['component'] for r in rows] == list(COMPONENTS)
    cells = {r['component']: r for r in rows}
    if case == 'primary_crossed':
        assert [r['value'] for r in rows] == [774, 284, None, None, None, None, None, None]
        assert cells['partner_loss']['unavailable_reason'] == 'nonpartner_conditions_differ'
        assert rows[0]['comparison_checks']['reference_omitted']['status'] == 'different'
        assert rows[0]['arm_metadata']['reference']['spread'] == {'kind': 'unspecified', 'magnitude': 58}
    elif case == 'matched':
        assert [r['value'] for r in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
    elif case == 'censored':
        assert cells['omitted_rate']['value'] is None
        assert cells['addback_fraction']['lower'] == pytest.approx(85/95)
        assert cells['addback_fraction']['upper'] == pytest.approx(.9)
        assert cells['addback_fraction']['bound_kind'] == 'conditional_input_domain_not_CI'
    else:
        assert cells['partner_loss_fraction']['value'] == .8
        for name in ('addback_gain', 'addback_fraction', 'restored_reference_fraction'):
            assert cells[name]['unavailable_reason'] == 'role_measurement_not_distinct'
    for row in rows:
        assert row['evaluation_scope'] == 'reference_experimental_partner_components'
        assert row['partner_necessity'] == 'not_inferred'
        assert row['target_correspondence'] == 'not_evaluated'
        assert row['statistical_uncertainty'] == 'not_evaluated'


@pytest.mark.parametrize('case', CASES)
def test_selected_components_saved_only_reconstruction_and_exact_typed_subset(tmp_path, monkeypatch, case):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, args = setup_case(tmp_path, case=case)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.partner.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(current, selected))
        binding.validate_report(current, form, FORM)
        check_rows(form['measurements'], case)
        bad = deepcopy(form['measurements'])
        bad[0]['partner_necessity'] = 'required'
        with pytest.raises(ContractError):
            LiteraturePartnerRepository(store, context.run_id).validate_returned_values(
                bad, permitted_record_refs=current.received_record_refs)
        restored, = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[binding.as_record()], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings
        sheet = store.get(outcome['result']['sheet_ref'])
        allowed = {sheet['artifact_ref'], sheet['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return get_artifact(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved partner evidence must not be reinterpreted')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        import gene_annotation_episode.literature_partner_storage as storage
        import gene_annotation_episode.literature_partner_inputs as reader
        import gene_annotation_episode.literature_partner_calculations as calculator
        import gene_annotation_episode.literature_assay_inputs as sources
        monkeypatch.setattr(storage, 'read_partner_inputs', forbidden)
        monkeypatch.setattr(reader, 'read_partner_inputs', forbidden)
        monkeypatch.setattr(reader, 'populate_partner_components', forbidden)
        monkeypatch.setattr(calculator, 'populate_partner_components', forbidden)
        monkeypatch.setattr(sources, '_Sources', forbidden)
        store.db.execute('PRAGMA query_only=ON')
        assert asyncio.run(restored.execute(context, 'literature.partner.populate', args, 'selected')) == outcome
        assert form_with_facts({}, FORM, restored.facts(current, selected)) == form


@pytest.mark.parametrize('case', CASES)
def test_ordinary_partner_child_parent_delivery_preserves_scientific_meanings(tmp_path, case):
    store, context, args = setup_case(tmp_path/'state', case=case)
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate conditional experimental partner evidence',
            'scope': plain(context.scope), 'purpose': 'Return the requested partner components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.partner.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            check_rows(form['measurements'], case)
            first = form['measurements'][0]
            refs = {r['id']: r for r in inputs['working_state']['references']}
            assert refs[first['subject_ref']]['anchor']['quote'] == (
                'Pdx1 (Rv2606c)' if case == 'primary_crossed' else 'Synthetic subject')
            assert refs[first['partner_ref']]['anchor']['quote'] == (
                'Pdx2 (Rv2604c)' if case == 'primary_crossed' else 'Synthetic partner')
            if case == 'primary_crossed':
                terms = {r['id']: r for r in inputs['working_state']['terms']}
                factors = first['comparison_checks']['reference_omitted']['differing_factor_refs']
                assert [terms[ref]['label'] for ref in factors] == ['nitrogen_source']
                assert all(terms[ref]['source_ref'] == args['data_source_ref'] for ref in factors)
            received.append(form)
            commit = {key: [] for key in store.reasoning_schema()['required']}
            paper = store.get(args['source_ref'])
            raw = store.get_artifact(paper['artifact_ref'])
            label = 'Pdx1' if case == 'primary_crossed' else 'Synthetic subject'
            anchor = witness(paper['id'], raw, label)
            anchor.pop('representation')
            anchor['artifact_ref'] = paper['artifact_ref']
            commit['source_subjects'] = [{'alias': 'studied_molecule', 'reference_type': 'assay',
                'source_ref': paper['id'], 'label': label, 'anchor': anchor}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, action, receive]), run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path)==1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and summary['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_partner_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')


def test_parent_task_and_requested_qualifications_are_rendered_once(tmp_path):
    from gene_annotation_episode.literature_reference_parent_prompt import (
        REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt)
    from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
    store, context, args = setup_case(tmp_path, components=['partner_loss_fraction', 'addback_fraction'])
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.partner.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        rows = LiteraturePartnerRepository(store, context.run_id).project_cells([outcome['result']['sheet_ref']],
            permitted_record_refs=outcome['record_refs'], components=context.assignment['requested_partner_components'])
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {
            'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'goal': {'objective': 'Decide what controlled partner loss is established'},
            'child_reports': [{'measurements': rows}]}
        text = render_reference_evidence_parent_prompt(state, 'Own parent instructions')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert REFERENCE_PARENT_TASK in task and PARTNER_TASK not in task
        assert steering.count('Received experimental partner bindings') == 1
        for meaning in ('nonpartner_conditions_differ', 'unspecified', '58', 'partial', 'not_inferred'):
            assert meaning in steering
        assert steering.count('arm_metadata.reference.spread.kind') == 1
        assert 'reference_rate' not in steering and 'omitted_rate' not in steering
        assert 'measurement_id' not in steering and 'synthetic_reference' not in steering


def test_partner_task_repeats_after_lookup_delta_and_reconstruction(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Establish conditional partner requirements from controlled experiments'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_partner_components'] = ['partner_loss_fraction']
    first['available_report_facts']['literature_partner_cells'] = {'meaning': 'Condition-specific dependence'}
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {'cells': {
        'partner_loss_fraction': {'value': None, 'lower': None, 'upper': None, 'unit': 'dimensionless',
            'origin': 'derived', 'status': 'unavailable', 'bound_kind': 'point_only_not_uncertainty',
            'unavailable_reason': 'nonpartner_conditions_differ'}}, 'comparison_checks': {
                'reference_omitted': {'status': 'different', 'differing_factor_refs': [],
                    'unavailable_reason': 'nonpartner_conditions_differ'}},
        'arm_metadata': {'reference': {'spread': {'kind': 'unspecified', 'magnitude': 58}}},
        'partner_necessity': 'not_inferred'}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 2, 'exchange_index': 1,
        'result': {'status': 'completed', 'text': 'Nitrogen source changes with partner presence.'}}
    wire, reopened = LiteratureWire(tmp_path/'wire'), LiteratureWire(tmp_path/'reopened')
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(reopened, state_frame(second))
    asyncio.run(exercise())
    tasks = []
    for transport in (wire, reopened):
        for turn in transport.turns_sent():
            task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
            assert PARTNER_TASK in task and first['goal']['objective'] in task
            tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ('nonpartner_conditions_differ', 'unspecified', '58', 'not_inferred'):
            assert meaning in steering
