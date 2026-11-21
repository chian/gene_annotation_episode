"""Chunks of text for the spectro_direct extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form (made-up molecules DX-12, an enzyme, and DX-S4,
its substrate); ``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree, micro, epsilon and multiplication
signs) so byte offsets differ from character offsets.

``REAL`` is real: the Results paragraph on the steady-state kinetics of the flavin reductase ThdF of 'The NADH-dependent flavin reductase ThdF follows an
ordered sequential mechanism though crystal structures reveal two FAD molecules in the active site' (J Biol Chem 2025, doi 10.1016/j.jbc.2024.108128,
PMC11795597, PMID 39725031, open access, CC BY 4.0), found through Europe PMC full-text XML (/europepmc/webservices/rest/PMC11795597/fullTextXML). The
paragraph is whole and verbatim (one <p> of the XML, nothing removed), with only the markup removed (the italic K of KM and k of kcat and their subscripts,
which read 'KM' and 'kcat' as plain text). The publisher's non-breaking spaces (U+00A0) and the minus sign (U+2212) of 's-1' and 'min-1' are kept as they are.
It states, for ThdF, the Michaelis constants for NADH (19.5 uM) and for FAD (0.34 uM) and the turnover number kcat of 0.21 +- 0.08 s-1 (12.7 +- 4.9 min-1) for
FAD; it also cites the Michaelis constants and kcat values of three other flavin reductases (BorF, AbeF, PrnF), which are NOT the enzyme of the paragraph. It
states no assay method (the paper's Methods are other paragraphs), no control, no wavelength, no extinction coefficient, no enzyme or substrate concentration
of the measurement, no replicate count, no spread kind (the plus-minus sign is not named a standard error or deviation), no catalytic efficiency and no
specific activity. The values of the three other enzymes are the distractors of the overreach check.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_extraction import (
    SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_record import UNITS

PAPER_ID = 'PMC11795597'
SYNTHETIC = (
    'The enzyme DX-12 (48 kDa subunit) was purified to homogeneity and its activity on the native substrate DX-S4 was measured in a continuous '
    'spectrophotometric assay at 25 °C. The oxidation of NADH was followed at 340 nm with ε = 6.22 mM^-1 cm^-1, and the absorbance never rose above 0.9 AU. '
    'Reactions contained 20 nM DX-12 and 200 µM DX-S4. Initial rates were taken from the linear part of the progress curve, where less than 5% of the substrate '
    'had been consumed. The rate was proportional to the amount of enzyme over the range tested. A control without enzyme, a control with heat-inactivated DX-12 '
    'and a control without DX-S4 showed no change in absorbance. The substrate was varied at 10, 20, 50, 100, 200, 500 and 1000 µM and the Michaelis constant was '
    'Km = 40 µM. The active-site concentration was determined by active-site titration. The product was identified by HPLC as DX-P7. The catalytic efficiency '
    'kcat/Km was 5.0 × 10^5 M^-1 s^-1 (standard error 0.4 × 10^5 M^-1 s^-1), the turnover number kcat was 20 s^-1 (standard error 1.5 s^-1), and the specific '
    'activity was 25 U/mg (standard error 2 U/mg). The rate was 150-fold over the no-enzyme control (standard error 12-fold). The values are means of n = 3 '
    'independent experiments, with the standard error shown. The activity was clearly detected above the control.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'catalytic_efficiency': (500000, 'M^-1 s^-1', 'kcat/Km was 5.0 × 10^5 M^-1 s^-1'),
    'catalytic_efficiency_spread': (40000, 'M^-1 s^-1', 'standard error 0.4 × 10^5 M^-1 s^-1'),
    'turnover': (20, 's^-1', 'kcat was 20 s^-1'),
    'turnover_spread': (1.5, 's^-1', 'standard error 1.5 s^-1'),
    'specific_activity': (25, 'U/mg', 'specific activity was 25 U/mg'),
    'specific_activity_spread': (2, 'U/mg', 'standard error 2 U/mg'),
    'rate_over_control': (150, 'fold', '150-fold over the no-enzyme control'),
    'rate_over_control_spread': (12, 'fold', 'standard error 12-fold'),
    'km': (40, 'uM', 'Km = 40 µM'),
    'substrate_concentration': (200, 'uM', '200 µM DX-S4'),
    'enzyme_concentration': (20, 'nM', '20 nM DX-12'),
    'substrate_consumed_percent': (5, 'percent', 'less than 5% of the substrate had been consumed'),
    'wavelength': (340, 'nm', 'at 340 nm'),
    'extinction_coefficient': (6.22, 'mM^-1 cm^-1', 'ε = 6.22 mM^-1 cm^-1'),
    'absorbance_max': (0.9, 'AU', 'never rose above 0.9 AU'),
    'enzyme_mass': (48, 'kDa', '48 kDa subunit'),
    'replicate_count': (3, 'count', 'n = 3 independent experiments'),
    SERIES: ([10, 20, 50, 100, 200, 500, 1000], 'uM', 'varied at 10, 20, 50, 100, 200, 500 and 1000 µM'),
    SPREAD_KIND: ('standard_error', None, 'with the standard error shown'),
    'no_enzyme_control': ('yes', None, 'A control without enzyme'),
    'inactive_enzyme_control': ('yes', None, 'a control with heat-inactivated DX-12'),
    'no_substrate_control': ('yes', None, 'a control without DX-S4'),
    'rate_proportional_to_enzyme': ('yes', None, 'The rate was proportional to the amount of enzyme'),
    'linear_progress_curve': ('yes', None, 'taken from the linear part of the progress curve'),
    'active_site_concentration_determined': ('yes', None, 'determined by active-site titration'),
    'native_substrate': ('yes', None, 'on the native substrate DX-S4'),
    'purified_enzyme': ('yes', None, 'was purified to homogeneity'),
    'product_identified': ('yes', None, 'The product was identified by HPLC as DX-P7'),
    'independent_replicates': ('yes', None, 'n = 3 independent experiments'),
    'activity_detected_above_control': ('yes', None, 'The activity was clearly detected above the control'),
}

NB = ' '      # the publisher's non-breaking space, kept in the real paragraph
MINUS = '−'   # the publisher's minus sign of s-1 and min-1
REAL = (
    f'The KM value for NADH (19.5{NB}μM) is similar, that for FAD (0.34{NB}μM) is about four to 10 times lower than other kinetically studied short-chain flavin '
    f'reductases such as BorF (KM, FAD: 1.3{NB}μM; KM, NADH: 27{NB}μM) (9), AbeF (KM, FAD: 1.5{NB}μM; KM, NADH: 26{NB}μM) (9), or PrnF (KM, FAD: 3.2{NB}μM; '
    f'KM, NADH: 43{NB}μM) (34). The kcat value of ThdF is strikingly low with only 0.21{NB}{NB}±{NB}0.08{NB}s{MINUS}1 (12.7{NB}{NB}±{NB}4.9{NB}min{MINUS}1) for FAD. '
    f'For comparison, the kcat values for either substrate are around 55{NB}s{MINUS}1 for BorF, 100{NB}s{MINUS}1 for AbeF, and 65{NB}s{MINUS}1 in case of PrnF.')

# field -> (value, unit, quote) of the real paragraph, for ThdF: the Michaelis constant for NADH and the kcat for FAD with its plus-minus value.
REAL_STATED = {
    'km': (19.5, 'uM', f'KM value for NADH (19.5{NB}μM)'),
    'turnover': (0.21, 's^-1', f'0.21{NB}{NB}±{NB}0.08{NB}s{MINUS}1'),
    'turnover_spread': (0.08, 's^-1', f'0.21{NB}{NB}±{NB}0.08{NB}s{MINUS}1'),
}
# What the paragraph clearly states by the fields' general meaning, for ThdF: both Michaelis constants (NADH and FAD), the kcat and its plus-minus value in the two
# units the paragraph gives. The values of BorF, AbeF and PrnF are not the enzyme's and are not allowed.
REAL_ALLOWED = {
    'km': {(19.5, 'uM'), (0.34, 'uM')},
    'turnover': {(0.21, 's^-1'), (12.7, 'min^-1')},
    'turnover_spread': {(0.08, 's^-1'), (4.9, 'min^-1')},
}

# The expected identity of the model run (normalized: casefold, whitespace collapsed). The synthetic passage is about the enzyme DX-12 and its substrate DX-S4; the
# real paragraph is about ThdF (it names two substrates, NADH and FAD, so no single partner is expected: a real partner None is not checked).
SYNTHETIC_TARGET = 'dx-12'
SYNTHETIC_PARTNER = 'dx-s4'
REAL_EXPECTED_TARGET = 'thdf'
REAL_EXPECTED_PARTNER = None


def answer_from(chunk, stated, support=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. ``support`` maps a field to a support other than direct."""
    support = support or {}
    answer = {}
    for name in field_names():
        carries_unit = name in UNITS
        if name in stated:
            value, unit, quote = stated[name]
            answer[name] = {'status': 'stated', 'value': value, 'quote': quote, 'support': support.get(name, 'direct'), 'reason': None,
                            **({'unit': unit} if carries_unit else {})}
        else:
            answer[name] = {'status': 'unavailable', 'value': None, 'quote': None, 'support': None,
                            'reason': 'not_stated_in_passage', **({'unit': None} if carries_unit else {})}
    return answer


def synthetic_answer():
    return answer_from(SYNTHETIC, SYNTHETIC_STATED)


def real_answer():
    return answer_from(REAL, REAL_STATED)
