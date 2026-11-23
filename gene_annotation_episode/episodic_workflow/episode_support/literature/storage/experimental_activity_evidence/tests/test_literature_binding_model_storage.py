"""Synthetic custody, saved replay and exact numerical parent-form tests.

No primary paper packets or model-backed literature interpretation are used.
"""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
import math
from PIL import Image
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_binding_model_storage import COMPONENTS, FORMULA_CODES, FORMULA_MEANINGS, PROVIDER, LiteratureBindingModelRepository, binding_model_cells_schema, binding_model_population_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_binding_models import binding_model_operand_keys
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_binding_storage import LiteratureBindingRepository
from .unit_world import held, in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_binding_model_storage import OPERATIONS

def source(store, content, *, parents=(), text=None, provider='synthetic_binding_model_fixture'):
    artifact = store.artifact(content, 'application/octet-stream')
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': text, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def fixture(store, ctx, *, model=True, variance='known', censoring='none', expressions=('10', '20'), visual=False, page=False):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    root = source(store, 'Synthetic source methods.')
    raw_parents = [root['id']]
    raw_inputs = [root['id']]
    rows = [{'subject': 'SyntheticProtein', 'state': 'apo', 'experiment': 'synthetic-binding', 'ligand': ligand, 'expression': expression, 'locator': {'row_index': index, 'column': 'IC50'}} for index, (ligand, expression) in enumerate(zip(('reference', 'test'), expressions))]
    if visual:
        buffer = BytesIO()
        Image.new('RGB', (20, 10), (221, 222, 223)).save(buffer, format='PNG')
        image = source(store, buffer.getvalue(), parents=[root['id']])
        raw_inputs.append(image['id'])
        raw_parents.append(image['id'])
        for index, row in enumerate(rows):
            row['locator'] = {'original_source_ref': image['id'], 'original_artifact_ref': image['artifact_ref'], 'image_region': [5 * index, 0, 5 * index + 5, 5]}
    table = {'version': 'binding_parameter_table', 'table_id': 'SyntheticTable', 'parameter_kind': 'ic50', 'unit': 'nM', 'uncertainty_basis': 'fit_to_averaged_curve', 'minimum_experiment_count': 2, 'rows': rows}
    original = source(store, canonical(table), parents=raw_parents)
    native_context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature_table', (('literature_table', 'fixture'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {}, {}, (original['id'], *raw_inputs))
    native_args = {'source_ref': original['id'], 'representation': 'retained_visual_transcription' if visual else 'synthetic_fixture', 'subject': 'SyntheticProtein', 'state': 'apo', 'experiment': 'synthetic-binding', 'reference_ligand': 'reference', 'test_ligand': 'test', 'parameter_kind': 'ic50', 'design': 'unknown', 'protein_arrangement': 'unknown', 'interpretation_witnesses': []}
    native_repo = LiteratureBindingRepository(store, native_context.run_id)
    native_outcome = native_repo.populate(native_context, native_args, 'native')
    binding_ref = native_outcome['result']['sheet_ref']
    binding = native_repo.read(binding_ref)
    args = {'source_ref': binding_ref, 'model_source_ref': None, 'model_witnesses': []}
    received = [binding_ref]
    records = {'root': root, 'original': original, 'native': binding, 'native_outcome': native_outcome}
    if model:
        parent = source(store, 'Synthetic covariance declaration.', parents=[root['id']])
        witness_source = source(store, 'Known joint natural-log covariance for the selected estimates.', parents=[root['id']])
        keys = binding_model_operand_keys(binding['sheet'])
        declaration = {'version': 'known_normal_log_binding', 'parameter_kind': 'ic50', 'measurement_order': ['reference', 'test'], 'measurement_keys': [keys['reference'], keys['test']], 'log_covariance': [[0.04, 0.01], [0.01, 0.09]], 'variance_status': variance, 'censoring_model': censoring, 'log_basis': 'natural_log_nM', 'origin': 'synthetic'}
        model_source = source(store, canonical(declaration), parents=[parent['id']])
        quote = 'Known joint natural-log covariance for the selected estimates.'
        witness = {'source_ref': witness_source['id'], 'representation': 'original', 'start': 0, 'end': len(quote.encode()), 'quote': quote}
        args.update(model_source_ref=model_source['id'], model_witnesses=[witness])
        received.extend([model_source['id'], parent['id'], witness_source['id']])
        records.update(model_source=model_source, parent=parent, witness_source=witness_source, declaration=declaration)
    context = replace(native_context, received_record_refs=tuple(received), assignment={'page': {'source_ref': root['id']}} if page else {})
    return (store, context, args, records)

def new_model(store, context, args, declaration, *, parents=None, text=None):
    original = store.get(args['model_source_ref'])
    selected = source(store, canonical(declaration), parents=original['parent_source_refs'] if parents is None else parents, text=text)
    return (replace(context, received_record_refs=(*context.received_record_refs, selected['id'])), {**args, 'model_source_ref': selected['id']})


@in_unit
def test_missing_model_preserves_native_partial_cells_and_original_limit(store, ctx):
    store, context, args, _ = fixture(store, ctx, model=False, expressions=('10', '>20'))
    repo = LiteratureBindingModelRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'no-model')
    cells = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    assert cells[0]['value'] == pytest.approx(math.log(2))
    assert cells[0]['relation'] == 'gt' and cells[0]['status'] == 'reported_limit'
    assert cells[0]['bound_kind'] == 'reported_limit_arithmetic'
    assert all((row['value'] is None and row['unavailable_reason'] == 'binding_sampling_model_not_supplied' for row in cells[1:]))
    assert all((row['model_kind'] == 'not_supplied' and row['variance_status'] == 'not_supplied' for row in cells))
    assert all((row['model_source_ref'] is None for row in cells))
    validate_schema(cells, binding_model_cells_schema())
    saved = repo.read(outcome['result']['sheet_ref'])
    assert saved['model_source_provenance'] is None and saved['sheet']['model'] is None

@pytest.mark.parametrize('variance,censoring,expressions,reason,conditions', [('estimated', 'none', ('10', '20'), 'known_log_covariance_required', ['supplied_log_covariance']), ('unknown', 'none', ('10', '20'), 'covariance_status_unknown', []), ('known', 'unknown', ('10', '>20'), 'binding_censoring_mechanism_unreported', ['supplied_log_covariance']), ('known', 'threshold_of_log_estimate', ('10', '>20'), None, ['supplied_log_covariance', 'known_normal_log_parameters', 'threshold_censoring_of_log_estimate']), ('known', 'threshold_of_log_estimate', ('<10', '>20'), 'two_censored_observations_unsupported', ['supplied_log_covariance'])])
@in_unit
def test_conditioned_model_meanings_survive_projection(store, ctx, variance, censoring, expressions, reason, conditions):
    store, context, args, _ = fixture(store, ctx, variance=variance, censoring=censoring, expressions=expressions)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    row = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=('source_profile_log_ratio',))[0]
    assert row['unavailable_reason'] == reason and row['conditional_on'] == conditions
    assert row['variance_status'] == variance and row['censoring_model'] == censoring
    if reason is None:
        assert row['relation'] == 'eq' and row['status'] == 'populated'
        assert row['bound_kind'] is None and row['value'] > 0

@pytest.mark.parametrize('part', ['binding', 'model', 'witness', 'parent'])
@in_unit
def test_every_actual_direct_source_must_be_received_before_any_publication(store, ctx, part):
    store, context, args, records = fixture(store, ctx)
    denied = {'binding': args['source_ref'], 'model': args['model_source_ref'], 'witness': records['witness_source']['id'], 'parent': records['parent']['id']}[part]
    context = replace(context, received_record_refs=tuple((ref for ref in context.received_record_refs if ref != denied)))
    before = held(store, 'source')
    repo = LiteratureBindingModelRepository(store, context.run_id)
    with pytest.raises(ContractError, match='not_received'):
        repo.populate(context, args, 'invalid')
    assert held(store, 'source') == before
    assert len(store.table(OPERATIONS).select()) == 0
    assert not held(store, 'observation')

@in_unit
def test_page_lineage_accepts_direct_descendants_without_raw_receipt(store, ctx):
    store, context, args, records = fixture(store, ctx, page=True, visual=True)
    outcome = LiteratureBindingModelRepository(store, context.run_id).populate(context, args, 'descendants')
    assert outcome['status'] == 'completed'
    assert records['root']['id'] not in context.received_record_refs

@pytest.mark.parametrize('part', ['model', 'witness', 'parent'])
@in_unit
def test_page_lineage_rejects_foreign_direct_source_even_if_received(store, ctx, part):
    store, context, args, records = fixture(store, ctx, page=True)
    foreign = source(store, 'Foreign scope source.')
    context = replace(context, received_record_refs=(*context.received_record_refs, foreign['id']))
    if part == 'model':
        args['model_source_ref'] = foreign['id']
    elif part == 'witness':
        args['model_witnesses'] = [{'source_ref': foreign['id'], 'representation': 'original', 'start': 0, 'end': 7, 'quote': 'Foreign'}]
    else:
        context, args = new_model(store, context, args, records['declaration'], parents=[records['parent']['id'], foreign['id']])
    with pytest.raises(ContractError, match='outside_assigned_source'):
        LiteratureBindingModelRepository(store, context.run_id).populate(context, args, 'foreign')

@pytest.mark.parametrize('problem,expected', [('no_witness', 'witness_required'), ('wrong_quote', 'source_quote_mismatch'), ('bad_owner', 'measurement_owner_mismatch'), ('bad_covariance', 'positive_definite'), ('wrong_kind', 'parameter_kind_mismatch')])
@in_unit
def test_supplied_source_model_and_witnesses_are_validated_without_fallback(store, ctx, problem, expected):
    store, context, args, records = fixture(store, ctx)
    if problem == 'no_witness':
        args['model_witnesses'] = []
    elif problem == 'wrong_quote':
        args['model_witnesses'][0]['quote'] = 'Invented model interpretation.'
    else:
        declaration = deepcopy(records['declaration'])
        if problem == 'bad_owner':
            declaration['measurement_keys'].reverse()
        elif problem == 'bad_covariance':
            declaration['log_covariance'] = [[1, 1], [1, 1]]
        else:
            declaration['parameter_kind'] = 'reported_hill_kd'
        context, args = new_model(store, context, args, declaration)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    with pytest.raises((ContractError, ValueError), match=expected):
        repo.populate(context, args, 'invalid')
    assert len(store.table(OPERATIONS).select()) == 0

@in_unit
def test_original_model_bytes_used_instead_of_text_derivative(store, ctx):
    store, context, args, records = fixture(store, ctx)
    bad = source(store, b'\xff', parents=[records['parent']['id']], text=records['model_source']['artifact_ref'])
    context = replace(context, received_record_refs=(*context.received_record_refs, bad['id']))
    with pytest.raises(ValueError, match='malformed_binding_model_source'):
        LiteratureBindingModelRepository(store, context.run_id).populate(context, {**args, 'model_source_ref': bad['id']}, 'invalid')

@in_unit
def test_forged_provider_and_nonselected_binding_sheet_rejected(store, ctx):
    store, context, args, records = fixture(store, ctx)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    native_record = store.get(args['source_ref'])
    fields = {name: value for name, value in native_record.items() if name not in ('id', 'record_type', 'origin')}
    fields['accession'] = 'forged-binding-output'
    forged = store.put('source', fields, origin='tool')
    context = replace(context, received_record_refs=(*context.received_record_refs, forged['id']))
    with pytest.raises(ContractError, match='not_selected_output'):
        repo.populate(context, {**args, 'source_ref': forged['id']}, 'forged')
    with pytest.raises(ContractError, match='run_mismatch'):
        LiteratureBindingModelRepository(store, 'other-run').populate(replace(context, run_id='other-run'), args, 'wrong-run-native')
    outcome = repo.populate(context, args, 'selected')
    record = store.get(outcome['result']['sheet_ref'])
    fields = {name: value for name, value in record.items() if name not in ('id', 'record_type', 'origin')}
    fields['accession'] = 'forged-model-output'
    forged_model = store.put('source', fields, origin='tool')
    with pytest.raises(ContractError, match='not_selected_output'):
        repo.read(forged_model['id'])

@pytest.mark.parametrize('changed,value', [('value', 100), ('relation', 'gt'), ('bound_kind', 'reported_limit_arithmetic'), ('conditional_on', []), ('formula_code', FORMULA_CODES['log_parameter_contrast']), ('parameter_kind', 'reported_hill_kd'), ('model_kind', 'unreported'), ('variance_status', 'estimated'), ('censoring_model', 'unknown'), ('model_origin', 'reported'), ('contrast_meaning', 'activity_probability'), ('independent_preparation_count', 2)])
@in_unit
def test_saved_cell_authority_rejects_modified_meaning(store, ctx, changed, value):
    store, context, args, _ = fixture(store, ctx)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    cells = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=('source_profile_log_ratio',))
    cells[0][changed] = value
    with pytest.raises(ContractError, match='differs_from_saved'):
        repo.validate_returned_values(cells, permitted_record_refs=outcome['record_refs'])


@pytest.mark.parametrize('selection', [('not_a_component',), ('log_parameter_contrast',) * 2, 'source_signed_index', [[1]]])
@in_unit
def test_invalid_component_selections_are_rejected(store, ctx, selection):
    store, context, args, _ = fixture(store, ctx, model=False)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    with pytest.raises(ContractError, match='component_selection_invalid'):
        repo.project_cells([], permitted_record_refs=(), components=selection)

