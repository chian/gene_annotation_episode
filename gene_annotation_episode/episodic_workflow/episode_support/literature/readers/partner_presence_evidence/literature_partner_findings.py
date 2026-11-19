"""The investigation finding of a saved A107 partner sheet (``literature_partner_cells``): controlled features that
code reads from the sheet's cell rows, each with its validator (``INVESTIGATION_FINDING_FEATURES_a107.md`` sections
1 and 2.3, adopted by the owner on 19 November 2026).

A finding is the evidence type ``partner_requirement_experiment``, the sheet's reference, the partner and experiment
it binds, the fixed target correspondence of the cell, a direction computed by code (C6), and the numbers, counts and
fixed-vocabulary values of the cells (F1.a to F1.x). A nullable value is omitted when the cell holds ``null``. No
model-written text: the assessment's question, conclusion and limitations stay in the sheet, inside the Episode that
saved it. Agreement over the sheets an Episode holds is three counts (F1.y to F1.aa); sheets are listed side by side
and never combined into one score.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import (
    CHECK_REASONS, NATIVE_UNITS, REASONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.partner_presence_evidence.literature_assay_inputs import (
    SOURCE_KINDS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import (
    CELLS, LiteraturePartnerRepository)

EVIDENCE_TYPE = 'partner_requirement_experiment'
DIRECTIONS = ('support', 'opposition', 'measured_neutral', 'unknown')
CORRESPONDENCE = ('established', 'unresolved', 'not_evaluated')
STATUSES = ('populated', 'bounded', 'unavailable')
CHECKS = ('matched', 'different', 'unresolved')
PARTNER_STATES = ('present', 'absent', 'unreported', 'no_arm')
SPREAD_KINDS = ('SD', 'SEM', 'CI', 'unspecified', 'unreported', 'no_arm')
ORIGINS = ('reported', 'graph_derived', 'synthetic', 'derived')
RATE_CELLS = ('reference_rate', 'omitted_rate', 'addback_rate')

# name -> (validator, required): ('number', low, high), ('count', high), ('choice', options), ('refs', most)
FEATURES = {
    'evidence_type': (('choice', (EVIDENCE_TYPE,)), True),
    'sheet_refs': (('refs', 1), True),
    'partner_refs': (('refs', 1), True),
    'target_correspondence': (('choice', CORRESPONDENCE), True),
    'direction': (('choice', DIRECTIONS), True),
    'partner_loss_fraction': (('number', -math.inf, math.inf), False),
    'partner_loss_fraction_status': (('choice', STATUSES), True),
    'partner_loss_fraction_lower': (('number', -math.inf, math.inf), False),
    'partner_loss_fraction_upper': (('number', -math.inf, math.inf), False),
    'partner_loss_unavailable_reason': (('choice', REASONS), False),
    'addback_fraction': (('number', -math.inf, math.inf), False),
    'restored_reference_fraction': (('number', -math.inf, math.inf), False),
    'reference_rate_unit': (('choice', NATIVE_UNITS), False),
    'reference_omitted_check': (('choice', CHECKS), True),
    'reference_omitted_check_reason': (('choice', CHECK_REASONS), False),
    'differing_condition_count': (('count', None), True),
    'addback_omitted_check': (('choice', CHECKS), True),
    'observed_arm_count': (('count', 3), True),
    'omitted_partner_state': (('choice', PARTNER_STATES), True),
    'addback_partner_state': (('choice', PARTNER_STATES), True),
    'conditions_complete_arm_count': (('count', 3), True),
    'reference_spread_kind': (('choice', SPREAD_KINDS), True),
    'reference_spread_magnitude': (('number', 0, math.inf), False),
    'omitted_spread_kind': (('choice', SPREAD_KINDS), True),
    'omitted_spread_magnitude': (('number', 0, math.inf), False),
    'value_origin': (('choice', ORIGINS), False),
    'source_kind': (('choice', SOURCE_KINDS), True),
    'experiment_refs': (('refs', 1), True),
    'function_refs': (('refs', 1), True),
}
MEANINGS = {
    'evidence_type': 'The A107 evidence type: partner_requirement_experiment (one literature partner component sheet)',
    'sheet_refs': 'The saved partner sheet (one reference)',
    'partner_refs': 'The partner reference record the sheet binds (none when the source names none)',
    'target_correspondence': "The cell's fixed target correspondence (not_evaluated on a literature partner sheet)",
    'direction': ('support when the reference/omitted comparison is matched and the partner loss fraction (or its '
                  'lower bound) is above 0; opposition when matched and the loss fraction is at most 0; unknown '
                  'otherwise'),
    'partner_loss_fraction': 'Partner loss over reference rate, dimensionless (negative: the rate rose without the '
                             'partner); absent when the cell holds no value',
    'partner_loss_fraction_status': 'Whether the partner loss fraction cell is populated, bounded or unavailable',
    'partner_loss_fraction_lower': 'Lower end of the conditional censor domain of the loss fraction (not a confidence '
                                   'interval); absent unless bounded',
    'partner_loss_fraction_upper': 'Upper end of the conditional censor domain of the loss fraction (not a confidence '
                                   'interval); absent unless bounded',
    'partner_loss_unavailable_reason': 'The fixed reason the loss fraction cell is unavailable; absent otherwise',
    'addback_fraction': 'Addback gain over partner loss, dimensionless; absent when the cell holds no value',
    'restored_reference_fraction': 'Addback gain over reference rate, dimensionless; absent when the cell holds no '
                                   'value',
    'reference_rate_unit': 'The native unit of the reference rate cell; absent when unreported',
    'reference_omitted_check': 'Whether the reference and omitted arms are a matched comparison',
    'reference_omitted_check_reason': 'The fixed reason the reference/omitted comparison is not matched; absent when '
                                      'matched',
    'differing_condition_count': 'Nonpartner condition factors that differ between the reference and omitted arms',
    'addback_omitted_check': 'Whether the addback and omitted arms are a matched comparison',
    'observed_arm_count': 'Rate cells (reference, omitted, addback) that are not unavailable',
    'omitted_partner_state': 'Partner state of the omitted arm (no_arm when the sheet has none)',
    'addback_partner_state': 'Partner state of the addback arm (no_arm when the sheet has none)',
    'conditions_complete_arm_count': 'Arms whose nonpartner condition coverage is complete',
    'reference_spread_kind': 'Reported spread kind of the reference arm; SD, SEM and CI are distinct',
    'reference_spread_magnitude': 'Reported spread magnitude of the reference arm, in its rate unit; absent when '
                                  'unreported',
    'omitted_spread_kind': 'Reported spread kind of the omitted arm; SD, SEM and CI are distinct',
    'omitted_spread_magnitude': 'Reported spread magnitude of the omitted arm, in its rate unit; absent when '
                                'unreported',
    'value_origin': 'How the reference rate value was obtained; absent when no value',
    'source_kind': 'The kind of source the operands were read from',
    'experiment_refs': 'The experiment reference the sheet binds (none when the source identifies none)',
    'function_refs': 'The function term the source ties to the partner (none when the source names none)',
}
AGREEMENT = {
    'matched_sheet_count': 'Sheets whose reference/omitted comparison is matched',
    'matched_loss_sheet_count': 'Of those, sheets whose partner loss fraction is above 0',
    'distinct_experiment_count': 'Distinct experiments over the matched sheets (independent experiments, not sheets)',
}


def validate_features(features):
    """Each feature against its validator; a required feature present, a bound pair ordered. A violation raises
    ``ValueError``."""
    if not set(features) <= set(FEATURES) or not {name for name, (_, required) in FEATURES.items() if required} <= set(features):
        raise ValueError('partner_finding_features_mismatch')
    for name, value in features.items():
        rule = FEATURES[name][0]
        if rule[0] == 'number':
            valid = type(value) in (int, float) and math.isfinite(value) and rule[1] <= value <= rule[2]
        elif rule[0] == 'count':
            valid = type(value) is int and value >= 0 and (rule[1] is None or value <= rule[1])
        elif rule[0] == 'choice':
            valid = value in rule[1]
        else:
            valid = type(value) is list and len(value) <= rule[1] and all(type(item) is str for item in value)
        if not valid:
            raise ValueError('partner_finding_feature_invalid:' + name)
    if 'partner_loss_fraction_lower' in features and features['partner_loss_fraction_lower'] > features.get(
            'partner_loss_fraction_upper', math.inf):
        raise ValueError('partner_finding_bounds_unordered')
    return features


def _some(features, name, value):
    if value is not None:
        features[name] = value


def _refs(value):
    return [] if value is None else [value]


def direction(features):
    """C6: computed by code from the matched check and the loss fraction (or its lower bound when bounded)."""
    if features['reference_omitted_check'] != 'matched':
        return 'unknown'
    loss = features.get('partner_loss_fraction')
    if loss is None and features['partner_loss_fraction_status'] == 'bounded':
        lower = features.get('partner_loss_fraction_lower')
        return 'support' if lower is not None and lower > 0 else 'unknown'
    if loss is None:
        return 'unknown'
    return 'support' if loss > 0 else 'opposition'


def sheet_features(reader, sheet_ref):
    """The features of one sheet this Episode saved, read from its cell rows."""
    cells = {row['component']: row['cell'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    loss, gain, reference = cells['partner_loss_fraction'], cells['addback_gain'], cells['reference_rate']
    check = cells['partner_loss']['comparison_checks']['reference_omitted']
    arms = reference['arm_metadata']
    features = {'evidence_type': EVIDENCE_TYPE, 'sheet_refs': [sheet_ref], 'partner_refs': _refs(reference['partner_ref']),
                'target_correspondence': reference['target_correspondence'],
                'partner_loss_fraction_status': loss['status'],
                'reference_omitted_check': check['status'],
                'differing_condition_count': len(check['differing_factor_refs']),
                'addback_omitted_check': gain['comparison_checks']['addback_omitted']['status'],
                'observed_arm_count': sum(cells[name]['status'] != 'unavailable' for name in RATE_CELLS),
                'omitted_partner_state': 'no_arm' if arms['omitted'] is None else arms['omitted']['partner_state'],
                'addback_partner_state': 'no_arm' if arms['addback'] is None else arms['addback']['partner_state'],
                'conditions_complete_arm_count': sum(arm is not None and arm['condition_coverage'] == 'complete'
                                                     for arm in arms.values()),
                'reference_spread_kind': 'no_arm' if arms['reference'] is None else arms['reference']['spread']['kind'],
                'omitted_spread_kind': 'no_arm' if arms['omitted'] is None else arms['omitted']['spread']['kind'],
                'source_kind': reference['source_kind'],
                'experiment_refs': _refs(reference['experiment_ref']),
                'function_refs': _refs(reference['function_ref'])}
    _some(features, 'partner_loss_fraction', loss['value'])
    if loss['status'] == 'bounded':
        _some(features, 'partner_loss_fraction_lower', loss['lower'])
        _some(features, 'partner_loss_fraction_upper', loss['upper'])
    _some(features, 'partner_loss_unavailable_reason', loss['unavailable_reason'])
    _some(features, 'addback_fraction', cells['addback_fraction']['value'])
    _some(features, 'restored_reference_fraction', cells['restored_reference_fraction']['value'])
    _some(features, 'reference_rate_unit', reference['unit'] if reference['unit'] in NATIVE_UNITS else None)
    _some(features, 'reference_omitted_check_reason', check['unavailable_reason'])
    if arms['reference'] is not None:
        _some(features, 'reference_spread_magnitude', arms['reference']['spread']['magnitude'])
    if arms['omitted'] is not None:
        _some(features, 'omitted_spread_magnitude', arms['omitted']['spread']['magnitude'])
    _some(features, 'value_origin', reference['origin'])
    features['direction'] = direction(features)
    return validate_features(features)


POPULATION_TOOLS = ('literature_partner_populate', 'literature_partner_source_populate')


def produced_sheet_refs(outcomes):
    """The sheets the completed grader units among ``outcomes`` saved, in unit order (the view's own record of its
    work, so that a summary is a function of the view: on a replay the reader may already hold later products)."""
    return [outcome['outcome']['result']['sheet_ref'] for outcome in outcomes
            if outcome['kind'] == 'tool' and outcome['tool'] in POPULATION_TOOLS
            and outcome['outcome']['status'] == 'completed']


def current_sheet_features(reader, outcomes):
    """The features of each current sheet the units of ``outcomes`` saved, in the order the sheets were first saved."""
    produced = set(produced_sheet_refs(outcomes))
    return [sheet_features(reader, ref) for ref in LiteraturePartnerRepository(reader).current_sheet_refs()
            if ref in produced]


def merged_sheet_features(own, returned):
    """This Episode's own sheets and the sheets its children returned, one entry per sheet (first seen kept): sheets
    are listed side by side, never combined."""
    result = {}
    for features in (*own, *returned):
        result.setdefault(features['sheet_refs'][0], features)
    return list(result.values())


def agreement(sheets):
    """F1.y to F1.aa over the sheets an Episode holds: counts, never a combined score."""
    matched = [features for features in sheets if features['reference_omitted_check'] == 'matched']
    return {'matched_sheet_count': len(matched),
            'matched_loss_sheet_count': sum(features.get('partner_loss_fraction', 0) > 0 for features in matched),
            'distinct_experiment_count': len({ref for features in matched for ref in features['experiment_refs']})}
