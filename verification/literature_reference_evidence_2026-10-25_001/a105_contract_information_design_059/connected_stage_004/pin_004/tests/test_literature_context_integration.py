"""Contextual uncertainty and fixed question meanings in ordinary episodes."""
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
from gene_annotation_episode.literature_context_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_context_storage import LiteratureContextRepository, context_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_integration import source, witness
from test_runtime import FixtureController, ScriptedProvider

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT/'research/experimental_scoring_review_2026-10-23/a108_plausibility_sheet_014/huc_2023_primary.xml'
COMPONENTS = ['coverage_lower', 'coverage_upper', 'capability_lower', 'capability_upper',
              'selected_point', 'sampling_lower', 'sampling_upper']
FORM = obj({'measurements': context_cells_schema()})


def interval(lower, upper, *, lc=True, uc=True):
    return {'lower': lower, 'upper': upper, 'lower_closed': lc, 'upper_closed': uc}


def observation(key, value, unit, *, relation='numeric'):
    return {'requirement_key': key, 'measurement_key': key+'-measured', 'unit': unit,
        'interval': interval(value, value) if relation == 'numeric' else None, 'relation': relation,
        'reported_sd': None, 'reported_sem': None, 'reported_plusminus': None,
        'reported_count': None, 'count_relation': 'unknown', 'replicate_kind': 'unknown'}


def inputs_for(case):
    primary = case == 'primary'
    inputs = {'question_kind': 'organism_capability' if primary or case == 'capability' else 'sample_context_coverage',
        'origin': 'reported' if primary else 'synthetic', 'scope_status': 'defined',
        'frame_status': 'unreported' if primary else 'defined', 'pairing': 'unknown' if primary else 'paired',
        'weight_basis': 'equal_units', 'sampling_design': 'unknown' if primary else 'independent_equal_weight',
        'alpha': None if primary else .05, 'permitted_remainder': True,
        'requirements': [
            {'key': 'access', 'unit': 'state', 'supported': [], 'incompatible': []},
            {'key': 'exposure', 'unit': 'mM', 'supported': [interval(2.5, 10)],
                'incompatible': [interval(0, 2.5, uc=False)]},
            {'key': 'oxygen', 'unit': 'percent_O2_gas', 'supported': [interval(0, 1)],
                'incompatible': [interval(1, None, lc=False, uc=False)]}],
        'routes': [{'key': 'biological_route', 'requirements': ['access', 'exposure', 'oxygen'],
            'requirements_complete': True, 'joint_support': 'established'}],
        'contexts': [], 'marginals': []}
    if primary:
        # Purified enzyme assays give no native sample frame or local habitat
        # values. Do not manufacture native context rows from technical vials.
        inputs['requirements'] = [
            {'key': 'local_hydrogen', 'unit': 'ppbv_H2_gas', 'supported': [], 'incompatible': []},
            {'key': 'local_oxygen', 'unit': 'percent_O2_gas', 'supported': [], 'incompatible': []}]
        inputs['routes'] = [{'key': 'native_atmospheric_context',
            'requirements': ['local_hydrogen', 'local_oxygen'],
            'requirements_complete': False, 'joint_support': 'unresolved'}]
        return inputs
    if case == 'marginal':
        inputs.update(pairing='unpaired_marginals', sampling_design='unknown', alpha=None,
            marginals=[{'requirement_key': key, 'lower': p, 'upper': p}
                for key, p in zip(('access', 'exposure', 'oxygen'), (.8, .8, .9))])
        return inputs
    for i in range(12 if case == 'capability' else 10):
        access = i == 0 if case == 'capability' else i < 8
        exposure = 5. if (i == 0 if case == 'capability' else i < 6) else 1.
        oxygen = .5 if (i == 0 if case == 'capability' else i < 5) else 2.
        measurements = [observation('access', None, 'state', relation='supported' if access else 'incompatible'),
            observation('exposure', exposure, 'mM'), observation('oxygen', oxygen, 'percent_O2_gas')]
        for row in measurements:
            row['measurement_key'] += '-'+str(i)
        inputs['contexts'].append({'key': 'microhabitat-'+str(i), 'weight': 1.,
            'cluster_key': 'independent-specimen-'+str(i), 'scope_match': 'matched', 'observations': measurements})
    return inputs


def setup_case(path, *, case='paired'):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw = PRIMARY.read_bytes() if case == 'primary' else (
        b'SyntheticProtein in SyntheticOrganism FixtureStrain; trace-gas metabolism; '
        b'measured biological microhabitats; fixed sample frame; contextual compatibility endpoint.')
    paper = source(store, raw)
    w = lambda quote: witness(paper['id'], raw, quote)
    literals = dict.fromkeys(LITERAL_FIELDS)
    if case == 'primary':
        literals.update(molecule=w('Huc'), organism=w('M. smegmatis'), strain=w('PRC1'),
            function=w('atmospheric H<sub>2</sub> oxidation'), biological_context=w('stationary phase'))
        interpretations = [w('purified Huc')]
    else:
        literals.update(molecule=w('SyntheticProtein'), organism=w('SyntheticOrganism'),
            strain=w('FixtureStrain'), function=w('trace-gas metabolism'),
            biological_context=w('measured biological microhabitats'), sample_frame=w('fixed sample frame'),
            endpoint=w('contextual compatibility endpoint'))
        interpretations = [w(raw.decode())]
    data = {'version': 'a108_source_context_measurements_v1', 'inputs': inputs_for(case)}
    dataset = source(store, canonical(data), parents=[paper['id']])
    args = {'source_ref': paper['id'], 'data_source_ref': dataset['id'],
        'source_kind': 'retained_extraction' if case == 'primary' else 'synthetic_fixture',
        'literals': literals, 'interpretation_witnesses': interpretations}
    refs = [paper['id'], dataset['id']]
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_context_components': COMPONENTS}
    context = BindingContext('context-fixture-run', 'context-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, case):
    assert [row['component'] for row in rows] == COMPONENTS
    values = [row['value'] for row in rows]
    if case == 'primary':
        assert values == [0., 1., 0., 1., None, None, None]
        assert all(row['context_units'] == 0 and row['actual_sampling_n'] is None for row in rows)
        assert all(row['frame_status'] == 'unreported' and row['permitted_remainder'] is True for row in rows)
    elif case == 'paired':
        assert values[:5] == [.5, .5, 1., 1., .5]
        assert values[5:] == pytest.approx([.070530591653, .929469408347])
        assert all(row['actual_sampling_n'] == 10 for row in rows)
    elif case == 'capability':
        assert values[:2] == pytest.approx([1/12, 1/12])
        assert values[2:] == [1., 1., 1., None, None]
    else:
        assert values[:4] == pytest.approx([.5, .8, 0., 1.])
        assert values[4:] == [None, None, None]
        assert all(row['pairing'] == 'unpaired_marginals' for row in rows)
    assert all(row['evaluation_scope'] == 'reference_organism_sample_compatibility' for row in rows)
    assert all(row['target_correspondence'] == 'not_evaluated' for row in rows)


@pytest.mark.parametrize('case', ['primary', 'paired', 'marginal', 'capability'])
def test_actual_selected_return_and_saved_only_reconstruction(tmp_path, monkeypatch, case):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, args = setup_case(tmp_path, case=case)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.context.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(current, selected))
        binding.validate_report(current, form, FORM)
        check_rows(form['measurements'], case)
        repo = LiteratureContextRepository(store, context.run_id)
        bad = deepcopy(form['measurements'])
        bad[0]['question_kind'] = ('sample_context_coverage'
            if bad[0]['question_kind'] == 'organism_capability' else 'organism_capability')
        with pytest.raises(ContractError):
            repo.validate_returned_values(bad, permitted_record_refs=current.received_record_refs)
        descriptor = binding.as_record()
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        restored, = composition.bindings
        saved = store.get(outcome['result']['sheet_ref'])
        allowed = {saved['artifact_ref'], saved['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return get_artifact(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved compatibility must not be reinterpreted')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.read_context_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.populate_context_compatibility', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.empty_context_inputs', forbidden)
        store.db.execute('pragma query_only=ON')
        assert asyncio.run(restored.execute(context, 'literature.context.populate', args, 'selected')) == outcome
        assert form_with_facts({}, FORM, restored.facts(current, selected)) == form


@pytest.mark.parametrize('case', ['primary', 'paired', 'marginal', 'capability'])
def test_ordinary_child_parent_delivery_has_one_own_observation_per_action(tmp_path, case):
    store, context, args = setup_case(tmp_path/'state', case=case)
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the specified organism/sample compatibility question',
            'scope': plain(context.scope), 'purpose': 'Return only requested compatibility and uncertainty components',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.context.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            check_rows(form['measurements'], case)
            label = 'Huc' if case == 'primary' else 'SyntheticProtein'
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
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and summary['credit'] == 0
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_context_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')


def test_context_task_repeats_after_lookup_and_reconstruction_at_provider_boundary(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_context_prompt import CONTEXT_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Evaluate compatibility with the specified native biological situation.'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_context_components'] = COMPONENTS
    first['available_report_facts']['literature_context_cells'] = {'meaning': 'Scoped biological compatibility and uncertainty.'}
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {
        'cells': {'selected_point': {'value': None, 'unit': 'dimensionless', 'status': 'unavailable',
            'origin': 'derived', 'unavailable_reason': 'capability_unresolved', 'conditional_on': []}},
        'question_kind': 'organism_capability', 'scope_status': 'defined', 'frame_status': 'unreported',
        'pairing': 'unknown', 'permitted_remainder': True, 'actual_sampling_n': None,
        'requirement_definitions': [{'unit': 'ppbv_H2_gas', 'supported': [], 'incompatible': []}],
        'route_definitions': [{'requirements': [0], 'requirements_complete': False, 'joint_support': 'unresolved'}],
        'measurement_corrections': 'not_applied', 'target_correspondence': 'not_evaluated'}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'decision_index': 2,
        'exchange_index': 1, 'result': {'status': 'completed', 'text': 'The selected experiment used purified protein.'}}
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
            tasks.append(task)
            assert CONTEXT_TASK in task and first['goal']['objective'] in task
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ('organism_capability', 'unreported', 'unresolved', 'ppbv_H2_gas',
                'Context operating requirements', 'Alternative biological routes', 'none established'):
            assert meaning in steering


def test_parent_receives_exact_definitions_once_with_only_requested_cells(tmp_path):
    from gene_annotation_episode.literature_reference_parent_prompt import (
        REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt)
    store, context, args = setup_case(tmp_path)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.context.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        repo = LiteratureContextRepository(store, context.run_id)
        rows = repo.project_cells([outcome['result']['sheet_ref']],
            permitted_record_refs=outcome['record_refs'], components=['selected_point', 'sampling_lower'])
        assert rows[0]['requirement_definitions'][1]['supported'] == [interval(2.5, 10)]
        assert rows[0]['route_definitions'] == [{'requirements': [0, 1, 2],
            'requirements_complete': True, 'joint_support': 'established'}]
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {
            'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'goal': {'objective': 'Decide which biological compatibility uncertainty to investigate'},
            'child_reports': [{'measurements': rows}]}
        text = render_reference_evidence_parent_prompt(state, 'Own parent instructions')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert REFERENCE_PARENT_TASK in task and state['goal']['objective'] in task
        assert steering.count('Context operating requirements') == 1
        assert steering.count('Alternative biological routes') == 1
        assert 'selected_point' in steering and 'sampling_lower' in steering
        assert 'coverage_point' not in steering
        assert '[2.5, 10]' in steering and 'percent_O2_gas' in steering
        assert 'hoeffding_outer_sampling_enclosure' in steering
        assert 'actual_sampling_n' in steering
        assert 'literature_measurement_' not in text and 'cluster_key' not in text
