"""Build declarative fixtures/expected arithmetic, not a scientific reader."""
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = 'source_' + 'a' * 24
TEXT_SOURCE = 'source_' + 'b' * 24
VIEW = 'image_view_' + 'c' * 24
VIEW2 = 'image_view_' + 'd' * 24
FIELDS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
    'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment', 'condition',
    'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')


def image(quote, *, reference=False, view=VIEW):
    return {'kind': 'image', 'view_ref': view,
            'region': [110, 40, 180, 65] if reference else [10, 40, 80, 65], 'quote': quote}


def unknown():
    return {'status': 'unknown', 'value': None, 'witnesses': []}


def visual(label, denominator='1.00', *, identity='visual1', state='exact', relation='supported'):
    witness = image(label)
    return {'representation_id': identity, 'kind': 'visual_signal_pair',
        'selection': {'reading_state': state, 'candidates': [{'numerator': witness,
            'denominator': image(denominator, reference=True)}] if state != 'unreadable' else [],
            'fragments': [] if state != 'unreadable' else [{'view_ref': VIEW,
                'region': [10, 40, 80, 65], 'raw_fragment': None}],
            'signal_scale': {'value': 'supported', 'witnesses': [witness]}},
        'comparison_relation': {'value': relation, 'witnesses': [witness] if relation != 'unknown' else []},
        'physical_measurement': unknown(), 'reference_measurement': unknown()}


def request(rows):
    return {'version': 'relative_signal_source_selection_v2', 'source_ref': SOURCE,
        'comparison': {name: unknown() for name in FIELDS}, 'representations': rows}


def cell(value=None, candidates=(), *, reason=None, status='unavailable', origin='derived', unit='fraction', domains=()):
    return {'value': value, 'value_candidates': list(candidates), 'reported_domains': list(domains),
        'unit': unit, 'status': status, 'origin': origin, 'formula': 'declared example arithmetic',
        'unavailable_reason': reason, 'conditional_on': ['source_comparison_interpretation']}


def unavailable_cells():
    return {'calibrated_amount_ratio': cell(reason='calibrated_amount_conversion_unimplemented'),
        'amount_adjusted_effect': cell(reason='functional_response_conversion_unimplemented', unit=None),
        'source_profile_log_ratio': cell(reason='observation_model_unimplemented', unit='dimensionless'),
        'source_signed_index': cell(reason='observation_model_unimplemented', origin='proposed', unit='dimensionless')}


def sheet(*, ratio=None, candidates=(), reason=None, conflict=False, resolved=False, complete=False, domains=None):
    # Only declared expected numbers are transformed; this does not read,
    # authenticate, classify or reconcile any source/selection.
    status = 'populated' if ratio is not None else 'conflicting' if conflict and resolved else 'unavailable'
    differences = [float(Fraction(str(x)) - 1) for x in candidates]
    logs = [math.log(x) for x in candidates if x > 0]
    cells = {'reported_ratio': cell(ratio, candidates, reason=reason, status=status),
        'difference_from_reference': cell(float(Fraction(str(ratio)) - 1) if ratio is not None else None,
            differences, reason=reason, status=status),
        'log_reported_ratio': cell(math.log(ratio) if ratio is not None and ratio > 0 else None,
            logs, reason='zero_reported_ratio' if ratio == 0 else reason,
            status='unavailable' if ratio == 0 else status, unit='dimensionless'), **unavailable_cells()}
    for name, values in (domains or {}).items():
        cells[name]['reported_domains'] = values
    return {'version': 'relative_signal_sheet_v2', 'scope': 'reported_relative_signal',
        'cells': cells, 'selected_roster_resolved': resolved, 'point_candidate_set_complete': complete,
        'known_source_conflict': conflict, 'independent_preparation_count': None, 'annotation_credit': None}


def domain(lower, upper, *, lower_infinite=False, upper_infinite=False, lower_closed=True, upper_closed=True):
    return {'lower': lower, 'lower_infinite': lower_infinite, 'lower_closed': lower_closed,
        'upper': upper, 'upper_infinite': upper_infinite, 'upper_closed': upper_closed,
        'meaning': 'reported_estimate_domain'}


def main():
    examples = []
    def add(name, selected, expected, explanation):
        examples.append({'name': name, 'evidence_class': 'constructed selection and expected arithmetic; no native operation',
            'selection': selected, 'expected_sheet': expected, 'scientific_limit': explanation})
    add('visual_only', request([visual('0.60')]),
        sheet(ratio=.6, candidates=[.6], resolved=True, complete=True),
        'No JATS percentage is required. Actual source/view receipts still need future native execution.')
    prose = {'representation_id': 'prose1', 'kind': 'jats_percent',
        'selection': {'source_ref': TEXT_SOURCE, 'section_id': 's1', 'paragraph_index': 0,
            'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'},
        'comparison_relation': {'value': 'supported', 'witnesses': [image('0.60')]},
        'physical_measurement': unknown(), 'reference_measurement': unknown()}
    add('mixed_same_reported_quantity', request([prose, visual('0.60')]),
        sheet(ratio=.6, candidates=[.6], resolved=True, complete=True),
        'Fixture prose would report60%. No independence or preparation count follows from two representations.')
    add('linked_representation_conflict', request([visual('1.00'), visual('1.12', identity='visual2')]),
        sheet(candidates=[1.,1.12], reason='source_representation_conflict', conflict=True, resolved=True, complete=True),
        'Only when both rows are witnessed as the same reported quantity; these are alternatives, not confidence limits.')
    add('known_plus_unreadable', request([visual('0.64'), visual('unreadable', identity='visual2', state='unreadable')]),
        sheet(candidates=[.64], reason='unreadable_transcription'),
        'Do not drop the unresolved reading and silently report a complete0.64 scalar.')
    ambiguous = visual('0.60', state='ambiguous')
    ambiguous['selection']['candidates'].append({'numerator': image('0.80'), 'denominator': image('1.00', reference=True)})
    add('ambiguous_numeral', request([ambiguous]), sheet(candidates=[.6,.8], reason='ambiguous_transcription'),
        'Alternative readings of one label do not automatically establish inconsistent experiments.')
    add('printed_zero', request([visual('0')]), sheet(ratio=0., candidates=[0.], resolved=True, complete=True),
        'Reported signal zero is not proof of zero molecules. log point remains unavailable; no pseudocount.')
    log_upper = math.nextafter(math.log(.1), math.inf)
    censor_domains = {'reported_ratio': [domain(0.,.1,upper_closed=False)],
        'difference_from_reference': [domain(-1.,-.9,upper_closed=False)],
        'log_reported_ratio': [domain(None,log_upper,lower_infinite=True,lower_closed=False,upper_closed=False)]}
    add('printed_upper_limit', request([visual('<0.10')]),
        sheet(reason='reported_limit_not_point', resolved=True, domains=censor_domains),
        'Reported-estimate domains, not a true-amount confidence bound. Finite log export must enclose rounding outward.')
    add('reported_ND_without_limit', request([visual('ND')]), sheet(reason='unsupported_expression'),
        'Retain exact ND spelling; no inferred numerical threshold, exact zero or expansion of its meaning.')
    add('zero_reference', request([visual('0.60', '0')]), sheet(reason='positive_denominator_not_established'),
        'Both printed primitive values survive; no invented positive reference.')
    scale = visual('0.60'); scale['selection']['signal_scale']={'value':'different','witnesses':[image('0.60')]}
    add('known_different_signal_scales', request([scale]), sheet(reason='signal_scales_differ'),
        'Known different scales are a comparability failure, not contradictory source reports; preserve primitives.')
    duplicate = visual('0.60', identity='copy_of_visual1')
    add('exact_source_duplicate', request([visual('0.60'), duplicate]),
        sheet(ratio=.6,candidates=[.6],resolved=True,complete=True),
        'Exact original reading locators deduplicate arithmetic; physical/biological preparation count remains unknown.')
    add('different_reported_quantities', request([visual('0.60'), visual('0.80',identity='other_experiment',relation='different')]),
        sheet(candidates=[.6],reason='different_reported_quantities'),
        'Distinct experiments are not contradictory source representations.0.80 survives its native row, not this comparison candidate set.')
    for name, value in [('EXAMPLES_004.json', examples), ('SOURCE_GROUNDED_CELLS_004.json', {
        'evidence_class': 'inherited root-verified YeaG facts; no067 primary read or native execution',
        'source': 'a105_gel_case_parent_review_064/COMPONENT_CONVERSION_001.md',
        'ratios': {'K116A':.64,'R232A':.48,'Y382stop':.96}, 'K426A_candidates':[1.,1.12],
        'axis_bearing': 'principally A106 expression comparability; no direct A105 activity or calibrated amount',
        'native_view_refs_for_new_api': None, 'new_api_execution': False,
        'synthetic_conditional_examples': {'replacement_per_amount': float(Fraction(20,100)/Fraction(64,100)),
            'coexistence_variant_response': float((Fraction(68,100)-Fraction(60,100))/Fraction(40,100))}})]:
        with (HERE/name).open('x') as stream:
            json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps({'proposed_synthetic_examples':len(examples),'source_grounded_fact_table':'inherited_root_only',
                      'application_or_reader_execution':False,'native_view_receipts_created':0}))


if __name__ == '__main__':
    main()
