"""Constructed source regression cases; no paper or live-model evidence.

Local interpretation records must survive independently of whole-model requests.
Legacy-shape tests exercise retained-record consistency, not migration of an old
native implementation descriptor into a new implementation generation.
"""
from copy import deepcopy as cp
import importlib.util
from pathlib import Path

from PIL import Image
import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_v3_inputs as source
from gene_annotation_episode import literature_controlled_response_v3_population as population
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode import literature_controlled_response_figure_inputs as graph
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from test_literature_controlled_response_v3_inputs import Fixture


def unique_local_fixture(*, second_pair=False):
    f = Fixture()
    f.args['variance_status'] = dict(value='unknown', witnesses=[])
    f.args['model_kind'] = dict(value='none', witnesses=[])
    pairs = f.args['local_pair_assignments']
    if second_pair:
        other = cp(pairs[0])
        other.update(pair_key='condition1-distinct', condition='condition1',
            protein=dict(role=shared.PRIMITIVE_ORDER[0], reading_key=None),
            control=dict(role=shared.PRIMITIVE_ORDER[1], reading_key=None))
        pairs.append(other)
    for i, pair in enumerate(pairs):
        for name, value in (('admissibility', 'compatible'), ('scope', 'same'), ('variance_status', 'known')):
            quote = f'Constructed local pair {i}: {name} is {value}.'
            f.append(quote)
            pair[name] = f.interp(value, quote)
    return f


def legacy_shape(extraction):
    """Project the older shape without adding or repairing any witness record."""
    result = cp(extraction)
    result.pop('local_pair_extractions')
    result['diagnostics'] = []
    result['diagnostics'] = shared._unique_diagnostics(result, stable=True)
    return result


def test_original_unknown_global_request_preserves_supported_local_variance():
    f = Fixture()
    original_local = cp(f.args['local_pair_assignments'])
    original_covariance = cp(f.args['covariance'])
    f.args['variance_status'] = dict(value='unknown', witnesses=[])
    result = f.read()
    assert f.args['local_pair_assignments'] == original_local
    assert f.args['covariance'] == original_covariance
    assert f.calls == shared._reference_closure(f.args)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    recorded = result['local_pair_extractions'][0]['variance_status']
    assert recorded['selection'] == original_local[0]['variance_status']
    assert recorded['witnesses'][0]['authentication'] == 'exact_utf8_byte_span'
    assert result['requested_model']['variance_status']['effective_value'] == 'unknown'
    assert result['effective_model']['variance_status'] == 'unknown'
    assert result['effective_model']['model_kind'] == 'none'
    populated = population.populate_controlled_response_v3(result)
    pair = populated['local_sheet']['pairs'][0]
    assert pair['difference']['value'] == .00395
    assert pair['difference']['bound_kind'] == 'conditional_digitization'
    assert pair['variance']['value'] == 4.5e-7
    assert pair['variance']['unit'] == '(umol/min)^2'
    assert pair['standard_uncertainty']['value'] == pytest.approx((4.5e-7)**.5)
    assert pair['dependencies']['variance']['full_source_covariance_required'] is True
    assert populated['final_sheet']['cells']['contrast_variance']['value'] is None
    assert populated['final_sheet']['cells']['source_profile_log_ratio']['value'] is None


def test_all_three_local_interpretations_keep_their_own_actual_witnesses():
    f = unique_local_fixture(second_pair=True)
    # Local covariance does not require a selected whole-experiment covariance.
    f.args['covariance'] = None
    result = f.read()
    assert result['covariance'] is None
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    for pair, row in zip(f.args['local_pair_assignments'], result['local_pair_extractions']):
        assert row['pair_key'] == pair['pair_key']
        for name in ('admissibility', 'scope', 'variance_status'):
            assert row[name]['selection'] == pair[name]
            assert [w['selection'] for w in row[name]['witnesses']] == pair[name]['witnesses']
            assert all(w['authentication'] == 'exact_utf8_byte_span' for w in row[name]['witnesses'])
    assert all(row['variance']['value'] is not None for row in population.populate_controlled_response_v3(result)['local_sheet']['pairs'])


@pytest.mark.parametrize('name', ['admissibility', 'scope', 'variance_status'])
def test_unavailable_unique_local_witness_remains_unknown(name):
    f = unique_local_fixture()
    selected = f.args['local_pair_assignments'][0][name]
    ref = 'source_' + 'd'*24
    quote = 'Unavailable constructed local interpretation'
    selected['witnesses'] = [dict(kind='text', source_ref=ref, representation='original',
        start=0, end=len(quote.encode()), quote=quote)]
    original = f.source
    def unavailable(reference, representation):
        if reference == ref:
            f.calls.append((reference, representation))
            raise EOFError('constructed missing retained source')
        return original(reference, representation)
    result = source.read_controlled_response_v3_inputs(f.args, read_source=unavailable)
    row = result['local_pair_extractions'][0][name]
    assert row['selection']['value'] == selected['value']
    assert row['effective_value'] == 'unknown'
    assert row['witnesses'][0]['authentication'] == 'unavailable'
    assert row['witnesses'][0]['canonical_locator'] is None
    assert f.calls == shared._reference_closure(f.args)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    pair = population.populate_controlled_response_v3(result)['local_sheet']['pairs'][0]
    assert pair['variance']['value'] is None
    assert (pair['difference']['value'] is not None) == (name == 'variance_status')


def test_image_local_witnesses_keep_geometry_and_interpretation_attribution():
    f = unique_local_fixture()
    image = f.args['images'][0]
    for i, name in enumerate(('admissibility', 'scope', 'variance_status')):
        f.args['local_pair_assignments'][0][name]['witnesses'] = [dict(kind='image',
            image_id=image['image_id'], region=[i, 0, i+1, 1], quote='Constructed local '+name)]
    result = f.read()
    for row in result['local_pair_extractions'][0].values():
        if isinstance(row, dict):
            witness = row['witnesses'][0]
            assert witness['authentication'] == 'image_bytes_and_geometry_only'
            assert witness['attribution'] == 'investigating_episode_interpretation'
            assert witness['canonical_locator']['kind'] == 'image'
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    assert population.populate_controlled_response_v3(result)['local_sheet']['pairs'][0]['variance']['value'] == 4.5e-7


@pytest.mark.parametrize('mutation', ['pair_key', 'row_order', 'row_deletion', 'witness_deletion',
    'witness_substitution', 'witness_identity', 'effective_value', 'selection_value', 'unexpected_field', 'legacy_missing'])
def test_saved_local_associations_cannot_be_substituted_deleted_or_reordered(mutation):
    f = unique_local_fixture(second_pair=True)
    result = f.read()
    rows = result['local_pair_extractions']
    if mutation == 'pair_key': rows[0]['pair_key'] = rows[1]['pair_key']
    elif mutation == 'row_order': rows.reverse()
    elif mutation == 'row_deletion': rows.pop()
    elif mutation == 'witness_deletion': rows[0]['scope']['witnesses'] = []
    elif mutation == 'witness_substitution': rows[0]['scope']['witnesses'] = cp(rows[1]['scope']['witnesses'])
    elif mutation == 'witness_identity': rows[0]['scope']['witnesses'][0]['byte_sha256'] = '0'*64
    elif mutation == 'effective_value': rows[0]['variance_status']['effective_value'] = 'unknown'
    elif mutation == 'selection_value': rows[0]['variance_status']['selection']['value'] = 'estimated'
    elif mutation == 'unexpected_field': rows[0]['scope']['invented'] = True
    else: result = legacy_shape(result)
    with pytest.raises(ExperimentalContractError):
        source.validate_controlled_response_v3_extraction(f.args, result)


def test_legacy_shape_uses_existing_retained_witnesses_and_cannot_fill_missing_ones():
    f = Fixture()
    result = legacy_shape(f.read())
    Draft202012Validator(source._extraction_schema()).validate(result)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    f.args['variance_status'] = dict(value='unknown', witnesses=[])
    missing = legacy_shape(f.read())
    with pytest.raises(ExperimentalContractError, match='saved_witness_missing:local_pair_assignments.variance_status'):
        source.validate_controlled_response_v3_extraction(f.args, missing)


def test_saved_local_reconstruction_opens_no_sources_or_images_or_calculators(monkeypatch):
    f = unique_local_fixture()
    result = f.read()
    calls = cp(f.calls)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved reconstruction attempted acquisition/decoding/scientific population')
    for module, names in ((shared, ('open_controlled_response_sources', '_Inputs', '_Sources', '_native_number', '_native_unit')),
            (graph, ('read_controlled_response_rate_figure', '_strict_decode', '_count_bar_runs')),
            (local, ('populate_controlled_response_local',)), (owner, ('populate_controlled_response_owner',)),
            (population, ('populate_controlled_response_v3',))):
        for name in names: monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(Image, 'open', forbidden)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    assert f.calls == calls


def test_original095_unknown_global_alternate_reaches_runtime_custody_check(tmp_path):
    # Execute the unchanged original failing consumer, using current production
    # code. Its original artifact/body remains unchanged and inspectable.
    path = Path(__file__).resolve().parents[1] / ('verification/literature_reference_evidence_2026-10-25_001/'
        'controlled_episode_integration_095/coherent_code_001/tests/test_literature_controlled_response_consumer.py')
    spec = importlib.util.spec_from_file_location('original095_controlled_consumer', path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    original.test_actual_runtime_digest_and_complete_alternate_wrapper_cannot_replace_selected_output(tmp_path)
