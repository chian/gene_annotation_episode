"""Retained original-paper measurements through the four reusable A105 graders.

These examples supply no invented variance, null prediction or full-model
assumption. Scientific interpretations are explicit and anchored to passages
that are checked against the retained source bytes. They are not model tests
of autonomous scientific interpretation or selected-episode storage tests.
"""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.literature_parent_depletion_inputs import read_parent_depletion_inputs
from gene_annotation_episode.literature_parent_depletion_calculations import populate_parent_depletion_components
from gene_annotation_episode.literature_product_partition_inputs import read_product_partition_inputs
from gene_annotation_episode.literature_product_partition_calculations import populate_product_partition_components
from gene_annotation_episode.literature_rate_reader import read_rate_table
from gene_annotation_episode.literature_rate_bound_calculations import populate_rate_table_bounds
from test_literature_product_partition_inputs import PRIMARY, PRIMARY_SHA, fixture as partition_selection
from test_literature_product_coupling_212 import original as coupling_selection, run as read_coupling


ROOT = Path(__file__).resolve().parents[1]
RATE_CASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/coupled_redox_case_093/generation_002'
DEPLETION_CASE = ROOT / 'verification/a105_matched_control_primary_306/source'
DEPLETION_PIN = '24d5734e8a8643ab20306a1725843686460761362cb85a9ef0c1e6c25304a2ae'
DEPLETION_ARTICLE_PIN = '1919a2a62baa2983b2bf9e9ccbde7c9631bdc2322c2951be68ecc1c798da4e1e'


def _interpretation(status, *refs):
    return {'status': status, 'support_refs': list(refs)}


def _source_location(raw, quote, label):
    """Locate original text for a test's explicit scientific interpretation."""
    token = quote.encode()
    start = raw.index(token)
    assert raw[start:start + len(token)] == token
    return f'{label}#bytes={start}:{start + len(token)}'


def _checked_witness(raw, witness):
    assert raw[witness['start']:witness['end']].decode() == witness['quote']
    return f"{witness['source_ref']}#bytes={witness['start']}:{witness['end']}"


def _operand(cell, component, source_ref, measurement_keys):
    # Every fixture below selects a supported point; bounds are not collapsed.
    assert cell['value'] is not None
    assert cell['status'] in ('point', 'populated')
    return {'value': cell['value'], 'unit': cell['unit'], 'status': 'point', 'reason': None,
        'measurement_keys': list(measurement_keys), 'source_refs': [source_ref],
        'origin': 'derived' if cell['origin'] == 'calculated' else cell['origin'],
        'native_component': component}


def _assessment(assay_type, quantity_kind, assertion_ref, effect, interpretations):
    quantities = {role: None for role in ROLES}
    quantities['effect'] = effect
    return {'version': INPUT_VERSION, 'assay_type': assay_type, 'quantity_kind': quantity_kind,
        'assertion_ref': assertion_ref, 'quantities': quantities,
        'interpretations': interpretations, 'prediction_model': None}


def _assert_partial(sheet, expected):
    effect = sheet['cells']['measured_effect']
    assert effect['value'] == pytest.approx(expected)
    assert effect['input_origins'] and 'synthetic' not in effect['input_origins']
    for name in ('effect_variance', 'effect_precision', 'source_log_evidence_ratio'):
        cell = sheet['cells'][name]
        assert cell['value'] is None
        assert cell['status'] == 'unavailable'
        assert cell['reasons']
    assert 'effect_variance_not_selected' in sheet['cells']['effect_variance']['reasons']
    assert {'effect_variance_not_selected', 'assertion_prediction_not_selected',
        'alternative_prediction_not_selected', 'prediction_model_not_selected'} <= set(
            sheet['cells']['source_log_evidence_ratio']['reasons'])
    assert sheet['prediction_model'] is None
    assert sheet['annotation_credit'] is None


def activity_example():
    custody = json.loads((RATE_CASE / 'PRIMARY_TABLE_CUSTODY.json').read_text())
    raw = (ROOT / custody['source_path']).read_bytes()
    assert sha256(raw).hexdigest() == custody['source_sha256']
    context = custody['table_context_and_unit_definitions']
    table_ref = _checked_witness(raw, context)
    assert 'One unit was equivalent to 1 μmol' in context['quote']
    assert 'TTC reduction each 1-ml assay mixture incubated at 25°C' in context['quote']
    arms = ('ttc@25|TTC', 'ttc@25|TTC − crotonyl-CoA')
    for row in custody['rows']:
        if row['arm'] in arms:
            for key in ('mixture_cell', 'value_cell', 'assay_heading'):
                _checked_witness(raw, row[key]['witness'])
    saved = json.loads((RATE_CASE / 'RATE_EXTRACTION.json').read_text())
    mapped = (RATE_CASE / 'MAPPED_TABLE.tsv').read_text()
    assert sha256(mapped.encode()).hexdigest() == custody['mapped_table_sha256']
    source = saved['rows'][0]['source']
    extracted = read_rate_table({'source_ref': source['source_ref'], 'artifact_ref': source['artifact_ref'],
        'text': mapped, 'representation': 'retained_extraction', 'delimiter': '\t'},
        expected_subject=saved['subject'], expected_experiment=saved['experiment'])
    assert extracted == saved
    selected = [next(row for row in extracted['rows'] if row['arm'] == arm) for arm in arms]
    native = populate_rate_table_bounds(extracted, reference_arm=arms[0], test_arm=arms[1],
        reference_condition=selected[0]['condition'], test_condition=selected[1]['condition'])
    assert [row['value'] for row in selected] == [12, .6]
    assert all(row['uncertainty']['kind'] == 'unreported' and row['uncertainty']['count'] is None
               for row in selected)
    effect = _operand(native['cells']['retained_fraction'], 'retained_fraction', source['source_ref'],
        [identity('retained_rate_row', row['source']) for row in selected])
    assessment = _assessment('activity_rate', 'rate_ratio', 'assertion_ttc_substrate_omission_response', effect, {
        'measurement_identity': _interpretation('supported', table_ref),
        'normalization_basis': _interpretation('supported', table_ref),
        'assertion_relevance': _interpretation('supported', table_ref),
        'condition_scope': _interpretation('supported', table_ref),
        'kinetic_model': _interpretation('not_applicable', table_ref),
        # Substrate omission is not a no-enzyme control or isolated attribution.
        'background_alternatives': _interpretation('unknown', table_ref),
        'attribution_supported': _interpretation('unknown', table_ref),
    })
    return assessment, native


def endpoint_example():
    workbook = DEPLETION_CASE / 'amidase-paper/data/PLA55254_P205_subtrate_specificity_screening.xlsx'
    raw = workbook.read_bytes()
    assert sha256(raw).hexdigest() == DEPLETION_PIN
    article = (DEPLETION_CASE / 'PMC11741061.xml').read_bytes()
    assert sha256(article).hexdigest() == DEPLETION_ARTICLE_PIN
    source_ref = 'source_' + DEPLETION_PIN
    selected = {'version': 'a105_parent_depletion_xlsx_selection_v1', 'source_ref': source_ref,
        'expected_sha256': DEPLETION_PIN, 'sheet_name': 'summary', 'compound': 'Capecitabine',
        'submix': 'Sub7', 'time_hours': 24}
    extracted = read_parent_depletion_inputs(selected, raw)
    native = populate_parent_depletion_components(extracted)
    assert extracted['row_number'] == 5
    screening = _source_location(article, 'Substrate specificity screening of P205', 'PMC11741061')
    control = _source_location(article, 'P205-S146A served as a negative control.', 'PMC11741061')
    # Re-read the actual product-identification paragraph before assigning scope.
    paragraphs = [' '.join(''.join(p.itertext()).split()) for p in ET.fromstring(article).iter('p')]
    product_paragraph = next(p for p in paragraphs if 'each was incubated individually with purified P131' in p)
    assert 'capecitabine' in product_paragraph and 'analytical standards' in product_paragraph
    effect_cell = native['cells']['active_minus_inactive']
    effect = _operand(effect_cell, 'active_minus_inactive', source_ref, effect_cell['input_measurement_keys'])
    assessment = _assessment('endpoint_conversion', 'conversion_difference',
        'assertion_p205_parent_disappearance_24h', effect, {
            'measurement_identity': _interpretation('supported', screening, control),
            'endpoint_alignment': _interpretation('supported', source_ref + '#summary!B5,F5'),
            'assertion_relevance': _interpretation('supported', screening),
            'background_alternatives': _interpretation('unknown', control),
            'attribution_supported': _interpretation('unknown', control),
            'product_identity': _interpretation('unknown', screening),
        })
    return assessment, native, extracted


def distribution_example():
    raw = PRIMARY.read_bytes()
    assert sha256(raw).hexdigest() == PRIMARY_SHA
    selected, read, witness = partition_selection(raw, primary=True)
    selected['evidence'] = [
        {'role': 'competing_contribution', 'witness': witness('RpiA in the HFP sample was confirmed by mass spectrometry')},
        {'role': 'composition', 'witness': witness('39.7% ketose (ribulose) and 60.3% aldose (ribose)')},
    ]
    extracted = read_product_partition_inputs(selected, read_source=read)
    native = populate_product_partition_components(extracted)
    root = ET.fromstring(raw)
    composition = root.find(".//p[@id='p0060']")
    assert composition is not None and 'equilibrium mixture' in ''.join(composition.itertext())
    composition_ref = _checked_witness(raw, witness('39.7% ketose (ribulose) and 60.3% aldose (ribose)'))
    contaminant_ref = _checked_witness(raw, selected['evidence'][0]['witness'])
    reverse_ref = _source_location(raw, 'same equilibrium is established by starting with either', 'PMC12051542')
    effect = _operand(native['cells']['partition_a_fraction'], 'partition_a_fraction', selected['source_ref'],
        [extracted['quantities']['a']['measurement_key']])
    assessment = _assessment('product_distribution', 'equilibrium_fraction',
        'assertion_hfp_preparation_r5p_equilibrium_fraction', effect, {
            'measurement_identity': _interpretation('supported', composition_ref),
            'species_identity': _interpretation('supported', composition_ref),
            'common_denominator': _interpretation('supported', composition_ref),
            'equilibrium_state': _interpretation('supported', reverse_ref),
            'assertion_relevance': _interpretation('supported', composition_ref),
            'background_alternatives': _interpretation('unknown', contaminant_ref),
            'attribution_supported': _interpretation('unknown', contaminant_ref),
        })
    return assessment, native


def coupling_example():
    source, selected, _ = coupling_selection(1)
    extracted, native = read_coupling(source, selected)
    identity_refs = [_checked_witness(source.content, w)
                     for w in selected['relationships']['product_identity']['witnesses']]
    product_conditions = selected['context']['product_conditions']
    cofactor_conditions = selected['context']['cofactor_conditions']
    assert '10–30 min' in product_conditions['quote']
    assert 'steady state kinetic experiments' in cofactor_conditions['quote']
    conditions_refs = [_checked_witness(source.content, w) for w in (product_conditions, cofactor_conditions)]
    pairing = [_checked_witness(source.content, w)
               for w in selected['relationships']['source_pairing']['witnesses']]
    cell = native['cells']['product_per_cofactor']
    effect = _operand(cell, 'product_per_cofactor', source.reference, cell['input_measurement_keys'])
    assessment = _assessment('reaction_coupling', 'stoichiometric_ratio',
        'assertion_t252n_reported_product_per_nadh', effect, {
            'measurement_identity': _interpretation('supported', *pairing),
            'product_identity': _interpretation('supported', *identity_refs),
            'assertion_relevance': _interpretation('supported', *pairing),
            'matched_windows': _interpretation('unknown', *conditions_refs),
            'attribution_supported': _interpretation('unknown', *pairing),
        })
    return assessment, native, extracted


def test_retained_activity_rate_comparison_does_not_promote_substrate_omission_to_attribution():
    assessment, native = activity_example()
    sheet = grade_assay(assessment)
    _assert_partial(sheet, .05)
    assert native['cells']['fractional_decrease']['value'] == .95
    assert sheet['interpretations']['attribution_supported']['status'] == 'unknown'
    assert sheet['cells']['attributed_fraction']['value'] is None


def test_retained_endpoint_controls_leave_shared_uncertainty_and_product_identity_unknown():
    assessment, native, extracted = endpoint_example()
    sheet = grade_assay(assessment)
    _assert_partial(sheet, .589291007953367)
    assert native['cells']['active_minus_abiotic']['value'] == pytest.approx(.726749353835549)
    assert native['cells']['active_minus_inactive']['standard_error_of_difference'] is None
    assert extracted['active_control_covariance'] == 'unknown'
    assert sheet['interpretations']['product_identity']['status'] == 'unknown'
    assert (native['cells']['active_minus_inactive']['input_measurement_keys'][0]
            == native['cells']['active_minus_abiotic']['input_measurement_keys'][0])


def test_retained_equilibrium_distribution_preserves_contaminant_attribution_limit():
    assessment, native = distribution_example()
    sheet = grade_assay(assessment)
    _assert_partial(sheet, .603)
    assert native['cells']['partition_b_fraction']['value'] == .397
    assert native['cells']['selected_closure_deviation']['value'] == 0
    assert native['uncertainty_calculation'] == 'not_implemented'
    assert sheet['interpretations']['equilibrium_state']['status'] == 'supported'
    assert sheet['interpretations']['attribution_supported']['status'] == 'unknown'
    assert sheet['cells']['attributed_fraction']['value'] is None


def test_retained_coupling_ratio_does_not_upgrade_different_protocols_to_physical_fraction():
    assessment, native, extracted = coupling_example()
    sheet = grade_assay(assessment)
    _assert_partial(sheet, 92 / 216)
    assert native['cells']['productive_fraction']['value'] is None
    assert native['cells']['productive_fraction']['conditional_value'] == pytest.approx(92 / 216)
    assert native['cells']['product_per_cofactor_variance']['value'] is None
    assert extracted['relationships']['same_preparation']['value'] == 'unknown'
    assert sheet['interpretations']['matched_windows']['status'] == 'unknown'


def test_primary_examples_require_no_case_specific_grader_or_invented_model_inputs():
    examples = [activity_example()[0], endpoint_example()[0], distribution_example()[0], coupling_example()[0]]
    assert {item['assay_type'] for item in examples} == {
        'activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'}
    for original in examples:
        assert original['prediction_model'] is None
        assert all(value is None for role, value in original['quantities'].items() if role != 'effect')
        renamed = {**original, 'assertion_ref': 'assertion_another_case_same_measurement_question'}
        first, second = grade_assay(original), grade_assay(renamed)
        assert first['cells'] == second['cells']
        assert first['interpretations'] == second['interpretations']
