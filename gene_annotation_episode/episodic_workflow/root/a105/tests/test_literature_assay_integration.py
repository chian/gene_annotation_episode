from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories
'Synthetic source operand graph through selected action, state and typed return.\n\nNo biological source or actual model inference is represented by these fixtures.\n'
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_storage import LiteratureAssayRepository, assay_cells_schema
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import read_assay_inputs
from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import FixtureController, ScriptedProvider
TEXT = 'Protein P from organism X was assayed as construct P-His in purified preparation with substrate A.\nThe assay condition was 30 C and pH 7.\nOne preparation was measured for identified product B formation.\nThe reported net sample-minus-blank rate was 1.00 µM/min.\nA separately measured contaminant contributed 0.15 uM/min.\nThe quantitative calibration recovery ratio was 1.00 fraction.\nThe assayed molecule concentration was 1000 nM.\nThe same-endpoint condition-control test rate was 2.00 uM/min.\nThe same-endpoint condition-control reference rate was 1.60 uM/min.\nThe distinct corrected-scale residual variance was 0.0625 min^-2.\nSynthetic assumption: complete known covariance and a normal corrected-effect observation model.\n'
COMPONENTS = ['attributed_rate', 'condition_response', 'corrected_activity', 'effect_variance', 'source_presence_index']
FORM = obj({'measurements': assay_cells_schema()})

def location_only(value):
    """The model's input form: a source location without the quotation the host reads."""
    if isinstance(value, list):
        return [location_only(item) for item in value]
    if isinstance(value, dict):
        located = 'start' in value and 'end' in value
        return {key: location_only(item) for key, item in value.items() if not (located and key == 'quote')}
    return value


def setup_store(path, *, full=True):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')

    def source(text, provider):
        artifact = store.artifact(text, 'text/plain')
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    main = source(TEXT, 'synthetic_assay_fixture')

    def witness(quote):
        start = len(TEXT[:TEXT.index(quote)].encode('utf-8'))
        return {'source_ref': main, 'representation': 'original', 'start': start, 'end': start + len(quote.encode('utf-8')), 'quote': quote}

    def measurement(line, number, unit):
        quote = next((row for row in TEXT.splitlines() if row.startswith(line)))
        nstart, ustart = (quote.index(number), quote.index(unit) if unit else len(quote))
        return {'witness': witness(quote), 'number_start': nstart, 'number_end': nstart + len(number), 'unit_start': ustart, 'unit_end': ustart + len(unit)}
    args = {'source_ref': main, 'source_kind': 'synthetic_fixture', 'assay': {'molecule': witness('Protein P'), 'organism': witness('organism X'), 'genotype': None, 'construct': witness('construct P-His'), 'preparation': witness('purified preparation'), 'condition': witness('30 C and pH 7'), 'intended_variable': None, 'experimental_system': None, 'expression_host': None, 'measured_entity': witness('product B'), 'asserted_input': witness('substrate A'), 'asserted_output': witness('product B'), 'endpoint': {'value': 'product_formation', 'witnesses': [witness('identified product B formation')]}, 'arrangement': {'value': 'single_preparation', 'witnesses': [witness('One preparation')]}}, 'primitives': {'q': measurement('The reported net', '1.00', 'µM/min'), 'g': measurement('A separately measured', '0.15', 'uM/min'), 'k': measurement('The quantitative calibration', '1.00', 'fraction'), 'E': measurement('The assayed molecule', '1000', 'nM'), 'u': measurement('The same-endpoint condition-control test', '2.00', 'uM/min'), 'v': measurement('The same-endpoint condition-control reference', '1.60', 'uM/min')}, 'covariance_source_ref': None, 'distinct_residual_variance': measurement('The distinct corrected', '0.0625', 'min^-2') if full else None, 'variance_status': 'known' if full else 'unknown', 'observation_model': 'known_normal_nonnegative_presence' if full else 'none', 'model_witnesses': [witness('Synthetic assumption: complete known covariance and a normal corrected-effect observation model.')] if full else []}
    references = [main]
    if full:

        def read(ref, representation):
            row = store.get(ref)
            artifact = row['artifact_ref'] if representation == 'original' else row['text_ref']
            return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
        parsed = read_assay_inputs(args, read_source=read)
        observations = parsed['primitive_observations']
        order = ['q', 'g', 'k', 'E', 'u', 'v']
        diagonal = [0.04, 0.0225, 0.0025, 10000, 0.01, 0.01]
        covariance = {'version': 'a105_primitive_covariance_v1', 'primitive_order': order, 'primitive_measurement_keys': [observations[key]['measurement_key'] for key in order], 'primitive_units': [observations[key]['raw_unit'] for key in order], 'covariance': [[diagonal[i] if i == j else 0.0 for j in range(6)] for i in range(6)], 'origin': 'synthetic'}
        cov = source(canonical(covariance), 'synthetic_assay_covariance')
        args['covariance_source_ref'] = cov
        references.append(cov)
    else:
        args['primitives']['g'] = None
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': references, 'requested_assay_components': COMPONENTS}
    context = BindingContext('assay-run', 'assay-child', 'literature', (('literature', 'case'),), store.validate_scope(), assignment, {}, references)
    return (store, context, args)

def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding

@pytest.mark.parametrize('full', [False, True])
def test_source_assay_cells_validate_exact_semantics_and_replay_without_parsing(tmp_path, monkeypatch, full):
    store, context, args = setup_store(tmp_path, full=full)
    binding = binding_for(store, context)
    outcome = asyncio.run(binding.execute(context, 'literature.assay.populate', location_only(args), 'selected'))
    assert outcome['status'] == 'completed', outcome
    ref = outcome['result']['sheet_ref']
    current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    facts = binding.facts(current, {'committed_record_refs': [ref]})
    form = form_with_facts({}, FORM, facts)
    binding.validate_report(current, form, FORM)
    cells = form['measurements']
    byname = {row['component']: row for row in cells}
    assert byname['condition_response']['value'] == 1.25
    assert all((row['interpretation_kind'] == 'episode_source_interpretation' for row in cells))
    assert all((row['endpoint_kind'] == 'product_formation' for row in cells))
    assert all((row['arrangement_kind'] == 'single_preparation' for row in cells))
    assert all((row['operand_source_kind'] == 'synthetic_fixture' for row in cells))
    assert all((row['covariance_origin'] == ('synthetic' if full else None) for row in cells))
    assert store.get(cells[0]['assayed_subject_ref'])['label'] == 'Protein P'
    assert store.get(cells[0]['condition_ref'])['name'] == '30 C and pH 7'
    assert cells[0]['genotype_ref'] is None
    assert store.get(cells[0]['measured_entity_ref'])['label'] == 'product B'
    assert store.get(cells[0]['asserted_input_ref'])['label'] == 'substrate A'
    assert store.get(cells[0]['asserted_output_ref'])['label'] == 'product B'
    assert all((row['evaluated_scope'] == 'interpreted_source_endpoint' for row in cells))
    assert len(byname['condition_response']['input_measurement_refs']) == 2
    assert all((store.get(ref)['reference_type'] == 'literature_result' for ref in byname['condition_response']['input_measurement_refs']))
    second = binding.literature_assay_repository().populate(context, args, 'repeat-selected')
    repeated = binding.literature_assay_repository().project_cells([second['result']['sheet_ref']], permitted_record_refs=second['record_refs'], components=COMPONENTS)
    assert [row['input_measurement_refs'] for row in repeated] == [row['input_measurement_refs'] for row in cells]
    assert not set((ref for row in cells for ref in row['input_measurement_refs'])).intersection(second['changed_record_refs'])
    if full:
        assert byname['attributed_rate']['value'] == 0.85
        assert byname['corrected_activity']['value'] == pytest.approx(0.68)
        assert byname['effect_variance']['value'] == pytest.approx(0.11124225)
        assert byname['source_presence_index']['value'] == pytest.approx(0.777561486079)
    else:
        assert byname['attributed_rate']['value'] is None
        assert byname['corrected_activity']['unavailable_reason'] == 'correction_inputs_not_supplied'
        assert byname['source_presence_index']['value'] is None
    wrong = deepcopy(form)
    wrong['measurements'][0]['endpoint_kind'] = 'oxygen_consumption'
    with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
        binding.validate_report(current, wrong, FORM)
    wrong = deepcopy(form)
    wrong['measurements'][0]['value'] = 123
    with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
        binding.validate_report(current, wrong, FORM)
    parent = replace(current, role='annotation', episode_id='parent', path=(('annotation', 'root'),), assignment={})
    binding.received_form_references(parent, form, FORM, 'admitted')
    assert binding.received_report_facts(parent)['literature_assay_cells'] == cells
    assert len(binding.literature_assay_repository().read(ref)['sheet']['cells']) == 14
    store.close()

    def forbidden(*args, **kwargs):
        raise AssertionError('saved source graph replay must not parse/refit')
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs.read_assay_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a105.library.literature_activity_calculations.populate_corrected_activity', forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteratureAssayRepository(reopened, context.run_id)
        assert repo.populate(context, args, 'selected') == outcome
        assert repo.received_cells(parent) == cells
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=(args['source_ref'],) if full else ()), args, 'selected')

def test_scripted_source_assay_child_returns_score_with_no_extra_controller_observation(tmp_path):
    from .source_location_fixture import verified_source_locations
    store, context, args = setup_store(tmp_path / 'state')
    question_term = store.put('term', {'namespace': 'synthetic', 'accession': 'assay_product_B_question', 'label': 'Product B formation', 'term_type': 'reaction', 'source_ref': args['source_ref'], 'anchor': None}, origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': list(context.scope['subject_refs']), 'predicate': 'catalyzes', 'value': {'type': 'term_ref', 'ref': question_term}, 'context_refs': []}, origin='caller')['id']
    context = replace(context, assignment={**plain(context.assignment), 'proposed_annotation_ref': proposed, 'literature_task': {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [args['source_ref']], 'credit_unit': 1}}, received_record_refs=(*context.received_record_refs, question_term, proposed))
    commissioned_form = obj({**FORM['properties'], 'findings': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}, 'x-source': 'changed_assessment_refs'}})
    received, controllers = ([], [])
    try:
        child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(context.assignment), 'goal': 'Evaluate the selected synthetic assay and its source correction', 'scope': plain(context.scope), 'purpose': 'Return numerical assay components with endpoint and source context', 'schema_json': json.dumps(commissioned_form), 'initial_report_json': '{}'}, 'report_update': {}}
        work = {'selection': {'kind': 'tool', 'tool': 'literature.assay.populate', 'arguments': verified_source_locations(store, args)}, 'report_update': {}}

        def receives(inputs):
            form, = inputs['child_reports']
            received.append(form)
            assert [row['component'] for row in form['measurements']] == COMPONENTS
            assert form['measurements'][-1]['value'] == pytest.approx(0.777561486079)
            commit = {key: [] for key in store.reasoning_schema()['required']}
            row = store.get(args['source_ref'])
            start = TEXT.encode('utf-8').index(b'Protein P')
            commit['source_subjects'] = [{'alias': 'source_molecule', 'reference_type': 'assay', 'source_ref': args['source_ref'], 'label': 'Protein P', 'anchor': {'source_ref': args['source_ref'], 'artifact_ref': row['artifact_ref'], 'start': start, 'end': start + 9, 'quote': 'Protein P'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(result)
            return result
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]), run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=literature_binding_factories(rate_population=True), binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(received) == 1
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_assay_operations').fetchone()[0] == 1
        assert not store.list('observation') and (not store.list('assessment'))
    finally:
        store.close()

def test_copied_provider_label_does_not_manufacture_a_selected_assay_output(tmp_path):
    store, context, args = setup_store(tmp_path, full=False)
    try:
        repo = LiteratureAssayRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        row = store.get(outcome['result']['sheet_ref'])
        request = json.loads(store.get_artifact(row['request_ref']))
        request['operation_key'] = 'never-selected'
        false_request = store.artifact(canonical(request), 'application/json')
        fields = {name: row[name] for name in ('provider', 'accession', 'uri', 'artifact_ref', 'text_ref', 'version', 'retrieved_at', 'parent_source_refs')}
        fields['request_ref'] = false_request
        fake = store.put('source', fields, origin='tool', scope=plain(context.scope))
        with pytest.raises(ContractError, match='not_selected_output'):
            repo.read(fake['id'])
    finally:
        store.close()

@pytest.mark.parametrize('unknown', ['molecule', 'endpoint'])
def test_unidentified_observation_scope_preserves_arithmetic_without_claiming_source_score(tmp_path, unknown):
    store, context, args = setup_store(tmp_path)
    try:
        if unknown == 'molecule':
            args['assay']['molecule'] = None
        else:
            args['assay']['endpoint'] = {'value': 'unknown', 'witnesses': []}
        result = LiteratureAssayRepository(store, context.run_id).populate(context, args, 'partial-scope')
        assert result['status'] == 'completed'
        cells = result['result']['cells']
        assert cells['corrected_activity']['value'] == pytest.approx(0.68)
        assert cells['source_presence_index']['value'] is None
        assert cells['source_presence_index']['unavailable_reason'] == ('assayed_molecule_unresolved' if unknown == 'molecule' else 'source_endpoint_unresolved')
    finally:
        store.close()

@pytest.mark.parametrize('endpoint', ['growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'])
def test_concentration_rate_correction_does_not_score_a_different_endpoint_model(tmp_path, endpoint):
    store, context, args = setup_store(tmp_path)
    try:
        args['assay']['endpoint']['value'] = endpoint
        result = LiteratureAssayRepository(store, context.run_id).populate(context, args, 'different-model')
        cells = result['result']['cells']
        assert cells['net_rate']['value'] == 1
        assert cells['condition_response']['value'] == 1.25
        for name in ('corrected_activity', 'effect_variance', 'effect_standard_uncertainty', 'effect_precision', 'source_profile_log_ratio', 'source_presence_index'):
            assert cells[name]['value'] is None
            assert cells[name]['unavailable_reason'] == 'endpoint_requires_different_model'
    finally:
        store.close()
