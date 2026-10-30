"""Synthetic-only actual capability probes and proposed reference arithmetic.

This is research evidence for a proposal, not an installed reader/calculator.
"""
from copy import deepcopy
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_assay_inputs import _Sources, read_assay_inputs, ASSAY_LITERAL_FIELDS
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_native_inputs import read_rate_source_inputs, MEANINGS, _number, _unit, _converted
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_figure_measurements import read_bar_ordinate
from gene_annotation_episode.domain import ContractError


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output_directory):
    source_text = ('Invented synthetic comparison; μ prefix exercises UTF8.\n'
        'Shared endpoint: initial retained-tracer rate.\n'
        'Normalization: same paired-reference protein mass for all four arms.\n'
        'Condition 1 and condition 0 are the intended protocol levels.\n'
        'Protein condition 1: 12 nmol/min/mg.\n'
        'Empty condition 1: 2 nmol/min/mg.\n'
        'Protein condition 0: 5 nmol/min/mg.\n'
        'Empty condition 0: 1 nmol/min/mg.\n')
    raw = source_text.encode()
    source_ref = 'synthetic_source_056'
    artifact_ref = 'artifact_' + hashlib.sha256(raw).hexdigest()
    def read(reference, representation):
        assert reference == source_ref and representation == 'original'
        return {'artifact_ref': artifact_ref, 'content': raw}
    def witness(quote, start=0):
        at = source_text.index(quote, start)
        return {'source_ref': source_ref, 'representation': 'original',
            'start': len(source_text[:at].encode()), 'end': len(source_text[:at + len(quote)].encode()), 'quote': quote}
    def meaning(value, quote=None):
        return {'value': value, 'witnesses': [] if quote is None else [witness(quote)]}
    sources = _Sources(read)
    roles = ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')
    lines = ('Protein condition 1: 12 nmol/min/mg.', 'Empty condition 1: 2 nmol/min/mg.',
             'Protein condition 0: 5 nmol/min/mg.', 'Empty condition 0: 1 nmol/min/mg.')
    arms, native = {}, {}
    for role, line in zip(roles, lines):
        token = line.split(': ')[1].split()[0]
        whole = witness(line)
        start = line.index(token, line.index(':'))
        selected = {'witness': whole, 'number_start': start, 'number_end': start + len(token)}
        number = _number(selected, sources, 'rate')
        unit = _unit(witness('nmol/min/mg', source_text.index(line)), sources, witness('initial retained-tracer rate'))
        native[role] = {'number': number, 'unit': unit, 'canonical_value': _converted(number, unit)}
        arm = {name: None for name in MEANINGS}
        arm.update(subject=witness('Protein' if role.startswith('protein') else 'Empty', source_text.index(line)),
            condition=witness('condition 1' if role.endswith('1') else 'condition 0', source_text.index(line)),
            endpoint=witness('initial retained-tracer rate'),
            normalization=witness('same paired-reference protein mass for all four arms'),
            measurement_identity=whole, rate={'number': selected, 'unit': witness('nmol/min/mg', source_text.index(line))},
            uncertainty={'kind': 'unreported', 'magnitude': None, 'unit': None, 'kind_witnesses': [],
                'count': None, 'sampling_basis': meaning('unspecified')})
        arms[role] = arm
    arguments = {'input_mode': 'native_source_spans', 'source_ref': source_ref, 'source_kind': 'synthetic_fixture',
        'experiment': witness('synthetic comparison'), 'arms': arms,
        'comparison': {'subject_relation': meaning('different', 'Protein'),
            'endpoint_relation': meaning('same', 'Shared endpoint'),
            'normalization_relation': meaning('same', 'same paired-reference protein mass for all four arms'),
            'intended_change': witness('intended protocol levels')},
        'dependence': meaning('unknown'), 'observation_model': meaning('none')}
    try:
        read_rate_source_inputs(arguments, read_source=read)
    except ExperimentalContractError as error:
        four_arm_failure = {'code': error.code, 'field': error.field}
    else:
        raise AssertionError('Existing two-arm route unexpectedly accepted four named roles')
    pair_results = []
    for index in (0, 2):
        selected = {**deepcopy(arguments), 'arms': {'reference': arms[roles[index]], 'test': arms[roles[index + 1]]}}
        extracted = read_rate_source_inputs(selected, read_source=read)
        condition = extracted['rows'][0]['condition']
        calculated = populate_rate_contrast(extracted, reference_arm='reference', test_arm='test',
            reference_condition=condition, test_condition=condition)
        pair_results.append({'condition': condition, 'difference': calculated['cells']['rate_difference'],
            'difference_se': calculated['cells']['difference_se']})
    line = lines[0]
    assay = {name: None for name in ASSAY_LITERAL_FIELDS}
    assay.update(endpoint=meaning('transport_flux', 'initial retained-tracer rate'), arrangement=meaning('unknown'))
    assay_args = {'source_ref': source_ref, 'source_kind': 'synthetic_fixture', 'assay': assay,
        'primitives': {role: None for role in ('q', 'g', 'k', 'E', 'u', 'v')},
        'covariance_source_ref': None, 'distinct_residual_variance': None,
        'variance_status': 'unknown', 'observation_model': 'none', 'model_witnesses': []}
    start, unit_start = line.index('12'), line.index('nmol')
    assay_args['primitives']['q'] = {'witness': witness(line), 'number_start': start, 'number_end': start + 2,
        'unit_start': unit_start, 'unit_end': unit_start + len('nmol/min/mg')}
    try:
        read_assay_inputs(assay_args, read_source=read)
    except ExperimentalContractError as error:
        assay_failure = {'code': error.code, 'field': error.field}
    else:
        raise AssertionError('Concentration-rate assay must not accept specific amount-rate q')
    selection = {'roi': {'left': 1, 'top': 1, 'right': 5, 'bottom': 8}, 'rgb_min': [0, 0, 0],
        'rgb_max': [10, 10, 10], 'minimum_row_fraction': .5, 'minimum_run_rows': 1,
        'edge_tolerance_pixels': 0, 'calibration': {'first': {'pixel': 1, 'value': 10},
            'second': {'pixel': 9, 'value': 0}, 'unit': 'nmol/min/mg'}}
    try:
        read_bar_ordinate(b'synthetic non-image: unit rejection precedes decoding', selection)
    except ContractError as error:
        graph_failure = {'code': str(error), 'detail': error.detail}
    else:
        raise AssertionError('Existing graph helper must not accept an unsupported rate unit')
    assert four_arm_failure == {'code': 'closed_fields_required', 'field': 'arms'}
    assert assay_failure['code'] == 'incompatible_primitive_unit'
    assert graph_failure['code'] == 'unsupported_calibration_unit'
    # The proposed linear arithmetic below is a transparent research reference,
    # not a production function or selected scientific action.
    x = [Fraction(v) for v in (12, 2, 5, 1)]
    coefficients = [1, -1, -1, 1]
    covariance = [[Fraction(str((1, .25, .36, .09)[i])) if i == j else Fraction(0)
        for j in range(4)] for i in range(4)]
    effect = sum(a*b for a, b in zip(coefficients, x))
    variance = sum(coefficients[i]*covariance[i][j]*coefficients[j] for i in range(4) for j in range(4))
    correlated = [[covariance[i][j] + Fraction('0.16') for j in range(4)] for i in range(4)]
    correlated_variance = sum(coefficients[i]*correlated[i][j]*coefficients[j] for i in range(4) for j in range(4))
    assert effect == 6 and variance == Fraction('1.7') == correlated_variance
    canonical_effect = sum(a * Fraction(str(native[role]['canonical_value']))
        for a, role in zip(coefficients, roles))
    canonical_variance = variance * Fraction('0.001') ** 2
    assert canonical_effect == Fraction('0.006') and canonical_variance == Fraction('0.0000017')
    receipt = {'scope': 'synthetic code-only proposal probes; no Store, episode, model or source paper',
        'source_sha256': hashlib.sha256(raw).hexdigest(), 'native_helpers': native,
        'existing_four_arm_failure': four_arm_failure, 'existing_two_arm_results': pair_results,
        'existing_assay_specific_rate_failure': assay_failure, 'existing_rate_graph_failure': graph_failure,
        'proposed_research_arithmetic': {'x': [float(v) for v in x], 'coefficients': coefficients,
            'unit': 'nmol/min/mg_paired_reference_input', 'effect': float(effect),
            'variance': float(variance), 'variance_with_shared_common_offset': float(correlated_variance),
            'canonical_unit': 'umol/min/mg_paired_reference_input',
            'canonical_effect': float(canonical_effect),
            'canonical_variance': float(canonical_variance),
            'known_normal_model_not_selected': True, 'source_profile_score': None},
        'production_or_test_edits': False, 'controller_observations': 0}
    with (output_directory / 'SYNTHETIC_SOURCE_001.txt').open('x') as stream:
        stream.write(source_text)
    with (output_directory / 'SYNTHETIC_INTERFACE_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    print(json.dumps({'status': 'passed', 'actual_two_arm_differences': [r['difference']['value'] for r in pair_results],
        'four_arm_interface_missing': four_arm_failure, 'assay_unit_guard': assay_failure,
        'graph_unit_guard': graph_failure, 'proposed_effect': float(effect), 'proposed_variance': float(variance),
        'canonical_effect': float(canonical_effect), 'canonical_variance': float(canonical_variance)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUT)
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    if not destination.is_relative_to(OUT):
        parser.error('Output must remain in this proposal-owned directory')
    destination.mkdir(parents=True, exist_ok=True)
    main(destination)
