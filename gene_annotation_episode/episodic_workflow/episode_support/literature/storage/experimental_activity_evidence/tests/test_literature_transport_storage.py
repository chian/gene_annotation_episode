"""Synthetic selected-operation custody, persistence and typed subset checks.

No primary paper, network request or model-backed scientific interpretation.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import LiteratureQuantityRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_transport_inputs import read_transport_inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_transport_storage import COMPONENTS, FORMULA_CODES, PROVIDER, LiteratureTransportRepository, transport_response_cells_schema, transport_response_population_schema
from .unit_world import held, in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_transport_storage import OPERATIONS

def source(store, content, *, parents=(), provider='synthetic_transport_fixture', alias=False):
    artifact = store.artifact(content, 'application/octet-stream')
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact if alias else None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def witness(row, text):
    return {'source_ref': row['id'], 'representation': 'original', 'start': 0, 'end': len(text.encode('utf-8')), 'quote': text}

def measurement(row, text):
    number, unit = text.split()
    return {'witness': witness(row, text), 'number_start': 0, 'number_end': len(number), 'unit_start': len(number) + 1, 'unit_end': len(text)}

def fixture(store, ctx, *, km=True, covariance=False, page=False):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    root_text = 'Synthetic common kinetic curve.'
    root = source(store, root_text, alias=True)
    primitive = source(store, '10 uM; 40 uM', parents=[root['id']])
    model_text = 'Conditional Michaelis-Menten response model.'
    model = source(store, model_text, parents=[root['id']])
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'fixture'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'page': {'source_ref': root['id']}} if page else {}, {}, (root['id'], primitive['id'], model['id']))
    st = measurement(primitive, '10 uM')
    sr = measurement(primitive, '40 uM')
    sr['witness'].update(start=7, end=12)
    curve = {name: None for name in ('molecule', 'analyte', 'preparation', 'experimental_system', 'endpoint')}
    curve['curve'] = witness(root, root_text)
    args = {'source_ref': root['id'], 'source_kind': 'synthetic_fixture', 'primitives': {'substrate_test': st, 'substrate_reference': sr}, 'km_sheet_ref': None, 'curve_contexts': {name: deepcopy(curve) for name in ('substrate_test', 'substrate_reference', 'km')}, 'covariance_source_ref': None, 'variance_status': 'unknown', 'observation_model': 'michaelis_menten', 'model_witnesses': [witness(model, model_text)]}
    records = {'root': root, 'primitive': primitive, 'model': model}
    if km:
        xml = '<article><body><sec id="s"><p id="p">SyntheticProtein has apparent Km = 16.5 ± 6.4 uM for pyruvate.</p></sec></body></article>'
        original = source(store, xml, parents=[root['id']])
        quantity_context = replace(context, assignment={}, received_record_refs=(original['id'],))
        quantity_args = {'source_ref': original['id'], 'source_kind': 'synthetic_fixture', 'section_id': 's', 'paragraph_id': 'p', 'subject': 'SyntheticProtein', 'quantity': 'apparent_km', 'analyte': 'pyruvate'}
        repo = LiteratureQuantityRepository(store, context.run_id)
        outcome = repo.populate(quantity_context, quantity_args, 'native-km')
        args['km_sheet_ref'] = outcome['result']['sheet_ref']
        context = replace(context, received_record_refs=(*context.received_record_refs, args['km_sheet_ref']))
        records.update(original=original, quantity=repo.read(args['km_sheet_ref']), quantity_context=quantity_context, quantity_args=quantity_args)
    if covariance:
        repo = LiteratureTransportRepository(store, context.run_id)

        def read_source(ref, representation):
            row = store.get(ref)
            return {'artifact_ref': row['artifact_ref'], 'content': store.get_artifact(row['artifact_ref'])}

        def read_quantity(ref):
            extracted = records['quantity']['sheet']['extraction']
            anchor = {name: extracted['source'][name] for name in ('source_ref', 'artifact_ref', 'section_id', 'paragraph_id', 'expression_start', 'expression_end')}
            anchor.update(quantity=extracted['quantity'], analyte=extracted['analyte'])
            key = 'transport_quantity_' + hashlib.sha256(json.dumps(anchor, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            return {'sheet_ref': ref, 'input_source_ref': extracted['source']['source_ref'], 'value': extracted['value'], 'unit': 'uM', 'origin': 'synthetic', 'reported_uncertainty_kind': 'unspecified', 'measurement_key': key, **{field: records['quantity']['experimental_bindings'][field] for field in ('reported_subject_ref', 'analyte_ref')}}
        extraction = read_transport_inputs(args, read_source=read_source, read_quantity=read_quantity)
        declaration = {'version': 'a105_transport_covariance', 'primitive_order': ['substrate_test', 'substrate_reference', 'km'], 'primitive_measurement_keys': [extraction['measurement_keys'][name] for name in ('substrate_test', 'substrate_reference', 'km')], 'primitive_units': ['uM'] * 3, 'covariance': [[1, 0.1, 0], [0.1, 4, 0], [0, 0, 0.25]], 'origin': 'synthetic'}
        cov = source(store, canonical(declaration), parents=[root['id']])
        args.update(covariance_source_ref=cov['id'], variance_status='known')
        context = replace(context, received_record_refs=(*context.received_record_refs, cov['id']))
        records.update(covariance=cov, declaration=declaration)
    return (store, context, args, records)


@pytest.mark.parametrize('part', ['root', 'primitive', 'model', 'quantity', 'covariance'])
@in_unit
def test_direct_sources_require_receipt_without_partial_publication(store, ctx, part):
    store, context, args, records = fixture(store, ctx, covariance=True)
    denied = args['km_sheet_ref'] if part == 'quantity' else records[part]['id']
    context = replace(context, received_record_refs=tuple((ref for ref in context.received_record_refs if ref != denied)))
    before = (held(store, 'source'), held(store, 'reference'))
    repo = LiteratureTransportRepository(store, context.run_id)
    with pytest.raises(ContractError, match='not_received'):
        repo.populate(context, args, 'invalid')
    assert (held(store, 'source'), held(store, 'reference')) == before
    assert len(store.table(OPERATIONS).select()) == 0

@pytest.mark.parametrize('part', ['root', 'primitive', 'model', 'quantity', 'covariance'])
@in_unit
def test_page_lineage_is_not_supplied_by_provider_label(store, ctx, part):
    store, context, args, records = fixture(store, ctx, covariance=True, page=True)
    original = args['km_sheet_ref'] if part == 'quantity' else records[part]['id']
    old = store.get(original)
    unrelated = source(store, store.get_artifact(old['artifact_ref']), provider=old['provider'])
    changed = deepcopy(args)
    if part == 'root':
        changed['source_ref'] = unrelated['id']
    elif part == 'quantity':
        changed['km_sheet_ref'] = unrelated['id']
    elif part == 'covariance':
        changed['covariance_source_ref'] = unrelated['id']
    elif part == 'model':
        changed['model_witnesses'][0]['source_ref'] = unrelated['id']
    else:
        changed['primitives']['substrate_test']['witness']['source_ref'] = unrelated['id']
    context = replace(context, received_record_refs=(*context.received_record_refs, unrelated['id']))
    with pytest.raises(ContractError, match='outside_assigned_source'):
        LiteratureTransportRepository(store, context.run_id).populate(context, changed, 'invalid')

@pytest.mark.parametrize('change,reason', [('no_km', 'concentration_inputs_not_supplied'), ('no_context', 'kinetic_curve_identity_not_supplied'), ('different_curve', 'different_kinetic_curves'), ('unknown_model', 'observation_model_unspecified')])
@in_unit
def test_scientific_partial_inputs_are_completed_with_precise_reasons(store, ctx, change, reason):
    store, context, args, _ = fixture(store, ctx, km=change != 'no_km')
    if change == 'no_context':
        args['curve_contexts']['substrate_test'] = None
    elif change == 'different_curve':
        args['curve_contexts']['substrate_test']['endpoint'] = deepcopy(args['model_witnesses'][0])
    elif change == 'unknown_model':
        args['observation_model'] = 'unknown'
        args['model_witnesses'] = []
    repo = LiteratureTransportRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'partial')
    assert outcome['status'] == 'completed'
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    assert rows[5]['value'] is None and rows[5]['unavailable_reason'] == reason
    assert rows[0]['value'] == 10 and rows[1]['value'] == 40
    if change in ('no_context', 'different_curve'):
        assert rows[4]['value'] == pytest.approx(40 / 56.5)
    if change == 'no_km':
        assert rows[2]['unavailable_reason'] == 'concentration_not_supplied'
        assert rows[2]['reported_km_uncertainty_kind'] == 'not_supplied'
        assert rows[0]['reported_subject_ref'] is None and rows[0]['analyte_ref'] is None

@in_unit
def test_missing_covariance_never_inferred_from_untyped_km_spread(store, ctx):
    store, context, args, _ = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    assert rows[5]['value'] == pytest.approx(113 / 212)
    assert rows[7]['value'] is None and rows[7]['unavailable_reason'] == 'primitive_covariance_not_supplied'
    assert rows[8]['value'] is None and rows[8]['reported_km_uncertainty_kind'] == 'unspecified'

@in_unit
def test_only_received_selected_quantity_output_is_authoritative(store, ctx):
    store, context, args, records = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    actual = store.get(args['km_sheet_ref'])
    forged_record = {key: value for key, value in actual.items() if key not in ('id', 'record_type', 'origin')}
    forged = store.put('source', forged_record, origin='caller')
    context = replace(context, received_record_refs=(*context.received_record_refs, forged['id']))
    with pytest.raises(ContractError, match='sheet_required'):
        repo.populate(context, {**args, 'km_sheet_ref': forged['id']}, 'forged')
    wrong_args = {**records['quantity_args'], 'quantity': 'specific_activity', 'analyte': None}
    raw = source(store, '<article><body><sec id="s"><p id="p">SyntheticProtein has specific activity of 12 ± 2 umol/min/mg.</p></sec></body></article>')
    qcontext = replace(records['quantity_context'], received_record_refs=(raw['id'],))
    quantity = LiteratureQuantityRepository(store, context.run_id).populate(qcontext, {**wrong_args, 'source_ref': raw['id']}, 'wrong-quantity')
    wrong_ref = quantity['result']['sheet_ref']
    context = replace(context, received_record_refs=(*context.received_record_refs, wrong_ref))
    with pytest.raises(ContractError, match='apparent_km_required'):
        repo.populate(context, {**args, 'km_sheet_ref': wrong_ref}, 'wrong-quantity')
    other = LiteratureTransportRepository(store, 'different-run')
    with pytest.raises(ContractError, match='sheet_run_mismatch'):
        other.populate(replace(context, run_id='different-run'), args, 'cross-run')

@pytest.mark.parametrize('mutation,reason', [(lambda value: value.update(primitive_measurement_keys=['wrong'] * 3), 'measurement_owner_mismatch'), (lambda value: value.update(primitive_order=['km', 'substrate_reference', 'substrate_test']), 'primitive_order_mismatch'), (lambda value: value.update(primitive_units=['nM'] * 3), 'primitive_unit_mismatch'), (lambda value: value.update(covariance=[[1, 2, 0], [2, 1, 0], [0, 0, 1]]), 'positive_semidefinite'), (lambda value: value.update(covariance=[[1, 1, 0], [0, 1, 0], [0, 0, 1]]), 'symmetric_covariance')])
@in_unit
def test_invalid_covariance_cannot_half_publish_output(store, ctx, mutation, reason):
    store, context, args, records = fixture(store, ctx, covariance=True)
    declaration = deepcopy(records['declaration'])
    mutation(declaration)
    changed = source(store, canonical(declaration), parents=[records['root']['id']])
    args['covariance_source_ref'] = changed['id']
    context = replace(context, received_record_refs=(*context.received_record_refs, changed['id']))
    before = (held(store, 'source'), held(store, 'reference'))
    with pytest.raises(ValueError, match=reason):
        LiteratureTransportRepository(store, context.run_id).populate(context, args, 'invalid')
    assert (held(store, 'source'), held(store, 'reference')) == before

@in_unit
def test_operation_identity_request_schema_and_new_record_accounting(store, ctx):
    store, context, args, _ = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    first = repo.populate(context, args, 'first')
    second = repo.populate(context, args, 'second')
    assert second['changed_record_refs'] == [second['result']['sheet_ref']]
    with pytest.raises(ContractError, match='reused_for_different_work'):
        repo.populate(context, {**args, 'observation_model': 'unknown'}, 'first')
    with pytest.raises(ContractError, match='run_mismatch'):
        repo.populate(replace(context, run_id='other'), args, 'new')
    with pytest.raises(ContractError, match='operation_key_required'):
        repo.populate(context, args, '')
    with pytest.raises(ContractError, match='representation_error'):
        repo.populate(context, {**args, 'km': 16.5}, 'illegal-numeric-input')
    assert first['result']['cells'] == second['result']['cells']

@pytest.mark.parametrize('field,value', [('value', 999), ('formula_code', 'transport_apparent_km'), ('reported_subject_ref', None), ('reported_km_uncertainty_kind', 'unreported'), ('variance_status', 'estimated'), ('conditional_on', []), ('test_curve_ref', None)])
@in_unit
def test_forged_typed_values_are_rejected(store, ctx, field, value):
    store, context, args, _ = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    ref = outcome['result']['sheet_ref']
    rows = repo.project_cells([ref], permitted_record_refs=outcome['record_refs'], components=('condition_response',))
    rows[0][field] = value
    with pytest.raises(ContractError, match='differs_from_saved'):
        repo.validate_returned_values(rows, permitted_record_refs=outcome['record_refs'])


@in_unit
def test_same_operand_anchors_and_representation_aliases_share_quantity_and_curve_identities(store, ctx):
    store, context, args, records = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    first = repo.populate(context, args, 'first')
    saved_first = repo.read(first['result']['sheet_ref'])
    quantity = LiteratureQuantityRepository(store, context.run_id).populate(records['quantity_context'], records['quantity_args'], 'same-native-operand')
    changed = deepcopy(args)
    changed['km_sheet_ref'] = quantity['result']['sheet_ref']
    for curve in changed['curve_contexts'].values():
        curve['curve']['representation'] = 'text'
    context = replace(context, received_record_refs=(*context.received_record_refs, changed['km_sheet_ref']))
    second = repo.populate(context, changed, 'same-anchors')
    saved_second = repo.read(second['result']['sheet_ref'])
    assert saved_first['extraction']['measurement_keys'] == saved_second['extraction']['measurement_keys']
    assert saved_first['experimental_bindings'] == saved_second['experimental_bindings']
    assert saved_first['extraction']['curve_keys'] == saved_second['extraction']['curve_keys']
    assert second['changed_record_refs'] == [second['result']['sheet_ref']]

@pytest.mark.parametrize('page', [False, True])
@in_unit
def test_received_standalone_covariance_is_allowed_outside_page_assignment(store, ctx, page):
    store, context, args, records = fixture(store, ctx, covariance=True, page=page)
    standalone = source(store, canonical(records['declaration']))
    context = replace(context, received_record_refs=(*context.received_record_refs, standalone['id']))
    args['covariance_source_ref'] = standalone['id']
    repo = LiteratureTransportRepository(store, context.run_id)
    if page:
        with pytest.raises(ContractError, match='outside_assigned_source'):
            repo.populate(context, args, 'standalone')
    else:
        outcome = repo.populate(context, args, 'standalone')
        assert outcome['result']['cells']['condition_response_variance']['value'] > 0
        assert standalone['id'] in repo.read(outcome['result']['sheet_ref'])['direct_input_source_refs']

@in_unit
def test_typed_schema_rejects_freehand_formulas_and_unbounded_reasons(store, ctx):
    store, context, args, _ = fixture(store, ctx)
    repo = LiteratureTransportRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=('condition_response',))
    for field, value in (('formula_code', 'St * (K + Sr) / (Sr * (K + St))'), ('unavailable_reason', 'arbitrary source prose'), ('conditional_on', ['unspecified new model']), ('origin', 'proposed'), ('formula', 'raw formula')):
        bad = deepcopy(rows)
        bad[0][field] = value
        with pytest.raises(ContractError, match='representation_error'):
            repo.validate_returned_values(bad, permitted_record_refs=outcome['record_refs'])

@in_unit
def test_copied_tool_source_without_selected_quantity_receipt_is_rejected(store, ctx):
    store, context, args, _ = fixture(store, ctx)
    actual = store.get(args['km_sheet_ref'])
    record = {key: value for key, value in actual.items() if key not in ('id', 'record_type', 'origin')}
    record['retrieved_at'] = 'synthetic-forgery'
    forged = store.put('source', record, origin='tool')
    context = replace(context, received_record_refs=(*context.received_record_refs, forged['id']))
    with pytest.raises(ContractError, match='not_selected_output'):
        LiteratureTransportRepository(store, context.run_id).populate(context, {**args, 'km_sheet_ref': forged['id']}, 'forged-selected')
