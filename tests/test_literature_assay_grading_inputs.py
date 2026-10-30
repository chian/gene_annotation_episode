"""Source binding and native-component admission for reusable assay grading."""
from copy import deepcopy
from hashlib import sha256

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assay_grading import ROLES, grade_assay
from gene_annotation_episode.literature_assay_grading_inputs import read_assay_grading_inputs

SOURCE = 'source_' + 'a' * 64
ASSERTION = 'hypothesis_' + 'b' * 64
SUPPORT = 'reference_' + 'c' * 64
RAW = b'Effect = 0.8 fraction.\nVariance = 0.04 fraction_squared.\nAssay conditions recorded.\n'


def fixture(raw=RAW, *, effect_unit='fraction', variance_unit='fraction_squared'):
    artifact = 'artifact_' + sha256(raw).hexdigest()
    def witness(token):
        start = raw.index(token.encode())
        return {'source_ref': SOURCE, 'representation': 'original', 'start': start,
                'end': start + len(token.encode()), 'quote': token}
    def literal(token, unit, *, unit_offset=0):
        number = witness(token)
        unit_w = witness(unit)
        if unit_offset:
            start = raw.index(unit.encode(), unit_offset)
            unit_w.update(start=start, end=start+len(unit.encode()))
        return {'kind': 'source_number', 'number': {'witness': number,
            'number_start': 0, 'number_end': len(token)}, 'unit': unit_w, 'origin': 'synthetic'}
    args = {'source_ref': SOURCE, 'source_kind': 'synthetic_fixture',
        'assay_type': 'endpoint_conversion', 'quantity_kind': 'conversion_fraction',
        'assertion_ref': ASSERTION, 'quantities': dict.fromkeys(ROLES),
        'interpretations': {}, 'prediction_model': None}
    args['quantities']['effect'] = literal('0.8', effect_unit)
    args['quantities']['effect_variance'] = literal('0.04', variance_unit)
    anchor = witness('Assay conditions recorded.')
    anchor.pop('representation'); anchor['artifact_ref'] = artifact
    records = {ASSERTION: {'id': ASSERTION, 'record_type': 'hypothesis'},
        SUPPORT: {'id': SUPPORT, 'record_type': 'reference', 'anchor': anchor}}
    def read_source(ref, representation):
        assert ref == SOURCE and representation == 'original'
        return {'artifact_ref': artifact, 'content': raw}
    return args, read_source, records.__getitem__


def read(args, source, record, cells=lambda *args: []):
    return read_assay_grading_inputs(args, read_source=source, read_record=record, read_cells=cells)


def test_actual_numbers_fill_partial_sheet_and_estimated_precision_without_quality_default():
    args, source, record = fixture()
    args['interpretations']['variance_correspondence'] = {'status': 'supported', 'support_refs': [SUPPORT]}
    extraction = read(args, source, record)
    cells = grade_assay(extraction)['cells']
    assert cells['measured_effect']['value'] == .8
    assert cells['effect_variance']['value'] == .04
    assert cells['effect_precision']['value'] == 25
    assert cells['source_log_evidence_ratio']['value'] is None
    assert 'prediction_model_not_selected' in cells['source_log_evidence_ratio']['reasons']


def test_explicit_synthetic_source_cannot_be_relabelled_as_reported_experiment():
    args, source, record = fixture()
    args['quantities']['effect']['origin'] = 'reported'
    extraction = read(args, source, record)
    assert extraction['quantities']['effect']['origin'] == 'synthetic'
    assert grade_assay(extraction)['cells']['measured_effect']['input_origins'] == ['synthetic']


@pytest.mark.parametrize('mutation', [
    lambda a: a['quantities']['effect']['number']['witness'].update(quote='0.9'),
    lambda a: a['quantities']['effect']['number'].update(number_start=2),
    lambda a: a['quantities']['effect']['number'].update(value=.99),
])
def test_forged_values_and_clipped_numbers_are_rejected(mutation):
    args, source, record = fixture()
    mutation(args)
    with pytest.raises(ValueError):
        read(args, source, record)


def test_source_upper_bound_never_becomes_point_measurement():
    args, source, record = fixture(RAW.replace(b'= 0.8', b'= <0.8'))
    extraction = read(args, source, record)
    assert extraction['quantities']['effect']['status'] == 'bounded'
    assert extraction['quantities']['effect']['value'] is None
    assert grade_assay(extraction)['cells']['measured_effect']['value'] is None


@pytest.mark.parametrize('prefix', ['approximately '])
def test_unsupported_point_interpretation_preserves_other_available_inputs(prefix):
    args, source, record = fixture(RAW.replace(b'= 0.8', ('= ' + prefix + '0.8').encode()))
    extraction = read(args, source, record)
    assert extraction['quantities']['effect']['status'] == 'unavailable'
    assert extraction['quantities']['effect_variance']['value'] == .04


@pytest.mark.parametrize('prefix,relation,lower,upper', [
    ('<', 'lt', None, .8), ('<=', 'le', None, .8),
    ('>', 'gt', .8, None), ('>=', 'ge', .8, None), ('at least ', 'ge', .8, None)])
def test_source_censoring_retains_actual_threshold_and_direction(prefix, relation, lower, upper):
    args, source, record = fixture(RAW.replace(b'= 0.8', ('= ' + prefix + '0.8').encode()))
    extraction = read(args, source, record)
    effect = extraction['quantities']['effect']
    assert effect['value'] is None and effect['status'] == 'bounded'
    assert effect['bound'] == {'relation': relation, 'lower': lower, 'upper': upper}
    measured = grade_assay(extraction)['cells']['measured_effect']
    assert measured['status'] == 'bounded' and measured['bound'] == effect['bound']


@pytest.mark.parametrize('printed', ['not >0.8', '>10.8', '>-0.8', '>0.8e2', '>0.8.2'])
def test_lower_limit_does_not_bypass_original_numeric_boundary_checks(printed):
    args, source, record = fixture(RAW.replace(b'= 0.8', ('= ' + printed).encode()))
    with pytest.raises(ValueError):
        read(args, source, record)


def test_approximation_with_lower_limit_remains_unresolved_not_censored_point():
    args, source, record = fixture(RAW.replace(b'= 0.8', b'= about >0.8'))
    effect = read(args, source, record)['quantities']['effect']
    assert effect['status'] == 'unavailable' and 'bound' not in effect


@pytest.mark.parametrize('unit,canonical,assay_type,quantity_kind', [
    ('pS', 'pS', 'transport_response', 'electrical_conductance'),
    ('pA', 'pA', 'transport_response', 'electrical_current'),
    ('mg/mL', 'mg/ml', 'protein_amount', 'protein_amount')])
def test_new_type_native_units_accept_authenticated_literal_effects_and_variance(unit, canonical, assay_type, quantity_kind):
    raw = RAW.replace(b'fraction', unit.encode())
    args, source, record = fixture(raw, effect_unit=unit, variance_unit=unit + '_squared')
    args.update(assay_type=assay_type, quantity_kind=quantity_kind)
    args['interpretations']['variance_correspondence'] = {'status': 'supported', 'support_refs': [SUPPORT]}
    extraction = read(args, source, record)
    assert extraction['quantities']['effect']['unit'] == canonical
    assert extraction['quantities']['effect_variance']['unit'] == canonical + '_squared'
    cells = grade_assay(extraction)['cells']
    assert cells['measured_effect']['value'] == .8
    assert cells['effect_precision']['value'] == 25


def test_clipped_variance_unit_and_unanchored_support_rejected():
    args, source, record = fixture()
    unit = args['quantities']['effect_variance']['unit']
    unit.update(quote='fraction', end=unit['start'] + len('fraction'))
    with pytest.raises(ContractError, match='partial_source_unit'):
        read(args, source, record)
    args, source, record = fixture()
    args['interpretations']['variance_correspondence'] = {'status': 'supported', 'support_refs': [SOURCE]}
    with pytest.raises(ContractError, match='anchored_support'):
        read(args, source, lambda ref: {'id': SOURCE, 'record_type': 'source'} if ref == SOURCE else record(ref))


def test_unrelated_same_source_unit_cannot_change_measurement_dimension():
    raw = RAW.replace(b'Effect = 0.8 fraction.', b'Effect = 0.8 mM.\nUnrelated control = 2 fraction.')
    args, source, record = fixture(raw)
    with pytest.raises(ContractError, match='unit_not_adjacent_to_number'):
        read(args, source, record)


def test_actual_saved_partition_component_is_bound_and_cannot_masquerade_as_rate(tmp_path):
    from test_literature_product_partition_storage import setup
    from gene_annotation_episode.literature_product_partition_storage import LiteratureProductPartitionRepository
    store, context, partition_args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, partition_args, 'partition')
        ref = outcome['result']['sheet_ref']
        rows = repo.project_cells([ref], permitted_record_refs=outcome['record_refs'], components=['partition_a_fraction'])
        args, _, record = fixture()
        args.update(source_ref=partition_args['source_ref'], assay_type='product_distribution', quantity_kind='equilibrium_fraction')
        args['quantities'] = dict.fromkeys(ROLES)
        args['quantities']['effect'] = {'kind': 'received_component',
            'namespace': 'literature_product_partition_cells', 'sheet_ref': ref, 'component': 'partition_a_fraction'}
        def source(reference, representation):
            s = store.get(reference)
            return {'artifact_ref': s['artifact_ref'], 'content': store.get_artifact(s['artifact_ref'])}
        extraction = read(args, source, record, lambda *arguments: rows)
        assert extraction['quantities']['effect']['value'] == .603
        assert grade_assay(extraction)['cells']['measured_effect']['value'] == .603
        with pytest.raises(ContractError, match='not_received'):
            read(args, source, record)
        args.update(assay_type='activity_rate', quantity_kind='rate')
        with pytest.raises(ContractError, match='partition_is_not_rate'):
            read(args, source, record, lambda *arguments: rows)
    finally:
        store.close()


def test_actual_compiled_native_nondetection_does_not_become_measured_zero(tmp_path):
    """The retained P450 row prints zero with explicit nondetection meaning."""
    from test_literature_common_assessment_221 import Case
    from test_literature_common_assessment_binding_223 import selected
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    case = Case(tmp_path / 'native_nondetection', 3)
    try:
        _, _, _, _, rows = selected(case, ['estimate_product_test'])
        assert rows[0]['value'] == 0
        assert rows[0]['native_semantics'] == 'reported_nondetection'
        selector = {'namespace': 'literature_compiled_assay_v3_cells',
            'sheet_ref': rows[0]['sheet_ref'], 'component': 'estimate_product_test'}
        normalized, retained = _component(selector, lambda *args: rows)
        assert normalized['value'] is None and normalized['status'] == 'unavailable'
        assert normalized['reason'] == 'native_reported_nondetection_is_not_point'
        assert retained == rows[0]
    finally:
        case.store.close()


def test_compiled_native_component_does_not_inherit_unselected_estimate_owners(tmp_path):
    from test_literature_common_assessment_221 import Case
    from test_literature_common_assessment_binding_223 import selected
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    case = Case(tmp_path / 'native_owners', 1)
    try:
        _, _, _, _, rows = selected(case, ['estimate_product_test'])
        row = rows[0]
        selector = {'namespace': 'literature_compiled_assay_v3_cells',
            'sheet_ref': row['sheet_ref'], 'component': 'estimate_product_test'}
        normalized, _ = _component(selector, lambda *args: rows)
        selected_keys = set(row['operand_keys'])
        unselected_keys = {b['owner_key'] for b in row['estimate_bindings']} - selected_keys
        assert selected_keys <= set(normalized['measurement_keys'])
        assert not unselected_keys.intersection(normalized['measurement_keys'])
        assert normalized['value'] == 92
    finally:
        case.store.close()


def test_compiled_partial_variance_uses_selected_uncertainty_not_legacy_full_model(tmp_path):
    from test_literature_compiled_assay_185 import setup
    from test_literature_compiled_assay_uncertainty_215 import v2, block, selected, VAR
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    store, context, args, _ = setup(tmp_path / 'component_variance')
    try:
        context, args = v2(context, args)
        context, args, _ = block(store, context, args)
        _, _, _, _, _, rows = selected(store, context, args)
        row = next(r for r in rows if r['component'] == VAR)
        assert row['variance_status'] == 'unknown'
        assert row['uncertainty']['variance_status'] == 'estimated'
        selector = {'namespace': 'literature_compiled_assay_v2_cells',
            'sheet_ref': row['sheet_ref'], 'component': VAR}
        normalized, retained = _component(selector, lambda *args: [row])
        assert normalized['value'] == row['value']
        assert 'estimated_covariance' in normalized['qualifications']
        assert 'unknown_covariance' not in normalized['qualifications']
        assert normalized['origin'] == 'synthetic'
        assert retained == row
    finally:
        store.close()


def test_controlled_design_uses_actual_component_key_and_preserves_native_value(tmp_path):
    from test_literature_controlled_response_storage_v3 import native_case
    from gene_annotation_episode.literature_controlled_response_storage import LiteratureControlledResponseRepository
    store, context, native_args, _ = native_case(tmp_path)
    try:
        repo = LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, native_args, 'controlled')
        rows = [r for r in outcome['result']['cells'] if r['component'] == 'controlled_response_difference'
                and r['kind'] == 'final']
        assert len(rows) == 1
        row = rows[0]
        args, _, record = fixture()
        args.update(source_ref=native_args['source_ref'], assay_type='activity_rate', quantity_kind='rate_difference')
        args['quantities'] = dict.fromkeys(ROLES)
        args['quantities']['effect'] = {'kind': 'received_component',
            'namespace': 'literature_controlled_response_component_cells', 'sheet_ref': row['sheet_ref'],
            'component': row['component_key']}
        def source(reference, representation):
            source_row = store.get(reference)
            return {'artifact_ref': source_row['artifact_ref'], 'content': store.get_artifact(source_row['artifact_ref'])}
        extraction = read(args, source, record, lambda *arguments: rows)
        assert extraction['quantities']['effect']['value'] == row['cell']['value']
        assert extraction['quantities']['effect']['status'] == 'point'
        assert set(row['cell']['conditional_on']) <= set(extraction['quantities']['effect']['qualifications'])
    finally:
        store.close()
