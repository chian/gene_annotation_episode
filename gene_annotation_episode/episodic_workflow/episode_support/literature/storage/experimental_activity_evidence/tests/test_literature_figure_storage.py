"""Synthetic native images exercise selected custody and saved-only receipts.

These pixel fixtures are not scientific measurements or an episode run.
"""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from PIL import Image
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_figure_storage import BINDINGS, COMPONENTS, FORMULA_CODES, LiteratureFigureRepository, PROVIDER, figure_cells_schema, figure_population_schema
from .unit_world import held, in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_figure_storage import OPERATIONS

def source(store, content, *, parents=(), text=False):
    artifact = store.artifact(content)
    return store.put('source', {'provider': 'synthetic_figure_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact if text else None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def image_bytes(rows):
    image = Image.new('RGB', (12, 12), 'white')
    for y in rows:
        for x in range(2, 10):
            image.putpixel((x, y), (20, 80, 160))
    output = BytesIO()
    image.save(output, format='PNG')
    image.close()
    return output.getvalue()

def selection(unit='relative_turnover_percent'):
    return {'roi': {'left': 2, 'top': 0, 'right': 10, 'bottom': 10}, 'rgb_min': [20, 80, 160], 'rgb_max': [20, 80, 160], 'minimum_row_fraction': 1, 'minimum_run_rows': 2, 'edge_tolerance_pixels': 0, 'calibration': {'first': {'pixel': 0, 'value': 100}, 'second': {'pixel': 10, 'value': 0}, 'unit': unit}}

def fixture(store, ctx, *, page=False, second=True, rows=range(3, 7), unit='relative_turnover_percent'):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    records = {}
    records['ancestor'] = source(store, 'Synthetic source provenance.')
    records['root'] = source(store, b'\xff\x00Synthetic paper bytes.', parents=[records['ancestor']['id']])
    root = records['root']['id']
    records['firstimage'] = source(store, image_bytes(rows), parents=[root])
    records['secondimage'] = source(store, image_bytes(range(5, 9)), parents=[root])
    text = 'Subject A|Partner A|Subject B|Partner B|Experiment|Endpoint|Condition A|Condition B|Normalization|Function'
    records['literal'] = source(store, text, parents=[root], text=True)
    records['interpretation'] = source(store, 'Supplied synthetic experimental design.', parents=[root])
    repeat = {'reported_n': 3, 'repeat_kind': 'technical', 'independent_preparation_count': None, 'spread_kind': 'SD', 'spread_numeric_status': 'not_extracted'}
    document = {'version': 'literature_figure_selection', 'first': {'image_source_ref': records['firstimage']['id'], 'image_origin': 'synthetic', 'axis_scale': 'linear', 'selection': selection()}, 'second': {'image_source_ref': records['secondimage']['id'], 'image_origin': 'synthetic', 'axis_scale': 'linear', 'selection': selection(unit)} if second else None, 'design': {'arrangement': 'coexisting_sequential_catalysts', 'contrast_kind': 'partner_swap', 'endpoint_scope': 'coupled_final_product', 'normalization_basis': 'reported_relative_turnover', 'measurement_relation': 'distinct_physical_measurements', 'first_repeat': repeat, 'second_repeat': deepcopy(repeat) if second else None}}
    records['recipe'] = source(store, json.dumps(document), parents=[root])
    literals, offset = ({}, 0)
    for field, quote in zip((literal for literal, _ in BINDINGS.values()), text.split('|')):
        literals[field] = {'source_ref': records['literal']['id'], 'representation': 'text', 'start': offset, 'end': offset + len(quote), 'quote': quote}
        offset += len(quote) + 1
    quote = 'Supplied synthetic experimental design.'
    args = {'source_ref': root, 'data_source_ref': records['recipe']['id'], 'source_kind': 'synthetic_fixture', 'literals': literals, 'interpretation_witnesses': [{'source_ref': records['interpretation']['id'], 'representation': 'original', 'start': 0, 'end': len(quote), 'quote': quote}]}
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'fixture'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'page': {'source_ref': root}} if page else {}, {}, tuple((row['id'] for key, row in records.items() if key != 'ancestor')))
    return (store, context, args, records, document)

def retain_recipe(store, context, args, records, document):
    row = source(store, json.dumps(document), parents=[records['root']['id']])
    args['data_source_ref'] = row['id']
    records['recipe'] = row
    return replace(context, received_record_refs=(*context.received_record_refs, row['id']))


@pytest.mark.parametrize('rows,reason', [((), 'no_bar_pixels'), ((0, 1, 2), 'truncated_mean_edge'), ((1, 2, 5, 6), 'ambiguous_bar_runs')])
@in_unit
def test_partial_native_failures_retain_second_raw_measurement(store, ctx, rows, reason):
    store, context, args, _, _ = fixture(store, ctx, rows=rows)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'partial')
    cells = repo.read(outcome['result']['sheet_ref'])['sheet']['cells']
    assert cells['first_ordinate']['value'] is None
    assert cells['first_ordinate']['unavailable_reason'] == reason
    assert cells['second_ordinate']['value'] == 45
    assert cells['ordinate_difference']['unavailable_reason'] == 'missing_ordinate'

@pytest.mark.parametrize('second,unit,reason', [(False, 'relative_turnover_percent', 'second_ordinate_unreported'), (True, 'arbitrary_signal', 'ordinate_unit_mismatch')])
@in_unit
def test_missing_second_or_unit_mismatch_preserves_unknowns(store, ctx, second, unit, reason):
    store, context, args, _, _ = fixture(store, ctx, second=second, unit=unit)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'partial')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    assert rows[0]['value'] == 65
    assert rows[2]['value'] is rows[2]['unit'] is None
    assert rows[2]['unavailable_reason'] == reason
    assert rows[1]['value'] == (45 if second else None)
    assert rows[1]['second_image_origin'] == ('synthetic' if second else None)
    assert (rows[1]['design']['second_repeat'] is None) == (not second)

@pytest.mark.parametrize('part', ['root', 'recipe', 'firstimage', 'secondimage', 'literal', 'interpretation'])
@in_unit
def test_every_direct_source_requires_receipt_initial_and_replay(store, ctx, part):
    store, context, args, records, _ = fixture(store, ctx)
    repo = LiteratureFigureRepository(store, context.run_id)
    repo.populate(context, args, 'selected')
    denied = replace(context, received_record_refs=tuple((ref for ref in context.received_record_refs if ref != records[part]['id'])))
    for operation in ('new', 'selected'):
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(denied, args, operation)
    assert len(store.table(OPERATIONS).select()) == 1

@pytest.mark.parametrize('part', ['root', 'recipe', 'firstimage', 'secondimage', 'literal', 'interpretation'])
@in_unit
def test_all_direct_sources_including_recipe_images_need_page_lineage(store, ctx, part):
    store, context, args, records, document = fixture(store, ctx, page=True)
    foreign = source(store, store.get_artifact(records[part]['artifact_ref']))
    if part == 'literal':
        for witness in args['literals'].values():
            witness['source_ref'] = foreign['id']
    elif part == 'interpretation':
        args['interpretation_witnesses'][0]['source_ref'] = foreign['id']
    elif part in ('firstimage', 'secondimage'):
        document[part.removesuffix('image')]['image_source_ref'] = foreign['id']
        context = retain_recipe(store, context, args, records, document)
    else:
        args['source_ref' if part == 'root' else 'data_source_ref'] = foreign['id']
    context = replace(context, received_record_refs=(*context.received_record_refs, foreign['id']))
    repo = LiteratureFigureRepository(store, context.run_id)
    with pytest.raises(ContractError, match='outside_assigned_source'):
        repo.populate(context, args, 'invalid')
    assert not held(store, 'context') and (not held(store, 'reference'))

@in_unit
def test_transitive_provenance_order_dedup_and_receipt_independence(store, ctx):
    store, context, args, records, document = fixture(store, ctx, page=True)
    middle = source(store, 'Intermediate source.', parents=[records['root']['id']])
    image = source(store, store.get_artifact(records['firstimage']['artifact_ref']), parents=[middle['id']])
    document['first']['image_source_ref'] = image['id']
    document['second'] = deepcopy(document['first'])
    context = retain_recipe(store, context, args, records, document)
    context = replace(context, received_record_refs=(*context.received_record_refs, image['id']))
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    saved = repo.read(outcome['result']['sheet_ref'])
    assert saved['direct_input_source_refs'] == [records['root']['id'], records['recipe']['id'], image['id'], records['literal']['id'], records['interpretation']['id']]
    assert saved['input_source_refs'][-2:] == [records['ancestor']['id'], middle['id']]
    assert middle['id'] not in context.received_record_refs
    assert saved['sheet']['cells']['ordinate_difference']['value'] == 0

@in_unit
def test_native_range_failure_remains_a_saved_partial_sheet(store, ctx):
    store, context, args, records, document = fixture(store, ctx)
    document['first']['selection']['calibration']['first']['value'] = 10 ** 400
    context = retain_recipe(store, context, args, records, document)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'range')
    saved = repo.read(outcome['result']['sheet_ref'])
    assert saved['sheet']['cells']['first_ordinate']['unavailable_reason'] == 'numerical_model_range'
    assert saved['sheet']['cells']['second_ordinate']['value'] == 45
    assert saved['sheet']['cells']['ordinate_difference']['unavailable_reason'] == 'missing_ordinate'

@in_unit
def test_authority_operation_identity_and_immutable_idempotence(store, ctx):
    store, context, args, _, _ = fixture(store, ctx)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    reference = outcome['result']['sheet_ref']
    actual = store.get(reference)
    record = {key: value for key, value in actual.items() if key not in ('id', 'record_type', 'origin')}
    caller_copy = store.put('source', record, origin='caller')
    with pytest.raises(ContractError, match='sheet_required'):
        repo.read(caller_copy['id'])
    record['retrieved_at'] = '2026-01-01T00:00:00Z'
    copy = store.put('source', record, origin='tool')
    with pytest.raises(ContractError, match='not_selected_output'):
        repo.read(copy['id'])
    with pytest.raises(ContractError, match='sheet_run_mismatch'):
        LiteratureFigureRepository(store, 'different-run').read(reference)
    with pytest.raises(ContractError, match='reused_for_different_work'):
        repo.populate(context, {**args, 'source_kind': 'retained_extraction'}, 'selected')
    with pytest.raises(ContractError, match='run_mismatch'):
        repo.populate(replace(context, run_id='different-run'), args, 'new')
    with pytest.raises(ContractError, match='operation_key_required'):
        repo.populate(context, args, '')
    second = repo.populate(context, args, 'second')
    assert second['changed_record_refs'] == [second['result']['sheet_ref']]
    outcome['result']['cells']['first_ordinate']['value'] = 999
    assert repo.populate(context, args, 'selected')['result']['cells']['first_ordinate']['value'] == 65

@in_unit
def test_equal_spans_keep_ten_field_meanings_and_missing_fields_remain_null(store, ctx):
    store, context, args, _, _ = fixture(store, ctx)
    witness = args['literals']['first_subject']
    args['literals'] = {field: deepcopy(witness) for field in args['literals']}
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'equal')
    bindings = repo.read(outcome['result']['sheet_ref'])['experimental_bindings']
    assert len(set(bindings.values())) == 10
    for field in args['literals']:
        args['literals'][field] = None
    args['interpretation_witnesses'] = []
    empty = repo.populate(context, args, 'no-witnesses')
    saved = repo.read(empty['result']['sheet_ref'])
    assert all((ref is None for ref in saved['experimental_bindings'].values()))
    assert len(saved['direct_input_source_refs']) == 4


@pytest.mark.parametrize('field,value', [('value', 999), ('lower', 40), ('upper', 90), ('unit', 'nanomolar'), ('origin', 'derived'), ('formula_code', 'native_first_minus_second'), ('first_subject_ref', None), ('first_partner_ref', None), ('second_subject_ref', None), ('second_partner_ref', None), ('experiment_ref', None), ('endpoint_ref', None), ('first_condition_ref', None), ('second_condition_ref', None), ('normalization_ref', None), ('function_ref', None), ('second_image_source_ref', None), ('source_kind', 'retained_extraction'), ('first_image_origin', 'published'), ('second_image_origin', 'published'), ('first_axis_unit', 'nanomolar'), ('second_axis_unit', None)])
@in_unit
def test_forged_valid_numbers_bindings_and_scientific_meanings_rejected(store, ctx, field, value):
    store, context, args, _, _ = fixture(store, ctx)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=('first_ordinate',))
    assert rows[0][field] != value
    rows[0][field] = value
    with pytest.raises(ContractError, match='differs_from_saved'):
        repo.validate_returned_values(rows, permitted_record_refs=outcome['record_refs'])

@pytest.mark.parametrize('mutate', [lambda row: row.update(value=float('nan')), lambda row: row.update(lower=float('inf')), lambda row: row.update(bound_kind='95 percent confidence interval'), lambda row: row.update(partner_necessity='necessary'), lambda row: row.update(statistical_uncertainty='SD'), lambda row: row.update(explanation='arbitrary prose'), lambda row: row['design'].update(explanation='arbitrary prose'), lambda row: row['design']['first_repeat'].update(reported_n=True), lambda row: row['design']['first_repeat'].update(independent_preparation_count=0)])
@in_unit
def test_closed_rows_reject_prose_nonfinite_and_unsupported_meanings(store, ctx, mutate):
    store, context, args, _, _ = fixture(store, ctx)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    mutate(rows[0])
    with pytest.raises(ContractError, match='representation_error'):
        repo.validate_returned_values(rows, permitted_record_refs=outcome['record_refs'])

@in_unit
def test_syntactically_valid_forged_design_meaning_rejected(store, ctx):
    store, context, args, _, _ = fixture(store, ctx)
    repo = LiteratureFigureRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    rows[0]['design']['first_repeat']['repeat_kind'] = 'biological'
    with pytest.raises(ContractError, match='differs_from_saved'):
        repo.validate_returned_values(rows, permitted_record_refs=outcome['record_refs'])

@pytest.mark.parametrize('mode', ['unknown_axis', 'unsupported_unit', 'bad_witness', 'extra_argument', 'duplicate_json', 'nonfinite_json'])
@in_unit
def test_invalid_selected_input_cannot_publish_records(store, ctx, mode):
    store, context, args, records, document = fixture(store, ctx)
    if mode == 'unknown_axis':
        document['first']['axis_scale'] = 'unknown'
        context = retain_recipe(store, context, args, records, document)
    elif mode == 'unsupported_unit':
        document['first']['selection']['calibration']['unit'] = 'percent'
        context = retain_recipe(store, context, args, records, document)
    elif mode == 'bad_witness':
        args['literals']['first_subject']['quote'] = 'Different'
    elif mode == 'extra_argument':
        args['measurements'] = {'first': 100}
    else:
        raw = '{"version":1,"version":2}' if mode == 'duplicate_json' else '{"value":NaN}'
        row = source(store, raw, parents=[records['root']['id']])
        args['data_source_ref'] = row['id']
        context = replace(context, received_record_refs=(*context.received_record_refs, row['id']))
    repo = LiteratureFigureRepository(store, context.run_id)
    kinds = ('source', 'reference', 'term', 'context')
    before = [held(store, kind) for kind in kinds]
    with pytest.raises((ContractError, ValueError)):
        repo.populate(context, args, 'invalid')
    assert [held(store, kind) for kind in kinds] == before
    assert len(store.table(OPERATIONS).select()) == 0
