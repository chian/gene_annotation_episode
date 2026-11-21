"""Chunks of text for the radioligand extraction tests, and the answer an extractor that read them correctly would give.

``SYNTHETIC`` is an explicitly synthetic passage (not a publication) that states every field of the form;
``synthetic_answer`` is the answer that reads it correctly. It contains multi-byte characters (degree and micro signs) so byte
offsets differ from character offsets.

``REAL`` is real: the Methods paragraph on the analysis of the saturation and competition binding data of 'Structural and functional
determination of peptide versus small molecule ligand binding at the apelin receptor' (Nature Communications 15, 10714, 2024, doi
10.1038/s41467-024-55381-w, PMC11680790, PMID 39730334, open access, CC BY 4.0), as the publisher's XML gives the paragraph's own text
(a thin space U+2009 between each number and its unit, and the reference number '58' that follows 'Biosoft)' as plain text). The
paragraph is whole (one paragraph in the XML, nothing removed). It says how the data of a radioligand binding experiment were
analysed: a saturation analysis (EBDA and LIGAND) giving the receptor affinity KD and the receptor density Bmax, a Bmax calculated
with 'the known KD value of the radiolabel (0.076 nM)', its 'known specific activity' (2200 Ci/mmol) and a protein concentration of
1 mg/mL, a non-linear 'one site-specific binding with Hill slope' fit of the saturation data, a non-linear one-site competition fit
with 'constraints for the radiolabel concentration (0.1 nM) and KD (0.076 nM)', and a Ki of a competing ligand calculated with the
Cheng-Prusoff equation. It gives no measured KD, Bmax, IC50 or Ki value of the experiment itself, no isotope, no separation method,
no preparation type, no incubation time or temperature, no non-specific binding definition (so no Kd of an unlabelled displacer and no statement that it is the unlabelled radioligand), no dissociation
rate, no replicate count and no statement of depletion (or of a correction for it), equilibrium, radioligand purity, filter binding or the wash.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_extraction import (
    ASSAY_FORMAT, FIT_MODEL, ISOTOPE, PREPARATION_TYPE, SEPARATION, SERIES, SPREAD_KIND, field_names)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import UNITS

PAPER_ID = 'PMC11680790'
REAL = (
    'Saturation binding data were analysed using the EBDA and LIGAND components of the KELL (Kinetic, EBDA, Ligand, Lowry) software package (Biosoft)58 to generate receptor affinity (KD) and receptor density (Bmax) values. '
    'Bmax values, in fmol/mg, were calculated using the known KD value of the radiolabel (0.076 nM), known specific activity of the radiolabel (2200 Ci/mmol), and concentration of protein used (1 mg/mL). '
    'Saturation data were presented using the nonlinear one site-specific binding with Hill slope model fitted by GraphPad Prism version 6.07 for Windows (GraphPad Software). '
    'Competition binding data were presented using the nonlinear one site Fit Ki [2] model fitted by GraphPad Prism, with constraints for the radiolabel concentration (0.1 nM) and KD (0.076 nM). '
    'The software was also used to calculate the binding affinity (Ki value) of competing ELA-11 ligand using the Cheng-Prusoff equation.')

SYNTHETIC = (
    'Binding of [3H]DX-17 to the DX receptor was measured in membranes of HEK293 cells at 25 °C. The assay was about the DX receptor and its ligand DX-17. [3H]DX-17 had a specific activity of 85 Ci/mmol, '
    'and 20 µg of membrane protein was used per tube. In a saturation experiment the membranes were incubated with [3H]DX-17 at 10 concentrations of '
    '0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6 and 51.2 nM for 60 min. The series ran from 0.1 nM to 51.2 nM. Non-specific binding was determined with '
    '1000 nM unlabelled DX-17, the cold form of [3H]DX-17 (its Kd was 2.0 nM), a 500-fold excess over the Kd, and was subtracted from the total binding to give the specific binding; at the highest '
    'concentration it was 25% of the total binding. The bound radioligand was separated from the free radioligand by rapid filtration through GF/B filters. '
    'Binding of [3H]DX-17 to the filters, measured without membranes, was negligible after the filters were pre-soaked in polyethylenimine, and the loss of '
    'bound radioligand during the 10 s ice-cold wash was considered and was below 5%. The radiochemical purity of [3H]DX-17 was checked by HPLC before each '
    'experiment. The binding was at equilibrium because an association time course reached a plateau within 60 min. The dissociation rate constant of '
    '[3H]DX-17 was 0.2 min⁻¹. Only 6% of the added radioligand was '
    'bound, so depletion of the free radioligand was avoided. In the competition experiment the free radioligand was measured in each tube, which corrected for depletion. The saturation data were fitted by non-linear regression with a one-site binding model, which '
    'gave a KD = 2.0 nM (standard error 0.2 nM), a Bmax of 1200 fmol/mg protein and a Hill slope of 1.0. In a competition experiment 1 nM [3H]DX-17 was '
    'displaced by an unlabelled ligand, which gave an IC50 of 7.5 nM; the Ki = 5.0 nM (standard error 0.3 nM) was calculated with the Cheng-Prusoff equation '
    'using the KD of [3H]DX-17 on the same membranes. Each condition was measured in 3 tubes, and 3 independent experiments were done on separate days with '
    'fresh membranes. The affinity was also measured by surface plasmon resonance.')

# field -> (value, unit, quote) for the synthetic passage: every field of the form.
SYNTHETIC_STATED = {
    'kd': (2.0, 'nM', 'a KD = 2.0 nM'),
    'bmax': (1200, 'fmol/mg', 'a Bmax of 1200 fmol/mg protein'),
    'ki': (5.0, 'nM', 'the Ki = 5.0 nM'),
    'ic50': (7.5, 'nM', 'an IC50 of 7.5 nM'),
    'hill_slope': (1.0, 'ratio', 'a Hill slope of 1.0'),
    'kd_spread': (0.2, 'nM', 'standard error 0.2 nM'),
    'ki_spread': (0.3, 'nM', 'standard error 0.3 nM'),
    'specific_activity': (85, 'Ci/mmol', 'a specific activity of 85 Ci/mmol'),
    'radioligand_concentration': (1, 'nM', '1 nM [3H]DX-17 was displaced'),
    'radioligand_range_lowest': (0.1, 'nM', 'ran from 0.1 nM'),
    'radioligand_range_highest': (51.2, 'nM', 'to 51.2 nM'),
    'receptor_amount': (20, 'ug', '20 µg of membrane protein'),
    'percent_bound': (6, 'percent', 'Only 6% of the added radioligand was bound'),
    'nonspecific_fraction': (25, 'percent', 'it was 25% of the total binding'),
    'nonspecific_ligand_concentration': (1000, 'nM', '1000 nM unlabelled DX-17'),
    'nonspecific_ligand_kd': (2.0, 'nM', 'its Kd was 2.0 nM'),
    'nonspecific_excess': (500, 'ratio', 'a 500-fold excess over the Kd'),
    'incubation_time': (60, 'min', 'for 60 min'),
    'dissociation_rate': (0.2, '1/min', 'dissociation rate constant of [3H]DX-17 was 0.2 min⁻¹'),
    'temperature': (25, 'C', 'at 25 °C'),
    'titration_point_count': (10, 'count', 'at 10 concentrations'),
    'technical_replicate_count': (3, 'count', 'measured in 3 tubes'),
    'replicate_count': (3, 'count', '3 independent experiments'),
    SERIES: ([0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2], 'nM', '0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6 and 51.2 nM'),
    ASSAY_FORMAT: ('saturation', None, 'In a saturation experiment'),
    ISOTOPE: ('tritium', None, 'Binding of [3H]DX-17 to the DX receptor'),
    SEPARATION: ('filtration', None, 'rapid filtration through GF/B filters'),
    PREPARATION_TYPE: ('membrane', None, 'measured in membranes of HEK293 cells'),
    SPREAD_KIND: ('standard_error', None, 'standard error 0.2 nM'),
    FIT_MODEL: ('one_site', None, 'with a one-site binding model'),
    'ligand_depletion_checked': ('yes', None, 'so depletion of the free radioligand was avoided'),
    'nonspecific_binding_determined': ('yes', None, 'Non-specific binding was determined with 1000 nM unlabelled DX-17'),
    'depletion_corrected': ('yes', None, 'the free radioligand was measured in each tube, which corrected for depletion'),
    'nonspecific_ligand_is_unlabelled_radioligand': ('yes', None, 'the cold form of [3H]DX-17'),
    'equilibrium_reached': ('yes', None, 'The binding was at equilibrium because an association time course reached a plateau within 60 min'),
    'radioligand_purity_checked': ('yes', None, 'The radiochemical purity of [3H]DX-17 was checked by HPLC'),
    'filter_binding_checked': ('yes', None, 'Binding of [3H]DX-17 to the filters, measured without membranes, was negligible'),
    'wash_dissociation_considered': ('yes', None, 'the loss of bound radioligand during the 10 s ice-cold wash was considered'),
    'nonlinear_fit_used': ('yes', None, 'fitted by non-linear regression'),
    'cheng_prusoff_applied_with_own_kd': ('yes', None, 'calculated with the Cheng-Prusoff equation using the KD of [3H]DX-17 on the same membranes'),
    'independent_experiments': ('yes', None, '3 independent experiments were done on separate days'),
    'single_estimate_method': ('no', None, 'also measured by surface plasmon resonance'),
}


# field -> (value, unit, quote) for the real passage: only what it states about the experiment it is about. The specific activity and the
# radiolabel concentration of the competition fit are stated with their numbers; the non-linear fit of the saturation data is stated in
# words. The KD (0.076 nM) is NOT in it: the passage cites it as the 'known' KD of the radiolabel, a property borrowed from elsewhere and
# not measured in the experiment described, so stating it is an overreach (owner's decision).
REAL_STATED = {
    'specific_activity': (2200, 'Ci/mmol', 'known specific activity of the radiolabel (2200 Ci/mmol)'),
    'radioligand_concentration': (0.1, 'nM', 'constraints for the radiolabel concentration (0.1 nM)'),
    'nonlinear_fit_used': ('yes', None, 'Saturation data were presented using the nonlinear one site-specific binding with Hill slope model'),
}
# What else a careful reader may also state from the real passage: nothing. The known KD of the radiolabel is cited, not measured. The Cheng-Prusoff equation is named and the radiolabel KD
# is a constraint of the competition fit, but the passage does not say the KD is that of the same radioligand on the same preparation;
# the fit model ('one site-specific binding with Hill slope') is neither plainly a one-site nor a Hill model; the protein
# concentration (1 mg/mL) is not an amount per assay. They are not in the allowed set (a model that states them is reported, not allowed).
REAL_MAY_ALSO_STATE = set()

# identity expectations (OWNER_DECISION 18); see check_identity in the leaf test
SYNTHETIC_TARGET = 'dx receptor'
SYNTHETIC_PARTNER = 'dx-17'
# The paragraph only describes data analysis: it never names the receptor ('receptor affinity') or the radiolabel; ELA-11 is a competing
# ligand with no named target. So no target and no partner.
REAL_EXPECTED_TARGET = None
REAL_EXPECTED_PARTNER = None


def answer_from(chunk, stated, support=None):
    """The answer that states ``stated`` (field -> (value, unit, quote)) and leaves every other field unavailable. Every stated
    field has support 'direct' unless ``support`` (field -> support) names a weaker one; an unavailable field has none."""
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


REAL_KD = (0.076, 'nM', 'known KD value of the radiolabel (0.076 nM)')     # a cited, not measured, KD: used only to test quote refusals


# The one quote of the real paragraph that is obviously weaker than the others: '0.1 nM' is given as a constraint of the fit ('constraints
# for the radiolabel concentration'), so the concentration of the experiment is stated only by implication.
REAL_SUPPORT = {'radioligand_concentration': 'implied'}


def real_answer():
    return answer_from(REAL, REAL_STATED, REAL_SUPPORT)
