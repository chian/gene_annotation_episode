"""Reported source chemistry and synthetic contrasts through ordinary episodes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.communication import form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a110.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a110.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_inputs import LITERAL_FIELDS
from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_report_contracts import reaction_cells_schema
from gene_annotation_episode.episodic_workflow.root.a110.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a110.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

BASE = Path(__file__).parent / 'fixtures/source_records'
COMPONENTS = ['ratio_mean', 'claim_mean_squared_error', 'reaction_comparison',
              'resource_coverage', 'resource_comparison_upper']
FORM = obj({'measurements': reaction_cells_schema()})


def source(store, raw, *, parents=(), text=None):
    artifact = store.artifact(raw, 'application/octet-stream')
    text_ref = store.artifact(text, 'text/plain') if text is not None else None
    return store.put('source', {'provider': 'source_reaction_example', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': text_ref, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def witness(ref, raw, quote, representation='original'):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': representation, 'start': start,
            'end': start+len(token), 'quote': quote}

def location_inputs(value):
    """Tool arguments in the current input form: a source location without a supplied quotation."""
    if isinstance(value, list):
        return [location_inputs(item) for item in value]
    if isinstance(value, dict):
        located = 'quote' in value and {'start', 'end'} <= set(value)
        return {key: location_inputs(item) for key, item in value.items() if not (located and key == 'quote')}
    return value



def setup_case(path, *, primary=False, incomplete=False, target_sequence=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT' if target_sequence is None else target_sequence,
        molecule='dna' if target_sequence is None else 'protein')
    raw = ((BASE/'primary_csid/PMC6265302_original.xml').read_bytes() if primary else
        b'SyntheticProtein produces ProductA per ProductB in independent preparations. '
        b'Matched synthetic reaction and resource budget with declared usable supply.')
    paper = source(store, raw)
    refs = [paper['id']]
    literals = dict.fromkeys(LITERAL_FIELDS)
    if primary:
        layout = (BASE/'primary_csid/supplement_layout.txt').read_bytes()
        supplement = source(store, (BASE/'primary_csid/41467_2018_7563_MOESM1_ESM.pdf').read_bytes(),
            parents=[paper['id']], text=layout)
        refs.append(supplement['id'])
        sw = lambda quote: witness(supplement['id'], layout, quote, 'text')
        literals.update(molecule=witness(paper['id'], raw, 'CsiD'),
            construct=witness(paper['id'], raw, 'N-terminal His-tag'),
            experiment=sw('Supplementary Figure 2:'), numerator=sw('succinic acid'),
            denominator=sw('L-2-hydroxyglutarate'), endpoint=sw('products of the CsiD reaction'),
            condition=witness(paper['id'], raw, '20\u2009mM ammonium acetate buffer pH 7.25'))
        interpretations = [sw('succinic acid : L-2-hydroxyglutarate = 1:1')]
        ratio = {'mode': 'source_summary', 'ratio_kind': 'product_pair', 'unit': 'mol_per_mol',
            'origin': 'reported', 'observations': [], 'mean': 1., 'sample_sd': None,
            'independent_n': None, 'claim': 1., 'alternatives': []}
        budget = None
    else:
        w = lambda quote: witness(paper['id'], raw, quote)
        literals.update(molecule=w('SyntheticProtein'), numerator=w('ProductA'),
            denominator=w('ProductB'), experiment=w('independent preparations'),
            endpoint=w('synthetic reaction'), resource_context=w('declared usable supply'))
        interpretations = [w(raw.decode('utf-8'))]
        ratio = {'mode': 'independent_units', 'ratio_kind': 'product_pair', 'unit': 'mol_per_mol',
            'origin': 'synthetic', 'observations': [
                {'measurement_key': 'preparation1', 'value': .7},
                {'measurement_key': 'preparation2', 'value': .9}],
            'mean': None, 'sample_sd': None, 'independent_n': None, 'claim': 1.,
            'alternatives': [{'key': 'half_product_ratio', 'prediction': .5}]}
        budget = {'basis': 'usable_batch', 'unit': 'umol', 'origin': 'synthetic',
            'resources_complete': not incomplete, 'resources': [
                {'resource_key': 'reagent1', 'value': 12., 'lower': 12., 'upper': 12., 'coefficient': 1.},
                {'resource_key': 'reagent2', 'value': 6., 'lower': 6., 'upper': 6., 'coefficient': 1.}],
            'demand': 10.}
    data = {'version': 'a110_source_reaction_measurements_v1', 'ratio': ratio, 'budget': budget}
    dataset = source(store, canonical(data), parents=refs)
    refs.append(dataset['id'])
    args = {'source_ref': paper['id'], 'data_source_ref': dataset['id'],
        'source_kind': 'retained_extraction' if primary else 'synthetic_fixture',
        'literals': literals, 'interpretation_witnesses': interpretations}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_reaction_components': COMPONENTS}
    context = BindingContext('reaction-fixture-run', 'reaction-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host))
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize('primary', [False, True])
def test_selected_in_ordinary_child_and_received_once(tmp_path, primary):
    store, context, args = setup_case(tmp_path/'state', primary=primary)
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the source product-pair ratio and resource requirements',
            'scope': plain(context.scope), 'purpose': 'Return the requested numerical chemistry components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.reaction.populate',
            'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert [row['component'] for row in rows] == COMPONENTS
            assert rows[0]['value'] == pytest.approx(1. if primary else .8)
            assert rows[2]['value'] == (None if primary else pytest.approx(1/3))
            label = 'CsiD' if primary else 'SyntheticProtein'
            paper = store.get(args['source_ref'])
            raw = store.get_artifact(paper['artifact_ref'])
            start = raw.index(label.encode())
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'studied_molecule', 'reference_type': 'assay',
                'source_ref': paper['id'], 'label': label, 'anchor': {'source_ref': paper['id'],
                    'artifact_ref': paper['artifact_ref'], 'start': start, 'end': start+len(label), 'quote': label}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, action, receive]), run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path)==1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisode),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and summary['credit'] == 0
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_reaction_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_reaction_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')


def test_recurring_reaction_task_and_material_qualifications_at_provider(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a110.decision_context import state_frame
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_prompt import REACTION_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Evaluate what the source reaction experiment actually measures.'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_reaction_components'] = COMPONENTS
    first['available_report_facts']['literature_reaction_cells'] = {'meaning': 'Reported reference reaction constraints.'}
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {
        'cells': {'claim_mean_squared_error': {'value': None, 'unit': 'squared_ratio',
            'status': 'unavailable', 'origin': 'derived', 'unavailable_reason': 'summary_variance_unreported',
            'conditional_on': []}}, 'ratio_mode': 'source_summary', 'ratio_kind': 'product_pair',
        'ratio_unit': 'mol_per_mol', 'claim_prediction': 1., 'alternative_predictions': [],
        'budget_basis': None, 'resources_complete': None, 'measurement_corrections': 'not_applied',
        'target_correspondence': 'not_evaluated'}}
    wire = LiteratureWire(tmp_path/'wire')
    reopened = LiteratureWire(tmp_path/'reopened')
    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(reopened, state_frame(second))
    asyncio.run(exercise())
    tasks = []
    for transport in (wire, reopened):
        for turn in transport.turns_sent():
            text = turn['input'][0]['text']
            task, steering = text.split('\n\nSTEERING\n', 1)
            tasks.append(task)
            assert REACTION_TASK in task and first['goal']['objective'] in task
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ('source_summary', 'product_pair', 'mol_per_mol', 'not_applied', 'not_evaluated'):
            assert meaning in steering


def test_parent_steering_groups_only_admitted_reaction_cells_and_keeps_own_task(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.library.literature_reference_parent_presentation import REFERENCE_PARENT_TASK
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reference_parent_presentation import render_reference_evidence_parent_prompt
    store, context, args = setup_case(tmp_path)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.reaction.populate', location_inputs(args), 'selected'))
        assert outcome['status'] == 'completed'
        repo = LiteratureReactionRepository(store, context.run_id)
        rows = repo.project_cells([outcome['result']['sheet_ref']],
            permitted_record_refs=outcome['record_refs'], components=['reaction_comparison', 'resource_coverage'])
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {
            'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'goal': {'objective': 'Decide which source reaction uncertainty needs further investigation'},
            'child_reports': [{'measurements': rows}]}
        text = render_reference_evidence_parent_prompt(state, 'Own parent instructions')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert REFERENCE_PARENT_TASK in task
        assert state['goal']['objective'] in task
        assert steering.count('Calculated source cells') == 1
        assert steering.count('claim_prediction') == 1
        assert 'reaction_comparison' in steering and 'resource_coverage' in steering
        assert 'claim_nominal_squared_error' not in steering
        assert 'simple_fixed_consumption_model' in steering
        assert 'measurement_corrections' in steering and 'not_applied' in steering
        assert 'measurement_key' not in text and 'literature_measurement_' not in text
