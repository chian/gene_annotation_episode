"""Selected native measurements preserve experimental meaning across episodes."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_figure_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_figure_storage import LiteratureFigureRepository, figure_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_integration import source, witness
from test_runtime import FixtureController, ScriptedProvider

BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE / 'primary_f420_partner_013'
COMPONENTS = ['first_ordinate', 'second_ordinate', 'ordinate_difference']
FORM = obj({'measurements': figure_cells_schema()})
CASES = ['primary_swap', 'primary_representation', 'missing_second', 'cropped_first']


def synthetic_image(top):
    image = Image.new('RGB', (12, 12), 'white')
    for y in range(top, 10):
        for x in range(2, 10):
            image.putpixel((x, y), (20, 80, 160))
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def synthetic_selection():
    return {'roi': {'left': 2, 'right': 10, 'top': 0, 'bottom': 10},
        'rgb_min': [20, 80, 160], 'rgb_max': [20, 80, 160],
        'minimum_row_fraction': 1, 'minimum_run_rows': 2, 'edge_tolerance_pixels': 0,
        'calibration': {'first': {'pixel': 0, 'value': 100},
            'second': {'pixel': 10, 'value': 0}, 'unit': 'relative_turnover_percent'}}


def setup_case(path, *, case='primary_swap', components=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    primary = case.startswith('primary_')
    raw = ((PRIMARY/'PMC8764529.xml').read_bytes() if primary else
           b'SyntheticSubject SyntheticPartner secondPartner. Paired product formation; '
           b'combined assay with stated conditions and normalization.')
    paper = source(store, raw)
    refs = [paper['id']]
    literals = dict.fromkeys(LITERAL_FIELDS)
    w = lambda quote: witness(paper['id'], raw, quote)
    if primary:
        tables = json.loads((PRIMARY/'NATIVE_DOCX_TABLES_001.json').read_bytes())
        docx = [source(store, (PRIMARY/row['file']).read_bytes(), parents=[paper['id']]) for row in tables]
        projected = json.dumps(tables, ensure_ascii=False).encode()
        table = source(store, projected, parents=[row['id'] for row in docx])
        refs.extend(row['id'] for row in docx)
        refs.append(table['id'])
        tw = lambda quote: witness(table['id'], projected, quote)
        constructs = tables[0]['tables'][1]
        subject = constructs[14][1]
        standard, cognate = constructs[37][1], constructs[19][1]
        literals.update(first_subject=tw(subject), second_subject=tw(subject),
            first_partner=tw(cognate if case=='primary_swap' else standard), second_partner=tw(standard),
            experiment=w('combined assay'), endpoint=w('product formation'),
            first_condition=w('pH 7.4'), second_condition=w('pH 7.4'),
            normalization=w('normalization of AUC'), function=w('CofC/D reaction'))
        recipe = json.loads((PRIMARY/'NATIVE_BAR_SELECTIONS_001.json').read_bytes())
        selected = {row['quantity']: row for row in recipe['rows']}
        names = (['figure6B_cognate_3PG', 'figure6B_standard_3PG'] if case=='primary_swap'
                 else ['figure2C_MycB3_Mjan_3PG', 'figure6B_standard_3PG'])
        images = {}
        sides = []
        for name in names:
            row = selected[name]
            if row['image'] not in images:
                images[row['image']] = source(store, (PRIMARY/row['image']).read_bytes(), parents=[paper['id']])
                refs.append(images[row['image']]['id'])
            sides.append({'image_source_ref': images[row['image']]['id'], 'image_origin': 'published',
                          'axis_scale': 'linear', 'selection': row['selection']})
        repeat = {'reported_n': 3, 'repeat_kind': 'biological',
            'independent_preparation_count': None, 'spread_kind': 'SD', 'spread_numeric_status': 'not_extracted'}
        design = {'arrangement': 'coexisting_sequential_catalysts',
            'contrast_kind': 'partner_swap' if case=='primary_swap' else 'source_representation',
            'endpoint_scope': 'coupled_final_product', 'normalization_basis': 'reported_relative_turnover',
            'measurement_relation': 'distinct_physical_measurements' if case=='primary_swap' else 'unresolved',
            'first_repeat': repeat, 'second_repeat': deepcopy(repeat)}
    else:
        literals.update(first_subject=w('SyntheticSubject'), first_partner=w('SyntheticPartner'),
            second_subject=w('SyntheticSubject'), second_partner=w('secondPartner'),
            experiment=w('combined assay'), endpoint=w('product formation'),
            first_condition=w('stated conditions'), normalization=w('normalization'))
        sides = []
        for top in (3, 2):
            picture = source(store, synthetic_image(top), parents=[paper['id']])
            refs.append(picture['id'])
            sides.append({'image_source_ref': picture['id'], 'image_origin': 'synthetic',
                          'axis_scale': 'linear', 'selection': synthetic_selection()})
        repeat = {'reported_n': None, 'repeat_kind': 'unknown', 'independent_preparation_count': None,
                  'spread_kind': 'unreported', 'spread_numeric_status': 'unreported'}
        design = {'arrangement': 'unresolved', 'contrast_kind': 'other',
            'endpoint_scope': 'unreported', 'normalization_basis': 'unreported',
            'measurement_relation': 'unresolved', 'first_repeat': repeat, 'second_repeat': deepcopy(repeat)}
        if case=='missing_second':
            sides[1] = None
            design['second_repeat'] = None
        else:
            sides[0]['selection']['roi']['top'] = 4
    dataset = source(store, json.dumps({'version': 'literature_figure_selection_v1',
        'first': sides[0], 'second': sides[1], 'design': design}), parents=[paper['id']])
    refs.append(dataset['id'])
    args = {'source_ref': paper['id'], 'data_source_ref': dataset['id'],
        'source_kind': 'retained_extraction' if primary else 'synthetic_fixture',
        'literals': literals, 'interpretation_witnesses': [w('product formation')]}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': list(dict.fromkeys(refs)), 'requested_figure_components': components or COMPONENTS}
    context = BindingContext('figure-fixture-run', 'figure-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(assignment['source_refs']))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, case):
    assert [row['component'] for row in rows] == COMPONENTS
    values = [row['value'] for row in rows]
    if case=='primary_swap':
        assert values == pytest.approx([89.96845425867508, 65.48895899053628, 24.479495268138805])
    elif case=='primary_representation':
        assert values == pytest.approx([75.52859618717504, 65.48895899053628, 10.039637196638765])
    elif case=='missing_second':
        assert values == [65., None, None]
        assert rows[1]['unavailable_reason'] == 'second_ordinate_unreported'
    else:
        assert values == [None, 75., None]
        assert rows[0]['unavailable_reason'] == 'truncated_mean_edge'
        assert rows[2]['unavailable_reason'] == 'missing_ordinate'
    for row in rows:
        assert row['bound_kind'] == 'conditional_digitization_not_confidence_interval'
        assert row['statistical_uncertainty'] == 'not_extracted'
        assert row['partner_necessity'] == 'not_evaluated'
        assert row['target_correspondence'] == 'not_evaluated'
    if case.startswith('primary_'):
        assert rows[-1]['unit'] == 'relative_turnover_percentage_points'
        assert rows[0]['design']['first_repeat']['independent_preparation_count'] is None
        assert rows[0]['design']['first_repeat']['spread_kind'] == 'SD'


@pytest.mark.parametrize('case', CASES)
def test_selected_native_cells_and_saved_only_binding_reconstruction(tmp_path, monkeypatch, case):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    store, context, args = setup_case(tmp_path, case=case)
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.figure.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        form = form_with_facts({}, FORM, binding.facts(current, selected))
        binding.validate_report(current, form, FORM)
        check_rows(form['measurements'], case)
        bad = deepcopy(form['measurements'])
        bad[0]['partner_necessity'] = 'required'
        with pytest.raises(ContractError):
            LiteratureFigureRepository(store, context.run_id).validate_returned_values(
                bad, permitted_record_refs=current.received_record_refs)
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[binding.as_record()], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        restored, = composition.bindings
        sheet = store.get(outcome['result']['sheet_ref'])
        allowed = {sheet['artifact_ref'], sheet['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(ref):
            assert ref in allowed
            return get_artifact(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('saved graph evidence must not be reinterpreted')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        import gene_annotation_episode.literature_figure_storage as storage
        import gene_annotation_episode.literature_figure_inputs as reader
        import gene_annotation_episode.literature_figure_measurements as native
        monkeypatch.setattr(storage, 'read_figure_inputs', forbidden)
        monkeypatch.setattr(reader, 'read_figure_inputs', forbidden)
        for name in ('read_bar_ordinate', 'compare_ordinate_cells'):
            monkeypatch.setattr(reader, name, forbidden)
            monkeypatch.setattr(native, name, forbidden)
        store.db.execute('PRAGMA query_only=ON')
        assert asyncio.run(restored.execute(context, 'literature.figure.populate', args, 'selected')) == outcome
        assert form_with_facts({}, FORM, restored.facts(current, selected)) == form


@pytest.mark.parametrize('case', CASES)
def test_ordinary_figure_child_parent_delivery_and_observation_counts(tmp_path, case):
    store, context, args = setup_case(tmp_path/'state', case=case)
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the paired experimental graph measurements',
            'scope': plain(context.scope), 'purpose': 'Return the requested source figure components and meanings',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.figure.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            check_rows(form['measurements'], case)
            if case.startswith('primary_'):
                delivered = {row['id']: row for row in inputs['working_state']['references']}
                for field in ('first_subject_ref', 'first_partner_ref', 'second_subject_ref', 'second_partner_ref'):
                    record = delivered[form['measurements'][0][field]]
                    assert 'N-His' in record['label']
                    assert record['anchor']['quote'] == record['label']
            received.append(form)
            commit = {key: [] for key in store.reasoning_schema()['required']}
            paper = store.get(args['source_ref'])
            raw = store.get_artifact(paper['artifact_ref'])
            label = 'KQH55_09515' if case.startswith('primary_') else 'SyntheticSubject'
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
        assert store.db.execute('SELECT count(*) FROM literature_figure_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_figure_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')


def test_parent_receives_requested_difference_and_experimental_meanings_once(tmp_path):
    from gene_annotation_episode.literature_reference_parent_prompt import (
        REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt)
    from gene_annotation_episode.literature_figure_prompt import FIGURE_TASK
    store, context, args = setup_case(tmp_path, components=['ordinate_difference'])
    with store:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.figure.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        rows = LiteratureFigureRepository(store, context.run_id).project_cells([outcome['result']['sheet_ref']],
            permitted_record_refs=outcome['record_refs'], components=['ordinate_difference'])
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {
            'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'goal': {'objective': 'Decide what the partner swap establishes'},
            'child_reports': [{'measurements': rows}]}
        text = render_reference_evidence_parent_prompt(state, 'Own parent instructions')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert REFERENCE_PARENT_TASK in task and FIGURE_TASK not in task
        assert steering.count('Received experimental figure bindings') == 1
        assert steering.count('design.contrast_kind') == 1
        for meaning in ('partner_swap', 'coexisting_sequential_catalysts', 'coupled_final_product',
                'reported_relative_turnover', 'not_extracted', 'relative_turnover_percentage_points',
                'conditional_digitization_not_confidence_interval', 'first_partner_ref', 'second_partner_ref',
                'design.first_repeat.spread_kind', 'SD', 'design.first_repeat.independent_preparation_count'):
            assert meaning in steering
        assert 'first_ordinate' not in steering and 'second_ordinate' not in steering
        assert 'image_sha256' not in text and 'rgb_min' not in text and 'roi.' not in text


def test_figure_task_repeats_through_lookup_delta_and_reconstruction(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_figure_prompt import FIGURE_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    first = snapshot()
    first['goal']['objective'] = 'Examine the actual coupled product graph comparison'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_figure_components'] = ['ordinate_difference']
    first['available_report_facts']['literature_figure_cells'] = {'meaning': 'Native plotted comparison'}
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {'cells': {
        'ordinate_difference': {'value': 24.48, 'lower': 23.84, 'upper': 25.12,
            'unit': 'relative_turnover_percentage_points', 'status': 'populated', 'origin': 'derived',
            'bound_kind': 'conditional_digitization_not_confidence_interval', 'unavailable_reason': None}},
        'design': {'contrast_kind': 'partner_swap', 'endpoint_scope': 'coupled_final_product'},
        'statistical_uncertainty': 'not_extracted', 'partner_necessity': 'not_evaluated'}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 2, 'exchange_index': 1,
        'result': {'status': 'completed', 'text': 'Both catalysts coexist in each reaction arm.'}}
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
            assert FIGURE_TASK in task and first['goal']['objective'] in task
            tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        for meaning in ('partner_swap', 'coupled_final_product', 'conditional_digitization_not_confidence_interval',
                'not_extracted', 'not_evaluated'):
            assert meaning in steering
